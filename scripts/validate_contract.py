#!/usr/bin/env python3
"""Validate Reviewer JSON contracts. Never performs visual or narrative inference.

Requires jsonschema>=4.18. All schema references resolve locally, without network.
Usage: python validate_contract.py --input input.json [--output report.json]
       python validate_contract.py --state state.json
       python validate_contract.py --check-schemas
"""
import argparse
import importlib.util
from functools import lru_cache
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError as exc:
    raise SystemExit("Missing validation dependency: install jsonschema>=4.18 in your Python environment.") from exc

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
NAMES = ("review-input.schema.json", "review-output.schema.json", "persistent-visual-state.schema.json", "animatic-input.schema.json", "animatic-output.schema.json")
LEVEL = {"low": 0, "medium": 1, "high": 2, "critical": 3}
AREAS = ("current_shot_compliance", "cross_shot_continuity")


@lru_cache(maxsize=1)
def validators():
    documents = [json.loads((SCHEMAS / name).read_text(encoding="utf-8-sig")) for name in NAMES]
    registry = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in documents)
    result = {}
    for name, schema in zip(NAMES, documents):
        Draft202012Validator.check_schema(schema)
        result[name] = Draft202012Validator(schema, registry=registry)
    return result


def validate_schema(value, name):
    return [f"schema {name} /{'/'.join(map(str, e.absolute_path))}: {e.message}"
            for e in validators()[name].iter_errors(value)]


def areas(issue):
    return {issue["review_area"], *issue.get("related_review_areas", [])}


def expected_verdict(report):
    current = [i for i in report["issues"] if i["attribution"] == "current"]
    if any(LEVEL[i["severity"]] >= 2 for i in current):
        return "REGENERATE"
    if any(LEVEL[i["severity"]] >= 1 for i in current):
        return "REVISE"
    if any(LEVEL[u["potential_severity"]] >= 1 for u in report["uncertainties"]):
        return "REVISE"
    if any(i["attribution"] == "unresolved" or
           (i["attribution"] in ("previous", "next") and LEVEL[i["severity"]] >= 1)
           for i in report["issues"]):
        return "REVISE"
    return "PASS"


