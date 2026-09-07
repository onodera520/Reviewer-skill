"""Build original, deterministic static diagrams and blind review inputs.

Requires Pillow. This is test-material generation, not an image reviewer.
Do not expose this script or cases.json to a blinded evaluator.
All artwork is original synthetic test artwork; no third-party images are used.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent
FIX = ROOT / "fixtures"
FIX.mkdir(exist_ok=True)
W, H = 1200, 720


def opaque(prefix, name):
    return prefix + hashlib.sha256(name.encode()).hexdigest()[:12]


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def character(d, x, *, blue=True, bags=2, handed="right", bound=False,
              standing=True, back=False, wound=False):
    coat = "#244761" if blue else "#b44d3d"
    hair = "#152632" if blue else "#63362f"
    cy = 316 if standing else 377
    if not standing:
        d.rectangle((x-64, 367, x+64, 513), fill="#946542", outline="#422f28", width=5)
        d.rectangle((x-67, 510, x+69, 530), fill="#946542", outline="#422f28", width=4)
        for xx in (x-52, x+50):
            d.line((xx, 527, xx, 618), fill="#422f28", width=11)
    d.rounded_rectangle((x-43, cy+48, x+43, cy+167), 12, fill=coat, outline="#12232c", width=4)
    if standing:
        for xx in (x-24, x+24):
            d.line((xx, cy+161, xx, 596), fill="#26313c", width=23)
            d.rounded_rectangle((xx-16, 586, xx+23, 608), 7, fill="#14212c")
    else:
        for direction in (-1, 1):
            d.line((x+direction*21, cy+139, x+direction*50, 549), fill="#26313c", width=24)
            d.line((x+direction*50, 549, x+direction*50, 603), fill="#26313c", width=21)
            d.rectangle((x+direction*50-14, 596, x+direction*50+22, 614), fill="#14212c")
    for direction in (-1, 1):
        hx = x + direction*66
        d.line((x+direction*33, cy+66, hx, cy+135), fill=coat, width=22)
        d.ellipse((hx-12, cy+128, hx+12, cy+154), fill="#dfb38f", outline="#6f5440", width=2)
    d.ellipse((x-36, cy-5, x+36, cy+66), fill="#dfb38f", outline="#2b2325", width=3)
    if blue:
        d.pieslice((x-37, cy-12, x+37, cy+43), 175, 365, fill=hair)
    else:
        d.arc((x-41, cy-8, x+41, cy+76), 170, 365, fill=hair, width=16)
    if back:
        d.ellipse((x-34, cy-3, x+34, cy+58), fill=hair)
    else:
        for dx in (-12, 12):
            d.ellipse((x+dx-3, cy+24, x+dx+3, cy+31), fill="#252526")
        d.line((x-8, cy+44, x+8, cy+44), fill="#7d4b3c", width=2)
    if wound:
        d.line((x+20, cy+32, x+29, cy+46), fill="#b11222", width=5)
    if bound:
        for yy in (cy+84, cy+98, cy+112):
            d.line((x-55, yy, x+55, yy), fill="#d2aa67", width=10)
        d.line((x-50, 569, x+50, 569), fill="#d2aa67", width=9)
    if bags:
        side = -1 if handed == "right" else 1
        for i in range(bags):
            bag(d, x+side*66 + (i*28 if side>0 else -i*28), cy+153, i)


def bag(d, x, y, i=0):
    d.arc((x-14, y-12, x+14, y+16), 180, 360, fill="#e6dcc5", width=6)
    d.rounded_rectangle((x-22, y, x+22, y+63), 4,
                        fill="#f5dd99" if not i else "#f5bf77", outline="#685738", width=3)
    d.rectangle((x-14, y+20, x+14, y+36), fill="#bc6046")


def room(*, stock=True, texture=False, occluded=False, blurred=False, reverse=False,
         swapped=False, bags=2, handed="right", placed=False, bound=False,
         seated=False, day=False, bright=False, damaged=False, wound=False,
         blue=True, new_scene=False, door_open=False, light_on=True):
    im = Image.new("RGB", (W, H), "#d7ded9")
    d = ImageDraw.Draw(im)
    d.polygon([(0,0),(W,0),(W,560),(0,560)], fill="#aabbbc" if not new_scene else "#ddc2a8")
    d.rectangle((0,560,W,H), fill="#8b9697")
    for x in range(-400,1700,200):
        d.line((600,550,x,720), fill="#6d7f80", width=2)
    for y in (594,649,715):
        d.line((0,y,W,y), fill="#6d7f80", width=2)
    # Physical environment anchors: entrance and window on one wall, shelves on the other.
    d.rectangle((15,205,123,559), fill="#506b70", outline="#2f414a", width=8)
    if door_open:
        d.polygon([(20,208),(95,245),(95,552),(20,558)], fill="#172c39", outline="#1d303a")
        d.line((94,245,94,550), fill="#849b9e", width=7)
    else:
        d.rectangle((35,230,101,390), fill="#263a57" if not day else "#accfec")
        d.ellipse((96,422,104,430), fill="#cbd2ac")
    d.rectangle((155,115,350,278), fill="#34567a" if not day else "#b6dfee", outline="#384d55", width=9)
    if day:
        d.ellipse((282,137,322,177), fill="#fff2ab")
        d.polygon([(167,263),(220,218),(280,267)], fill="#84b08c")
    else:
        d.ellipse((290,139,317,166), fill="#d9e0ce")
        for x,y in [(180,143),(223,160),(265,193),(198,232)]:
            d.ellipse((x,y,x+3,y+3), fill="#e5e2c9")
    d.line((252,118,252,275), fill="#384d55", width=7)
    d.line((158,196,347,196), fill="#384d55", width=7)
    if damaged:
        pts=[(268,146),(286,181),(266,208),(305,224),(281,261)]
        d.line(pts, fill="#f0f6ef", width=5)
        d.line((286,181,332,162), fill="#f0f6ef", width=4)
        d.line((266,208,257,245), fill="#f0f6ef", width=3)
        d.polygon([(280,225),(311,232),(288,253)], fill="#162c3d")
    d.rounded_rectangle((445,35,775,65), 10, fill="#f2f5e9" if light_on else "#687579", outline="#54686c", width=4)
    if light_on:
        d.line((475,76,475,97),fill="#e4ece4",width=3)
        d.line((745,76,745,97),fill="#e4ece4",width=3)
    sx0,sx1 = (805,1160) if not new_scene else (885,1160)
    d.rectangle((sx0,207,sx1,550), fill="#576b72", outline="#243b46", width=8)
    for yy in (315,425,536):
        d.rectangle((sx0+9,yy,sx1-9,yy+13), fill="#bdc8c4", outline="#324b58", width=3)
    if stock:
        for row, yy in enumerate((305,415,526)):
            for col in range(7 if not new_scene else 5):
                xx=sx0+20+col*45
                color=["#df9564","#a8bd63","#75aec2","#d4bd69"][(row+col+(1 if texture else 0))%4]
                ht=57+(col%2)*12
                if texture: ht+=4 if col%2 else -3
                if row%2:
                    d.rectangle((xx,yy-ht,xx+29,yy), fill=color, outline="#344b52", width=2)
                    d.rectangle((xx+4,yy-ht+18,xx+25,yy-ht+24), fill="#eee5cd")
                else:
                    d.rounded_rectangle((xx,yy-ht,xx+26,yy),5,fill=color,outline="#344b52",width=2)
                    d.rectangle((xx+7,yy-ht-9,xx+20,yy-ht+1),fill="#d9e0d4")
                    d.rectangle((xx+3,yy-34,xx+23,yy-22),fill="#ece1c2")
    d.rectangle((440,205,645,385),fill="#7a989c",outline="#304b57",width=7)
    d.rectangle((455,220,630,360),fill="#c4d8d1",outline="#55727b",width=3)
    d.line((542,221,542,360),fill="#62777a",width=4)
    # Counter and asymmetrical register establish stable world anchors.
    d.polygon([(292,420),(735,420),(775,461),(260,461)],fill="#d3b28d",outline="#433f3a")
    d.rectangle((260,462,775,559),fill="#797266",outline="#433f3a",width=4)
    d.rectangle((660,382,720,420),fill="#263e48",outline="#15252e",width=3)
    d.rectangle((668,388,711,409),fill="#82a39a")
    if reverse:
        # Stylized opposite-side projection; persistent anchors and character poses
        # are reversed together, and back-of-head views make viewpoint explicit.
        pass
    ax,bx=(384,635) if not swapped else (635,384)
    character(d,bx,blue=False,bags=0,back=reverse)
    character(d,ax,blue=blue,bags=bags,handed=handed,bound=bound,
              standing=not seated,back=reverse,wound=wound)
    if placed:
        bag(d,530,366)
        bag(d,575,366,1)
    if occluded:
        # Solid foreground display blocks the stock-bearing region, not a label.
        d.polygon([(775,180),(W,158),(W,630),(775,638)],fill="#e8c99f",outline="#614f40")
        d.line((792,197,792,620),fill="#f7e3c3",width=6)
        d.rectangle((860,265,1082,442),fill="#c4835f",outline="#6b5545",width=6)
        d.ellipse((919,300,1019,400),fill="#ecd3a5",outline="#6b5545",width=4)
    if blurred:
        region=im.crop((sx0+3,210,sx1-3,550)).filter(ImageFilter.GaussianBlur(36))
        im.paste(region,(sx0+3,210))
        # Deliberately strong defocus ensures item occupancy is unassessable.
        haze=Image.new("RGB",region.size,"#8b9692")
        region=Image.blend(region,haze,.8)
        im.paste(region,(sx0+3,210))
    if reverse:
        im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if bright:
        im=ImageEnhance.Brightness(im).enhance(1.045)
    return im


IMAGES={}


def picture(name, **opts):
    im=room(**opts)
    if name == "face":
        im=im.crop((309,291,461,439)).resize((W,H),Image.Resampling.LANCZOS)
    elif name == "upper":
        im=im.crop((235,268,747,440)).resize((W,H),Image.Resampling.LANCZOS)
    fname=opaque("v",name)+".png"
    im.save(FIX/fname)
    IMAGES[name]=fname


for name,opts in {
    "base":{},"empty":{"stock":False},"face":{},"upper":{},
    "covered":{"occluded":True},"blurred":{"blurred":True},"texture":{"texture":True},
    "no_bags":{"bags":0},"placed":{"bags":0,"placed":True},
    "other_hand":{"handed":"left"},"one_bag":{"bags":1},
    "changed_coat":{"blue":False},"bound":{"bound":True,"seated":True,"bags":0},
    "free":{"bags":0},"reverse":{"reverse":True},"swapped":{"swapped":True},
    "day":{"day":True},"brighter":{"bright":True},"broken":{"damaged":True},
    "wound":{"wound":True},"other_store":{"new_scene":True},
    "open_door":{"door_open":True},"lights_off":{"light_on":False}
}.items(): picture(name,**opts)


BASE_SPEC="便利店内部，同一连续夜间场景。静态全景，柜台、左墙入口及窗、柜台另一端的三层金属货架可见。林默为短黑发深蓝外套人物，苏晴为棕色短发红褐上衣人物；林默在靠窗端，苏晴在靠货架端。当前静态画面是两人停留交谈。"


def shot(sid,img="base",spec=BASE_SPEC,scene="STORE",version="v1"):
    return {"shot_id":sid,"scene_id":scene,"spec_version":version,"shot_spec":spec,
            "image":{"image_id":sid+"_IMAGE","ref":IMAGES[img]}}


def inp(prev="base",cur="base",pspec=BASE_SPEC,cspec=BASE_SPEC,scene="STORE",**extra):
    result={"schema_version":"1.0","current":shot("SHOT_02",cur,cspec,scene),
            "previous":shot("SHOT_01",prev,pspec),
            "continuity_context":{"previous_to_current":"continuous","current_to_next":"unknown",
                                  "basis":"前后两镜处于同一场景、同一段连续交谈；未描述中断、时间跳跃或未列出的状态变化。"}}
    result.update(extra)
    return result


def state(value="摆满饮料和零食",through="SHOT_01", image="SHOT_01_IMAGE", version="v1"):
    return {"schema_version":"1.0","scene_id":"STORE","continuity_segment_id":"STORE_CONT_01",
            "through_shot_id":through,"coverage_start_shot_id":"SHOT_01","facts":[{
                "fact_id":"F_SHELF_STOCK","entity_id":"SHELF_A","category":"background_object_state",
                "scope":"scene","property":"stocking_state","value":value,
                "world_anchor":"柜台收银机端后方、与入口窗墙相对的墙边","importance":"high",
                "basis":"observed","established_at_shot_id":"SHOT_01","last_confirmed_at_shot_id":"SHOT_01",
                "evidence":[{"source_type":"image","source_ref":image,"locator":"三层金属货架各层陈列区域",
                             "observation":"各层有明显商品陈列；已核验图像版本 "+version+"。"}]}]}


CASES=[]


def case(key,title,data,overall,compliance,continuity,*,errors=(),severity=None,
         kind="synthetic_visual",checks=(),forbidden=(),tags=()):
    fid=opaque("i",key)+".json"
    save_json(FIX/fid,data)
    c={"case_id":key,"title":title,"kind":kind,"input":"fixtures/"+fid,
       "expected":{"overall_result":overall,"current_shot_compliance":compliance,
                   "cross_shot_continuity":continuity,"required_error_types":list(errors),
                   "required_assertions":list(checks),"forbidden_assertions":list(forbidden)},
       "tags":list(tags)}
    if severity:c["expected"]["minimum_severity"]=severity
    CASES.append(c)


case("C01","满载货架整体变空",inp(cur="empty"),"REGENERATE","PASS","FAIL",
     errors=["background_state_continuity"],severity="high",
     checks=["SHELF_A 陈列区域清晰可见；保持满载基线，不写入空架状态"],tags=["background_object_state","critical_gate"])
case("C02","脸部特写令货架离画",inp(cur="face",cspec="同一便利店连续交谈。林默脸部特写，只展示头部和很少的近旁背景，不要求货架入画。"),
     "PASS","PASS","PASS",checks=["货架 stocking_state 为 not_testable；继续保留满载状态"],
     forbidden=["货架消失","便当消失"],tags=["visibility","critical_gate"])
case("C03","前景展示板遮住商品区域",inp(cur="covered",cspec=BASE_SPEC+"机位略移，近处大型展示板遮住后景货架陈列区；只允许核对仍可辨的静态区域。"),
     "PASS","PASS","PASS",checks=["货架陈列状态不可检验，保留原状态"],forbidden=["商品消失"],tags=["occlusion","critical_gate"])
case("C04","关键陈列区域无法辨认",inp(cur="blurred",cspec=BASE_SPEC+"货架商品陈列是此场景的关键视觉状态。"),
     "REVISE","uncertain","uncertain",checks=["报告货架结构及陈列状态辨识度不足，要求清晰图像"],forbidden=["确认空架","REGENERATE"],tags=["uncertain"])
case("C05","商品包装细节随机变化",inp(cur="texture"),"PASS","PASS","PASS",
     forbidden=["逐件商品数量、包装或纹理差异作为错误"],tags=["non_pixel"])
bag_spec=BASE_SPEC+"林默右手拿着两个剧情关键便当袋。"
case("C06","可见右手中关键道具消失",inp(cur="no_bags",pspec=bag_spec),"REGENERATE","PASS","FAIL",
     errors=["prop_continuity"],severity="high",checks=["角色自身右手为空且无遮挡；不得用观众右侧定义右手"],tags=["prop"])
case("C07","持物手在画外",inp(cur="upper",pspec=bag_spec,cspec="连续交谈，林默与苏晴上半身近景，仅展示人物头部、肩部和胸部，手和便当袋不要求入画。"),
     "PASS","PASS","PASS",checks=["继续保留两个便当袋的持物状态"],forbidden=["道具消失"],tags=["visibility","prop"])
case("C08","明确放下便当",inp(cur="placed",pspec=bag_spec,cspec=BASE_SPEC+"此静态画面中林默已将两个便当袋放在柜台中部，两手为空。"),
     "PASS","PASS","PASS",checks=["更新道具为柜台中部，依据当前 Spec，不保留右手持物预期"],tags=["authorized_change"])
case("C09","便当换手没有依据",inp(cur="other_hand",pspec=bag_spec),"REGENERATE","PASS","FAIL",
     errors=["prop_continuity"],severity="high",checks=["按角色自身左右手判定"],tags=["prop"])
case("C10","剧情数量由二变一",inp(cur="one_bag",pspec=bag_spec),"REGENERATE","PASS","FAIL",
     errors=["prop_continuity"],severity="high",checks=["精确核对两个剧情袋，不能只核对有无"],tags=["prop"])
case("C11","人物固定外观变化",inp(cur="changed_coat"),"REGENERATE","FAIL","FAIL",
     errors=["character_continuity"],severity="high",checks=["同一原因只报告一个问题并关联两个分项"],tags=["character"])
bound_spec=BASE_SPEC+"林默被三道绳子绑在椅子上，双腿也被绑；没有便当袋。"
case("C12","没有解绑却自由站立",inp(prev="bound",cur="free",pspec=bound_spec),"REGENERATE","PASS","FAIL",
     errors=["character_state_continuity"],severity="critical",checks=["束缚和坐姿是持续剧情事实"],tags=["character_state","critical_gate"])
case("C13","反打与世界锚点一致",inp(cur="reverse",cspec="便利店内部同一连续交谈，镜头从柜台另一侧拍摄人物背面。世界位置不变：林默仍在靠窗端，苏晴仍在靠三层货架端；屏幕上的人物和背景左右关系随反向视点改变。"),
     "PASS","PASS","PASS",checks=["用窗、收银机、货架等世界锚点确认人物关系"],forbidden=["仅因屏幕左右互换判空间错误"],tags=["spatial","critical_gate"])
swap_input=inp(cur="swapped",cspec="便利店内部，全景静态画面，林默与苏晴站着交谈。门窗、柜台、三层货架均在画面中。")
swap_input["current"]["spec_version"]="v2"
case("C14","相同锚点下人物真正换位",swap_input,
     "REGENERATE","PASS","FAIL",errors=["spatial_continuity"],severity="high",tags=["spatial"])
case("C15","明确开门并继承结果",inp(cur="open_door",cspec=BASE_SPEC+"入口门已经打开，应保持打开状态。"),
     "PASS","PASS","PASS",checks=["当前明确开门预期替换先前关门事实"],tags=["background_object_state","authorized_change"])
case("C16","夜间变成白天",inp(cur="day",cspec="同一便利店，同一连续交谈的静态全景，人物仍在原位；没有时间跳跃。"),
     "REGENERATE","PASS","FAIL",errors=["lighting_time_continuity"],severity="high",tags=["lighting_time"])
case("C17","轻微曝光差异",inp(cur="brighter"),"PASS","PASS","PASS",forbidden=["轻微曝光提升导致重生成"],tags=["lighting_time","non_pixel"])
new=inp(cur="other_store",scene="STORE_B",cspec="新场景：另一家便利店内部，静态全景。林默与苏晴进入另一家店交谈；背景采用该店的新布局。")
new["continuity_context"]={"previous_to_current":"new_scene","current_to_next":"unknown","basis":"明确切入另一家便利店；不继承上一店环境。"}
new["persistent_visual_state"]=state()
case("C18","场景切换重建环境",new,"PASS","PASS","PASS",checks=["不携带旧店货架世界锚点与库存事实，建立 STORE_B 状态；只比较有依据的同名人物稳定身份"],tags=["new_scene"])
case("C19","破碎窗户无依据恢复",inp(prev="broken",pspec=BASE_SPEC+"窗右侧玻璃有明显裂纹和缺口。"),
     "REGENERATE","PASS","FAIL",errors=["scene_condition_continuity"],severity="high",tags=["scene_condition"])
third=inp(prev="face",cur="empty",pspec="同一场景林默脸部特写，货架离画。",persistent_visual_state=state(through="SHOT_02"))
third["previous"]=shot("SHOT_02","face","同一场景林默脸部特写，货架离画。")
third["current"]=shot("SHOT_03","empty")
case("C20","三镜状态跨不可见镜头继承",third,"REGENERATE","PASS","FAIL",
     errors=["background_state_continuity"],severity="high",kind="stateful_visual",
     checks=["引用 SHOT_01 历史证据；保留满载，不能把 SHOT_02 未见当作清空"],tags=["persistent_state","critical_gate"])
pollute=inp(prev="empty",cur="empty",persistent_visual_state=state(through="SHOT_02"))
pollute["previous"]=shot("SHOT_02","empty")
pollute["current"]=shot("SHOT_03","empty")
pollute["story_context"]="SHOT_02 中货架错误地变空，已确认属于生成错误；没有剧情清空货架的动作。"
case("C21","错误前镜不能污染基线",pollute,"REGENERATE","PASS","FAIL",
     errors=["background_state_continuity"],severity="high",kind="stateful_visual",
     checks=["即使相邻两图同为空架，也保留 SHOT_01 满载事实"],tags=["persistent_state","critical_gate"])
repair=inp(prev="empty",cur="base",pspec=BASE_SPEC+"货架必须摆满商品。",cspec=BASE_SPEC+"货架必须摆满商品。")
case("C22","当前恢复正确状态，归因前镜",repair,"REVISE","PASS","uncertain",
     checks=["问题归属 previous；要求修正前镜，不得要求当前复制空架"],forbidden=["当前镜 REGENERATE"],tags=["attribution"])
future=inp(pspec=bag_spec,cspec=bag_spec)
future["next"]=shot("SHOT_03","placed",BASE_SPEC+"林默已将两个便当袋放在柜台中部，双手空。")
future["continuity_context"]["current_to_next"]="continuous"
case("C23","下一镜放下道具不提前套用",future,"PASS","PASS","PASS",
     checks=["截至 SHOT_02 仍为右手两个袋；不得把 SHOT_03 放袋事实写入当前状态"],tags=["next_shot","persistent_state"])
unknown=inp(cur="empty")
unknown["continuity_context"]={"previous_to_current":"unknown","current_to_next":"unknown","basis":"素材未注明是否同一连续时段，也无法排除是相似店铺。"}
case("C24","连续关系无法确认",unknown,"REVISE","PASS","uncertain",checks=["需要场景或连续关系依据"],forbidden=["确认 continuity error"],tags=["uncertain"])
case("C25","错误裁切是单镜问题",inp(cur="face",cspec=BASE_SPEC+"货架完整入画为关键必现元素，不可裁去。"),
     "REGENERATE","FAIL","PASS",severity="high",checks=["记录静态构图或必现元素不合规"],forbidden=["世界中的货架或商品物理消失"],tags=["compliance","visibility"])
missing=inp(cur="empty");missing["previous"]["image"]=None
case("C26","前镜图片缺失",missing,"REVISE","PASS","uncertain",kind="context_variant",
     checks=["previous_image_inspected=false；不编造前镜实际商品数量"],tags=["missing_input"])
video=inp()
video["current"]["shot_spec"]={"storyboard_keyframe":{"static_state":BASE_SPEC},"video_constraints":{"camera_movement":"缓慢推进并环绕人物","action_timing":"第2秒人物转头，第4秒交接袋子"}}
case("C27","只提取静态 Spec 字段",video,"PASS","PASS","PASS",kind="context_variant",
     forbidden=["运镜审查","动作时序审查","要求静态图实现第4秒交接"],tags=["static_only"])
revision=inp(cur="empty",persistent_visual_state=state(image="SHOT_01_IMAGE_OLD",version="v1"))
revision["previous"]=shot("SHOT_01","empty",BASE_SPEC,"STORE","v2")
revision["story_context"]="SHOT_01 图片及 Spec 已替换为 v2；历史状态引用 v1 图像 SHOT_01_IMAGE_OLD。版本变更的详细批准内容未提供。"
case("C28","来源修订使旧状态需复核",revision,"REVISE","PASS","uncertain",kind="stateful_visual",
     checks=["隔离或复核过期满载依据，不以 v1 状态确认 v2 当前错误"],tags=["revision"])
case("C29","伤口无依据恢复",inp(prev="wound",pspec=BASE_SPEC+"林默脸颊有新鲜伤口，需持续。"),
     "REGENERATE","PASS","FAIL",severity="high",tags=["character_state"])
CASES[-1]["expected"]["acceptable_error_type_groups"]=[["character_continuity","character_state_continuity"]]
case("C30","灯具突然关闭",inp(cur="lights_off"),"REVISE","PASS","FAIL",
     errors=["background_state_continuity"],severity="medium",tags=["background_object_state"])
only={"schema_version":"1.0","current":shot("SHOT_01"),"continuity_context":{"previous_to_current":"new_scene","current_to_next":"unknown","basis":"明确这是本场首镜，没有前镜，也未提供需比较的后镜。"}}
case("C31","首镜建立状态",only,"PASS","PASS","not_applicable",kind="context_variant",
     checks=["建立满载状态；不伪称完成前后两图比较"],tags=["first_shot"])
noimg=copy.deepcopy(only);noimg["current"]["image"]=None
case("C32","当前图片缺失",noimg,"REVISE","uncertain","not_applicable",kind="context_variant",
     checks=["current_image_inspected=false；列明缺失图像"],forbidden=["推测当前实际画面"],tags=["missing_input"])

save_json(ROOT/"cases.json",{"schema_version":"1.0","fixture_provenance":"Original deterministic synthetic diagrams drawn with Pillow by build_fixtures.py. No real generated-storyboard validation has been completed by creating these files.","cases":CASES})
blind_ids={"C01","C02","C03","C12","C13","C20"}
save_json(FIX/"blind-batch.json",{"schema_version":"1.0","instructions":"读取本清单中的输入 JSON，实际打开每张引用的 PNG，仅根据输入审查当前静态分镜。不要读取 cases.json、build_fixtures.py 或预期答案。图片 ref 相对各输入 JSON 所在目录解析。输出每案当前图合规、跨镜连续性、最终 PASS/REVISE/REGENERATE、依据、可见性说明及截至当前镜的持久状态。", "inputs":[Path(c["input"]).name for c in CASES if c["case_id"] in blind_ids]})
print(json.dumps({"images":len(IMAGES),"cases":len(CASES),"blind_batch":str(FIX/"blind-batch.json")},ensure_ascii=False))
