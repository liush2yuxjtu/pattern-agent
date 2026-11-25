# 应变 · Style3D MCP / API

用 `Pattern.GetAllMainClothPieceIds` 和 `Simulation.GetClothStrainMap` 逐片取原生应变。按 [Style3D 操作约定](../style3d.md) 核对有效性和网格对应。区分「为原长的百分比」和「比原长伸长的百分比」。当前接口返回以 1 为原长的比值时，前者为 `ratio × 100`，后者为 `(ratio − 1) × 100`。例如 1.12 表示原长的 112%，即伸长 12%。换版本时先核对 schema 和参考状态。原始值、单位字段和换算方式一并保留。按同尺度标注热点，说明统计口径。需要方向分析时，另用匹配的纸样与变形网格计算并明确其定义。
