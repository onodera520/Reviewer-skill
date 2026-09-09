"""Semantic contract checks for Animatic reports, never media understanding."""
LAYERS = ('visual_anchor_consistency','dynamic_execution_consistency','shot_sequence_consistency')
LEVEL = {'low':0,'medium':1,'high':2,'critical':3}

def walk(value, key):
    if isinstance(value,dict):
        for k,v in value.items():
            if k==key: yield v
            else: yield from walk(v,key)
    elif isinstance(value,list):
        for v in value: yield from walk(v,key)

def evidence(value):
    for batch in walk(value,'evidence'): yield from batch

def inside(t,ranges): return any(r['start']-1e-6<=t<=r['end']+1e-6 for r in ranges)

def covered(ranges,duration):
    if duration is None or duration<=0: return False
    end=0.0
    for r in sorted(ranges,key=lambda r:r['start']):
        if r['start']>end+0.001: return False
        end=max(end,r['end'])
    return end>=duration-0.001

def input_errors(inp,schema):
    errors=schema(inp,'animatic-input.schema.json')
    if errors: return errors
    ids=[s['shot_id'] for s in inp['shots']]
    if len(set(ids))!=len(ids): errors.append('duplicate Shot ID')
    seq=inp.get('expected_sequence',ids)
    if len(set(seq))!=len(seq) or set(seq)!=set(ids): errors.append('expected_sequence must list every Shot ID exactly once')
    for seg in inp.get('provided_segments',[]):
        if seg['shot_id'] not in ids: errors.append('provided segment references unknown shot')
        if seg['time_range']['end']<=seg['time_range']['start']: errors.append('provided segment has invalid time range')
    images=[s['image']['image_id'] for s in inp['shots'] if s.get('image')]
    if len(set(images))!=len(images): errors.append('duplicate source image ID; supply distinct versioned references')
    prior=inp.get('persistent_visual_state')
    if prior and prior['through_shot_id'] in ids: errors.append('input state must precede the reviewed sequence')
    return errors

def verdict(issues,uncertainties):
    if any(i['repair_action']=='regenerate' and LEVEL[i['severity']]>=2 and i['repair_target'] in ('video_shot','storyboard_image') for i in issues):
        return 'REGENERATE'
    if any(LEVEL[i['severity']]>=1 or i['repair_target']=='unresolved' for i in issues): return 'REVISE'
    if any(LEVEL[u['potential_severity']]>=1 for u in uncertainties): return 'REVISE'
    return 'PASS'

