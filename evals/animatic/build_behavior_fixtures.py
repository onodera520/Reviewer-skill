"""Original synthetic visual cases. Answer key is separate from blinded inputs.

Reuses only drawing function ASTs from the static fixture builder; importing that
builder would overwrite existing static evaluation artifacts, so do not import it.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
def build(ffmpeg,ffprobe):
    tree=ast.parse((ROOT/'evals'/'build_fixtures.py').read_text(encoding='utf-8-sig'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('room','character','bag')]
    from PIL import ImageEnhance,ImageFilter
    scope={'Image':Image,'ImageDraw':ImageDraw,'ImageEnhance':ImageEnhance,'ImageFilter':ImageFilter,'W':1200,'H':720}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'fixture_drawing','exec'),scope)
    room=scope['room']
    spec=importlib.util.spec_from_file_location('media',ROOT/'scripts'/'prepare_animatic.py')
    media=importlib.util.module_from_spec(spec); spec.loader.exec_module(media)
    base=ROOT/'evals'/'animatic'; inputs=[]; truth=[]
    def push(im,amount):
        w,h=im.size; inset=int(w*amount)
        return im.crop((inset,int(inset*h/w),w-inset,h-int(inset*h/w))).resize((600,360))
    for label in ('anchor','drift','dissolve','source','audio'):
        key=hashlib.sha256(('animatic-'+label).encode()).hexdigest()[:10]
        folder=base/'fixtures'/key; folder.mkdir(parents=True,exist_ok=True)
        image=room(stock=label!='source')
        wide=[push(image,n*.001) for n in range(10)]
        if label=='drift': wide[6:]=[push(room(stock=False),n*.001) for n in range(6,10)]
        close=image.crop((380,250,720,550)).resize((600,360))
        frames=wide+[close]*10
        if label=='dissolve':
            frames[8:12]=[Image.blend(wide[7],close,a) for a in (.2,.4,.6,.8)]
        for n,im in enumerate(frames): im.save(folder/f'frame-{n:03d}.png')
        frames[5].save(folder/'reference-1.png'); close.save(folder/'reference-2.png')
        args=[ffmpeg,'-hide_banner','-v','error','-nostdin','-y','-framerate','10','-i',str(folder/'frame-%03d.png')]
        if label=='audio': args+=['-f','lavfi','-i','sine=frequency=700:sample_rate=16000:duration=2','-c:a','pcm_s16le']
        args+=['-c:v','ffv1',str(folder/'preview.mkv')]; subprocess.run(args,check=True)
        inp={'schema_version':'1.0','review_mode':'animatic','video':{'video_id':'V_'+key,'ref':str(folder/'preview.mkv'),'version':'1'},
             'shots':[
                {'shot_id':'S1','scene_id':'STORE','spec_version':'1','clip_id':'CLIP1','image_number':1,
                 'shot_spec':'夜间便利店。蓝外套人物右手持两个便当袋，位于柜台前；右后景三层货架摆满商品。人物静止停顿；轻微向前推近。',
                 'image':{'image_id':'I1','ref':str(folder/'reference-1.png')},'anchor_position':'representative',
                 'preview_instruction':'轻微推近，人物保持停顿；参考图对应本镜约中间状态。'},
                {'shot_id':'S2','scene_id':'STORE','spec_version':'1','clip_id':'CLIP2','image_number':2,
                 'shot_spec':'接上镜，同一人物与状态，近景裁切；人物静止停顿。',
                 'image':{'image_id':'I2','ref':str(folder/'reference-2.png')},'anchor_position':'representative',
                 'continuity_from_previous':'continuous','continuity_basis':'剧情明确紧接上镜；跨 Clip 但仍在同一场景。'}],
             'expected_sequence':['S1','S2'], 'provided_segments':[{'shot_id':'S1','time_range':{'start':0,'end':1}}, {'shot_id':'S2','time_range':{'start':1,'end':2}}],
             'story_context':'人物保持原地和既有持物状态。没有清空货架、更换服装或交接动作。智能分镜硬切；无台词、音乐或字幕，环境音效允许。'}
        path=folder/'input.json'; path.write_text(json.dumps(inp,ensure_ascii=False,indent=2),encoding='utf-8'); inputs.append(str(path))
        dest=base/'results'/('prepared-'+key)
        if not dest.exists(): media.prepare(folder/'preview.mkv',dest,ffmpeg=ffmpeg,ffprobe=ffprobe,dense_ranges=[{'start_seconds':0,'end_seconds':2}],anchor_times=[.5,1.5])
        man=json.loads((dest/'manifest.json').read_text(encoding='utf-8'))
        montage=Image.new('RGB',(1200,4*206),'white'); d=ImageDraw.Draw(montage)
        for n,f in enumerate(man['extracted_frames']):
            thumb=Image.open(f['ref']).resize((240,144)); x=(n%5)*240;y=(n//5)*206
            montage.paste(thumb,(x,y)); d.text((x+6,y+149),f"{f['time_seconds']:.3f} s",fill='black')
        montage.save(dest/'contact.png')
        truth.append({'input':str(path),'prepared':str(dest/'manifest.json'),'contact':str(dest/'contact.png'),
                      'case':label,'expected':{'anchor':'PASS','drift':'REGENERATE','dissolve':'REVISE','source':'REGENERATE','audio':'REVISE'}[label]})
    (base/'blind-inputs.json').write_text(json.dumps({'inputs':inputs},ensure_ascii=False,indent=2),encoding='utf-8')
    (base/'behavior-truth.json').write_text(json.dumps(truth,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(truth),'truth':str(base/'behavior-truth.json')},ensure_ascii=False))
if __name__=='__main__': build(sys.argv[1],sys.argv[2])
