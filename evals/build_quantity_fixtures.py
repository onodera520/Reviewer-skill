"""Build original controlled diagrams, not reproductions of a user's image.

Run only when maintaining fixtures. Evaluators receive inputs.json and media,
never this builder or truth.json. No production review code is modified.
"""
import json
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent / 'quantity'

def box(draw, x, y, details=False):
    # One closed container: lid rim, single body, base, and connected sides.
    draw.polygon([(x,y+20),(x+300,y+20),(x+280,y+100),(x+20,y+100)], fill='#c8c6b4', outline='#303a40', width=4)
    draw.polygon([(x,y+20),(x+35,y-15),(x+285,y-15),(x+300,y+20)], fill='#e4e7d8', outline='#303a40', width=4)
    draw.line([(x,y+20),(x+300,y+20)], fill='#25323b', width=8)
    draw.line([(x+20,y+100),(x+280,y+100)], fill='#25323b', width=8)
    if details:
        draw.line([(x+110,y-13),(x+105,y+20)], fill='#8c9187', width=4)
        draw.line([(x+210,y-13),(x+220,y+20)], fill='#8c9187', width=4)
        draw.polygon([(x+160,y-15),(x+185,y-15),(x+188,y+20),(x+177,y+98),(x+152,y+98),(x+162,y+20)], fill='#b27c59')
        draw.rectangle((x+45,y+36,x+125,y+65), fill='#faf5df', outline='#777777', width=2)
        draw.line([(x+218,y+31),(x+270,y+39)], fill='white', width=5)
        draw.line([(x+215,y+43),(x+262,y+51)], fill='#e8eadc', width=3)

def build(ffmpeg):
    media=ROOT/'media'; media.mkdir(parents=True,exist_ok=True)
    for key in ('q01','q02','q03','q04'):
        im=Image.new('RGB',(1000,720),'#e7e2d8'); d=ImageDraw.Draw(im)
        d.rectangle((0,585,1000,720), fill='#a3937e')
        if key=='q04':
            for x,y in ((150,190),(560,190),(150,410),(560,410)): box(d,x,y)
        else:
            box(d,350,450,key=='q02'); box(d,350,330,key=='q02')
        if key=='q03':
            # Opaque foreground: hides lid/base connections, so visible stripes
            # cannot establish an exact object count.
            d.rectangle((310,255,690,430),fill='#747f88')
            d.rectangle((310,448,690,565),fill='#747f88')
        im.save(media/(key+'.png'))
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-y',
        '-loop','1','-framerate','4','-i',str(media/'q03.png'),'-t','1',
        '-an','-c:v','ffv1',str(media/'q05.mkv')],check=True)
    prompt='柜台上放着两盒独立包装的便当，分别交给两位等候者，每人一盒；数量是交接的关键事实。'
    inputs=[{'case_id':k,'image_ref':'media/'+k+'.png','image_prompt':prompt} for k in ('q01','q02','q03','q04')]
    inputs.append({'case_id':'q05','video_ref':'media/q05.mkv','image_ref':'media/q03.png','image_prompt':prompt,
        'preview_instruction':'便当镜头保持静止，供确认交接前的道具状态。'})
    (ROOT/'inputs.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2),encoding='utf-8')
    truth={'provenance':'Original controlled diagrams; not user failure images.', 'cases':[
        {'case_id':'q01','physical_count':2,'expected':'PASS','reason':'Two bodies, four rim/base lines; do not count lines.'},
        {'case_id':'q02','physical_count':2,'expected':'PASS','reason':'Compartments, bands, labels and highlights belong to the same two bodies.'},
        {'case_id':'q03','physical_count':2,'expected':'uncertain / REVISE','reason':'Exact count cannot be established through opaque foreground; hidden truth is not observation.'},
        {'case_id':'q04','physical_count':4,'expected':'FAIL / high / REGENERATE','reason':'Four separate complete bodies contradict plot-critical two-box requirement.'},
        {'case_id':'q05','physical_count':2,'expected':'uncertain / REVISE','reason':'Repeated occluded source contributes no new count information.'}]}
    (ROOT/'truth.json').write_text(json.dumps(truth,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Created 4 controlled diagrams and 1 repeated-source video.')

if __name__=='__main__': build(sys.argv[1])
