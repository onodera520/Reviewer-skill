# Generator 来源兼容

仅在输入来自 Generator、含 Clip 分组或需匹配全片图号时读取。静态模式只适配实际图片及用户提供的对应图片提示词，以 Shot Spec 补充背景，不审查声音、运镜或动作执行时序；智能分镜模式按 [智能分镜模块](animatic-review.md) 读取适用的动作／运镜与对应时刻依据。不评价 Clip 分组质量或重新规划时间预算。

当前 Generator 区分完整镜头（如 A1）和智能快切 Shot（如镜头1），二者不要求一一对应。以对应 Image Prompt 所属的智能 Shot 绑定图片，不按完整镜头编号猜配。source_full_shot_ids / source_beat_ids 仅帮助追溯剧情。

## 当前来源形态

当前 Generator 输出包 schema_version 为 2.0，输入仍为 1.1，Shot Schema 仍为 1.0，timeline／Clip Plan 各为 1.0。以实际输入声明为准，不因版本变化自行改写来源。这些是来源格式版本，不替代每个 Shot 的 spec_version，也不改变 Reviewer 自己的 1.0 契约。

结构化来源的 `shots[].spec` 是原 Shot Spec，`shots[].storyboard_description` 是描述。`shots[].image_prompt.zh_cn` 是带版本和来源定位的对象，实际 Prompt 正文取其 `text`，而非将整个对象序列化成 Prompt；保留 Prompt 原文及可用 image_prompt_version，同时核对该对象的 shot_id、spec_version 与所选 Spec 的绑定；影响判断的冲突列待确认。`clips[].clip_id`、`clip_version` 和 `video_prompt.zh_cn` 属于 Clip；Clip Plan 的 shot_spans 与 Clip Prompt 元数据中的 source_shots 引用可用于定位镜头和版本，不能作为新的视觉要求。静态模式无需阅读整体视频 Prompt 正文。

默认成品是按 Clip 排列的中文 Markdown，每个 Clip 包含全部镜头的详细描述、按 Shot 排列的 Image Prompts 和一份整体“智能镜头 Prompt”（原 Video Prompt，内部仍为 video_prompt 字段）；它通常不导出完整 Shot Spec。参考图条目标明全片图号、起始／代表／结束用途与镜内关键帧单点时间。不要将默认 MD 当作完整生成包，也不要因缺少 timeline／Clip Plan 的必填项就拒绝本来足够明确的自然语言原 Spec。

## 镜头、版本与图片绑定

- 每张实际图片必须关联明确 shot_id、spec_version，并保留用户提供的全片图号 image_number。核对镜头号、版本和图号是否互相一致；冲突或无法确定绑定时列为 uncertainty，不能猜配。
- Generator 原生整数 spec_version 归一化为同值字符串；已知 Spec 证据使用 `source_ref: SHOT_ID_SPEC` 和对应字符串 source_version。整数 clip_version 如需保存同样转字符串；未知版本保持 null。
- 可选 clip_id、clip_version 仅用于组织输入；Clip 版本不能代替 Shot 版本。全片图号不因换 Clip 或续批重置，亦不能单独证明某张图是哪个版本。
- 用户只提供单镜时，不为审静态图索要无关 Clip 设计或生成完整包。只给对应 Prompt 与图片即可执行提示词符合性审查，未知 shot_spec / spec_version 保留 null，不索要无关 Spec，也不反向编造原设计。

## 单一静态目标

对应图片提示词是直接依据。可用 Spec 的补充读取位置：机位／景别／焦点取 storyboard_keyframe.camera_state；前中后景取 composition；可见人物站位、相对镜头身体朝向和头脸朝向取 blocking，尤其 blocking[].facing；姿态、道具持有、环境与光线的指定时刻状态取 state，结合适用 environment 与资产状态。

