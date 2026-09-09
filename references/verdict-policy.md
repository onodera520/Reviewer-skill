# 严重程度与结果

新审查遵循 [预览审查口径](story-preview.md)。严重程度取决于故事理解与修复影响，不按提示词字面差异计分。缺省 profile 的历史记录仍按旧语义校验。

## 严重程度

| severity | 影响 |
| --- | --- |
| critical | 破坏核心剧情事实：无依据被绑变自由、核心人物身份替换等 |
| high | 人物、核心道具、关键环境结构、明显世界空间关系错误，必须实质影响故事理解 |
| medium | 显著背景状态不一致（如满载货架整体变空）、非核心道具漂移、明显灯光状态变化，但未破坏核心剧情 |
| low | 有明确证据、确有意义但不影响剧情的次要差异；普通生成随机性不计错 |

按事实的叙事作用、变化规模与可见显著程度分级，不按类别机械分级。多个低等级问题不因数量自动升级；若共同破坏关键事实，合并问题并说明实质影响。

## 静态分项计算

issue 的主 `review_area` 与可选 `related_review_areas` 一起决定它影响哪些分项。归属于前镜／后镜的错误不能把当前单镜合规判 FAIL。

对每个分项按顺序计算：

1. 有归属于 `current` 的已确认错误，包括 low：`FAIL`。
2. 无上述错误，但有影响本分项判断的 uncertainties、未决归因，或连续范围内其他镜头存在 medium 及以上待处理错误：`uncertain`。其他镜头问题只影响连续性，不影响当前合规；仅有其他镜头 low 问题时可保持 PASS，并保留说明。
3. 适用检查完成且无错误：`PASS`。
4. 仅连续性可用 `not_applicable`：首镜或新场景且不存在需要比较的前后连续状态。下一镜可用于比较时，首镜也有适用连续性检查。

当前合规不允许 `not_applicable`。本应进行连续性审查却缺材料时使用 `uncertain`。确定错误和不确定项可并存：有当前错误的分项保留 FAIL，uncertainties 仍单列。合理离画的单项 `not_testable` 不自动令整个连续性 uncertain；它没有提供矛盾证据。

## 静态 overall_result 确定顺序

1. 当前镜已确认 critical / high 错误 → `REGENERATE`。
2. 当前镜已确认 medium 错误 → `REVISE`。
3. 任一 unresolved 归因问题、前镜／后镜 medium 及以上待修错误、potential_severity 为 medium 及以上的 uncertainty → `REVISE`。
4. 只有 low 错误或 low 不确定项，或所有适用检查通过 → `PASS`，保留问题与说明。

缺对应图片提示词、当前图片未实际查看、关键证据不足、重要输入冲突至少记录 medium uncertainty，因此为 REVISE。uncertain 自身绝不触发 REGENERATE；如果还有独立的当前 high 错误，仍依第 1 条判 REGENERATE。

低等级已确认错误允许出现“分项 FAIL、总体 PASS”，意为存在可接受的小问题；不得为了使状态看起来一致而隐瞒问题。反之，“当前合规 PASS、连续性 FAIL、总体 REGENERATE”适用于当前图单独正确却严重穿帮。

`REVISE` 可表示局部修正、补证或修复其他镜头，必须在对应 recommended_fix / required_evidence 指明。`REGENERATE` 针对当前镜恢复既定事实，不授权改设计或自动生成。

## 智能分镜判定

智能分镜的三个分项是视觉锚点、动态执行、镜头序列，使用 PASS／FAIL／uncertain。每项有已确认的关联问题时为 FAIL；无确认错误但有影响核验的缺证或归因未定时为 uncertain；适用检查实际完成且无错误才为 PASS。确认错误与缺证可并存，保留 FAIL 并另列待确认项。视觉锚点最高优先检查，但不能抵消其他层的严重问题。

总体同时考虑影响与实际修复方式：

1. 已确认关键人物身份替换、核心道具或因果错误、严重漂移等，需要重新生成源图或指定视频镜头才能恢复正确设计：REGENERATE。问题须指明具体修复镜头，不能默认重生成全片。
2. 从现有正确素材重新排序、删除误加片段、裁切或调整剪辑可恢复预览：REVISE，即便镜头序列问题严重也不机械要求重生成。
3. 文字只有妨碍关键画面理解才报告，按实际影响和可修复性判定。声音、水印、字幕专项检查排除，不因这些项目要求修改。
4. 关键视觉或剧情证据不足、镜头映射不明、未解决输入冲突或来源归因：REVISE，明确所需材料。缺证自身不触发 REGENERATE。
5. 仅可接受的 low 差异／非关键不确定项，或全部检查通过：PASS，保留必要说明。多个 low 问题不因数量自动升级。

内部 issue 用 `repair_target` 定位 storyboard_image／video_shot／editing／unresolved（audio 仅为历史兼容保留），`repair_action` 表示 regenerate／revise。严重程度不等于修复手段；同因跨层问题使用一个 issue 的 layers 关联，不能重复计数升级。推荐修复只恢复既定设计，不以改机位、景别、人物安排掩盖问题。

`animatic_review.overall_result` 保留视频审查结论。合审时顶层 overall_result 还须包含静态审查的实质问题，按 REGENERATE 高于 REVISE 高于 PASS 汇总；各自结论不被另一个模块的通过覆盖。源图错误与被视频继承的同因错误说明依赖和修复范围，不产生互相矛盾的建议。
