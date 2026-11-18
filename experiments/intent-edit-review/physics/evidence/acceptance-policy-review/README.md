复查范围是 `run_native.mjs` 接入 `self_step_guard` 时的验收策略。没有修改生产源码；父代理完成了两处修复。

在仓库根目录复现：

```bash
node work/intent-physics/acceptance-policy-review/counterexamples.mjs > work/intent-physics/acceptance-policy-review/counterexamples.json
```

脚本调用实际 `guardSelfStep`，并从当前 `run_native.mjs` 提取原样的私有 `contacts(history)` 函数执行。只有外部 native/body 阶段提供合成位置提案；这不是 WASM 服装仿真。结果 JSON 包含完整坐标、三角索引、逐阶段返回值、当前运行时判定及源码 SHA。

| 反例 | 原策略 | 实际 guard 证据 | 当前策略 |
|---|---|---|---|
| 第一阶段被量化回退，后续阶段合法移动 | 整步最终位置变了，错误地允许时钟前进 | 约1米坐标、1个 Float32 ULP；`alpha=.5`，接受位移为0，`accepted=false` | `stalled=true`，拒绝 formal step |
| 接触反力把下落恢复到支撑原位 | 整步净位置为0，错误地拒绝合法接触静止 | 两个 guard 均 `accepted=true`，各接受位移约 `1.73204e-5 m` | `stalled=false`；净零位置仅作诊断 |

当前源码行：

- `run_native.mjs:65,70`：用 `phaseStalled ||= !result.accepted` 记住任一阶段拒绝，后续合法移动不能覆盖。
- `run_native.mjs:91`：`stalled` 只由阶段拒绝决定；`netPositionUnchanged` 不决定时钟验收。
- `run_native.mjs:97`：fresh-resume 分支在写出下一状态前拒绝 stalled。
- `run_native.mjs:108`：准备过程可以继续尝试；它不是已接受的正式物理时间。
- `run_native.mjs:117–125`：准备状态必须通过独立几何 gate，诊断用失败回放另有显式开关。
- `run_native.mjs:132,135`：正式帧在写入 `frames` 前拒绝 stalled。
- `run_native.mjs:138–139`：同实例 continuation 的两条分支也分别检查 stalled。
- `self_step_guard.mjs:138–147`：模块原契约已明确零存储进度不是可接受的非零物理步。

阶段边界是 native 整步、每轮 body/surface/self 组合、末尾 body 组合。它不是每一次 native 内部约束更新的连续碰撞证明。guard 的 `safe` 每次调用由保存位置创建，接受后更新；已有 MeshContact 的查询工厂按批次创建，guard 的 BVH 只复用拓扑并按实际 Float32 试验重算界限。没有发现新的 guard 跨物理步隐藏状态。

同实例 `run_native.mjs:140` 目前只比较位置；不能用这一行代替完整 fresh-resume 证明。`verify_resume.py:37–38` 才对新进程下一帧的位置、previous、张量场、接触标记和两项时钟逐项精确比较。run37 的真实新进程结果仍须独立完成，不由本策略控制测试替代。

本复查没有发现修复后仍存在的可复现验收控制流硬错误。`counterexamples.json` 的 PASS 仅说明上述当前策略反例通过；不能据此将整衣穿入、自交、材料标定或真人 fit 升级为 PASS。
