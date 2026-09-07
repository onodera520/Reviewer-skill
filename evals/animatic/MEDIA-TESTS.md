# 本地媒体测试

`build_media_fixtures.py` 只生成受控测试素材：两个硬切（中间镜头只有一帧）、淡入、变帧率、无音轨、数字静音音轨和非静音测试音。真值写入 `media-truth.json`，不交给执行盲评的 Reviewer。

设置 `REVIEWER_FFMPEG`、`REVIEWER_FFPROBE` 为本地程序的绝对路径，然后运行：

```text
python -m unittest discover -s reviewer/evals/animatic -p test_prepare_animatic.py -v
```

没有依赖时真实媒体测试显示 `skipped`，不能把跳过算作能力通过。测试确认实际解码、时间戳、抽帧和声音信号检查，不确认语义审查能力。

媒体预处理示例：

```text
python reviewer/scripts/prepare_animatic.py input.mp4 --output .reviewer/media-run-01 --ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe
```

输出目录必须尚不存在。`--segments` 接受分段 JSON 列表（`shot_id`、`start_seconds`、`end_seconds`）；这些始终是待核验提示。`--anchor-time` 可以重复提供参考时刻。`--dense-ranges` 接受时间范围 JSON 列表，在可疑动作、转场或字幕区域逐帧抽取。所有时间为秒，以首个视频帧的实际 PTS 为零点，原始 PTS 同时保留；音频片段带有对应视频时间偏移。

切点扫描不等于切点确认。相似画面的硬切、缓慢叠化、短暂字幕可能无法从默认采样判断。需要观察相邻原始帧、加密范围及实际时间序列；未观察到的部分应进入覆盖限制。

非静音测试音只能证明音轨有信号，不能自动判为音乐。无音轨和全部通道精确数字静音可完成声音约束检查；非静音需要实际听辨，未听辨时为 `uncertain`。生成的 WAV 只供审查取证，不作为用户报告中的原视频入口。
