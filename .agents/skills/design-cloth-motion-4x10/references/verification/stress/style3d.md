# 应力 · Style3D MCP / API

用 `Pattern.GetAllMainClothPieceIds` 枚举主裁片，再按片调用 `Simulation.GetClothStressMap`。按 [Style3D 操作约定](../style3d.md) 核对网格对应和有效状态。记录逐顶点原生标量，单位 kPa。用固定色标的热图和同视角定位图标出高值区，交代采样范围。比较时记录网格密度及统计口径，避免用单个异常顶点代替区域判断。

缝边、扣位或袖窿集中升高时，先定位到缝合段和扣合状态，再按症状核对面料或应变。原生标量图不包含经纬方向应力或张量分量。
