# 验证方法与操作手册

先按症状、任务范围和证据缺口选择检查，再读当前软件的操作手册。已有证据需匹配候选版、尺码、姿势、人台、面料和闭合状态。默认从最能区分原因的检查开始。完整验收按 [整衣验收](../finish-verification.md) 核对适用项。

先读所用软件的操作约定，再读对应条目。

- [Style3D MCP / 原生 JSON API](style3d.md)
- [CLO 3D MCP](clo3d.md)

| 检查项 | Style3D MCP / API | CLO 3D MCP |
| --- | --- | --- |
| 应力热点、拉扯 | [Style3D](stress/style3d.md) | [CLO 3D](stress/clo3d.md) |
| 伸长与活动松量 | [Style3D](strain/style3d.md) | [CLO 3D](strain/clo3d.md) |
| 人体受压、裁片接触压力 | [Style3D](pressure/style3d.md) | [CLO 3D](pressure/clo3d.md) |
| 上身效果、轮廓与线稿 | [Style3D](appearance/style3d.md) | [CLO 3D](appearance/clo3d.md) |
| 夹布、人体穿模、层间穿插 | [Style3D](collision/style3d.md) | [CLO 3D](collision/clo3d.md) |
| 缝合错配、缺失、反向及吃势 | [Style3D](sewing/style3d.md) | [CLO 3D](sewing/clo3d.md) |
| 褶皱、折角与异常折线 | [Style3D](folds/style3d.md) | [CLO 3D](folds/clo3d.md) |
| 人台、尺码、量体与姿势 | [Style3D](avatar/style3d.md) | [CLO 3D](avatar/clo3d.md) |
| 纸样导入、比例与几何 | [Style3D](pattern/style3d.md) | [CLO 3D](pattern/clo3d.md) |
| 面料赋值、丝缕与物性 | [Style3D](fabric/style3d.md) | [CLO 3D](fabric/clo3d.md) |
| 配饰、扣件与闭合 | [Style3D](closures/style3d.md) | [CLO 3D](closures/clo3d.md) |
| 模拟状态、稳定性与复测 | [Style3D](stability/style3d.md) | [CLO 3D](stability/clo3d.md) |

## 补充检查与新症状

上表可按款式与用途扩展。厚层夹布可从碰撞与面料检查着手，左右不对称可从姿势、纸样镜像和缝合方向着手，动态活动受限可在目标姿势中组合应变、压力和外观检查。按所用软件选择该行的操作手册。

遇到目录未覆盖的问题，先记录部位、尺码、姿势、出现时机、最近改动及可见症状。明确要区分的原因和可观察的通过条件，再查当前软件目录、原生 UI 或已有证据能支持的最小验证。保留使用的方法、输入、单位、证据来源和覆盖边界。依任务标准判定，缺少可信证据时记为待验证。新方法可沿用每项一个目录、每软件一份手册的结构。
