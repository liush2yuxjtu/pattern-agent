# Rapier native cloth probe

目标是复用现成开源动力学，交付单 HTML Garment Artifact。该目录验证 Rapier 0.21.0 的真实 JS/WASM 能力，提供可打包的适配器，不实现自写动力学。

`engine.mjs` 可供正式界面打包。`adapter.mjs` 是通用原始探针适配器。`native-seam.mjs` 是可独立执行的最小原生缝合示例。`probe.mjs` 和 `engine-probe.mjs` 产生数值报告。

## 已验证 API

| 功能 | 实际 API | 结果 |
| --- | --- | --- |
| 原生布料生成 | `SoftBodyDesc.cloth`、`clothTube`、`clothAnisotropic` | `cloth` 已运行，其余仅确认声明 |
| 纸样网格 | `new SoftBodyDesc(restXYZ)`、`setEdges`、`setDihedrals`、`setSurface` | 已运行 |
| 布面接触 | 默认 surface collider、`setParticleRadius` | 固定 trimesh 球及 MakeHuman 已运行 |
| 自接触 | `setSelfContacts(true)` | 同 body 两个不连接裁片的落布正反对照通过 |
| 固定点 | `setParticlePinned` | 装配后设置，步进后漂移为零 |
| 步进与输出 | `World.step()`、`particlePositions()` | 已运行 |
| 原生跨片缝合 | `addSoftBodyCluster`、`clusterProxy`、`JointData.spherical`、`createImpulseJoint` | 同 body 与跨 body 均收敛 |
| 资源释放 | `World.free()` | 适配器重复 dispose 可接受，释放后读取拒绝 |

`SoftBody` 没有运行时 `addEdges` 或 edge rest-length setter。高层 `SoftBodyDesc.addEdges` 只修改创建描述。原生 spherical joints 可以在创建后连接单粒子 cluster，不改变纸样结构边的 rest length。

## 已观察结果

完整输入、步数、dt、source SHA256、初始及最终 positions 保存在 `report.json` 和 `engine-report.json`。

| 实验 | 结果 | 证据 |
| --- | --- | --- |
| 49 粒子自由布，120 步 | PASS | 平均 Y 从 1 m 到 -3.454844 m |
| 49 粒子固定两点，240 步 | PASS | pin 漂移 0 m |
| 固定 trimesh 球，360 步 | PASS | 布被支持，最终及每 30 步样本均 0 体内点、0 严格面穿 |
| MakeHuman 头顶自由落布 | FAIL | 最终平均 Y=-3.105641 m，未保持在头顶。不能用最终 0 面穿证明穿戴成功，也未判定失败原因 |
| selfContacts 关闭 | PASS，负对照 | 上层布穿过下层固定布，最终最低 Y=-9.210772 m |
| selfContacts 开启 | PASS | 上层布最终最低 Y=0.009994 m |
| 跨 body spherical seam | PASS | 初始 gap 0.2 m，240 步后最大 gap 0.003982 m。无 joint 对照 19.640789 m |
| 同 body spherical seam、自接触开启 | PASS | 最大 gap 0.000345 m，全部结构边 rest length 不变 |
| 同 body coincident 输入的 zero-rest edge | PASS，有限用途 | gap 0.004645 m。要求初始装配 seam 已经重合，不能从不同位姿定义 seam rest |
| raw builder 临时 1 mm seam，然后恢复初始位姿 | FAIL | 结构边及 seam rest 为 `[0.5,0.5,1]` m，seam 最终仍为 1 m |
| raw builder 临时 1 mm seam，不恢复 | FAIL | rest 变为 `[1,0.999,0.001]` m，材料边也被更改 |
| `engine.mjs` 二维 rest、三维装配、原生 seam、pin | PASS | `engine-report.json` 记录最大 seam gap、二维 rest 误差及 pin 漂移 |
| `engine.mjs` MakeHuman 胸部法向接触，半径 3 mm | FAIL | 第 210 步有 4 对严格面穿，体内顶点为 0，最终面穿也为 0 |
| 同适配器同接触实验，半径 5 mm | PASS，离散样本 | 每 30 步样本均 0 体内点、0 严格面穿，最终最小间距约 0.004996 m |

默认接触半径为 5 mm。该参数是演示中的数值接触设置，未做真实面料厚度标定。不得把 3 mm 坏例改写为成功。

## 适配器 schema

| 字段 | 形状 | 单位及作用 |
| --- | --- | --- |
| `restXY` | `[[x,y],...]` 或 flat array | mm，二维纸样的材料 rest |
| `triangles` | `[[a,b,c],...]` 或 flat array | 粒子索引，自动提取结构边与 dihedral |
| `initialXYZ` | `[[x,y,z],...]` 或 flat array | m，三维初始装配位姿 |
| `seamPairs` | `[[a,b],...]` | 同 body 单粒子 cluster spherical joint |
| `seams` | `[{id,pairs:[[a,b],...]}]` | 与 mesh agent schema 兼容，等价于合并 `pairs` |
| `pinnedIDs` | `[index,...]` | 三维装配后才设置 pin |
| `body` | `{positions,triangles}` | flat xyz，m。使用显示用的同一个 MakeHuman 网格 |
| `gravity` | `[x,y,z]` | m/s²，默认 `[0,-9.81,0]` |
| `particleRadius` | number | m，默认 0.005 |
| `mass` | number | kg，总布体质量，默认 0.15 |

各片可以使用重叠的局部二维 UV。结构边只来自各片 triangles。跨片位置关系只由三维装配和显式 seam 决定。

```js
import {create} from './probes/rapier/engine.mjs';

const engine = await create({
  restXY: mesh.restXY,
  triangles: mesh.triangles,
  initialXYZ: assembledPositions,
  seams: mesh.seams,
  pinnedIDs: shoulderSupportIDs,
  body: {positions: makehuman.positions, triangles: makehuman.triangles},
});
engine.step(1);
const positions = engine.getPositions();
const stats = engine.nativeStats();
engine.dispose();
```

`step(n)` 使用固定 `dt=1/120` s，默认 n 为 1。`getPositions()` 返回 WASM 复制出的 Float32Array。`nativeStats()` 返回原生边、rest length、seam gap、计数及 rest 未变标志。`dispose()` 可重复调用。正式适配器只使用高层公开 API。

## 可复现命令

```sh
node probes/rapier/probe.mjs
node probes/rapier/engine-probe.mjs
node probes/rapier/native-seam.mjs
```

## 范围和限制

这些实验是小网格探针，不是成衣认证。它们没有证明 1200 粒子完整衣服可稳定穿戴。报告不含比较性性能结论。

胸部接触实验使用 `[0,0,-1]` 加速度隔离人体表面接触。它未测试正常重力下的完整穿戴。肩部 pin 是有标记的演示支撑。

独立审计同时检查顶点体内和三角面穿。零体内点不能替代面穿审计。每 30 步离散样本也不能证明两样本间没有穿越。任意纠缠、连续碰撞和有限厚度无穿透仍为 UNKNOWN。

缝合连接粒子位置，没有添加专用 seam bending 或材料 sewing 模型。二维材料没有经过真实布料标定。拓扑改变后须重建适配器。

建模时使用粒子、三角形和 seam pair 作为输入结构。验证时直接读取真实 WASM 粒子和 native edge rest，避免以接口存在代替行为证明。
