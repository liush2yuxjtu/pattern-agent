---
name: clo-dxf-fit-review
description: 在 Boat Linux 用 Rust 批量复核服装纸样、已保存姿势的网格和试穿证据，并交付离线报告。适用于将本机 CLO 的多姿势、线稿和缝合检查交给 Boat。
---

# 多姿势试穿复核

1. 确认源纸样、单位和各姿势的服装网格。DXF 保留作来源；先用已有工具从 DXF 建立工程并保存各姿势，或直接提供已保存的公制 CLO 服装 GLB。Rust 也可审计已有的结构化纸样和缝合定义。
2. 用 `../clo-rust-boat-fit-review/scripts/prepare_meshes.py` 一次核对所有姿势的 UV 和三角面索引，并在本机生成只含服装数据的批次目录。需要外观对照时附上授权线稿。需要原生合体或应力图时附上同姿势的 CLO PNG。
3. 在同一个 Boat 任务执行 `run_boat.py <sandbox> review <input> <output>`，或在 Boat 直接执行 `boat_batch.py review <input> <output>`。读取回执和每个姿势的 `map-status.json`。
4. 对照 HTML、CSV、JSON 与 VTK 的姿势数、裁片数和色标。说明哪些指标来自 Rust 几何、哪些来自 CLO 存档。比较同一视角和扣合状态的线稿与外观。

[Boat 批处理和输入结构](../clo-rust-boat-fit-review/references/boat-run.md)
