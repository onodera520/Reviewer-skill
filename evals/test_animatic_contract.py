"""Contract tests; these do not claim media content has been inspected."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

L = ['visual_anchor_consistency', 'dynamic_execution_consistency', 'shot_sequence_consistency']
def sample():
    inp = {'schema_version':'1.0', 'review_mode':'animatic',
           'video':{'video_id':'V1','ref':'test.mp4','version':'1'},
           'shots':[{'shot_id':'S1','scene_id':'SC1','spec_version':'1',
                     'shot_spec':'人站在柜台旁，轻微转头', 'image':{'image_id':'I1','ref':'a.png'},
                     'anchor_position':'representative'}]}
    state = {'schema_version':'1.0','scene_id':'SC1','continuity_segment_id':'SEG1',
             'through_shot_id':'S1','coverage_start_shot_id':'S1','facts':[]}
    out = {'schema_version':'1.0','review_mode':'animatic','video_id':'V1',
           'overall_result':'PASS','animatic_review':{'overall_result':'PASS', **dict.fromkeys(L,'PASS')},
           'shot_reviews':[{'shot_id':'S1','mapping_status':'confirmed',
                            'segments':[{'start':0,'end':1}], 'anchor_time':0.5,
                            'source_image_compliance':'not_applicable', **dict.fromkeys(L,'PASS')}],
           'issues':[],'uncertainties':[], 'state_snapshots':[], 'persistent_visual_state':state,
           'coverage':{'duration_seconds':1,'decoded_ranges':[{'start':0,'end':1}],
                       'visual_samples':[{'timestamp':t,'image_ref':f'f{t}.png','inspected':True} for t in [0,0.5,0.9]],
                       'inspected_image_ids':['I1'],'verified_shot_ids':['S1'],'mapping_complete':True,
                       'audio':{'status':'PASS','method':'no_audio_track','checked_ranges':[{'start':0,'end':1}], 'evidence':[]},
                       'limitations':[]},'notes':[]}
    return inp,out

def frame(t):
    return {'source_type':'video_frame','source_ref':'V1','source_version':'1','timestamp':t,
            'locator':'人物右手','observation':'右手完整可见'}

def issue():
    return {'issue_id':'E1','error_type':'prop_drift','severity':'high','shot_ids':['S1'],
            'layers':[L[0],L[1]],'repair_target':'video_shot','repair_action':'regenerate',
            'time_range':{'start':0.5,'end':0.9},'entity_ids':['P1'],'fact_ids':[],
            'expected':'继续持有便当袋','actual':'便当袋无依据变为空杯',
            'evidence':[frame(0.5),frame(0.9),{'source_type':'image','source_ref':'I1','locator':'右手','observation':'拿着便当袋'}],
            'reason':'无授权交接或替换动作','recommended_fix':'重生成 S1，保持便当袋'}

class AnimaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.v = module('validate_contract')
    def test_minimal_valid(self):
        self.assertEqual([], self.v.validate_pair(*sample()))
    def test_representative_not_first_valid(self):
        i,o=sample(); self.assertEqual([],self.v.validate_pair(i,o))
    def test_wrong_video_reference_rejected(self):
        i,o=sample(); o['video_id']='OTHER'; self.assertTrue(self.v.validate_pair(i,o))
    def test_mapping_unknown_cannot_pass(self):
        i,o=sample(); o['shot_reviews'][0]['mapping_status']='uncertain'; self.assertTrue(self.v.validate_pair(i,o))
    def test_nonsemantic_audio_cannot_pass(self):
        i,o=sample(); o['coverage']['audio']['method']='unavailable'; self.assertTrue(self.v.validate_pair(i,o))
    def test_extraction_not_inspection(self):
        i,o=sample()
        for s in o['coverage']['visual_samples']: s['inspected']=False
        self.assertTrue(self.v.validate_pair(i,o))
    def test_high_visual_requires_regenerate(self):
        i,o=sample(); o['issues']=[issue()]
        self.assertTrue(self.v.validate_pair(i,o))
        o['overall_result']=o['animatic_review']['overall_result']='REGENERATE'
        for layer in L[:2]: o['animatic_review'][layer]=o['shot_reviews'][0][layer]='FAIL'
        self.assertEqual([],self.v.validate_pair(i,o))
    def test_dynamic_single_frame_rejected(self):
        i,o=sample(); p=issue(); p['evidence']=[frame(0.5)]; o['issues']=[p]
        o['overall_result']=o['animatic_review']['overall_result']='REGENERATE'
        for layer in L[:2]: o['animatic_review'][layer]=o['shot_reviews'][0][layer]='FAIL'
        self.assertTrue(self.v.validate_pair(i,o))
    def test_unknown_frame_rejected(self):
        i,o=sample(); o['coverage']['audio']['evidence']=[frame(0.8)]
        self.assertTrue(self.v.validate_pair(i,o))
    def test_critical_edit_only_is_revise(self):
        i,o=sample(); p=issue(); p.update(layers=[L[2]],repair_target='editing',repair_action='revise',severity='critical')
        o['issues']=[p]; o['overall_result']=o['animatic_review']['overall_result']='REVISE'
        o['animatic_review'][L[2]]=o['shot_reviews'][0][L[2]]='FAIL'
        self.assertEqual([],self.v.validate_pair(i,o))
    def test_uncertainty_not_regeneration(self):
        i,o=sample(); o['coverage']['audio'].update(status='uncertain',method='unavailable',checked_ranges=[])
        o['uncertainties']=[{'finding_id':'U1','shot_ids':[],'layers':[L[2]],'question':'声音是否合规',
                            'reason':'当前不能听辨', 'potential_severity':'high','required_evidence':['可听辨音轨'],'evidence':[]}]
        o['animatic_review'][L[2]]='uncertain'; o['overall_result']=o['animatic_review']['overall_result']='REVISE'
        self.assertEqual([],self.v.validate_pair(i,o))
        o['overall_result']=o['animatic_review']['overall_result']='REGENERATE'
        self.assertTrue(self.v.validate_pair(i,o))
    def test_duplicate_or_unknown_sequence(self):
        i,o=sample(); i['expected_sequence']=['S1','X']; self.assertTrue(self.v.validate_pair(i,o))
    def test_bad_range(self):
        i,o=sample(); o['shot_reviews'][0]['segments'][0]={'start':0.9,'end':0.2}
        self.assertTrue(self.v.validate_pair(i,o))
    def test_wrong_spec_version(self):
        i,o=sample(); o['coverage']['audio']['evidence']=[{'source_type':'shot_spec','source_ref':'S1_SPEC','source_version':'0','locator':'state','observation':'站立'}]
        self.assertTrue(self.v.validate_pair(i,o))
    def test_unmapped_tail_cannot_pass(self):
        i,o=sample(); o['shot_reviews'][0]['segments'][0]['end']=0.8
        self.assertTrue(self.v.validate_pair(i,o))
    def test_decoded_gap_cannot_pass(self):
        i,o=sample(); o['coverage']['decoded_ranges']=[{'start':0,'end':0.5}]
        self.assertTrue(self.v.validate_pair(i,o))
    def test_audio_failure_without_actual_sound_evidence_rejected(self):
        i,o=sample(); o['coverage']['audio'].update(status='FAIL',method='listened')
        self.assertTrue(self.v.validate_pair(i,o))
    def test_source_error_requires_spec_evidence(self):
        i,o=sample(); p=issue(); p.update(repair_target='storyboard_image',layers=[L[0]])
        o['issues']=[p]; o['overall_result']=o['animatic_review']['overall_result']='REGENERATE'
        o['animatic_review'][L[0]]=o['shot_reviews'][0][L[0]]='FAIL'
        self.assertTrue(self.v.validate_pair(i,o))
    def state_sample(self):
        i,o=sample()
        i['shots'][0].update(continuity_from_previous='continuous',continuity_basis='剧情明确连续')
        e={'source_type':'shot_spec','source_ref':'S0_SPEC','source_version':'1','locator':'背景','observation':'货架满载'}
        f={'fact_id':'F1','entity_id':'SHELF','category':'background_object_state','scope':'scene',
           'property':'stock','value':'满载','world_anchor':None,'importance':'high','basis':'specified',
           'established_at_shot_id':'S0','last_confirmed_at_shot_id':None,'evidence':[e]}
        state=copy.deepcopy(o['persistent_visual_state']); state.update(through_shot_id='S0',coverage_start_shot_id='S0',facts=[f])
        i['persistent_visual_state']=state
        new=copy.deepcopy(state); new['through_shot_id']='S1'
        snap={'shot_id':'S1','phase':'exit','timestamp':0.9,'state':new,
              'visibility_checks':[],'state_changes':[],'state_invalidations':[]}
        o['state_snapshots']=[snap]; o['persistent_visual_state']=copy.deepcopy(new)
        return i,o
    def test_hidden_fact_preserved(self):
        self.assertEqual([],self.v.validate_pair(*self.state_sample()))
    def test_offscreen_fact_not_dropped(self):
        i,o=self.state_sample(); o['state_snapshots'][0]['state']['facts']=[]; o['persistent_visual_state']['facts']=[]
        self.assertTrue(self.v.validate_pair(i,o))
    def test_bad_frame_cannot_overwrite_baseline(self):
        i,o=self.state_sample(); o['state_snapshots'][0]['state']['facts'][0]['value']='空'
        o['persistent_visual_state']=copy.deepcopy(o['state_snapshots'][0]['state'])
        self.assertTrue(self.v.validate_pair(i,o))
    def test_future_observation_rejected(self):
        i,o=self.state_sample(); o['state_snapshots'][0]['timestamp']=0.5
        o['state_snapshots'][0]['state']['facts'][0]['evidence'].append(frame(0.9))
        o['persistent_visual_state']=copy.deepcopy(o['state_snapshots'][0]['state'])
        self.assertTrue(self.v.validate_pair(i,o))
    def test_cross_clip_no_reset(self):
        i,o=self.state_sample(); i['shots'][0]['clip_id']='CLIP2'
        self.assertEqual([],self.v.validate_pair(i,o))
    def test_same_clip_new_scene_must_clear_environment(self):
        i,o=self.state_sample(); i['shots'][0].update(clip_id='CLIP1',scene_id='SC2',continuity_from_previous='new_scene')
        o['state_snapshots'][0]['state']['scene_id']='SC2'; o['persistent_visual_state']['scene_id']='SC2'
        self.assertTrue(self.v.validate_pair(i,o))
        o['state_snapshots'][0]['state']['facts']=[]; o['persistent_visual_state']['facts']=[]
        self.assertEqual([],self.v.validate_pair(i,o))
    def test_known_error_cannot_refresh_last_confirmation(self):
        i,o=self.state_sample(); f=o['state_snapshots'][0]['state']['facts'][0]
        f.update(basis='both',last_confirmed_at_shot_id='S1'); f['evidence'].append(frame(0.9))
        o['persistent_visual_state']=copy.deepcopy(o['state_snapshots'][0]['state'])
        self.assertTrue(self.v.validate_pair(i,o))

class AnimaticMarkdownTests(unittest.TestCase):
    def test_human_report(self):
        r=module('render_review'); i,o=sample(); o['issues']=[issue()]
        o['overall_result']=o['animatic_review']['overall_result']='REGENERATE'
        for layer in L[:2]: o['animatic_review'][layer]=o['shot_reviews'][0][layer]='FAIL'
        text=r.render_report(o, context=i)
        for expected in ['智能分镜','REGENERATE','S1','00:00.500','严重程度：高','问题：','修改对象：','修改方案：']:
            self.assertIn(expected,text)
        for forbidden in ['test.mp4','![','persistent_visual_state','visual_samples','```json','审查层级','参考时刻','**证据：**','审查范围与限制','补充说明']:
            self.assertNotIn(forbidden,text)
    def test_video_only_omits_static(self):
        text=module('render_review').render_report(sample()[1],context=sample()[0])
        self.assertNotIn('## 静态分镜审查',text)
    def test_untrusted_text_cannot_insert_video(self):
        r=module('render_review'); i,o=sample(); o['notes']=['![video](D:/secret.mp4)']
        text=r.render_report(o,context=i); self.assertNotIn('![video]',text)
    def test_animatic_pass_is_one_glance(self):
        r=module('render_review'); i,o=sample(); text=r.render_report(o,context=i)
        self.assertIn('未发现需要修改的问题',text)
        self.assertNotIn('| 审查层级 |',text)
        self.assertLess(len(text),220)
    def test_uncertainty_shows_required_next_step_only(self):
        r=module('render_review'); i,o=sample()
        o['coverage']['audio'].update(status='uncertain',method='unavailable',checked_ranges=[])
        o['uncertainties']=[{'finding_id':'U1','shot_ids':[],'layers':[L[2]],'question':'是否含音乐？',
                            'reason':'未实际听辨','potential_severity':'high','required_evidence':['听辨完整音轨'],'evidence':[]}]
        o['animatic_review'][L[2]]='uncertain';o['overall_result']=o['animatic_review']['overall_result']='REVISE'
        text=r.render_report(o,context=i)
        for expected in ['待确认','是否含音乐','可能严重程度：高','听辨完整音轨']:
            self.assertIn(expected,text)
        self.assertNotIn('未实际听辨',text)
    def test_combined_report_keeps_both_sections_concise(self):
        from test_contract import sample as static_sample
        r=module('render_review'); i,o=sample(); _,static=static_sample()
        o['static_reviews']=[static]; o['overall_result']='REGENERATE'
        text=r.render_report(o,context=i)
        for expected in ['## 静态分镜问题','## 智能分镜问题','修改方案：']:
            self.assertIn(expected,text)
        for forbidden in ['**证据：**','审查层级','参考时刻']:
            self.assertNotIn(forbidden,text)

if __name__=='__main__': unittest.main()
