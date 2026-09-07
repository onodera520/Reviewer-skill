"""Readable Markdown delivery tests, separate from visual judgment."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from test_contract import sample

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('render_review', ROOT/'scripts/render_review.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


class RenderTests(unittest.TestCase):
    def test_static_report_only_exposes_problem_severity_and_fix(self):
        _, report = sample()
        text = render.render_report(report)
        for value in ['REGENERATE','问题 1','严重程度：高','满载','空','恢复原满载状态','背景物体状态连续性']:
            self.assertIn(value, text)
        for value in ['单镜合规','跨镜连续性','**证据：**','**判断依据：**','审查范围与限制','补充说明','右后景']:
            self.assertNotIn(value, text)

    def test_does_not_dump_internal_json_or_state(self):
        _, report = sample()
        text = render.render_report(report)
        for value in ['```json','schema_version','persistent_visual_state','fact_id','last_confirmed_at_shot_id','"issues"']:
            self.assertNotIn(value, text)

    def test_pass_is_short_and_has_no_empty_issue_sections(self):
        _, report = sample()
        report.update(overall_result='PASS', current_shot_compliance='PASS',cross_shot_continuity='PASS',issues=[])
        text=render.render_report(report)
        self.assertIn('未发现需要修改的问题',text)
        self.assertNotIn('待确认',text)
        self.assertNotIn('修复建议',text)
        self.assertLess(len(text),500)

    def test_uncertain_requests_evidence_without_inventing_error(self):
        _, report=sample()
        report.update(overall_result='REVISE',cross_shot_continuity='uncertain',issues=[])
        report['uncertainties']=[dict(finding_id='U1', review_area='cross_shot_continuity',entity_ids=['SHELF'],
            question='货架是否为空？',evidence=[],reason='背景无法辨认',potential_severity='high',required_evidence=['清晰原图'])]
        text=render.render_report(report)
        self.assertIn('待确认',text)
        self.assertIn('清晰原图',text)
        self.assertIn('可能严重程度：高',text)
        self.assertNotIn('问题 1',text)

    def test_external_error_does_not_name_current_for_repair(self):
        _, report=sample()
        report['issues'][0].update(attribution='previous',recommended_fix='修复前镜')
        report.update(overall_result='REVISE',cross_shot_continuity='uncertain')
        text=render.render_report(report)
        self.assertIn('修复前镜',text)

    def test_user_text_cannot_inject_markdown_images_or_code(self):
        _, report=sample()
        report['issues'][0]['reason']='![load](https://example.invalid/a.png)\n```json\n{}'
        text=render.render_report(report)
        self.assertNotIn('![load]',text)
        self.assertNotIn('```json',text)

    def test_render_is_pure_and_preserves_structured_state(self):
        _, report=sample()
        before=copy.deepcopy(report)
        render.render_report(report)
        self.assertEqual(before,report)

    def test_clip_metadata_is_omitted_from_minimal_report(self):
        _, report=sample()
        text=render.render_report(report,context={'clip_id':'CLIP_02','image_number':7})
        self.assertNotIn('图 7',text)
        self.assertNotIn('clip_id',text)
        self.assertNotIn('image_number',text)

    def test_evidence_locator_is_kept_internal(self):
        _, report=sample()
        report['issues'][0]['evidence'][2]['locator']='shot_spec'
        text=render.render_report(report)
        self.assertNotIn('静态设计要求',text)
        self.assertNotIn('shot_spec',text)

    def test_existing_file_requires_explicit_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'review.md'
            path.write_text('user content',encoding='utf-8')
            with self.assertRaises(FileExistsError):
                render.write_report(path,'report')
            self.assertEqual('user content',path.read_text(encoding='utf-8'))
            render.write_report(path,'report',overwrite=True)
            self.assertEqual('report',path.read_text(encoding='utf-8'))


if __name__=='__main__': unittest.main()
