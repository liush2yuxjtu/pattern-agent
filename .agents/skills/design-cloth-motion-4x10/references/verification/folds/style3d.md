# 褶皱与折角 · Style3D MCP / API

用 `Snapshot.ExportImage3D` 标出褶皱脊线和范围。按主裁片采 `Mesh.GetClothPieceSnapshot` 并用 `Mesh.ValidateSnapshot` 检查。需要数值时，在同裁片有效相邻三角面之间计算无符号二面折角，约定共面且朝向一致为 0°，写明边界、退化面及非流形边的过滤规则。

保存裁片、视图、角度单位和统计口径。同条件比较时固定网格设置和阈值。Style3D 的 `Vertex.GetAngleSummary` 对应 2D 顶点角，3D 折角用衣片网格复算。
