# 实际物理执行路径

本说明对应 GarmentCode `d449629979028123a5c4dc9e732a2ec19b7fce31` 与
NvidiaWarp-GarmentCode `63baf6855efdd89b2834b74640f84b3bb0d86b50`。
执行顺序为 `BoxMesh.load/serialize` → `SimConfig/PathCofig` → `Cloth` →
`sim_frame_sequence` → OBJ/GLB 与独立 HTML。原生依赖与 CPU 编译见 setup.md。

## 从纸样到模型

BoxMesh 采样裁片曲线、约束三角剖分、按位姿摆放，再合并缝边对应顶点。
接缝是共用拓扑，不是逐针缝纫。保存二维原长 `orig_lens`，避免把接缝合并后
拉歪的三维边长当成布料自然长度。仿真改变顶点位置，保留三角形拓扑。

Cloth.build_stage 调用修改版 `ModelBuilder.add_cloth_mesh_sewing_spring`：
三角形面积与密度决定顶点质量；为网格边创建距离弹簧，为相邻面创建弯曲约束。
人体经单位换算后以 `add_shape_mesh(body=-1)` 加入，是固定碰撞体。
输入需要人体 OBJ、尺寸 YAML 和与人体拓扑匹配的分区；围度数字不能代替碰撞表面。

## 实际求解与参数

`Cloth.integrator` 实际是 `XPBDIntegrator()`。旧注释中的 Euler 不是当前选择。
每子步先预测位置，再累加约束位置修正并更新速度；默认一轮求解，每帧十子步。

| 行为 | 实际路径 | 参数 |
| --- | --- | --- |
| 抗拉伸 | solve_springs；C = 两点距离 − 原长 | spring_ke、spring_kd |
| 抗弯曲 | bending_constraint；相邻三角形折角 | garment_edge_ke、garment_edge_kd |
| 人体接触和摩擦 | 粒子与固定形状接触约束 | soft_contact_*、body_friction、厚度 |
| 自碰撞 | 顶点/三角形、边/边约束 | enable_triangle_particle_collisions、enable_edge_edge_collisions |
| 附着与穿体纠偏 | attachment_constraint、reference_shape_drag_constraint | 标签及对应配置开关 |

构建器保存 tri_ke/tri_ka 等 FEM 材质字段，但本版本 XPBD 循环没有调用三角形
面内/面积 FEM 求解；不要据字段存在声称它生效。自碰撞开关也不保证零穿透。

SimConfig 为 60 帧/秒、每帧十子步，所以 dt=1/600 秒。每帧先 collide，再循环
clear_forces → integrator.simulate → 交换 state_0/state_1。GUI 配置前十帧零重力，
随后启用；附着释放、人体参考纠偏及碰撞过滤按实际标签和配置生效。
60fps 是仿真时间刻度，不是实时计算速度。代码重力值为 (0,-9.81,0)，项目还有
厘米/米及数值材料尺度；该配置未经真实面料标定，不能直接报告 SI 材料测量结果。

## 停止、失败与检查

sim_frame_sequence 在最小帧条件后按相邻帧的顶点位移判断基本静止，另有帧数和
墙钟时间上限。CPU numpy() 可能是共享视图；SnapshotCloth 每帧前复制旧位置，
只修正静止比较，不改变 XPBD 内核。静止不等于没有穿透或实体合身。

manifest 分别记录 executed/error、static、相交计数和 release。宽松 GUI 阈值与
仓库零穿透门槛分别判定；完整独立几何审计及实体试穿未执行时为 NOT_RUN。
异常保留诊断网格并退出 2；未稳定的帧数上限结果保留但明确标注。

## 复现示例

从技能根目录，用已安装依赖的 Python：

```bash
python scripts/garment_preview.py build \
  --pattern assets/example-shirt_specification.json \
  --repo /absolute/GarmentCode --mode simulate --resolution 1.5 \
  --max-frames 2400 --max-seconds 600 --out /output/new-shirt-run
```

数据集自定义人体还需匹配的 --body-mesh、--body-measurements；非米人体显式设置
--body-scale。网页只读取已生成的 GLB/内嵌几何。改纸样后重新运行 Python 求解。

源码：
- [Cloth 与帧循环](https://github.com/maria-korosteleva/GarmentCode/blob/d449629979028123a5c4dc9e732a2ec19b7fce31/pygarment/meshgen/garment.py)
- [配置与停止](https://github.com/maria-korosteleva/GarmentCode/blob/d449629979028123a5c4dc9e732a2ec19b7fce31/pygarment/meshgen/simulation.py)
- [XPBD 内核](https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode/blob/63baf6855efdd89b2834b74640f84b3bb0d86b50/warp/sim/integrator_xpbd.py)
