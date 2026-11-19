---
name: clo-fit-export
description: 在 Boat Linux 从同一批姿势导出试穿图、应变图、应力图、褶皱图。Rust 复算应变和折角，CLO 源图提供原生合体分类与应力画面。
---

# 四类图导出

1. 准备同拓扑的各姿势服装网格。每个姿势补上来自同一个 CLO 工程版本、视角配对的正背试穿图和正背应力图。
2. 一次运行 `run_boat.py <sandbox> fit-export <input> <output>`。Boat 已有输入和插件时执行 `boat_batch.py fit-export <input> <output>`。
3. 用 `map-status.json` 核对每姿势四类图都为 complete。CLO 原生试穿和应力图应和输入逐字节一致。Rust 从毫米网格生成应变和褶皱图，并保留 CSV、JSON、VTK 及 HTML。报告里的原生应力 PNG 只表示存档画面。
4. 缺少原生图时补齐相应正背图，或使用 `review` 生成明确标注缺图的复核。当前几何运行时无法重算材料应力或模拟新姿势。

[Boat 批处理和输入结构](../clo-rust-boat-fit-review/references/boat-run.md)
