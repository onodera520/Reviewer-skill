# 输入输出契约

本页定义内部完整 JSON 记录与显式 JSON 导出的契约。默认用户成品是 [干净的 Markdown 报告](report-format.md)，不直接显示技术字段、状态事实表或原始 JSON；只改变呈现，不降低审查和证据要求。

## 输入归一化

静态模式以 [输入 Schema](../schemas/review-input.schema.json) 为机器契约；智能分镜使用下文独立契约。用户可以提供自然语言、文件、图片及视频，不必填写 JSON；只归一化实际给出的信息，不补写原设计。

| 字段 | 处理 |
| --- | --- |
| schema_version | 固定 1.0 |
| current | 必须有对象；shot_id、scene_id、spec_version、shot_spec 均保留，未知 scene_id / spec_version 为 null |
| previous / next | 可省略；可仅有 Spec，不能因此声称比较过实际相邻图 |
| shot_spec | 原 object / string；缺失为 null，空字符串／空对象按缺失或不充分材料处理 |
| image | 可为 null／省略；存在时需 image_id 和 ref；image_id 标识不可变内容 |
| image_prompt | 可省略／null；原始文本用于定位转写问题，不能代替 Spec |
| clip_id / clip_version / image_number | ShotInput 可选分组元数据及全片图号；clip_id 为字符串，clip_version 为字符串或 null，image_number 为大于等于 1 的整数；不替代镜头身份、版本或场景连续关系 |
| assets | 可选角色／场景／道具资产，保留 asset_id、entity_id、kind、version 及图片或文字来源 |
| story_context | 可选原剧情依据，不能补写不存在的变化 |
| persistent_visual_state | 可选上一次报告返回的状态及其证据 |
| continuity_context | previous_to_current、current_to_next 为 continuous / new_scene / unknown，basis 说明关系依据 |

如果完全没有当前材料，用 `shot_id: UNASSIGNED_CURRENT` 作为明确临时占位，并在 limitations 中说明待补镜头号；不伪造正式编号。其他未知必需标识也只能使用明确注明的临时标识，后续绑定真实镜头时整体替换。

## 缺失、冲突与覆盖范围

- 当前 Spec 缺失、空、只有无法提取静态目标的文本：当前合规 uncertain，添加至少 medium uncertainty，说明缺什么约束。继续独立的、有依据的检查。
- 当前图片缺失或无法读取：current_image_inspected 为 false，当前合规 uncertain，总体至少 REVISE；不产生声称当前视觉已确认的 issues。
- 当前图片可打开但局部模糊：inspected 为 true，只把受影响属性列为 uncertain，不等于整图未读取。
- 原始 Prompt 缺失不阻止审图。资产缺失只影响必须靠资产才能确认的属性，不自动把其他全部检查变成 uncertain。
- 明确首镜／新场景且没有可比较后镜或实体状态：连续性 not_applicable。用户要求检查前后连续性却未提供足够材料，或连续关系未知：uncertain；不得以省略 previous 对象自动当首镜。
- 图片是主要视觉证据，资产仅能证明资产形态，不能证明它已出现在前镜。文字输入可以证明设计要求，不能冒充图像观察。
- 引用失效、版本冲突、明显空材料分别记录；未知事实不填成“已保持”。

`coverage.continuity_basis` 表示实际采用的来源：只用相邻材料为 adjacent，只用可信历史状态为 persistent_state，两者都用为 both，均未使用为 none。三个 image_inspected 仅表示本轮实际打开并看过对应图片；历史状态携带 image 证据不使 previous_image_inspected 自动变 true。limitations 写明只比较到哪一段、缺图、模糊或缺版本等实质限制。

文件输入中的相对 image.ref / asset.image_ref 相对该输入 JSON 所在目录解析；对话附件使用可实际访问的附件引用。只有知道文件位置时才转成绝对路径，不猜测资源根目录。校验脚本只校验引用身份，不打开图像或探测图片 URL。

## 契约校验命令

维护环境先安装 `python -m pip install -r scripts/requirements.txt`；运行 `python scripts/validate_contract.py --input input.json --output report.json`。可单独用 `--input` 校验输入、`--state` 校验静态状态、`--check-schemas` 校验 Schema。命令从 Skill 目录运行，或使用实际绝对路径；脚本不会自动安装依赖、读取媒体内容或访问远程 Schema。智能分镜按 review_mode 分流到独立契约。

结构通过仅表示字段、可追溯引用和机器可判的一致性满足契约。Spec 是否真的授权变化、地标是否对应、图片是否支持 evidence，仍须实际阅读和看图，不能用校验通过替代这些判断。

## 与现有 Generator 连接

输入来自 Generator 时读取 [Generator 兼容](generator-compatibility.md)。其当前输出包为 2.0，默认 Markdown 按 Clip 分组、每 Shot 一份 Image Prompt 及每 Clip 一份整体智能镜头 Prompt。静态审查只提取关键帧依据，视频审查另提取适用预览动态和参考图时刻。均按实际 Shot 及其版本审查，Clip 边界不自动重置场景状态，Prompt 不能反向替代原 Spec。

