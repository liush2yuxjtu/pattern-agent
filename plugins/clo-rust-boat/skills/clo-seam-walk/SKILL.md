---
name: clo-seam-walk
description: 在 Boat Linux 中用 Rust 一批核对服装缝合定义、边段方向、长度差、约束和工程连通性。用于领座、袖山、里布、门襟和下摆缝合复核。
---

# 批量排查缝合

1. 为一个批次准备源裁片边、CLO 边号映射、缝段定义和实测连通性参照。保留原始纸样，检查接缝长度差所对应的设计吃势。
2. 一次运行 `run_boat.py <sandbox> seam-walk <input> <output>`。Boat 已有输入和插件时执行 `boat_batch.py seam-walk <input> <output>`。
3. 读回 `sewn.pattern.json`、`seam-audit.json`、`seam-reopened.json`、`constraints.json`、`connectivity.json` 和 `run.json`。检查区间覆盖、方向、长度差、约束条数以及严格连通性参照。缺少来源或出现错误时留在该批次处理。
4. 将改动记录带回 CLO 工程后，才进行原生成衣缝合、模拟和画面复核。Boat 保存的是 Rust 缝合工程及求解约束。

[Boat 批处理和输入结构](../clo-rust-boat-fit-review/references/boat-run.md)
