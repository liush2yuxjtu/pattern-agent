# 缝合配对与走缝 · Style3D MCP / API

用 `Sewing.GetAllIds` 遍历原生缝合（含拉链拥有的连接），用 `Sewing.GetSegments` 和 `Pattern.GetEdges` 将每侧有序范围映射到裁片和线段。结合方向、对称标记、曲线起止参数、预期工艺单或同版参考，定位漏缝、交叠、反向及错配。必要时用 `Pattern.GetNotches` 查对位点。

用 `Sewing.GetLengths` 记录两侧原生总长（mm）和差值。按需查 `Sewing.GetProperty` 的启用、缝型及弹性等配置，以实测段和已知吃势核对。标明是否含拉链或多对多、是否覆盖内线。改纸样拓扑后重新读 ID 和边段。
