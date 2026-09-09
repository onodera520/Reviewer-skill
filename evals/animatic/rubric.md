# 新口径回归说明

新审查执行 [预览规则](../../references/story-preview.md)。现有未声明 review_profile 的 fixture 与历史报告保持旧语义，以下旧评测记录不代表新默认声音或 Spec 审查要求。新增口径见 [对照测试](../story-preview-rubric.md)；新评测跳过音频、水印和字幕专项，不能沿用旧答案的严格动作阶段或声音判定。

# 智能分镜评测

机器契约、媒体解码和实际审查分别验证。自动测试通过不能证明模型理解了视频。原静态 52 项回归继续运行。

## 可复现检查

安装 evals/requirements.txt 的 Python 依赖，将可信 FFmpeg／FFprobe 位置配置到 REVIEWER_FFMPEG、REVIEWER_FFPROBE，或加入 PATH。在 Skill 根目录执行：

```text
python -m unittest discover -s evals -p "test_*.py"
python scripts/validate_contract.py --check-schemas
```

无 FFmpeg 时媒体测试明确 skip，不能把含 skip 的结果写成媒体验收完成。提取清单的 preparation_only 不代表审查完成；必须实际看图并核对映射。

## 测试材料与盲评

build_media_fixtures.py 生成硬切、单帧短镜头、静音、非静音、淡入、变帧率和损坏视频。build_behavior_fixtures.py 生成包含人物、道具与货架的五组原创简化短视频。只在维护重建时运行，不在真实审查或盲评中运行。

blind-inputs.json 是执行者入口；input.json 只包含设计、源图和视频。behavior-truth.json、构建脚本和 results 中的报告只供维护者查看。媒体提取结果可提供给执行者，但初始 inspected 为 false；候选切点不等于已经匹配的 Shot。

先用独立上下文运行无 Skill 基线，再在另一个独立上下文加载 Skill 和相同原始输入。执行者均实际看图、检查视频时间序列和可用声音，不看答案、此前报告或生成代码。维护者对照画面评分；货架漂移、正常裁切、代表时刻和转场重复独立评测。

关注参考时刻、动作主体／对象／方向、关键因果、显著状态、正常遮挡／透视、硬切、顺序和声音证据。冻结只在动作确实必需时判错；音轨存在不证明违规；无法听辨的非静音轨为 uncertain。源图违反 Spec 时定位源图和受影响镜头，不能洗成正确基线。

## 当前完成范围

| 层级 | 已完成 | 仍待补充 |
| --- | --- | --- |
| 契约与报告 | 静态兼容、三层结果、归因、缺证、版本、状态防污染、Markdown | 随新问题补充回归 |
| 媒体读取 | 真实解码、实际 PTS、变帧率、单帧短镜、切点邻帧、静音和损坏输入 | 更多真实编码和异常时间戳 |
| 视觉内容 | 实际查看五组的全部解码帧及参考图：正常推近／非首帧锚点、货架漂移、叠化、错误源图继承、非静音缺证 | 动作主体／对象／方向、交接、身份漂移、反打、伤势门窗跨切点、错序漏镜、字幕与实物招牌的独立视频盲评 |
| 声音内容 | 无音轨、数字静音；非静音保持待确认 | 环境声、音效、台词、旁白和音乐的听辨对照 |
| 独立性 | 原静态盲评记录保留 | 本轮智能分镜独立代理因账户额度限制未完成；不能宣称盲评或全能力验收通过 |

results/behavior-results.json 将本轮五组标记为 author_informed_visual_review_not_blind。声音语义和真实生成视频未完成验收时，应在交付中说明，不能用 Schema 通过代替。
