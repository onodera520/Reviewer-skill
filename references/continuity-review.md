# 跨分镜视觉连续性

按 [预览审查口径](story-preview.md) 筛选有意义的事实。八类均需考虑，但不穷举微小细节；普通差异不制造问题或补证。

## 1. 先确定是否可比较

连续性审查是核对持续视觉事实，不是两张图像的相似度评分。先从提供的连续关系、Spec、剧情、场景与时间信息确认是否属于同一连续段；同一地点名不能证明连续，时间跳跃、闪回和不明连接必须保留未知。

对每一事实确认同一实体：以资产绑定、固定地标、结构特征、身份及可信状态链为据。仅“都在画面右边”或“看起来像”不足以证明同一货架。世界锚点不可确认时为 null，不虚构坐标。

前镜 → 当前镜是通常比较方向；当前镜 → 后镜可补充连续性证据。下一镜才发生的变化不得提前要求当前镜满足。不能用不同场景的布局来判当前场景错误。

## 2. 先判断属性可见性

对每条需比较的事实输出 visibility_check，按 `fact_id` 链接输入或输出状态。检查的是具体 property：货架结构可见，不代表商品数量可辨。

1. 依据当前比较目标的机位、景别、构图、世界位置，判断 `expected_visibility: yes / no / uncertain`。
2. 实际查看目标图片，记录 `observed_visibility: visible / partial / not_visible / unassessable`。
3. 查看取景、合理遮挡、景深及清晰度是否允许核对该属性。
4. 查明明确剧情或 Spec 是否授权状态改变，再给出 assessment。

| 情况 | assessment 与处理 |
| --- | --- |
| 应可见、属性可辨、与正确持续事实一致 | consistent |
| 应可见、属性可检验、实际明显矛盾且没有授权变化 | contradiction；确认错误 |
| 正常近景、离画或遮挡使属性无法测试 | not_testable；保留原事实，不判消失 |
| 关键背景虚化、实体无法匹配、连续关系不明或空间依据不足 | uncertain；说明需补什么证据 |
| Spec 要求物体入画，实际错误裁切 | 单镜构图不合规；该物体是否在世界中存在仍不可由裁切得知 |

未见物体不等于错误消失；但如果其已知位置及应出现区域清晰无遮挡，能够判断本应出现而未出现，可以记录 contradiction。不得用假想遮挡推翻清晰证据，也不得对不可见区域强行判错。

确认 continuity error 的六项条件必须同时有依据：连续关系明确、同一实体明确、正确既有状态明确、目标属性可检验、实际矛盾可见、无已提供的授权变化。证据不足进入 uncertainties，不进入已确认错误列表。

## 3. 八类必查事实

| category | error_type | 内容 |
| --- | --- | --- |
| environment | environment_continuity | 门、窗、货架、桌椅、柜台、墙面、建筑结构、大型陈设、固定装饰及显著背景物体的存在和结构 |
| prop | prop_continuity | 手机、钱包、刀、便当、杯子、包、武器、文件、桌面物件等持续道具的存在、增减、持有者、位置、数量、状态 |
| character | character_continuity | 身份、发型、服装、配饰、年龄感、伤口、污渍、衣物破损、人数 |
| character_state | character_state_continuity | 站／坐／跪／倒地、被绑／自由、持物、伤势、湿／干、完整／破损等状态 |
| spatial | spatial_continuity | 人物与人物、人物与固定地标及重要物件的世界空间关系 |
| background_object_state | background_state_continuity | 满／空货架、柜门开闭、桌面物品、灯具开关、门窗开闭、窗帘、积水、墙面损坏、车辆位置 |
| lighting_time | lighting_time_continuity | 日夜、主光来源及世界方向、环境光、灯具开关、冷暖关系、天气 |
| scene_condition | scene_condition_continuity | 破损地面、烟、雨、碎窗、倒桌、火灾、积水及其他已建立的剧情结果 |

类别有交叉时选最能解释原因的一类，不重复报同一错误。灯被关掉属于明确开关状态，曝光略暗不等于灯灭；伤口消失可按 character_state 分类，不再另报 character。

判断优先级：剧情重要状态 ＞ 人物 ＞ 关键道具 ＞ 空间关系 ＞ 显著背景元素 ＞ 环境状态 ＞ 次要装饰。人物无理由解绑属于 critical；普通装饰纹理变化不计错。

反打可能让屏幕左右互换而世界位置不变。用柜台、入口、墙面等固定锚点验证，不按屏幕坐标直接判交换位置。只有剧情关键手别才核对，并按角色身体判断；非关键左右手差异放行。

普通货架记录“满载／部分陈列／空”等有意义状态，不逐件数普通商品；“两个便当袋”等数量若影响剧情意图或必要结果则必须核对。允许普通包装、背景纹理、头发细节、曝光和微小阴影差异，不要求像素一致。

## 4. Persistent Visual State

状态是显式传入／返回的事实表，不是未经记录的长期记忆。`through_shot_id` 表示事实表更新截至当前镜，不表示每条事实都在当前图中可见。每条事实独立保留来源、建立镜头和最后图像确认镜头。

### 建立与来源

