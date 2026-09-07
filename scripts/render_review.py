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
    lines = [f"# 分镜审查 · {plain(report['shot_id'])}", '',
             f"**总体结论：{report['overall_result']} · {VERDICT[report['overall_result']]}**", '',
             '| 审查项 | 结论 |', '| --- | --- |']
    for area in AREAS:
        lines.append(f"| {AREAS[area]} | {STATUS[report[area]]} |")
    if context:
        parts=[]
        if context.get('clip_id'): parts.append(plain(context['clip_id']))
        if context.get('image_number'): parts.append(f"图 {context['image_number']}")
        if parts: lines += ['', '对应素材：'+' · '.join(parts)]
    if not report['issues']:
        lines += ['', '未发现已确认的问题。']
    for index, issue in enumerate(report['issues'], 1):
        lines += ['', f"## 问题 {index} · {TYPES[issue['error_type']]}", '',
                  f"**程度：{SEVERITY[issue['severity']]}｜涉及：{ATTRIBUTION[issue['attribution']]}**", '']
        if issue['previous_state'] is not None:
            lines += [f"**既有状态：**{plain(issue['previous_state'])}", '']
        lines += [f"**预期：**{plain(issue['expected_current_state'])}", '',
                  f"**实际：**{plain(issue['actual_current_state'])}", '', '**证据：**', '']
        lines += evidence_lines(issue['evidence'])
        lines += ['', f"**判断依据：**{plain(issue['reason'])}", '',
                  f"**修复建议：**{plain(issue['recommended_fix'])}"]
    if report['uncertainties']:
        lines += ['', '## 待确认', '']
        for item in report['uncertainties']:
            lines += [f"**{plain(item['question'])}**", '', plain(item['reason']), '']
            if item['evidence']:
                lines += evidence_lines(item['evidence']) + ['']
            lines += ['需要补充：', ''] + [f"- {plain(x)}" for x in item['required_evidence']] + ['']
    limitations = list(dict.fromkeys(report['coverage']['limitations']))
    if limitations:
        lines += ['', '## 审查范围与限制', ''] + [f'- {plain(x)}' for x in limitations]
    if report['notes']:
        lines += ['', '## 补充说明', ''] + [f'- {plain(x)}' for x in dict.fromkeys(report['notes'])]
    return '\n'.join(lines).rstrip() + '\n'


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
    layers={'visual_anchor_consistency':'视觉锚点一致性','dynamic_execution_consistency':'动态执行一致性','shot_sequence_consistency':'镜头序列一致性'}
    targets={'storyboard_image':'源分镜图及受影响镜头','video_shot':'指定视频镜头','editing':'剪辑','audio':'声音','unresolved':'待确认修复对象'}
    verdicts={'PASS':'通过','REVISE':'需修订或补充依据','REGENERATE':'需重生成下列指定素材'}
    source_labels={}
    for shot in (context or {}).get('shots',[]):
        if shot.get('image'):
            source_labels[shot['image']['image_id']]='分镜图 '+str(shot.get('image_number',shot['shot_id']))+' · '+shot['shot_id']
    lines=['# 分镜审查报告','',f"**总体结论：{report['overall_result']} · {verdicts[report['overall_result']]}**"]
    if report.get('static_reviews'):
        lines+=['','## 静态分镜审查','']
        for static in report['static_reviews']:
            text=render_report(static)
            # Nest the complete human report without exposing its internal contract.
            for line in text.splitlines():
                lines.append('##'+line if line.startswith('#') else line)
    lines+=['','## 智能分镜审查','',f"**结论：{report['animatic_review']['overall_result']}**",'',
            '| 审查层级 | 结论 |','| --- | --- |']
    lines += [f"| {label} | {STATUS[report['animatic_review'][key]]} |" for key,label in layers.items()]
    lines+=['','| 镜头 | 已核验时间 | 参考时刻 |','| --- | --- | --- |']
    for r in report['shot_reviews']:
        spans='、'.join(timecode(s['start'])+'–'+timecode(s['end']) for s in r['segments']) if r['mapping_status']=='confirmed' else '对应关系待核验'
        anchor=timecode(r['anchor_time']) if r['anchor_time'] is not None else '待确认'
        lines.append(f"| {plain(r['shot_id'])} | {spans} | {anchor} |")
    if not report['issues']: lines+=['','未发现已确认的问题。']
    for n,i in enumerate(report['issues'],1):
        t=i['time_range']; span=timecode(t['start'])+'–'+timecode(t['end'])
        lines+=['',f"### 问题 {n} · {'、'.join(layers[x] for x in dict.fromkeys(i['layers']))}",'',
                f"**镜头：{plain('、'.join(i['shot_ids']) or '全段')}｜时间：{span}｜程度：{SEVERITY[i['severity']]}**",'',
                f"**预期：**{plain(i['expected'])}",'',f"**实际：**{plain(i['actual'])}",'','**证据：**','']
        lines+=animatic_evidence(i['evidence'],source_labels)
        lines+=['',f"**判断依据：**{plain(i['reason'])}",'',f"**修复对象：**{targets[i['repair_target']]}",'',f"**修复建议：**{plain(i['recommended_fix'])}"]
    if report['uncertainties']:
        lines+=['','## 待确认','']
        for u in report['uncertainties']:
            lines += [f"**{plain(u['question'])}**",'',plain(u['reason']),'']
            lines += animatic_evidence(u['evidence'],source_labels)
            lines += ['需要补充：'+'；'.join(plain(x) for x in u['required_evidence']),'']
    cov=report['coverage']; audio=cov['audio']
    methods={'no_audio_track':'无音轨','decoded_silence':'已核验静音','listened':'已实际听辨','semantic_tool':'已完成声音内容识别','unavailable':'声音内容尚未核验'}
    lines += ['','## 审查范围与限制','',f"已核验镜头：{plain('、'.join(cov['verified_shot_ids']) or '暂无')}。声音：{methods[audio['method']]}。"]
    lines += ['',*[f'- {plain(x)}' for x in dict.fromkeys(cov['limitations'])]] if cov['limitations'] else []
    if report['notes']: lines+=['','## 补充说明','']+[f'- {plain(x)}' for x in dict.fromkeys(report['notes'])]
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