顶层摄影、起态／终态、完整动作设计或详细镜头描述可能覆盖多个阶段。不能用它们替换明确关键帧，也不能因为描述最后写“放下便当”就要求此前关键帧空手。原自然语言 Spec 足以明确静态目标时可直接核对，无须凑齐完整 Generator 包字段；主体、关键对象或必要剧情结果存在影响判断的互斥解释时，受影响项 uncertain，请求原设计依据，其他确定项继续。

这些补充约束按预览尺度判断，与对应提示词明显冲突时待确认；不把轻微动作阶段差异升级为错误。声音、水印和字幕专项要求不在本次检查范围。硬约束只有 applies_to 包含 image 且 time_range 覆盖目标关键帧时适用于本图；time_range=null 表示对所声明输出始终适用。若某条显式 image 约束的时间范围却排除该关键帧，记录输入冲突 uncertainty，不能默默丢掉，也不能把未来状态强加给当前图。这里读取静态约束的适用范围，不评价时间安排或动作执行。

## Clip 不等于 Scene

同一 Clip 可以包含多个场景；同一连续场景也可以跨多个 Clip。不能凭相同 Clip 或相邻排列认定连续，不能在 Clip 边界清空场景事实。用实际场景、叙事时间关系、transition 及可信状态依据判定；不明关系保持 unknown。

已有同场景连续依据时，跨 Clip 继承正确 persistent_visual_state；同 Clip 内明确换场时切换适用 scene 事实。闪回／平行叙事按其对应时空处理，不继承剪辑前另一条线的物理状态。Clip／Scene 元数据只帮助选对比较对象，不构成已实际看过生成图的证据。

## 智能分镜来源适配

逐 Shot 提取预览动作／运镜、参考图用途及单点时刻，保留原文和来源版本。Generator 的镜内单点时间是参考图目标依据，不是 Reviewer 已核实的视频实际时间；须结合真实切点映射到视频。时长压缩或映射不明时核对状态对应关系，不能机械复制来源时刻或将代表帧要求为首帧。

Generator 当前倾向短镜硬切并提供逐镜时长，但 Reviewer 不套固定 0.5–2 秒阈值，不要求复现正式成片的完整表演时长。其原台词／旁白、指定音乐和转场例外可能保留在来源 Prompt；本次只检查故事可读性、必要动态、明显连续性及硬切，不检查声音、水印或字幕专项要求，也不调用 OCR。不要把来源声音要求当作本次必须出现的内容；若预览动作说明与核心剧情事实矛盾，标记输入冲突，不能自行改导演方案。

要求源图审查时先按对应图片提示词判断主要意图，再查视频是否遵循源图及正确设计；源图错误不能经视频复现后成为连续性基准。按实际 Shot 入口／出口追踪状态，不能用代表图替代视频出口。

## 资产、人数和朝向

用户明确指定 text_only 资产且文字足以定义需要核对的形态时，按已提供文字核对，不仅因没有资产图片自动 uncertain，也不假称观察过资产图。只有必须靠未提供的视觉参考才能解决的属性才缺证。

已清晰绑定角色资产的 Prompt 可以只声明严格继承，不要求它重复固定外貌和服装。Reviewer 核对实际图与对应提示词及所绑定资产，不把合法省略当成错误。资产在 Generator 设计阶段有固定形象权威，但当前收到的资产与 Spec 未消解冲突时，Reviewer 标 uncertain 并说明所需版本，不重新设计或自行修订来源。

对实际应可见的人物比较其姿态、身体朝向及有差异的头脸朝向与关键帧相对镜头要求。画面左右、世界朝向和 gaze 不互相替代。场景快照包含的离画者或完全被遮挡者继续存在于持续状态，不因此强制加入本图；局部可见者只核对可辨属性。

## 交付保持精简

兼容仅影响来源映射；默认仍按 [报告交付](report-format.md) 输出干净 Markdown，完整 JSON 与持久状态保存到 `.reviewer` 内部记录。不要把 Clip 版本、Schema 版本、来源路径、状态表或原始 Video Prompt 加入默认审查成品。
