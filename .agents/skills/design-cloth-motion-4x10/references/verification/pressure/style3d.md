# 试穿接触压力 · Style3D MCP / API

确认 Fitting 权限。用 `Avatar.GetAllIds` → `Simulation.GetAvatarPressureMap` 定位人体主表面受压。需要查来源裁片时，用 `Pattern.GetAllMainClothPieceIds` → `Simulation.GetClothPressureMap`。两种图均为 Pa，输出 kPa 时除以 1000。按 [Style3D 操作约定](../style3d.md) 核对 `valid`、值数和网格指纹，保留原始单位。

标明压力图的承压侧、接触区域、采样范围及平均值是否包含零值。两侧网格离散不同，区域对照时用人体部位和裁片位置定位。显著压点结合 [人体碰撞](../collision/style3d.md)、扣位和同姿势图检查。
