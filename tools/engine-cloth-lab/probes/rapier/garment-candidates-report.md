# 粗网格成衣候选

目标是找到可运行的原生布料配置，并减少初始穿模。当前没有完整缝合且无穿模的成衣候选。

`garment-candidates.mjs` 读取 `src/pipeline.mjs` 生成 spacing40 的相同裁片。它只在初始装配阶段修改 positions。创建 engine 后只调用 Rapier 原生步进。

| 候选文件 | 初始结果 | 运行结果 | 判定 |
| --- | --- | --- | --- |
| `garment-candidate-project-weld-fail.json` | 0 inside、25 对 body 面穿，maxStretch 4.61 | 4 步后 20 对 body 面穿、37 对 self 面穿、gap 836 mm、maxStretch 19.48 | FAIL |
| `garment-candidate-planar-spring.json` | 0 inside、0 body 面穿、0 self 面穿、maxStretch 1.0 | 6 步后 5 对 self 面穿，maxStretch 4.71 | FAIL |
| `garment-candidate-planar-spring-gentle.json` | 0 inside、0 body 面穿、0 self 面穿、maxStretch 1.0 | 30 步后仍 0 inside、0 body 面穿、0 self 面穿，gap 467.88 mm，maxStretch 1.3704 | 仅短程装配候选。完整缝合 UNKNOWN |
| `garment-candidate-planar-spring-medium.json` | 0 inside、0 body 面穿、0 self 面穿、maxStretch 1.0 | 120 步后 3 个 inside、21 对 body 面穿、4 对 self 面穿、gap 378.52 mm | FAIL |
| `garment-candidate-cylinder-weld-gentle.json` | 0 inside，但 90 对 body 面穿、maxStretch 7.44 | 未步进 | FAIL |

全部动态候选有 485 particles、800 cloth triangles、62 seam joints 和 8000 body triangles。gentle 与 medium 只固定前片两个肩点。投影并不能保证三角形不穿体。失败候选再次证明 0 inside 不等于 0 面穿。

## 可供界面采用的有限配置

`garment-candidate-planar-spring-gentle.json` 保存 `positions`、`pins`、`config` 及运行后的 `finalPositions`。这是裁片在人体外侧的平面初始装配。它没有缝好，界面必须显示开缝。

```js
const engine = await create({
  restXY: mesh.restXY,
  triangles: mesh.triangles,
  initialXYZ: candidate.positions,
  pinnedIDs: candidate.pins,
  seams: mesh.seams,
  body: human,
  ...candidate.config,
});
```

配置使用原生 `JointData.spring(0,0.01,0.0035,...)`，不是自写约束。材料 edge frequency 为 60 Hz，bend frequency 为 2 Hz。global solver iterations 为 4，额外 PGS 为 2，额外 body solver iterations 和 impact-adaptive substeps 都为 0。

它的结构 rest length 逐项保持不变。二维纸样和三维装配没有合并为一个 rest 状态。30 步为 0.25 s 模拟时间。最大缝隙从 591.47 mm 降到 467.88 mm，远未闭合。大于 20% 拉伸的纸样面积比例为 0.003728。不能把该值称为面料合格率。

## 单步耗时

以下数字来自一次未开 profiler 的完整 run。计时范围仅包围 `engine.step(1)`。positions 被读取并检查有限，输出确有改变。初始化、报告 JSON 写入及三角审计不在该计时内。

gentle 首步为 277.59 ms。其余 29 步范围为 8.52 至 35.91 ms，中位数为 10.03 ms。没有 5 次重复，也没有实现间性能比较。

project-weld 失败候选前 4 步为 308、220、621、9467 ms。其速度下降与状态爆炸同时出现。不能把该数字归因为固定的人体三角形成本。

独立 profiler run 保存在 `garment-step.cpuprofile`。它没有用于上述耗时数字。全程 reset 的大量采样在 `MeshBodyCollider._build` 和审计 `buildBVH`。步进区域执行 Rapier WASM。热点只有 `wasm-function[297]`、`[1037]` 等 stripped 标号，不能据此声称已定位到某个 Rust 接触函数。

已确认的成本限制包括单线程 native step、8000 面精确碰撞、自接触以及约束迭代。各项占比尚未隔离。冷首步还含 WASM 首次执行成本。一次初始审计约 146 ms，30 步审计约 75 ms，须与原生步进耗时分开显示。

## 可复现命令

```sh
CANDIDATE_MODE=planar-spring-gentle CANDIDATE_STEPS=30 timeout 20s node probes/rapier/garment-candidates.mjs
CANDIDATE_MODE=planar-spring-medium CANDIDATE_STEPS=120 timeout 45s node probes/rapier/garment-candidates.mjs
```

脚本每 10 步保存检查点，支持外部 timeout。用户界面仍须使用可 terminate 的 Worker。运行失败时须显示真实失败，不能替换为缓存姿态。

`engine.mjs` 新增可选 `solverIterations`、`maxExtraSubsteps`、`seamMode`、`seamStiffness`、`seamDamping`。默认 spherical seam 行为保持不变。`native-seam.mjs` 只导出 `stitch`。CLI 最小例移到 `native-seam-cli.mjs`，浏览器 IIFE 打包已通过。