def pair_errors(inp,out,schema,static_pair):
    errors=input_errors(inp,schema)+schema(out,'animatic-output.schema.json')
    if errors: return errors
    preview=inp.get('review_profile','spec_fidelity')=='story_preview'
    if inp.get('review_profile','spec_fidelity')!=out.get('review_profile','spec_fidelity'):
        errors.append('review_profile mismatch; historical reports cannot be reinterpreted')
    shots={s['shot_id']:s for s in inp['shots']}; ids=list(shots)
    seq=inp.get('expected_sequence',ids); index={sid:n for n,sid in enumerate(seq)}
    cov=out['coverage']; duration=cov['duration_seconds']; video=inp['video']
    issues=out['issues']; uncertain=out['uncertainties']
    if out['video_id']!=video['video_id']: errors.append('video_id does not match input')
    sr={s['shot_id']:s for s in out['shot_reviews']}
    if set(sr)!=set(ids) or len(sr)!=len(out['shot_reviews']): errors.append('shot_reviews must cover each expected shot once')
    known={video['video_id']:('video',video['version'])}
    known.update({sid+'_SPEC':('shot_spec',s['spec_version']) for sid,s in shots.items()})
    if preview:
        known.update({sid+'_IMAGE_PROMPT':('image_prompt',s.get('image_prompt_version')) for sid,s in shots.items() if (s.get('image_prompt') or '').strip()})
        known.update({sid+'_PREVIEW_INSTRUCTION':('preview_prompt',None) for sid,s in shots.items() if (s.get('preview_instruction') or '').strip()})
        if inp.get('preview_prompt'): known['preview_prompt']=('preview_prompt',None)
    known.update({s['image']['image_id']:('image',None) for s in shots.values() if s.get('image')})
    known.update({a['asset_id']:('asset',a.get('version')) for a in inp.get('assets',[])})
    if inp.get('story_context'): known['story_context']=('story',None)
    prior=inp.get('persistent_visual_state')
    historical=[]
    if prior:
        for f in prior['facts']:
            known[f['fact_id']]=('persistent_state',None)
            historical.extend(f['evidence'])
            for e in f['evidence']: known.setdefault(e['source_ref'],(e['source_type'],e.get('source_version')))
    samples=cov['visual_samples']; inspected={s['timestamp'] for s in samples if s['inspected']}
    for t in [s['timestamp'] for s in samples]:
        if duration is not None and t>duration: errors.append('visual sample outside video duration')
        if not inside(t,cov['decoded_ranges']): errors.append('visual sample outside decoded coverage')
    for ranges in walk(out,'segments'):
        for r in ranges:
            if r['end']<=r['start'] or (duration is not None and r['end']>duration+0.001): errors.append('invalid segment time range')
    for r in list(walk(out,'time_range'))+cov['decoded_ranges']+cov['audio']['checked_ranges']:
        if r['end']<r['start'] or (duration is not None and r['end']>duration+0.001): errors.append('invalid evidence/coverage time range')
    for e in evidence({k:v for k,v in out.items() if k!='static_reviews'}):
        kind=e['source_type']; ref=e['source_ref']
        if ref not in known:
            errors.append(f'unknown evidence source: {ref}'); continue
        expected,version=known[ref]
        if kind in ('video_frame','audio_segment'):
            if ref!=video['video_id']: errors.append('media evidence must refer to this video')
        elif kind!=expected: errors.append(f'evidence type mismatch: {ref}')
        if version is not None and e.get('source_version')!=version: errors.append(f'stale or missing evidence version: {ref}')
        if kind=='image' and ref not in cov['inspected_image_ids'] and e not in historical: errors.append(f'image not inspected: {ref}')
        if kind=='video_frame' and not any(abs(e['timestamp']-t)<1e-6 for t in inspected): errors.append('video evidence not in inspected samples')
        if kind=='audio_segment':
            audio=cov['audio']
            if audio['method'] not in ('listened','semantic_tool','decoded_silence'): errors.append('audio content evidence without audio inspection')
            if not all(inside(e['time_range'][k],audio['checked_ranges']) for k in ('start','end')): errors.append('audio evidence outside checked coverage')
    if any(i not in known or known[i][0]!='image' for i in cov['inspected_image_ids']): errors.append('unknown inspected image')
    if any(i not in ids for i in cov['verified_shot_ids']): errors.append('unknown verified shot')
    if len({i['issue_id'] for i in issues})!=len(issues): errors.append('duplicate issue_id')
    if len({u['finding_id'] for u in uncertain})!=len(uncertain): errors.append('duplicate finding_id')
    for item in issues+uncertain:
        if any(sid not in ids for sid in item['shot_ids']): errors.append('finding references unknown shot')
    def has_unc(layer,sid=None):
        return any(layer in u['layers'] and (sid is None or not u['shot_ids'] or sid in u['shot_ids']) and LEVEL[u['potential_severity']]>=1 for u in uncertain)
    for i in issues:
        media=[e for e in i['evidence'] if e['source_type'] in ('video_frame','audio_segment')]
        if i['repair_target']!='storyboard_image' and not media: errors.append('video issue requires actual media evidence')
        if i['repair_target']=='storyboard_image' and not any(e['source_type']=='image' for e in i['evidence']): errors.append('source image error requires image evidence')
        if i['repair_target']=='storyboard_image':
            kind='image_prompt' if preview else 'shot_spec'
            if not any(e['source_type']==kind for e in i['evidence']): errors.append('source image error requires corresponding review basis evidence')
            if preview and not any(e['source_type']=='image_prompt' and e['source_ref'] in [sid+'_IMAGE_PROMPT' for sid in i['shot_ids']] for e in i['evidence']): errors.append('source image error refers to another shot prompt')
        if preview and i['repair_target']=='audio': errors.append('audio is excluded from story_preview review')
        if i['repair_action']=='regenerate' and (i['repair_target'] not in ('storyboard_image','video_shot') or LEVEL[i['severity']]<2): errors.append('regeneration requires confirmed high-impact image repair')
        if 'dynamic_execution_consistency' in i['layers'] and len({e['timestamp'] for e in media if e['source_type']=='video_frame'})<2:
            errors.append('dynamic conclusion requires at least two inspected timestamps')
        for e in media:
            if e['source_type']=='video_frame' and not inside(e['timestamp'],[i['time_range']]): errors.append('issue frame outside issue time range')
    for layer in LAYERS:
        expected='FAIL' if any(layer in i['layers'] for i in issues) else ('uncertain' if any(layer in u['layers'] for u in uncertain) else 'PASS')
        if out['animatic_review'][layer]!=expected: errors.append(f'inconsistent layer result: {layer}')
    for sid,r in sr.items():
        if sid not in shots: continue
        if r['mapping_status']=='confirmed':
            if not r['segments'] or sid not in cov['verified_shot_ids']: errors.append('confirmed mapping must have verified segments')
            for seg in r['segments']:
                if len([t for t in inspected if inside(t,[seg])])<2: errors.append('confirmed shot needs temporal visual inspection')
        elif not has_unc(LAYERS[2],sid) and not any(sid in i['shot_ids'] and LAYERS[2] in i['layers'] for i in issues):
            errors.append('unverified or missing mapping requires a finding')
        if r['anchor_time'] is not None:
            if not inside(r['anchor_time'],r['segments']) or r['anchor_time'] not in inspected: errors.append('anchor must be an inspected timestamp in matched shot')
        if r[LAYERS[0]]=='PASS':
            img=shots[sid].get('image')
            if not img or img['image_id'] not in cov['inspected_image_ids'] or r['anchor_time'] is None: errors.append('visual anchor PASS requires inspected source and matched reference moment')
        basis_missing = not any([shots[sid].get('shot_spec'),shots[sid].get('preview_instruction'),inp.get('preview_prompt')]) if preview else shots[sid]['shot_spec'] is None
        if basis_missing and not has_unc(LAYERS[1],sid): errors.append('missing action review basis requires uncertainty')
        if preview and r['source_image_compliance']!='not_applicable' and not (shots[sid].get('image_prompt') or '').strip():
            if r['source_image_compliance']!='uncertain' or not has_unc(LAYERS[0],sid): errors.append('source image compliance needs prompt or explicit uncertainty')
        for layer in LAYERS:
            expected='FAIL' if any(sid in i['shot_ids'] and layer in i['layers'] for i in issues) else ('uncertain' if any(sid in u['shot_ids'] and layer in u['layers'] for u in uncertain) else 'PASS')
            if r[layer]!=expected: errors.append(f'inconsistent shot layer: {sid}/{layer}')
    if cov['mapping_complete'] and any(r['mapping_status']!='confirmed' for r in sr.values()): errors.append('mapping_complete contradicts shot mapping')
    if cov['mapping_complete']:
        segments=sorted([(seg['start'],seg['end'],sid) for sid,r in sr.items() for seg in r['segments']])
        actual=[s[2] for s in segments]
        if (actual!=seq or not covered([{'start':s[0],'end':s[1]} for s in segments],duration)) and not any(LAYERS[2] in i['layers'] for i in issues) and not has_unc(LAYERS[2]):
            errors.append('sequence mismatch or unmapped footage requires sequence finding')
        if any(a[1]>b[0]+0.001 for a,b in zip(segments,segments[1:])) and not has_unc(LAYERS[2]) and not any(LAYERS[2] in i['layers'] for i in issues):
            errors.append('overlapping shot mappings require transition/mapping finding')
    if (not cov['mapping_complete'] or not covered(cov['decoded_ranges'],duration)) and not has_unc(LAYERS[2]): errors.append('incomplete mapping or decode coverage requires uncertainty')
    audio=cov['audio']
    if preview:
        if audio!={'status':'not_applicable','method':'skipped_by_scope','checked_ranges':[],'evidence':[]}:
            errors.append('story_preview audio must be skipped, not PASS or uncertain')
    elif audio['status']=='not_applicable' or audio['method']=='skipped_by_scope':
        errors.append('legacy audio scope cannot be silently skipped')
    if audio['method']=='unavailable' and audio['status']!='uncertain': errors.append('unavailable audio cannot pass/fail content check')
    if audio['status']=='PASS' and not covered(audio['checked_ranges'],duration): errors.append('audio PASS requires full coverage')
    if audio['method'] in ('listened','semantic_tool','decoded_silence') and audio['status']!='uncertain' and not audio['evidence']: errors.append('audio judgment requires evidence')
    if audio['status']=='uncertain' and not has_unc(LAYERS[2]): errors.append('unverified audio requires material sequence uncertainty')
    if audio['status']=='FAIL' and not any(LAYERS[2] in i['layers'] and any(e['source_type']=='audio_segment' for e in i['evidence']) for i in issues): errors.append('audio failure requires sound evidence issue')
    expected=verdict(issues,uncertain)
    if out['animatic_review']['overall_result']!=expected: errors.append('Animatic verdict inconsistent with findings/repairability')
    overall=expected
    for static in out.get('static_reviews',[]):
        sid=static['shot_id']
        if sid not in shots: errors.append('static review references unknown shot'); continue
        p={'schema_version':'1.0','current':{k:v for k,v in shots[sid].items() if k not in ('preview_instruction','anchor_position','continuity_from_previous','continuity_basis')}}
        p.update({k:inp[k] for k in ('assets','story_context') if k in inp})
        # A cached static report retains its original profile, including legacy reports.
        if 'review_profile' in static: p['review_profile']=static['review_profile']
        if static['coverage']['continuity_basis'] in ('adjacent','both'):
            position=index[sid]
            for field,offset in [('previous',-1),('next',1)]:
                n=position+offset
                if 0<=n<len(seq):
                    p[field]={k:v for k,v in shots[seq[n]].items() if k not in ('preview_instruction','anchor_position','continuity_from_previous','continuity_basis')}
            p['continuity_context']={'previous_to_current':shots[sid].get('continuity_from_previous','unknown'),
                                     'current_to_next':shots[seq[position+1]].get('continuity_from_previous','unknown') if position+1<len(seq) else 'unknown',
                                     'basis':shots[sid].get('continuity_basis','智能分镜输入中的连续关系')}
        # Supplied full reports are rechecked against the corresponding image/Spec.
        errors+=static_pair(p,static)
        rank={'PASS':0,'REVISE':1,'REGENERATE':2}
        if rank[static['overall_result']]>rank[overall]: overall=static['overall_result']
        if sid in sr and sr[sid]['source_image_compliance']!=static['current_shot_compliance']: errors.append('source image compliance differs from static report')
    if out['overall_result']!=overall: errors.append('overall verdict inconsistent with static/Animatic findings')
    errors+=state_errors(inp,out,shots,index,inspected)
    return errors

