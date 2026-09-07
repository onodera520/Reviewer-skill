"""Behavioral contract tests; no image judgments are made here."""
import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("contract", ROOT / "scripts/validate_contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def evidence(kind, ref, observation="清晰可见"):
    value = dict(source_type=kind, source_ref=ref, locator="右后景", observation=observation)
    if kind == "shot_spec": value["source_version"] = "1"
    return value


def sample():
    fact = dict(fact_id="F1", entity_id="SHELF", category="background_object_state",
                scope="scene", property="stock", value="满载", world_anchor="柜台后方",
                importance="high", basis="observed", established_at_shot_id="S1",
                last_confirmed_at_shot_id="S1", evidence=[evidence("image", "I1")])
    state = dict(schema_version="1.0", scene_id="STORE", continuity_segment_id="SEG1",
                 through_shot_id="S1", coverage_start_shot_id="S1", facts=[fact])
    def shot(n):
        return dict(shot_id=f"S{n}", scene_id="STORE", spec_version="1",
                    shot_spec="便利店同一区域，柜台后方货架可见。", image=dict(image_id=f"I{n}", ref=f"{n}.png"))
    inp = dict(schema_version="1.0", current=shot(2), previous=shot(1),
               persistent_visual_state=state,
               continuity_context=dict(previous_to_current="continuous", current_to_next="unknown", basis="同场连续"))
    out = dict(schema_version="1.0", shot_id="S2", overall_result="REGENERATE",
               current_shot_compliance="PASS", cross_shot_continuity="FAIL",
               coverage=dict(current_image_inspected=True, previous_image_inspected=True,
                             next_image_inspected=False, continuity_basis="both", limitations=[]),
               issues=[dict(issue_id="ERR1", review_area="cross_shot_continuity",
                            error_type="background_state_continuity", severity="high",
                            affected_shot_ids=["S1", "S2"], attribution="current", entity_ids=["SHELF"],
                            fact_ids=["F1"], previous_state="满载", expected_current_state="继续满载",
                            actual_current_state="空", evidence=[evidence("image", "I1"), evidence("image", "I2"),
                                evidence("shot_spec", "S2_SPEC", "无清空动作，仍可见")],
                            reason="同一可见货架无依据变空", recommended_fix="恢复原满载状态，保留机位")],
               uncertainties=[], notes=[],
               visibility_checks=[dict(fact_id="F1", shot_id="S2", expected_visibility="yes",
                                       observed_visibility="visible", assessment="contradiction",
                                       reason="无遮挡且陈列区域清楚", evidence=[evidence("image", "I2")])],
               persistent_visual_state=copy.deepcopy(state))
    out["persistent_visual_state"]["through_shot_id"] = "S2"
    return inp, out


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.i, self.o = sample()

    def good(self):
        self.assertEqual([], contract.validate_pair(self.i, self.o))

    def bad(self, text):
        errors = contract.validate_pair(self.i, self.o)
        self.assertTrue(any(text in x for x in errors), errors)

    def clear_issues(self):
        self.o.update(issues=[], visibility_checks=[], overall_result="PASS", cross_shot_continuity="PASS")

    def uncertainty(self, severity="high", area="cross_shot_continuity"):
        return dict(finding_id="U1", review_area=area, entity_ids=["SHELF"], question="能否确认陈列？",
                    evidence=[], reason="背景模糊", potential_severity=severity, required_evidence=["清晰原图"])

    def test_valid_shelf_error(self): self.good()

    def test_severe_current_error_cannot_pass(self):
        self.o["overall_result"] = "PASS"
        self.bad("overall_result")

    def test_uncertainty_requires_revise_not_regenerate(self):
        self.clear_issues()
        self.o.update(uncertainties=[self.uncertainty()], cross_shot_continuity="uncertain", overall_result="REVISE")
        self.good()
        self.o["overall_result"] = "REGENERATE"
        self.bad("overall_result")

    def test_low_uncertainty_can_pass(self):
        self.clear_issues()
        self.o.update(uncertainties=[self.uncertainty("low")], cross_shot_continuity="uncertain")
        self.good()

    def test_one_issue_can_fail_both_areas(self):
        self.o["issues"][0]["related_review_areas"] = ["current_shot_compliance"]
        self.o["current_shot_compliance"] = "FAIL"
        self.good()

    def test_missing_evidence_rejected(self):
        self.o["issues"][0]["evidence"] = []
        self.bad("evidence")

    def test_continuity_requires_prior_state(self):
        self.o["issues"][0]["previous_state"] = None
        self.bad("previous_state")

    def test_unknown_source_ref_rejected(self):
        self.o["issues"][0]["evidence"][0]["source_ref"] = "invented"
        self.bad("source_ref")

    def test_unknown_visibility_fact_rejected(self):
        self.o["visibility_checks"][0]["fact_id"] = "invented"
        self.bad("fact_id")

    def test_no_visibility_proof_for_error_rejected(self):
        self.o["visibility_checks"] = []
        self.bad("visibility")

    def test_occluded_property_cannot_be_contradiction(self):
        self.o["visibility_checks"][0].update(expected_visibility="no", assessment="contradiction")
        self.bad("visibility")

    def test_wrong_crop_is_compliance_only(self):
        issue = self.o["issues"][0]
        issue.update(review_area="current_shot_compliance", error_type="shot_spec_compliance",
                     previous_state=None, actual_current_state="货架裁出画面")
        self.o.update(current_shot_compliance="FAIL", cross_shot_continuity="PASS")
        self.o["visibility_checks"][0].update(observed_visibility="not_visible", assessment="not_testable")
        self.good()

    def test_hidden_state_retained_without_reconfirmation(self):
        self.clear_issues()
        self.o["visibility_checks"] = [dict(fact_id="F1", shot_id="S2", expected_visibility="no",
            observed_visibility="not_visible", assessment="not_testable", reason="脸部特写离画", evidence=[evidence("image", "I2")])]
        self.good()
        self.o["persistent_visual_state"]["facts"][0]["last_confirmed_at_shot_id"] = "S2"
        self.bad("last_confirmed")

    def test_hidden_state_cannot_be_deleted(self):
        self.clear_issues()
        self.o["persistent_visual_state"]["facts"] = []
        self.bad("dropped")

    def test_erroneous_frame_cannot_overwrite_state(self):
        self.o["persistent_visual_state"]["facts"][0]["value"] = "空"
        self.bad("contaminate")

    def test_error_cannot_reconfirm_state(self):
        self.o["persistent_visual_state"]["facts"][0]["last_confirmed_at_shot_id"] = "S2"
        self.bad("last_confirmed")

    def test_future_observation_cannot_enter_state(self):
        self.i["next"] = copy.deepcopy(self.i["current"])
        self.i["next"].update(shot_id="S3", image=dict(image_id="I3", ref="3.png"))
        self.o["persistent_visual_state"]["facts"][0]["evidence"].append(evidence("image", "I3"))
        self.bad("future")

    def test_new_scene_drops_old_scene_facts(self):
        self.clear_issues()
        self.i["current"]["scene_id"] = "STREET"
        self.i["continuity_context"]["previous_to_current"] = "new_scene"
        self.o["cross_shot_continuity"] = "not_applicable"
        self.o["coverage"]["continuity_basis"] = "none"
        self.o["persistent_visual_state"].update(scene_id="STREET", continuity_segment_id="SEG2", coverage_start_shot_id="S2")
        self.bad("scene")
        self.o["persistent_visual_state"]["facts"] = []
        self.good()

    def test_first_shot_not_applicable(self):
        self.clear_issues()
        self.i.pop("previous")
        self.i.pop("persistent_visual_state")
        self.i.pop("continuity_context")
        self.o["coverage"].update(previous_image_inspected=False, continuity_basis="none")
        self.o["cross_shot_continuity"] = "not_applicable"
        self.o["persistent_visual_state"].update(facts=[], coverage_start_shot_id="S2")
        self.good()

    def test_missing_current_image_requires_uncertainty(self):
        self.clear_issues()
        self.i["current"]["image"] = None
        self.o["coverage"]["current_image_inspected"] = False
        self.o.update(current_shot_compliance="uncertain", overall_result="REVISE",
                      uncertainties=[self.uncertainty(area="current_shot_compliance")])
        self.good()
        self.o["current_shot_compliance"] = "PASS"
        self.bad("current_shot_compliance")

    def test_missing_neighbor_cannot_claim_inspected(self):
        self.i["previous"]["image"] = None
        self.bad("inspected")

    def test_previous_error_does_not_regenerate_current(self):
        self.o["issues"][0]["attribution"] = "previous"
        self.o.update(overall_result="REVISE", cross_shot_continuity="uncertain")
        self.o["visibility_checks"][0].update(shot_id="S1", assessment="contradiction")
        self.good()

    def test_unresolved_attribution_is_uncertain(self):
        self.o["issues"][0]["attribution"] = "unresolved"
        self.o.update(overall_result="REVISE", cross_shot_continuity="uncertain")
        self.good()

    def test_duplicate_ids_rejected(self):
        self.o["issues"].append(copy.deepcopy(self.o["issues"][0]))
        self.bad("duplicate")

    def test_state_change_requires_spec_or_story_source(self):
        self.clear_issues()
        self.o["persistent_visual_state"]["facts"][0]["value"] = "部分陈列"
        self.bad("change")
        self.o["persistent_visual_state"]["facts"][0]["evidence"].append(evidence("shot_spec", "S2_SPEC", "明确移走部分商品"))
        self.good()

    def test_spec_version_mismatch_rejected(self):
        self.o["issues"][0]["evidence"][2]["source_version"] = "0"
        self.bad("version")

    def test_invalid_enum_and_unknown_field_rejected(self):
        self.o["overall_result"] = "APPROVED"
        self.o["video_review"] = {}
        self.bad("schema")

    def test_state_invalidation_allows_explained_quarantine(self):
        self.clear_issues()
        self.o.update(overall_result="REVISE", cross_shot_continuity="uncertain",
                      uncertainties=[self.uncertainty()], state_invalidations=[dict(
                          fact_id="F1", reason="来源已替换，需核实旧观察", evidence=[evidence("shot_spec", "S1_SPEC")])])
        self.o["persistent_visual_state"]["facts"] = []
        self.good()

    def test_invalidation_cannot_leave_fact_active(self):
        self.clear_issues()
        self.o.update(overall_result="REVISE", cross_shot_continuity="uncertain",
                      uncertainties=[self.uncertainty()], state_invalidations=[dict(
                          fact_id="F1", reason="版本失效", evidence=[evidence("shot_spec", "S1_SPEC")])])
        self.bad("invalidated")

    def test_spec_only_neighbor_needs_uncertainty(self):
        self.clear_issues()
        self.i.pop("persistent_visual_state")
        self.i["previous"]["image"] = None
        self.o["persistent_visual_state"]["facts"] = []
        self.o["coverage"].update(previous_image_inspected=False, continuity_basis="adjacent")
        self.bad("neighbor")

    def test_error_image_cannot_support_retained_correct_fact(self):
        self.o["persistent_visual_state"]["facts"][0]["evidence"].append(evidence("image", "I2", "错误空架"))
        self.bad("contaminate")

    def test_stale_version_can_be_cited_for_quarantine_only(self):
        self.clear_issues()
        old_ev = evidence("shot_spec", "S1_SPEC", "旧版满载要求")
        old_ev["source_version"] = "0"
        self.i["persistent_visual_state"]["facts"][0]["evidence"].append(old_ev)
        self.o.update(overall_result="REVISE", cross_shot_continuity="uncertain", uncertainties=[self.uncertainty()],
                      state_invalidations=[dict(fact_id="F1", reason="旧版依据不再可靠", evidence=[old_ev])])
        self.o["persistent_visual_state"]["facts"] = []
        self.good()

    def test_historical_fact_cannot_self_certify(self):
        self.i["persistent_visual_state"]["facts"][0]["evidence"] = [evidence("persistent_state", "F1")]
        self.bad("original")

    def test_compliance_error_requires_actual_image(self):
        self.i["current"]["image"] = None
        self.o["coverage"]["current_image_inspected"] = False
        self.o["issues"][0].update(review_area="current_shot_compliance", error_type="shot_spec_compliance",
            previous_state=None, evidence=[evidence("shot_spec", "S2_SPEC")])
        self.o.update(current_shot_compliance="FAIL", cross_shot_continuity="PASS", visibility_checks=[],
                      uncertainties=[self.uncertainty(area="current_shot_compliance")])
        self.bad("actual")

    def test_new_fact_cannot_be_created_from_failed_image(self):
        self.i.pop("persistent_visual_state")
        self.o["coverage"]["continuity_basis"] = "adjacent"
        self.o["persistent_visual_state"]["facts"][0].update(value="空", established_at_shot_id="S2",
            last_confirmed_at_shot_id="S2", evidence=[evidence("image", "I2")])
        self.bad("contaminate")

    def test_previous_attribution_needs_previous_visibility(self):
        self.o["issues"][0]["attribution"] = "previous"
        self.o.update(overall_result="REVISE", cross_shot_continuity="uncertain")
        self.bad("target visibility")

    def test_unknown_continuity_cannot_be_confirmed_error(self):
        self.i["continuity_context"]["previous_to_current"] = "unknown"
        self.bad("unknown continuity")

    def test_known_spec_version_cannot_be_omitted(self):
        self.o["issues"][0]["evidence"][2].pop("source_version")
        self.bad("source_version")

    def test_all_fixture_inputs_match_schema(self):
        for path in (ROOT / "evals/fixtures").glob("i*.json"):
            with self.subTest(input=path.name):
                self.assertEqual([], contract.validate_input(json.loads(path.read_text(encoding="utf-8"))))

    def test_clip_boundary_does_not_reset_scene_state(self):
        self.i['previous'].update(clip_id='CLIP_01',clip_version='1',image_number=1)
        self.i['current'].update(clip_id='CLIP_02',clip_version='3',image_number=2)
        self.good()
        self.o['persistent_visual_state']['facts']=[]
        self.bad('dropped')

    def test_same_clip_does_not_prevent_new_scene_reset(self):
        self.clear_issues()
        self.i['previous']['clip_id']='CLIP_01'
        self.i['current'].update(clip_id='CLIP_01',scene_id='STORE_B')
        self.i['continuity_context']['previous_to_current']='new_scene'
        self.o['persistent_visual_state'].update(scene_id='STORE_B',facts=[],continuity_segment_id='SEG2',coverage_start_shot_id='S2')
        self.o['coverage']['continuity_basis']='none'
        self.o['cross_shot_continuity']='not_applicable'
        self.good()

    def test_reference_links_and_complete_report_example(self):
        for path in ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for link in re.findall(r"\]\(([^)]+)\)", text):
                if "://" not in link and not link.startswith("#"):
                    self.assertTrue((path.parent / link.split("#")[0]).exists(), f"{path}: {link}")
            if path.name == "input-output.md":
                for block in re.findall(r"```json\n(.*?)\n```", text, re.S):
                    report = json.loads(block)
                    self.assertEqual([], contract.validate_schema(report, contract.NAMES[1]))


if __name__ == "__main__":
    unittest.main()
