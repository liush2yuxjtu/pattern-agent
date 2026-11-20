# 纸样导入与几何 · Style3D MCP / API

用 `Pattern.GetAllClothPieceIds` 与 `Pattern.GetEdges` 盘点裁片、轮廓和内部线。用 `Pattern.GetEdgeLengths` 取 2D 原生曲线长度，用已知尺寸验证缩放。需查刀口或缝份时读取 `Pattern.GetNotches`、`Pattern.GetSeamAllowanceProperties` 并记录权限或缺项。缝合净线与裁切外轮廓应按来样定义找到各自对应边。

用 `Pattern.ValidatePatternPiece` 或 `Pattern.ValidatePatternPieces` 查原生自交诊断。批量结果要逐片查 `valid` 和错误字段，同时核对目标版次、尺码、裁片数量、方向和镜像。
