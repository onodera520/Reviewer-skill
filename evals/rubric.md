# Reviewer 静态评测

智能分镜扩展见 [智能分镜评测](animatic/rubric.md)。原静态要求继续适用。

## 材料与盲评

cases.json 是维护者答案表；fixtures/i*.json 是盲评输入，图片引用相对各输入文件目录。fixtures/blind-batch.json 包含六个核心对照用例。PNG 是 build_fixtures.py 用 Pillow 从基本形状绘制的原创合成静态图，不是生产生成模型的输出，也不代表真实项目已验证。不得将本目录的答案用于普通审查。

先让独立评估上下文仅看输入及实际图片、不给 Skill，记录基线；随后在新上下文加载 Skill 和必要 references，对同一输入实际看图。两轮均不读 cases.json、绘图脚本或其他评估答案。常规近景、遮挡、反打、背景随机性与真正穿帮必须成对测试。对核心盲批再进行独立复测；不能把同一报告重复校验算作重复视觉测试。

逐案记录当前合规、跨镜连续性、最终决策、错误类别／严重度／归因、图像证据和状态处理。完整 runtime 报告使用 review-output Schema；评测汇总可以是紧凑记录，但必须明确它不是完整契约报告。实际打开每张需要的图片；可对相同内容去重。文字不能代替图片核验。

## 评分

- 确认穿帮需有正确基线、明确连续关系／实体、可检验属性、实际矛盾和无授权变化依据；不能因猜测判错。
- 满载货架整体清空、核心道具错误、无依据解绑等关键用例必须检出并正确分级。单镜 PASS 不抵消连续性 FAIL。
- 正常离画、遮挡、反打、微小包装或曝光差异不报消失或空间穿帮。不得通过字符串搜索“消失”给分，因为“不能判消失”是正确解释。
- 核心事实不可辨、缺图、来源失效或关系不明应 uncertain／REVISE；uncertain 不直接触发重生成。
- 三镜状态跨不可见镜头保留，错误帧不得建立／覆盖基线；下镜新事实不提前进入当前状态。场景切换清理不相关环境，稳定身份可在有依据时继续比较。
- 伤口等交叉类别按语义评分；character_continuity 与 character_state_continuity 均可，但不得重复同因问题。类别标签不是优先于证据的真值。
- 案例本身有歧义时记录原始结果，维护者实际查看材料、确认问题后修订输入并增加 Spec 版本，再重跑受影响案例。不得为凑通过率修改答案或把输入缺项当成审查器错误。

验收门槛：核心错误全部检出、正常对照零误报、证据不足不强判、状态继承／防污染通过。记录最终决策、分项、证据／状态这三类结果；发现未覆盖能力时如实列出限制。生产图尚未提供时，不宣称已完成真实生成分镜准确率验证。

## 可复现的契约验证

在 Skill 目录，使用支持 Python 3.10+ 的环境：

```text
python -m pip install -r evals/requirements.txt
python scripts/validate_contract.py --check-schemas
python evals/test_contract.py
python evals/test_render_review.py
python scripts/validate_contract.py --input evals/fixtures/i132bfbedb168.json --output 实际报告.json
```

安装 skill-creator 的环境还应执行其 scripts/quick_validate.py reviewer目录。此校验仅检查 Skill 基础结构，不证明视觉质量。检查 Markdown 链接、JSON 示例和所有 fixture 输入；成功命令及计数保留到评测记录。

scripts/validate_contract.py 不运行视觉模型，不验证中文证据的语义蕴含，也不证明“明示变化”真实存在；它只检查 JSON Schema、引用、已声明错误关联、状态和判定的一致性。输入或报告不合法返回非零退出码；缺图不通过伪造 inspected 标记补齐。

绘图脚本用于维护重建 fixture，会重写本目录 PNG／输入／cases.json；不要在盲评进行时运行。生产使用 Skill 不运行评测或绘图脚本。
