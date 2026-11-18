# 全网离散 accepted-step safeguard

新增源码仅 `experiments/intent-edit-review/physics/self_step_guard.mjs` 与 `test_self_step_guard.mjs`。本代理没有修改现有求解器、人体、材料、单位、阈值、原始记录，也没有提交。父代理负责真实逐phase集成与独立验收。

## API

`guardSelfStep(candidate, reference, previous, inverseMass, triangles, tree=null, options={})`

previous 可传null。默认 pure：输入坐标、reference、previous、质量、三角索引、传入BVH几何和原生bounds全部不写。返回 `positions: Float32Array`，以及可空的 previous 副本。只有 `options.inPlace=true` 才写 candidate/previous；任何与reference、质量、索引、tree几何或彼此重叠的输出buffer都拒绝，避免暗中改变受保护状态。

每次先把坐标转换成实际F32状态，然后检查**整个reference网格**：有严格重叠或双倍面积≤原epsilon²=1e-12m²的退化面即抛 `InvalidSelfStepReferenceError`（code=INVALID_REFERENCE，含完整referenceReport）。该模块不是解穿器。固定节点必须在reference/candidate中保持相同、已可F32精确表示的坐标，否则抛错；不能通过移动固定点制造可行回退。

完整拓扑用BVH真实leaf成员逐面验证。对每个F32 trial，重建全部精确节点bounds并进行真实三角SAT/共面正面积clip；不使用旧bounds猜测新几何，也不删除面。shared2/shared3正面积重叠明确计数并拒绝；退化candidate同样回退。

试探alpha顺序为1、1/2、1/4……，同一alpha对全部可动点作 `fround(reference+alpha*(candidate-reference))`，包含不参与当前相交的裁片。返回：

- alpha、iterations、geometryEvaluations、rejectedCandidates和完整每个拒绝trial的pair/退化/shared2/shared3统计；triangleCount/bvhTriangleCount始终保留完整NF。
- globalRollbackNorm、maxVertexRollback，均按实际F32 accepted−candidate计算；该全局step safeguard没有每顶点0.5mm接触cap，不把大回退藏在cap统计中。
- proposedDisplacementNorm(candidate−reference)、acceptedDisplacementNorm(accepted−reference)。
- fallbackToReference、zeroStoredProgress、accepted、status。

默认maxBacktracks=32。预算用完可显式返回已验证reference、alpha0、fallbackToReference=true；**非零proposal但没有F32 stored progress时，accepted=false/status=stalled**。alpha>0但F32量化成reference也同样标stall。正式物理步必须因此停止/拒绝，不能只因几何self0就继续推进时钟。

previous同步用 `previous += .8*(acceptedF32-candidateF32)`；零delta不重写signed zero。F32 previous保留F32算术存储，其他previous副本用F64。inPlace模式在明确stall时也写该显式回退状态，调用者必须读取accepted/status判断是否接受物理步。

## 验证：离散guard局部控制PASS

`node experiments/intent-edit-review/physics/test_self_step_guard.mjs`

15组控制、18个独立NumPy/SciPy SAT+退化断言。包含解析面内交错、整个可动网格统一插值、固定点、pure/inPlace契约、signed zero与previous同步、重叠buffer拒绝、无效reference显式拒绝、shared2/3、退化候选、alpha0预算边界、正alpha的F32无进度stall、40面多叶BVH和全部整数索引类型、全新Node进程逐位一致replay。

真实run33完整网格负控：source input的初始reference自交0，preparation-final.bin candidate自交6，7186面全部保留。guard返回alpha=.5，独立严格SAT为0、退化0、无reference fallback、有stored progress；全部输入与传入BVH保持不变；全新进程的返回状态和几何诊断bit-exact。

该真实负控跨整个24步准备，不是一个物理步。其proposed global norm=2.2772995045m，accepted norm=1.1386497790m，rollback norm=1.1386497255m，max vertex rollback=47.249127mm。单次检测约0.83s，仅用于该全网例的量级参考。

测试结果为test_self_step_guard.json；完整真实输入/返回状态为actual-result.json。

## 独立全gate明确FAIL：guard不代替人体条件

为防止把self0误当全状态通过，用原verify_preparation.py对上述返回状态进行独立完整检查（单独work checkpoint，原run33记录不动）：

| 指标 | 结果 |
|---|---:|
| strict self | 0 |
| 退化面 | 0 |
| seam gap | 0mm |
| both_arms_threaded | true |
| 人体内部采样 | 6668 |
| 最大人体穿入 | 17.03194mm |
| 布边→人体hits | 1007 |
| 人体边→布面hits | 562 |
| 整体独立gate | FAIL |

这是将初始到准备末态的跨度一次回退所得到的非物理例，不代表父代理逐native/body/self phase集成的run34结果。它说明离散self safeguard只守当前自交和退化条件，人体、数字穿臂、缝线、材料与真实动力学仍必须分别通过。此模块不是CCD、不是连续路径无碰撞证明、不是准确动力学或fit批准。

accepted-checkpoint/preparation-gate.json保留完整独立FAIL与人体/穿臂报告；manifest.json记录源码、测试和原始输入/状态哈希。物理fit、材料实测仍NOT_RUN。
