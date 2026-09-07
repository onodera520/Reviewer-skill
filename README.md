# Reviewer Skill

用于审查 AI 生成的静态分镜图，以及“智能分镜”（Animatic 式动态分镜预览视频）。它不生成素材、不改写 Prompt，也不重新设计镜头；它只根据 Shot Spec、参考分镜图、实际图片或视频与已建立的视觉状态，给出可追溯的审查结论。

默认交付一个精简的中文 Markdown 报告，只保留结论、问题、严重程度和可执行的修改方案。智能分镜问题额外标明 Shot 与视频时间范围、修改对象。内部 JSON 仅用于机器校验与跨镜持久状态传递，不会出现在默认成品中。

## 审查范围

静态分镜模式检查：

- 当前分镜图是否符合自身 Shot Spec。
- 人物、道具、空间关系、环境、背景状态、光线、时间和场景状态的跨镜连续性。
- 先判断一个属性是否应当可见；离画、遮挡、虚焦和合理机位变化不会被误判为“消失”。

智能分镜模式检查三层关系：

| 层级 | 检查内容 |
| --- | --- |
| 视觉锚点一致性 | 视频对应时刻是否继承原分镜图与正确的 Shot Spec，包括人物、构图、Blocking、道具、环境和光线。 |
| 动态执行一致性 | 小幅动作是否表达主体、对象、方向、因果和必要状态变化；是否有漂移、替换或变形。 |
| 镜头序列一致性 | Shot 顺序、跨切状态、硬切、叙事可读性，以及禁止的字幕、台词、旁白和音乐。 |

环境声和动作音效允许。没有音轨、或经完整验证的数字静音轨可以通过；非静音音轨在不能实际听辨或识别时会标记为 `uncertain`，不会凭音量猜测内容。

## 安装

将整个 `reviewer/` 目录放入 Codex 的个人 Skills 目录：

```text
%USERPROFILE%\.codex\skills\reviewer
```

安装校验所需 Python 依赖：

```powershell
python -m pip install -r scripts/requirements.txt
```

智能分镜的本地视频准备工具需要可信的 FFmpeg 与 FFprobe。可按优先级用命令行参数、`REVIEWER_FFMPEG` / `REVIEWER_FFPROBE` 环境变量、`scripts/media-tools.local.json` 或 PATH 配置它们。`media-tools.local.json` 是本机文件，不应提交到 Git。

## 输入和输出

- 静态图使用 `schemas/review-input.schema.json` 和 `schemas/review-output.schema.json`。
- 智能分镜使用 `review_mode: "animatic"`，对应 `schemas/animatic-input.schema.json` 和 `schemas/animatic-output.schema.json`。
- `persistent-visual-state.schema.json` 保存已建立的视觉事实。调用方显式传递该状态，Reviewer 不依赖隐含对话记忆。

用户可以提供自然语言脚本、Shot Spec、资产、图片和视频；Reviewer 负责归一化，但只以实际成功读取的媒体作为画面或声音证据。

完整规则入口是 [SKILL.md](SKILL.md)。智能分镜的具体规则在 [references/animatic-review.md](references/animatic-review.md)，静态连续性规则在 [references/continuity-review.md](references/continuity-review.md)。

## 报告形态

静态分镜报告会显示总体结论，以及每个已确认问题或待确认项：

```text
问题：当前货架为空，应保持满载商品陈列。
严重程度：高
修改方案：重新生成当前分镜，恢复既定货架状态。
```

智能分镜报告在此基础上增加受影响 Shot、实际视频时间范围和修改对象，例如“指定视频镜头”“剪辑”或“声音”。完整证据、可见性判断、版本和持久状态仍在内部结构中校验，避免人读报告被技术字段淹没。

## 本地验证

```powershell
python scripts/validate_contract.py --check-schemas
python -m unittest discover -s evals -p "test_*.py"
```

媒体测试需要本机 FFmpeg／FFprobe；缺少它们会明确跳过相关测试，不会伪称媒体能力已经验证。`scripts/prepare_animatic.py` 只做本地探测、抽帧与证据准备，不能替代实际审查。详见 [evals/animatic/rubric.md](evals/animatic/rubric.md)。

## 仓库内容

仓库跟踪 Skill 指令、参考规则、JSON Schema、校验/渲染/媒体准备脚本、以及必要的静态评测材料。`.gitignore` 排除了本机媒体工具配置、Python 缓存、抽帧、音频、报告、生成的视频测试材料和压缩包，避免上传机器相关或可再生成文件。
