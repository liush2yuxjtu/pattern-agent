# 已拒绝成功尺寸导出

实际检查发现：资源 SHA-256 与状态 asset 字段一致，OBJ 的 13,380 个顶点和 26,756 个三角面的索引拓扑能精确映射到对应资源；但标为 `neutral.obj` 的实际顶点不等于按状态 morphWeights 重建、以脚底归零的中性网格。

逐顶点距离 RMS 为 **20.0029827872 cm**，最大为 **46.0627617171 cm**，13,380 个顶点中 **9,038** 个超过 0.00001 cm 的导出舍入容差。输入 OBJ 的 X/Y/Z 跨度为 47.94747513 / 169.99250581 / 29.91206396 cm；重建 neutral 的跨度为 107.09489749 / 169.99997907 / 40.91663305 cm。该差异不能解释成文件数字舍入。

状态包含非零上臂、前臂和颈部旋转，因此 OBJ 可能是 posed 输出；本轮未运行完整 FK/LBS 来证明其与该 pose 完全相符，不作此断言。即便文件是正确 posed 输出，也不能直接用其包围盒高度和变形后的带尺路径替代约定的 neutral 尺寸。

`measurements.json` 和 `measurements.csv` 保留全部 12 项、cm 单位、定义、控制目标及三份输入指纹；**尺寸值和尺寸减目标的差值均为空/null，状态为 refused_neutral_export**。这不是成功的 12 项尺寸交付。拒绝原因是所给实际网格未通过中性状态一致性核对。

`consistency-audit.json` 单列实际 OBJ 路径诊断值、重建 neutral 的几何测量、缓存差值以及逐顶点核对。它们用于复核拒绝原因，不能当作从所给 neutral.obj 成功导出的正式尺寸。独立重建的尺寸与缓存差异最大 1.42e-14 cm，但缓存一致并不能证明 OBJ 一致。附带旧技能助手的 `state-reconstruction.json` 只验证 state+asset，未读取 OBJ，其 PASS 字样不能用于证明本次网格对应关系。

未改动输入、形体、姿态或控制目标；未重新拟合，未生成图片。使用 Python 标准库与 NumPy；未读取测量 UI 或评分器。输入/脚本/runtime 哈希、环境版本与完整定义索引保存在 audit JSON。token 与耗时未知，记录为 null。

复现：从仓库根目录运行 `bash work/model-size-skill-evals-20261118/iteration-1/eval-3-consistency-check/old_skill/run-1/outputs/reproduce.sh`。

建议提供真正从相同 state/asset 重建并导出的 neutral OBJ，再重新核对和测量；原文件保持不变。