## 智能分镜独立契约

使用 [animatic-input.schema.json](../schemas/animatic-input.schema.json) 与 [animatic-output.schema.json](../schemas/animatic-output.schema.json)，`review_mode: animatic`；保留原静态 Schema 不变。具体必填字段与枚举以这些 Schema 为准，判断流程见 [智能分镜模块](animatic-review.md)。

输入归一化保留 video 的 ID／引用／版本，按预期剧情排列 shots 及各自原 Spec、版本和对应分镜图。expected_sequence 省略时使用 shots 顺序；provided_segments 只作待验证映射。preview_instruction 保存原小幅动态／运镜说明，anchor_position 指定参考图的起始／代表／结束用途，不能覆盖原核心事实。可提供 assets、story_context、static_review_refs、persistent_visual_state；没有原静态审查记录不等于源图已通过。

视频与图片相对路径相对输入 JSON 所在目录解析；替换内容后同步不可变资源 ID／版本和受影响证据。无法读取视频、缺少参考图或 Spec、切点匹配不可靠时记录实际缺项，继续可独立完成的检查；不制造虚假镜头映射或视觉／声音观察。

输出包含顶层总体结果、animatic_review 的三层结论和视频总体结果、shot_reviews、issues、uncertainties、coverage 与 persistent_visual_state。可用 static_reviews 保存同时执行的完整静态报告。各 issue 保留 layers、repair_target、repair_action、关联镜头、时间范围、依据及修复建议；不确定项不混入 confirmed issues。

新增证据类型 video_frame 使用 source_ref=视频 ID 与实际 timestamp，audio_segment 使用该视频 ID 与实际 time_range；已知版本保留 source_version。原分镜图、Spec、资产仍使用各自来源标识。只看图不能提供音频观察，只解码不能声明视觉已核验。

state_snapshots 按已核验 Shot 的 entry／exit 保留实际 timestamp、state、visibility_checks、state_changes、state_invalidations；这些状态允许引用可追溯视频证据。最终持久状态承接最近已核验快照，不把未看过的终态、未来状态或错误帧写成正确事实。已有静态状态可用作可信设计基线，但代表图状态不能自动当视频出口。

内部完整结构和状态传递显式保存；默认 Markdown 不展示这些字段，也不加入原视频链接／播放入口。契约校验和解码仅验证结构或读取能力，实际三层判断仍需查看对应媒体；声音能力不足应明确 uncertain。

## 引用、关联与字段语义

Evidence 的 source_type 为 image / shot_spec / asset / story / persistent_state；source_ref 必须可解析到输入或可追溯历史材料，locator 是实际字段路径或画面区域，observation 写出该来源支持的事实。source_version 在 Spec 版本已知时必须填写；未知时可为 null，不能假造版本。不用编造测量框。

source_version、source_ref、fact_id 等标识用于内部追溯和校验，不在默认成品中作为技术字段展示。成品证据改写为“SHOT_02 分镜图 · 右后景货架：各层清晰可见且为空”等便于核对的文字；不能丢失证据的实际含义。

- image：source_ref 使用输入的不可变 image_id，替换图片换 ID。
- shot_spec：统一使用 `SHOT_ID_SPEC` 配合 source_version；未知版本为 null，不能假造版本，不使用其他引用拼接格式。
- asset：使用 asset_id，source_version 使用所选资产版本。
- story：使用 `story_context`，locator 指向提供文本中的相关位置。
- persistent_state：source_ref 使用历史 fact_id，并保留可追溯的原始证据；仅引用事实名不能替代必要视觉来源。

一次报告内 issue_id、finding_id、fact_id 唯一。连续性 issues 使用非空 fact_ids 链接输入或输出事实；visibility_checks 同样引用这些事实。related_review_areas 只列主 review_area 以外真正受影响的分项。单镜问题 previous_state 可以为 null；连续性问题必须非空。

没有已确认错误时 issues 为 []。不确定项放 uncertainties，必须包括 finding_id、review_area、entity_ids、question、evidence、reason、potential_severity、required_evidence。证据完全缺失时 uncertainties.evidence 可为 []；required_evidence 必须列出具体所需材料，不捏造证据填充。

报告可选输出 `state_invalidations: [{"fact_id": "旧事实 ID", "reason": "隔离原因", "evidence": []}]`。同一连续段内因来源过期或冲突而从活动状态移除输入事实时，必须提供对应 invalidation，并为受影响 entity 建立 uncertainty；失效 ID 不能仍出现在输出活动 facts 中。每项 evidence 使用相同 Evidence 结构，列出可用的版本／冲突依据；没有可用证据时可为空并说明。正常 new_scene 丢弃 scene 事实不需 invalidation。过期来源允许出现在 uncertainties 或 state_invalidations 作为失效说明，不得支持活动事实或已确认 issues。它不是掩盖当前图错误、清空正确基线的渠道。

