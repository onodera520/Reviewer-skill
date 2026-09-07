#!/usr/bin/env python3
"""Validate an internal report and render a clean UTF-8 Markdown deliverable.

The report JSON remains the state-transfer contract. This renderer neither
reviews images nor changes verdicts, prompts, or persistent facts.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

AREAS = {'current_shot_compliance':'单镜合规', 'cross_shot_continuity':'跨镜连续性'}
STATUS = {'PASS':'通过', 'FAIL':'存在已确认问题', 'uncertain':'证据不足，待确认', 'not_applicable':'不适用'}
VERDICT = {'PASS':'通过', 'REVISE':'需修订或补充依据', 'REGENERATE':'需重新生成当前分镜'}
SEVERITY = {'critical':'严重', 'high':'高', 'medium':'中', 'low':'低'}
ATTRIBUTION = {'current':'当前镜', 'previous':'前镜', 'next':'后镜', 'unresolved':'归因待确认'}
TYPES = {
    'shot_spec_compliance':'Shot Spec 合规', 'environment_continuity':'环境连续性',
    'prop_continuity':'道具连续性', 'character_continuity':'人物连续性',
    'character_state_continuity':'人物状态连续性', 'spatial_continuity':'空间连续性',
    'background_state_continuity':'背景物体状态连续性', 'lighting_time_continuity':'光线与时间连续性',
    'scene_condition_continuity':'场景状态连续性',
}


def plain(value):
    """Escape untrusted report strings as prose, not executable Markdown."""
    text = ' / '.join(str(value).splitlines()).strip()
    return re.sub(r'([\\`*_{}\[\]<>#|])', r'\\\1', text)


def phrase(value):
    return plain(value).rstrip('。；;，, ')


def source_label(ev):
    ref = ev['source_ref']
    kind = ev['source_type']
    if kind == 'image': return '分镜图 ' + ref.removesuffix('_IMAGE')
    if kind == 'shot_spec': return 'Shot Spec ' + ref.removesuffix('_SPEC')
    if kind == 'asset': return '参考资产 ' + ref
    if kind == 'story': return '剧情文本'
    return '已建立的视觉状态'


def readable_locator(value):
    labels = {
        'shot_spec':'静态设计要求', 'storyboard_keyframe':'指定画面',
        'camera_state':'机位与取景', 'composition':'构图', 'blocking':'人物站位',
        'state':'画面状态', 'asset_bindings':'资产绑定', 'identity_traits':'固定形象',
        'state_overrides':'本镜状态', 'must_have':'必须呈现的内容', 'must_not_have':'禁止呈现的内容',
        'facing':'人物朝向', 'world_position':'世界位置', 'screen_position':'画面位置',
        'time_of_day':'日夜', 'lighting':'光线', 'environment':'环境', 'shot_size':'景别',
    }
    text=str(value)
    for key in sorted(labels,key=len,reverse=True):
        text=re.sub(r'(?<![A-Za-z_])'+re.escape(key)+r'(?![A-Za-z_])',labels[key],text)
    text=re.sub(r'\[(\d+)\]',lambda m:f'（第{int(m.group(1))+1}项）',text)
    return text


def evidence_lines(evidence):
    lines, seen = [], set()
    for ev in evidence:
        key = ev['source_type'], ev['source_ref'], ev['locator'], ev['observation']
        if key in seen: continue
        seen.add(key)
        lines.append(f"- {plain(source_label(ev))}，{plain(readable_locator(ev['locator']))}：{plain(ev['observation'])}")
    return lines


def render_report(report, context=None):
    if report.get('review_mode') == 'animatic':
        return render_animatic(report, context)
    lines = [f"# 静态分镜审查 · {plain(report['shot_id'])}", '',
             f"**结论：{report['overall_result']}**"]
    lines += static_issue_lines(report, heading='##')
    return '\n'.join(lines).rstrip() + '\n'


def static_issue_lines(report, heading='##'):
    lines=[]
    if not report['issues'] and not report['uncertainties']:
        return ['', '未发现需要修改的问题。']
    for index, issue in enumerate(report['issues'], 1):
        previous = (f"前镜已建立“{phrase(issue['previous_state'])}”；" if issue['previous_state'] is not None else '')
        problem = f"{previous}当前为“{phrase(issue['actual_current_state'])}”，应为“{phrase(issue['expected_current_state'])}”。"
        lines += ['', f"{heading} 问题 {index} · {TYPES[issue['error_type']]}", '',
                  f"**严重程度：{SEVERITY[issue['severity']]}**", '',
                  f"**问题：**{problem}", '',
                  f"**修改方案：**{plain(issue['recommended_fix'])}"]
    for index,item in enumerate(report['uncertainties'],1):
        required='；'.join(plain(x) for x in item['required_evidence'])
        lines += ['', f"{heading} 待确认 {index}", '',
                  f"**可能严重程度：{SEVERITY[item['potential_severity']]}**", '',
                  f"**问题：**{plain(item['question'])}", '',
                  f"**下一步：**{required}"]
    return lines


def timecode(seconds):
    total=round(seconds*1000)
    minutes, remainder=divmod(total,60000)
    seconds, millis=divmod(remainder,1000)
    return f'{minutes:02d}:{seconds:02d}.{millis:03d}'


def animatic_evidence(items, labels=None):
    lines=[]
    for e in items:
        if e['source_type']=='video_frame':
            label='画面 '+timecode(e['timestamp'])
        elif e['source_type']=='audio_segment':
            r=e['time_range']; label='声音 '+timecode(r['start'])+'–'+timecode(r['end'])
        else: label=(labels or {}).get(e['source_ref'],source_label(e))
        lines.append(f"- {plain(label)}，{plain(readable_locator(e['locator']))}：{plain(e['observation'])}")
    return list(dict.fromkeys(lines))


def render_animatic(report, context=None):
    targets={'storyboard_image':'源分镜图及受影响镜头','video_shot':'指定视频镜头','editing':'剪辑','audio':'声音','unresolved':'待确认修复对象'}
    combined=bool(report.get('static_reviews'))
    lines=[('# 分镜审查报告' if combined else '# 智能分镜审查'),'',f"**结论：{report['overall_result']}**"]
    if combined:
        lines+=['','## 静态分镜问题']
        for static in report['static_reviews']:
            lines += ['', f"### {plain(static['shot_id'])} · {static['overall_result']}"]
            lines += static_issue_lines(static, heading='####')
        lines+=['','## 智能分镜问题','',f"**结论：{report['animatic_review']['overall_result']}**"]
    if not report['issues'] and not report['uncertainties']:
        lines+=['','未发现需要修改的问题。']
    for n,i in enumerate(report['issues'],1):
        t=i['time_range']; span=timecode(t['start'])+'–'+timecode(t['end'])
        shot=plain('、'.join(i['shot_ids']) or '全段')
        problem=f"{phrase(i['actual'])}；应为“{phrase(i['expected'])}”。"
        lines+=['',f"### 问题 {n} · {shot} · {span}",'',
                f"**严重程度：{SEVERITY[i['severity']]}**",'',
                f"**问题：**{problem}",'',f"**修改对象：**{targets[i['repair_target']]}",'',
                f"**修改方案：**{plain(i['recommended_fix'])}"]
    if report['uncertainties']:
        lines+=['','## 待确认']
        for n,u in enumerate(report['uncertainties'],1):
            shots=plain('、'.join(u['shot_ids']) or '全段')
            lines += ['',f"### 待确认 {n} · {shots}",'',
                      f"**可能严重程度：{SEVERITY[u['potential_severity']]}**",'',
                      f"**问题：**{plain(u['question'])}",'',
                      f"**下一步：**{'；'.join(plain(x) for x in u['required_evidence'])}"]
    return '\n'.join(lines).rstrip()+'\n'


def write_report(path, text, overwrite=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w' if overwrite else 'x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Normalized review input JSON')
    parser.add_argument('--report', type=Path, required=True, help='Complete internal report JSON')
    parser.add_argument('--output', type=Path, required=True, help='User-facing Markdown file')
    parser.add_argument('--overwrite', action='store_true', help='Only for a user-authorized revision')
    args = parser.parse_args(argv)
    if args.output.suffix.lower() != '.md': parser.error('--output must be a .md file')
    if args.output.resolve() in (args.input.resolve(), args.report.resolve()):
        parser.error('Markdown output must not overwrite input or structured state')
    spec = importlib.util.spec_from_file_location('reviewer_contract', Path(__file__).with_name('validate_contract.py'))
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    try:
        inp = json.loads(args.input.read_text(encoding='utf-8-sig'))
        report = json.loads(args.report.read_text(encoding='utf-8-sig'))
        errors = validator.validate_pair(inp, report)
        if errors:
            print('\n'.join(errors), file=sys.stderr)
            return 1
        write_report(args.output, render_report(report, context=inp if inp.get('review_mode')=='animatic' else inp['current']), overwrite=args.overwrite)
    except (OSError, ValueError) as exc:
        print(f'Cannot render report: {exc}', file=sys.stderr)
        return 2
    print(str(args.output.resolve()))
    return 0


if __name__ == '__main__': raise SystemExit(main())
