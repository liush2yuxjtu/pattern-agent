---
name: clo-rust-boat-fit-review
description: 在 Boat Linux 批量运行 CLO_RUST，检查准备、运行时、缝合和多姿势网格，并读回原生图和几何分析结果。也兼容此技能的已有调用。
---

# 运行 CLO Rust Boat

需要已经授权且在运行的 Boat sandbox。确认 Boat 客户端可访问它，并使用本插件提供的入口：

| 任务 | 批次模式 |
| --- | --- |
| 多姿势、线稿和几何复核 | `review` |
| 纸样缝合关系及约束复核 | `seam-walk` |
| 每姿势严格交付四类图 | `fit-export` |

本机用一个 `scripts/run_boat.py` 批次发送输入、在 Linux 执行并取回结果。在 Boat 已有输入时直接用 `scripts/boat_batch.py`。私人包带有 Linux `pattern-native`，启动时检查架构和 SHA-256。仓库版如果没有随附二进制，使用已授权 Boat 中现成的 `pattern-native` 路径。

先核对来源、姿势和各文件是否有权传入 Boat。每批次只复制指定的服装网格、缝合 JSON、线稿和存档图。UV 与三角索引须匹配，旧的结果目录不能被覆盖。核对实际运行回执和各模式输出后再汇报。

[批处理命令、输入目录和结果检查](references/boat-run.md)
