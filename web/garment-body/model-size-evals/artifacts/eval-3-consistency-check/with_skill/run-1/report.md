# 已拒绝成功尺寸导出

实际执行了技能的 `export_body_measurements.py`。资源 SHA-256 与状态声明匹配，实际 OBJ 有 13,380 个顶点、26,756 个三角形，完整拓扑与绕序也匹配；但这不足以证明它是所保存状态对应的中性网格。

在不调用尺寸求解器、不改变任何输入的前提下，用保存的 12 个 morphWeights 和对应 human.json 重建中性表面，按资源的 bodyVertexIds 进行 compact 索引映射，逐顶点与实际 OBJ 比较。最大位置误差为 **46.062761717058144 cm**，RMS 为 **20.00298278720461 cm**；**9,033 / 13,380** 顶点超出技能的 **0.002 cm** 容差。最大差异位于 compact 顶点 8787，实际坐标与重建坐标保存在 consistency-evidence.json。

因此，标为 neutral.obj 的文件不能通过与所给状态/资源的中性几何对应校验。文件名、缓存 measuredNeutral 和控制目标都不能解除这一不一致。状态含 163 个关节，其中 5 个非零；本次没有执行蒙皮姿态重建，因此不进一步声称输入一定是 posed 网格，也不对错误原因作未经计算的断言。

`measurements.refused.json` 和 `measurements.refused.csv` 各列出全部 12 项及其定义，value_cm 与差值均为空；控制目标仅放在单独的 target 字段中。这些是明确的拒绝结果，**不是成功测量导出**。没有将实际 OBJ 的站姿不明包围盒当作站立身高，没有用重建后另一份网格的测量代替所给 OBJ。

复核入口（从任意目录运行）：

```bash
python /workspace/work/pattern-agent/work/model-size-skill-evals-20261118/iteration-1/eval-3-consistency-check/with_skill/run-1/outputs/reproduce.py
```

该入口执行原始技能导出命令并记录原始 stderr 与退出码 1，再独立重算顶点误差、拓扑和指纹；所有产物写入当前 outputs。TRACE.json 保存命令与执行轨迹，source-hashes.json 保存输入、技能、引用合同和复现代码的 SHA-256。未使用缓存自报测量，未重新拟合、修改 shape/pose、生成服装图或运行 ImageGen；输入哈希复核保持一致。tokens、耗时与自评分没有可靠计量，均为 null。需要提供与保存状态真正对应的 neutral OBJ 后才可导出成功尺寸。

最终复核：JSON/CSV 的 12 项拒绝值一致，全部实际模型输入与技能代码指纹未变，没有 success 文件。任务元数据 eval_metadata.json 在执行后被并行流程更新，执行时与最终哈希差异保留在 TRACE.json；该元数据不是几何测量输入，不影响上述对应校验。