- 从明确且无冲突的对应提示词／Spec／剧情建立 `basis: specified`；从实际清晰图片、且不与更权威要求冲突的事实建立 `observed`；两者均成立使用 `both`。
- Spec 未写但前镜已清楚建立的显著背景状态也需维护。例如分别记录货架结构和 stocking_state，不能只记“有货架”漏掉商品满载。
- 引用可解析到输入材料的证据；历史事实携带的 image 证据属于已报告的历史观察，不能因此声称本轮打开过历史图。
- 没有历史状态时从可用前镜开始；coverage_start_shot_id 记录实际覆盖起点。只有当前图时可以建立当前事实，不假称检查过前镜。
- 无法确认的事实放 uncertainties，不作为已确认基线。需要描述明确 Spec 要求但尚未看见时可以 specified；last_confirmed_at_shot_id 为 null。

### 继承、更新与防污染

- 同一连续段默认保留事实；当前 Spec 未重复提及，不等于取消。
- 明确且无冲突的提示词、剧情或 Spec 描述的变化可以更新 value，证据记录变化来源。不能自行补“应该已经放下了”“可能有人清走了”。
- 正常离画、遮挡、景别变化仅改变本次 visibility_check；事实不删、last_confirmed_at_shot_id 不刷新。
- 当前图片违反某事实时，保留正确事实和最后可信确认时间；该错误图片不能成为此属性的基线，也不能给该事实添加支持性的 observed 证据。
- 当前其他独立且可信事实仍可建立。不要因为一处错误冻结整个状态表。
- Spec 明确改变状态、图像暂不可验证时更新 specified 值，last_confirmed_at_shot_id 不沿用旧值的确认时间：新值未观察过则为 null。即使当前图错误，明确作者设计的新值仍可替换预期事实；若图像错误呈现旧值，不能将旧值恢复为正确状态，也不能把错误图当作新值的支持证据。只有当前图确实支持新的预期值时，才添加其 image 证据和刷新确认时间；契约校验器不能证明图像内容是否支持描述，必须实际核实。
- 对同一个实体属性维持一个活动值；保留变化来源，避免同时输出互相矛盾的活动事实。

### 场景与版本

进入新场景／新连续段时丢弃上一段 scene 作用域事实，建立新场景的环境状态。entity 作用域也不是无条件携带：身份和叙事延续明确时携带稳定身份；伤势、持物等可变状态需要连续依据。返回旧场景不能自动假定旧桌面、灯光或损坏已保持／恢复。

图片使用不可变 image_id；替换图片使用新 ID。Spec 引用统一为 SHOT_ID_SPEC，已知版本时必须携带 source_version；未知版本不编造。输入版本已变但历史仍引用旧版时，重新读取受影响材料并核实；不能证明仍有效的事实从活动基线隔离，列为 uncertainty。不把改名或不同文件路径当作内容已验证。

同一连续段移除失效输入事实时，输出可选顶层 state_invalidations，每项为 fact_id、reason、evidence，并为受影响 entity 创建 uncertainty。移除的 fact_id 不得继续存在于输出 facts。新场景自然丢弃 scene 事实不需 invalidation；不可见、当前图错误或 Spec 未重复提及均不构成失效理由。旧版本证据可保留在 uncertainties／state_invalidations 解释为什么隔离，不能作为活动事实或已确认 issue 的支持证据。

下一镜只能帮助本轮判断；不得把只在下一镜才观察／指定的新状态写入截至当前镜的事实表，也不得把 last_confirmed_at_shot_id 刷新到下一镜。后镜比较的 visibility_check 可引用当前事实，shot_id 使用后镜 ID。

## 5. 证据、冲突与归因

每个连续性 issue 保留 previous_state、expected_current_state、actual_current_state、evidence、reason、recommended_fix。evidence 同时支持正确基线、目标实际画面、属性可测试性；reason 说明在已提供的哪些 Spec／剧情中未发现授权变化，不声称排除了未提供的全部剧情。

以对应图片提示词核对当前主要意图，Spec、资产和剧情补充背景；有影响判断的未解决冲突先标 uncertain。前镜已确认错误不得建立正确基线，当前恢复正确状态时修复前镜。动作阶段容差通过不代表已观察到完成状态，不能因此污染持久事实。

仅确认两图矛盾而不能确定错误方，可建 `attribution: unresolved` 的连续性问题，说明归因未定；分项 uncertain，总体 REVISE。当前图本身有独立明确 high 错误时，总体仍按判定规则 REGENERATE。

为保持单一 Schema，状态字段名称不随比较方向改变，但其语义固定为“比较基线／目标预期／目标实见”。常规 previous → current 中目标是本轮当前镜；只有 current → next 时，previous_state 描述本轮当前镜基线，expected_current_state 和 actual_current_state 描述下一镜比较目标。必须在这三个文本中写明镜头 ID，affected_shot_ids 按叙事顺序排列，evidence 指向实际目标图，attribution 始终相对于本轮 shot_id 使用 current／previous／next。不得因字段名误把后镜错误归给当前镜。

例如 current → next 对比中，当前镜右手持袋，下一镜同一只手清晰空着且无放下依据：若能确定下一镜错误，则 attribution: next，修复下一镜，当前单镜合规可 PASS，总体 REVISE；不重生成正确的当前镜。

同因问题只记录一次，用 fact_ids 链接有关事实；若也违反对应图片提示词，用 related_review_areas 关联。修复建议仅恢复正确状态；不自动改 Prompt，不让画面改取景来隐藏矛盾。