def state_errors(inp,out,shots,index,inspected):
    errors=[]; before=inp.get('persistent_visual_state'); last=-1.0
    for snap in out['state_snapshots']:
        sid=snap['shot_id']; t=snap['timestamp']; state=snap['state']
        if sid not in shots: errors.append('state snapshot references unknown shot'); continue
        if t<last or t not in inspected: errors.append('state snapshot must advance through inspected media timestamps')
        last=t
        if state['through_shot_id']!=sid or state['scene_id']!=shots[sid]['scene_id']: errors.append('snapshot scene/through_shot mismatch')
        sr=next((r for r in out['shot_reviews'] if r['shot_id']==sid),None)
        if not sr or sr['mapping_status']!='confirmed' or not inside(t,sr['segments']): errors.append('state requires verified shot mapping')
        old={f['fact_id']:f for f in (before or {}).get('facts',[])}; new={f['fact_id']:f for f in state['facts']}
        if len(new)!=len(state['facts']): errors.append('duplicate persistent fact')
        transition=shots[sid].get('continuity_from_previous','unknown')
        same_shot=before and before['through_shot_id']==sid
        new_scene=before and not same_shot and (transition=='new_scene' or (before['scene_id'] is not None and state['scene_id'] is not None and before['scene_id']!=state['scene_id']))
        if before and not same_shot and not new_scene and transition=='unknown' and not any(sid in u['shot_ids'] and 'shot_sequence_consistency' in u['layers'] for u in out['uncertainties']):
            errors.append('inheriting state across unknown narrative continuity requires uncertainty')
        for e in evidence(snap):
            owner=next((s for s in shots if e['source_ref'] in (s+'_SPEC',s+'_IMAGE_PROMPT',s+'_PREVIEW_INSTRUCTION') or (shots[s].get('image') and e['source_ref']==shots[s]['image']['image_id'])),None)
            if owner and index[owner]>index[sid]: errors.append('future source used in earlier state snapshot')
        invalid={x['fact_id'] for x in snap['state_invalidations']}
        changes={x['fact_id']:x for x in snap['state_changes']}
        checks={x['fact_id']:x for x in snap['visibility_checks']}
        for fid,f in new.items():
            for key in ('established_at_shot_id','last_confirmed_at_shot_id'):
                if f[key] in index and index[f[key]]>index[sid]: errors.append('future shot fact leaked into earlier snapshot')
            if any(e['source_type']=='video_frame' and e['timestamp']>t for e in f['evidence']): errors.append('future frame fact leaked into earlier snapshot')
            related=[i for i in out['issues'] if fid in i['fact_ids'] and sid in i['shot_ids']]
            failed=any(inside(t,[i['time_range']]) for i in related)
            bad_evidence=any(e['source_type']=='video_frame' and inside(e['timestamp'],[i['time_range']]) for e in f['evidence'] for i in related)
            if bad_evidence: errors.append('failed video frame cannot support a persistent fact')
            if fid in old and any(f[k]!=old[fid][k] for k in ('entity_id','property','scope','established_at_shot_id')):
                errors.append('persistent fact identity/provenance must not be rewritten')
            if fid in old and f['value']!=old[fid]['value']:
                change=changes.get(fid)
                kinds=('shot_spec','story','image_prompt','preview_prompt') if inp.get('review_profile')=='story_preview' else ('shot_spec','story')
                if not change or not any(e['source_type'] in kinds for e in change['evidence']): errors.append('state change lacks authored authorization')
            if new_scene and fid in old and old[fid]['scope']=='scene': errors.append('new scene retained unrelated environment fact')
            if f['last_confirmed_at_shot_id']==sid and f!=old.get(fid):
                c=checks.get(fid)
                if failed or not c or c['assessment']!='consistent': errors.append('unverified/hidden/failed fact cannot be re-confirmed')
                if not any(e['source_type']=='video_frame' and e['timestamp']<=t for e in f['evidence']): errors.append('video confirmation needs inspected frame evidence')
            if f['basis']=='specified' and f['last_confirmed_at_shot_id'] is not None: errors.append('specified-only state cannot claim observed confirmation')
        for fid,f in old.items():
            if fid not in new and fid not in invalid and not new_scene: errors.append('offscreen facts must persist or be explicitly invalidated')
        before=state
    final=out['persistent_visual_state']
    if final['through_shot_id'] not in shots and (before is None or final['through_shot_id']!=before['through_shot_id']): errors.append('final state references unknown shot')
    if before is not None and final!=before: errors.append('final persistent state must equal latest verified snapshot or unchanged input state')
    if before is None and final['facts']: errors.append('nonempty video state requires verified state snapshots')
    return errors
