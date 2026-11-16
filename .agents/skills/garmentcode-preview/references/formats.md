# 输入与输出约定

## 纸样

GarmentCodeData 的单个样本包含 `*_specification.json`。根对象的 `pattern.panels` 是布片字典，布片有二维 `vertices`、含 `endpoints` 的 `edges`、三维 `translation` 与 `rotation`。`pattern.stitches` 的前两项为 `{panel, edge}`，可能有第三项 `right_wrong`。曲率支持上游直线、二次／三次贝塞尔、圆弧格式，由官方解析器处理。

`properties.units_in_meter` 表示每米有多少个纸样长度单位：100 为厘米，1000 为毫米。上游 `BasicPattern` 会规范化单位；不要误把它理解为“每单位多少米”。

样本目录可能包含 `body_measurements.yaml` 或 `*_body_measurements.yaml`、设计参数 YAML、初始 `*_boxmesh.ply`、已仿真的 `*_sim.ply`。脚本支持匹配两种测量命名。目录里多个 specification 时需要显式文件路径。

随机人体测量中的 `body.body_sample` 对应人体网格名称。该名称本身不是人体几何。仿真需要实际网格，不能仅靠围度推断人体表面。默认非 SMPL 人体使用仓库的 GGG 分割；SMPL 则增加 `--smpl`。

## 输出

`existing` 模式直接接受 OBJ/PLY/GLB，不需要原纸样、源码或人体。GLB 默认米；
OBJ/PLY 默认厘米，其他单位用 `--existing-scale` 显式指定。其 manifest 输入哈希
来自实际网格，`mesh_generated_this_run=false`，`simulation.executed=false`。

- `preview.html`：独立离线三维预览，拖动旋转、滚轮缩放、线框、人体显隐、正面／背面。不是实时布料求解器。
- `preview-fragment.html`：同一预览的聊天片段。
- `garment-initial.glb`：本次生成的初始缝合网格，米单位。
- `garment.glb`：物理结果或明确标记的已有结果，米单位。
- `manifest.json`：输入 SHA-256、来源、模式、顶点／面数、软件版本、人体及仿真质量。
- `mesh/`：上游 OBJ、原始边长、缝合分割与标签、纹理、纸样副本等。OBJ 使用上游厘米单位。
- `runtime/`：该次运行独立的 `system.json` 和输入暂存。无需覆盖原仓库配置。

对初始和仿真网格保留相同的拓扑编号，便于比较顶点位移。GLB 导出和渲染导入可能复制 UV 接缝顶点；不要由 GLB 的顶点编号推断原始分割标签。

## 失败与状态

无效单位、非有限坐标、越界边索引、错误缝合关系、重复缝边会在调用原生网格器之前拒绝。物理超时、没有稳定或超出配置阈值时，上游阈值检查为 FAIL，保留诊断几何；不称为成功试穿。

schema_version=2 分别记录执行、稳定、上游宽松阈值、零人体/自相交计数、独立全量
审计和实体合身。`quality_passed` 兼容旧格式，仅对应上游配置阈值，与新增
`upstream_threshold_passed` 同义；使用 `release` 读取严格判定。计数检查通过也不
升级完整独立审计和合身的 NOT_RUN。未执行模式的检查一律 NOT_RUN。

退出码 0 表示所选计算/导出流程完成，零穿透 FAIL 的研究网格仍可交付排查；
仿真异常退出码 2，普通输入/环境错误为 1，argparse 参数错误为 2。读取 manifest
中的实际状态，不仅以退出码判断质量。达到帧数上限却尚未稳定时不会伪称静止。

更改人体、布料刚度、分辨率、碰撞策略或初始化都会影响最终褶皱。本工具负责技术预览，不推导生产缝份、排料或制造合格性。
