"""Prompt binding / historical policy / scope regression, not image inference."""
import copy
import unittest
from test_contract import sample as old_static
from test_animatic_contract import sample as old_video, module, L

def static():
    i,o=old_static()
    i['review_profile']=o['review_profile']='story_preview'
    i['current']['image_prompt']='男人伸手拿起便当。'
    i['current']['shot_spec']=None
    o.update(issues=[],uncertainties=[],visibility_checks=[],overall_result='PASS',current_shot_compliance='PASS',cross_shot_continuity='PASS')
    return i,o

def video():
    i,o=old_video(); i['review_profile']=o['review_profile']='story_preview'
    o['coverage']['audio']={'status':'not_applicable','method':'skipped_by_scope','checked_ranges':[],'evidence':[]}
    return i,o

class StoryPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.v=module('validate_contract')
    def test_prompt_without_spec_is_valid(self): self.assertEqual([],self.v.validate_pair(*static()))
    def test_legacy_spec_review_still_valid(self): self.assertEqual([],self.v.validate_pair(*old_static()))
    def test_legacy_audio_contract_still_valid(self): self.assertEqual([],self.v.validate_pair(*old_video()))
    def test_profile_cannot_silently_change(self):
        i,o=static(); del o['review_profile']; self.assertTrue(self.v.validate_pair(i,o))
    def test_missing_prompt_cannot_pass(self):
        i,o=static(); i['current']['image_prompt']=' '; self.assertTrue(self.v.validate_pair(i,o))
    def test_missing_prompt_accepts_honest_limited_review(self):
        i,o=static(); del i['current']['image_prompt']
        o.update(current_shot_compliance='uncertain',overall_result='REVISE')
        o['uncertainties']=[{'finding_id':'U1','review_area':'current_shot_compliance','entity_ids':[],
                            'question':'未提供对应提示词','reason':'只能核对已有连续状态','evidence':[],
                            'potential_severity':'medium','required_evidence':['该图片对应的原始提示词']}]
        self.assertEqual([],self.v.validate_pair(i,o))
    def prompt_issue(self):
        i,o=static(); _,old=old_static(); p=copy.deepcopy(old['issues'][0])
        p.update(review_area='current_shot_compliance',error_type='shot_spec_compliance',previous_state=None,fact_ids=[],related_review_areas=[])
        p['evidence']=[{'source_type':'image','source_ref':i['current']['image']['image_id'],'locator':'手部','observation':'拿着杯子'},
                       {'source_type':'image_prompt','source_ref':i['current']['shot_id']+'_IMAGE_PROMPT','locator':'全文','observation':'要求拿起便当'}]
        o.update(issues=[p],current_shot_compliance='FAIL',overall_result='REGENERATE')
        return i,o
    def test_wrong_object_requires_bound_prompt_evidence(self): self.assertEqual([],self.v.validate_pair(*self.prompt_issue()))
    def test_another_shot_prompt_is_not_current_basis(self):
        i,o=self.prompt_issue(); o['issues'][0]['evidence'][1]['source_ref']='OTHER_IMAGE_PROMPT'
        self.assertTrue(self.v.validate_pair(i,o))
    def test_old_prompt_version_rejected(self):
        i,o=self.prompt_issue(); i['current']['image_prompt_version']='2'
        o['issues'][0]['evidence'][1]['source_version']='1'; self.assertTrue(self.v.validate_pair(i,o))
    def test_prompt_spec_conflict_can_remain_uncertain(self):
        i,o=static(); i['current']['shot_spec']='男人放下杯子。'
        o.update(current_shot_compliance='uncertain',overall_result='REVISE')
        o['uncertainties']=[{'finding_id':'U1','review_area':'current_shot_compliance','entity_ids':[],
            'question':'提示词与 Spec 的动作对象和方向相反，采用哪一版？','reason':'主要故事意图冲突，不能自行选择',
            'evidence':[{'source_type':'image_prompt','source_ref':i['current']['shot_id']+'_IMAGE_PROMPT','locator':'全文','observation':'拿起便当'},
                        {'source_type':'shot_spec','source_ref':i['current']['shot_id']+'_SPEC','source_version':i['current']['spec_version'],'locator':'全文','observation':'放下杯子'}],
            'potential_severity':'medium','required_evidence':['确认对应提示词与 Spec 的有效版本']}]
        self.assertEqual([],self.v.validate_pair(i,o))
    def test_skipped_audio_allows_video_pass(self): self.assertEqual([],self.v.validate_pair(*video()))
    def test_new_profile_must_not_claim_audio_checked(self):
        i,o=video(); o['coverage']['audio']=old_video()[1]['coverage']['audio']; self.assertTrue(self.v.validate_pair(i,o))
    def test_legacy_cannot_skip_audio_silently(self):
        i,o=old_video(); o['coverage']['audio']=video()[1]['coverage']['audio']; self.assertTrue(self.v.validate_pair(i,o))
    def test_video_preview_prompt_can_supply_action_basis(self):
        i,o=video(); i['shots'][0]['shot_spec']=None; i['preview_prompt']='按图序硬切，人物保持停顿，小幅推近。'
        self.assertEqual([],self.v.validate_pair(i,o))
    def test_optional_source_review_cannot_pass_without_image_prompt(self):
        i,o=video(); o['shot_reviews'][0]['source_image_compliance']='PASS'; self.assertTrue(self.v.validate_pair(i,o))
    def test_small_variation_is_not_forced_to_be_an_issue(self):
        i,o=static(); o['notes']=['取便当的手势可读；尚未离开层板不影响动作意图，水印不在审查范围。']
        self.assertEqual([],self.v.validate_pair(i,o))

    def test_new_markdown_uses_prompt_label(self):
        i,o=self.prompt_issue()
        report=module('render_review').render_report(o,i)
        self.assertIn('提示词符合性',report)
        self.assertNotIn('Shot Spec 合规',report)
        self.assertNotIn('review_profile',report)

    def test_legacy_markdown_keeps_its_meaning(self):
        i,o=self.prompt_issue(); del o['review_profile']
        self.assertIn('Shot Spec 合规',module('render_review').render_report(o))

    def test_default_sampling_is_three_per_shot(self):
        media=module('prepare_animatic')
        frames=[{'time_seconds':i/10} for i in range(11)]
        self.assertEqual([0,5,10],media.sample_indices(frames,[0,11]))

if __name__=='__main__': unittest.main()