前后比较方向及归因按 [连续性模块第 5 节](continuity-review.md)；affected_shot_ids 按叙事顺序。未来比较仍使用固定字段名，但三个状态文本必须说明实际镜头 ID。结果按 [判定规则](verdict-policy.md) 计算。

## 完整内部报告示例

以下是货架满载变空案例的完整输出结构示例，不是真实审查记录。假设 SHOT_01、SHOT_02 的 Spec 和两图均已实际提供并查看，Spec 版本为 1；SHOT_02 只要求同一区域和货架入画，未独立要求商品满载。图中同一货架可由柜台和墙面地标识别。实际调用必须替换全部示例证据。

```json
{
  "schema_version": "1.0",
  "shot_id": "SHOT_02",
  "overall_result": "REGENERATE",
  "current_shot_compliance": "PASS",
  "cross_shot_continuity": "FAIL",
  "coverage": {
    "current_image_inspected": true,
    "previous_image_inspected": true,
    "next_image_inspected": false,
    "continuity_basis": "adjacent",
    "limitations": []
  },
  "issues": [
    {
      "issue_id": "ISSUE_001",
      "review_area": "cross_shot_continuity",
      "related_review_areas": [],
      "error_type": "background_state_continuity",
      "severity": "high",
      "affected_shot_ids": ["SHOT_01", "SHOT_02"],
      "attribution": "current",
      "entity_ids": ["SHELF_A"],
      "fact_ids": ["F_SHELF_STOCK"],
      "previous_state": "SHOT_01 金属货架三层摆满饮料和零食",
      "expected_current_state": "SHOT_02 同一货架可见陈列区应保持满载",
      "actual_current_state": "SHOT_02 货架清晰可见，但各层商品全部消失",
      "evidence": [
        {"source_type": "image", "source_ref": "SHOT_01_IMAGE", "locator": "柜台右后方三层金属货架", "observation": "三层均有大量商品"},
        {"source_type": "image", "source_ref": "SHOT_02_IMAGE", "locator": "柜台和墙面地标对应的同一货架", "observation": "三层陈列区域无遮挡且清晰，层板全空"},
        {"source_type": "shot_spec", "source_ref": "SHOT_02_SPEC", "source_version": "1", "locator": "场景、构图与静态状态", "observation": "延续同一区域，货架在背景可见，没有清空商品的状态变化"}
      ],
      "reason": "同一货架的满载状态已由前镜建立；当前该属性可检验，已提供的剧情和 Spec 没有授权清空变化",
      "recommended_fix": "重新生成 SHOT_02，恢复原货架满载饮料和零食的状态，保留既定机位和构图"
    }
  ],
  "uncertainties": [],
  "visibility_checks": [
    {
      "fact_id": "F_SHELF_STOCK",
      "shot_id": "SHOT_02",
      "expected_visibility": "yes",
      "observed_visibility": "visible",
      "assessment": "contradiction",
      "reason": "Spec 要求该货架入画，实际陈列区清晰无遮挡，可以核对满空状态",
      "evidence": [
        {"source_type": "shot_spec", "source_ref": "SHOT_02_SPEC", "source_version": "1", "locator": "构图", "observation": "同一区域的货架在可见背景中"},
        {"source_type": "image", "source_ref": "SHOT_02_IMAGE", "locator": "柜台右后方货架各层", "observation": "陈列区可辨，层板全空"}
      ]
    }
  ],
  "notes": ["错误空架不写入正确状态基线；最后图像确认停留在 SHOT_01"],
  "persistent_visual_state": {
    "schema_version": "1.0",
    "scene_id": "CONVENIENCE_STORE_INTERIOR",
    "continuity_segment_id": "STORE_NIGHT_CONTINUOUS_01",
    "through_shot_id": "SHOT_02",
    "coverage_start_shot_id": "SHOT_01",
    "facts": [
      {
        "fact_id": "F_SHELF_STOCK",
        "entity_id": "SHELF_A",
        "category": "background_object_state",
        "scope": "scene",
        "property": "stocking_state",
        "value": "摆满饮料和零食",
        "world_anchor": "柜台右后方墙边的三层金属货架",
        "importance": "high",
        "basis": "observed",
        "established_at_shot_id": "SHOT_01",
        "last_confirmed_at_shot_id": "SHOT_01",
        "evidence": [
          {"source_type": "image", "source_ref": "SHOT_01_IMAGE", "locator": "柜台右后方三层金属货架", "observation": "三层均有大量饮料和零食"}
        ]
      }
    ]
  }
}
```

内部完整报告始终包含 coverage、issues、uncertainties、visibility_checks、notes 和状态。完全缺乏可用事实时 facts 为 []，未知场景／连续段／覆盖起点为 null，through_shot_id 仍与报告 shot_id 相同；不得用示例事实填空。默认将此记录保存到成品旁的 `.reviewer/<报告文件主名>.json`，按 [报告交付](report-format.md) 生成 Markdown；只有用户明确要求 JSON 时才直接交付此完整结构。
