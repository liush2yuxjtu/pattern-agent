# 应变 · Style3D MCP / API

用 `Pattern.GetAllMainClothPieceIds` 和 `Simulation.GetClothStrainMap` 逐片取原生应变。按 [Style3D 操作约定](../style3d.md) 核对有效性和网格对应。原生应变比乘以 100 显示为百分比，原始值、单位字段与显示换算一并保留。按同尺度标注热点，说明原生逐顶点标量的定义和统计口径。需要方向分析时，另用匹配的纸样与变形网格计算并明确其定义。