def evidence_nodes(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "evidence":
                for index, ev in enumerate(child):
                    yield f"{path}/evidence/{index}", ev
            else:
                yield from evidence_nodes(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from evidence_nodes(child, f"{path}/{index}")


def duplicates(items, key, label):
    seen, errors = set(), []
    for item in items:
        value = item[key]
        if value in seen:
            errors.append(f"duplicate {label}: {value}")
        seen.add(value)
    return errors


def validate_input(inp):
    if inp.get('review_mode') == 'animatic':
        return animatic_module().input_errors(inp, validate_schema)
    errors = validate_schema(inp, NAMES[0])
    if errors:
        return errors
    shots = [inp[k] for k in ("previous", "current", "next") if k in inp]
    errors += duplicates(shots, "shot_id", "shot_id")
    errors += duplicates([s["image"] for s in shots if s.get("image")], "image_id", "image_id")
    errors += duplicates(inp.get("assets", []), "asset_id", "asset_id")
    if "persistent_visual_state" in inp:
        errors += validate_state(inp["persistent_visual_state"])
        state = inp["persistent_visual_state"]
        if inp.get("next", {}).get("shot_id") == state["through_shot_id"]:
            errors.append("input persistent state is from the future next shot")
        if inp["current"]["shot_id"] == state["through_shot_id"]:
            errors.append("input state must precede current shot; use the pre-review state for a revision")
    return errors


def animatic_module():
    spec = importlib.util.spec_from_file_location('reviewer_animatic', Path(__file__).with_name('validate_animatic.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_state(state):
    errors = validate_schema(state, NAMES[2])
    if errors:
        return errors
    errors += duplicates(state["facts"], "fact_id", "fact_id")
    keys = set()
    for fact in state["facts"]:
        key = (fact["entity_id"], fact["property"], fact["scope"])
        if key in keys:
            errors.append(f"duplicate entity/property fact: {key}")
        keys.add(key)
        sources = {e["source_type"] for e in fact["evidence"]}
        if fact["basis"] in ("observed", "both") and "image" not in sources:
            errors.append(f"fact {fact['fact_id']} observed basis needs original image evidence, not circular state references")
        if fact["basis"] in ("specified", "both") and not sources.intersection(("shot_spec", "story", "asset")):
            errors.append(f"fact {fact['fact_id']} specified basis needs original authored evidence")
        if fact["basis"] == "specified" and fact["last_confirmed_at_shot_id"] is not None:
            errors.append(f"fact {fact['fact_id']} specified-only value cannot have last_confirmed image observation")
    return errors


def validate_pair(inp, out):
    if inp.get('review_mode') == 'animatic':
        return animatic_module().pair_errors(inp, out, validate_schema, validate_pair)
    errors = validate_input(inp) + validate_schema(out, NAMES[1])
    if errors:
        return errors
    errors += validate_state(out["persistent_visual_state"])
    current = inp["current"]
    sid = current["shot_id"]
    incoming = inp.get("persistent_visual_state", {})
    outgoing = out["persistent_visual_state"]
    old = {f["fact_id"]: f for f in incoming.get("facts", [])}
    new = {f["fact_id"]: f for f in outgoing["facts"]}
    facts = {**old, **new}
    slots = {k: inp[k] for k in ("previous", "current", "next") if k in inp}
    shot_ids = {s["shot_id"] for s in slots.values()}
    known_history = {f[k] for f in old.values() for k in ("established_at_shot_id", "last_confirmed_at_shot_id") if f[k]}
    known_history.update(v for k, v in incoming.items() if k in ("through_shot_id", "coverage_start_shot_id") and v)
    allowed_shots = shot_ids | known_history
    coverage = out["coverage"]
    if out["shot_id"] != sid or outgoing["through_shot_id"] != sid:
        errors.append("shot_id / through_shot_id must identify current shot")
    if outgoing["scene_id"] != current["scene_id"]:
        errors.append("output state scene_id must match current scene_id")
    errors += duplicates(out["issues"], "issue_id", "issue_id")
    errors += duplicates(out["uncertainties"], "finding_id", "finding_id")
    errors += duplicates(out.get("state_invalidations", []), "fact_id", "invalidated fact_id")
    invalidated = {entry["fact_id"] for entry in out.get("state_invalidations", [])}
    for fid in invalidated:
        if fid not in old:
            errors.append(f"invalidated fact_id not in incoming state: {fid}")
        elif not any(old[fid]["entity_id"] in u["entity_ids"] for u in out["uncertainties"]):
            errors.append(f"invalidated fact {fid} needs an uncertainty for its entity")
        if fid in new:
            errors.append(f"invalidated fact {fid} must not remain active")
    pairs = set()
    for check in out["visibility_checks"]:
        pair = check["fact_id"], check["shot_id"]
        if pair in pairs:
            errors.append(f"duplicate visibility check: {pair}")
        pairs.add(pair)
        if check["fact_id"] not in facts:
            errors.append(f"visibility fact_id unknown: {check['fact_id']}")
        if check["shot_id"] not in shot_ids:
            errors.append(f"visibility shot_id not supplied: {check['shot_id']}")
        if check["assessment"] == "contradiction" and (check["expected_visibility"] != "yes" or
                                                       check["observed_visibility"] == "unassessable"):
            errors.append("visibility contradiction requires expected yes and an assessable property")

    # Sources are closed over supplied artifacts and attributed incoming evidence.
    sources = {}
    image_slots = {}
    historical = {(e["source_type"], e["source_ref"], e.get("source_version"))
                  for _, e in evidence_nodes(incoming)}
    for slot, shot in slots.items():
        inspected = coverage[f"{slot}_image_inspected"]
        if inspected and not shot.get("image"):
            errors.append(f"coverage {slot}_image_inspected has no supplied image")
        if shot.get("image"):
            image_id = shot["image"]["image_id"]
            sources[("image", image_id)] = None
            image_slots[image_id] = slot
        if shot["shot_spec"] is not None:
            sources[("shot_spec", shot["shot_id"] + "_SPEC")] = shot["spec_version"]
    for slot in ("previous", "next"):
        if slot not in slots and coverage[f"{slot}_image_inspected"]:
            errors.append(f"coverage {slot}_image_inspected has no supplied shot")
    for asset in inp.get("assets", []):
        sources[("asset", asset["asset_id"])] = asset["version"]
    if inp.get("story_context"):
        sources[("story", "story_context")] = None
    for f in old.values():
        sources[("persistent_state", f["fact_id"])] = None
    for path, ev in evidence_nodes(out):
        key = (ev["source_type"], ev["source_ref"])
        historic_key = (*key, ev.get("source_version"))
        if key not in sources and historic_key not in historical:
            errors.append(f"{path} unknown source_ref: {key}")
        quarantined_citation = path.startswith(("/uncertainties/", "/state_invalidations/")) and historic_key in historical
        if key in sources and key[0] in ("shot_spec", "asset") and sources[key] is not None and ev.get("source_version") is None and not quarantined_citation:
            errors.append(f"{path} source_version required for known version: {key}")
        if key in sources and ev.get("source_version") is not None and sources[key] != ev["source_version"] and not quarantined_citation:
            errors.append(f"{path} source_version mismatch: {key}")
        if ev["source_type"] == "image" and ev["source_ref"] in image_slots:
            slot = image_slots[ev["source_ref"]]
            if not coverage[f"{slot}_image_inspected"] and historic_key not in historical:
                errors.append(f"{path} image evidence not inspected: {ev['source_ref']}")

    basis = coverage["continuity_basis"]
    if basis in ("persistent_state", "both") and not old:
        errors.append("continuity_basis claims persistent_state without incoming facts")
    if basis in ("adjacent", "both") and not any(k in slots for k in ("previous", "next")):
        errors.append("continuity_basis claims adjacent without adjacent input")
    if not old and any(k in slots and not coverage[f"{k}_image_inspected"] and
                      inp.get("continuity_context", {}).get(link, "unknown") != "new_scene"
                      for k, link in (("previous", "previous_to_current"), ("next", "current_to_next"))):
        if not any(u["review_area"] == "cross_shot_continuity" and LEVEL[u["potential_severity"]] >= 1
                   for u in out["uncertainties"]):
            errors.append("uninspected continuous neighbor needs continuity uncertainty; Spec is not an observed image")

    for issue in out["issues"]:
        issue_areas = areas(issue)
        target_slot = issue["attribution"] if issue["attribution"] in slots else "current"
        target_image = slots[target_slot].get("image")
        ev_refs = {(e["source_type"], e["source_ref"]) for e in issue["evidence"]}
        if not target_image or not coverage[f"{target_slot}_image_inspected"] or ("image", target_image["image_id"]) not in ev_refs:
            errors.append(f"issue {issue['issue_id']} requires actual inspected target image evidence")
        if issue["review_area"] in issue.get("related_review_areas", []):
            errors.append("related_review_areas must not repeat primary review_area")
        if not set(issue["affected_shot_ids"]) <= allowed_shots:
            errors.append(f"issue {issue['issue_id']} affected_shot_ids unknown")
        if issue["attribution"] in slots and slots[issue["attribution"]]["shot_id"] not in issue["affected_shot_ids"]:
            errors.append("issue attribution must be in affected_shot_ids")
        if issue["attribution"] in ("previous", "next") and issue["attribution"] not in slots:
            errors.append("issue attribution references absent adjacent shot")
        for fid in issue.get("fact_ids", []):
            if fid not in facts:
                errors.append(f"issue fact_id unknown: {fid}")
        if "cross_shot_continuity" in issue_areas:
            context = inp.get("continuity_context", {})
            for slot, link in (("previous", "previous_to_current"), ("next", "current_to_next")):
                if slot in slots and slots[slot]["shot_id"] in issue["affected_shot_ids"] and context.get(link) == "unknown":
                    errors.append("unknown continuity relationship cannot establish a confirmed continuity error")
            if len(issue["affected_shot_ids"]) < 2:
                errors.append("continuity issue needs at least two affected_shot_ids")
            checks = [c for c in out["visibility_checks"] if c["fact_id"] in issue.get("fact_ids", []) and
                      c["shot_id"] in issue["affected_shot_ids"] and c["assessment"] == "contradiction"]
            if not checks:
                errors.append(f"issue {issue['issue_id']} has no linked visibility contradiction")
            if issue["attribution"] in slots and not any(c["shot_id"] == slots[target_slot]["shot_id"] for c in checks):
                errors.append("resolved continuity attribution needs corresponding target visibility contradiction")
            if not target_image or ("image", target_image["image_id"]) not in ev_refs:
                errors.append("continuity issue needs actual target image evidence")
            if not any(e["source_type"] in ("shot_spec", "story", "persistent_state") or
                       (e["source_type"] == "image" and target_image and e["source_ref"] != target_image["image_id"])
                       for e in issue["evidence"]):
                errors.append("continuity issue needs prior-state evidence")

    # Result logic is deterministic; semantic significance comes from the reviewer.
    for area in AREAS:
        failures = any(i["attribution"] == "current" and area in areas(i) for i in out["issues"])
        uncertain = any(u["review_area"] == area for u in out["uncertainties"]) or any(
            i["attribution"] == "unresolved" and area in areas(i) for i in out["issues"])
        if area == "cross_shot_continuity":
            uncertain = uncertain or any(i["attribution"] in ("previous", "next") and LEVEL[i["severity"]] >= 1
                                         for i in out["issues"])
        expected = "FAIL" if failures else "uncertain" if uncertain else "PASS"
        if area == "cross_shot_continuity" and out[area] == "not_applicable":
            links = inp.get("continuity_context", {})
            has_applicable_adjacent = any(k in slots and links.get(link, "unknown") != "new_scene"
                                         for k, link in (("previous", "previous_to_current"), ("next", "current_to_next")))
            has_applicable_state = bool(old) and links.get("previous_to_current") != "new_scene"
            if failures or uncertain or has_applicable_adjacent or has_applicable_state:
                errors.append("cross_shot_continuity not_applicable despite applicable or unresolved evidence")
        elif out[area] != expected:
            errors.append(f"{area} must be {expected}")
    missing_current = current["shot_spec"] is None or not coverage["current_image_inspected"]
    if missing_current and (out["current_shot_compliance"] not in ("uncertain", "FAIL") or
                            not any(u["review_area"] == "current_shot_compliance" and LEVEL[u["potential_severity"]] >= 1
                                    for u in out["uncertainties"])):
        errors.append("current_shot_compliance needs material uncertainty for missing Spec/uninspected current image")
    result = expected_verdict(out)
    if out["overall_result"] != result:
        errors.append(f"overall_result must be {result}")

    # State integrity. Authored evidence is necessary, not proof of narrative entailment.
    new_scene = inp.get("continuity_context", {}).get("previous_to_current") == "new_scene"
    future = inp.get("next", {})
    future_refs = {x for x in (future.get("shot_id", "") + "_SPEC" if future else None,
                              future.get("image", {}).get("image_id") if future.get("image") else None) if x}
    for fid, f in new.items():
        failed = any(i["attribution"] == "current" and fid in i.get("fact_ids", []) for i in out["issues"])
        current_image = current.get("image")
        if failed and current_image and any(e["source_type"] == "image" and e["source_ref"] == current_image["image_id"]
                                           for e in f["evidence"]):
            errors.append(f"fact {fid} would contaminate supporting evidence with a failed current image")
        checks = [c for c in out["visibility_checks"] if c["fact_id"] == fid and c["shot_id"] == sid]
        if f["last_confirmed_at_shot_id"] == sid and (failed or any(c["assessment"] != "consistent" for c in checks)):
            errors.append(f"fact {fid} last_confirmed cannot advance on failure, uncertainty or invisibility")
        if f["established_at_shot_id"] not in allowed_shots or (f["last_confirmed_at_shot_id"] and f["last_confirmed_at_shot_id"] not in allowed_shots):
            errors.append(f"fact {fid} unknown established/last_confirmed shot")
        if (future and (f["established_at_shot_id"] == future["shot_id"] or f["last_confirmed_at_shot_id"] == future["shot_id"])) or any(
                e["source_ref"] in future_refs for e in f["evidence"]):
            errors.append(f"fact {fid} contains future next-shot state")
        if new_scene and fid in old and old[fid]["scope"] == "scene":
            errors.append(f"new scene retained old scene fact {fid}; establish a new scene-scoped fact")
        if fid in old:
            before = old[fid]
            if any(f[k] != before[k] for k in ("entity_id", "property", "scope", "established_at_shot_id")):
                errors.append(f"fact_id {fid} cannot change identity/property/scope/provenance")
            changed = any(f[k] != before[k] for k in ("value", "world_anchor"))
            authorized = any(e["source_type"] in ("shot_spec", "story") and
                             e["source_ref"] not in future_refs and e not in before["evidence"] for e in f["evidence"])
            if changed and not authorized:
                errors.append(f"fact {fid} change lacks new authored change evidence")
                if failed:
                    errors.append(f"fact {fid} would contaminate baseline with a failed current state")
        if f["last_confirmed_at_shot_id"] == sid:
            img = current.get("image")
            if not img or not coverage["current_image_inspected"] or not any(
                    e["source_type"] == "image" and e["source_ref"] == img["image_id"] for e in f["evidence"]):
                errors.append(f"fact {fid} last_confirmed needs current inspected image evidence")
    for fid, f in old.items():
        if fid not in new and not new_scene and fid not in invalidated:
            errors.append(f"persistent fact {fid} dropped in continuous/unknown scene; retain or resolve provenance explicitly")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--check-schemas", action="store_true")
    args = parser.parse_args(argv)
    if args.output and not args.input:
        parser.error("--output requires --input for source/state validation")
    if not (args.input or args.state or args.check_schemas):
        parser.error("choose --input, --state or --check-schemas")
    try:
        validators()
        def read(path): return json.loads(path.read_text(encoding="utf-8-sig"))
        errors = []
        if args.input:
            inp = read(args.input)
            errors += validate_pair(inp, read(args.output)) if args.output else validate_input(inp)
        if args.state:
            errors += validate_state(read(args.state))
    except (OSError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("VALID: structural/contract checks passed; image truth and narrative evidence require visual review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
