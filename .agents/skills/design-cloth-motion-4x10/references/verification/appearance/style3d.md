# 上身外观与线稿图 · Style3D MCP / API

用 `Snapshot.GetProject3DImageConfig` 取配置，`Snapshot.ExportImage3D` 导出与线稿匹配的视角。核对输出文件及导出后实际视图。参考已在工程内时用 `Sketch.GetAllIds` → `Sketch.GetProperties` 找原图路径和导入信息，也可直接用用户给的原图。3D 导出可能暂停任务或改变界面。

按 [线稿对照](../../line-art.md) 对齐比例、视角、姿势和闭合状态，标出轮廓、长度和设计细节差异。MCP 提供取图和定位，差异由实际并排图或叠图评审。
