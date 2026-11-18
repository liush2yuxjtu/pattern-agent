# Measurement-branch benchmark

| Configuration | Assertion pass rate mean ± SD across cases |
| --- | --- |
| with_skill | 1.0000 ± 0.0000 |
| old_skill | 1.0000 ± 0.0000 |

- Three measurement-only cases × updated/frozen-old skill, six actual independent executions. Same prompt and inputs within each pair; N=1 per case/configuration.
- Saved-model and residual-cache require 12 actual mesh measurements. Consistency-check requires rejection of a mesh that does not correspond to saved neutral morph geometry; correct rejection is not successful model matching.
- Residual-cache waist target 108 cm differs from actual mesh tape 99.0830995146 cm. Cached measuredNeutral claims are never treated as measured geometry.
- Native Claude routing BLOCKED. Image Gen NOT_REQUESTED; no new Image Gen call. Person accuracy, fitting, garment generation and cloth physics are outside this branch.
- Time and token telemetry are unavailable (null). Official raw aggregation fallback zeros are preserved for provenance but never interpreted as observations.
- Standard deviation is across heterogeneous cases, not repeated-run reliability; these paired N=1 runs establish no statistical advantage.
- 本轮比较是 old_skill 与 with_skill（新版技能），不是 with-skill 与无技能基线；六次执行使用同一用户 prompt，每个 case/arm 仅一次。
- saved-model 两组均从实际 neutral.obj 计算 12 项值并以保存 morphWeights、资源与实际拓扑核验对应；独立 grader 得到最大顶点误差 5.021991000355831e-09 cm。仅看接近目标的此案例不足以区分复制目标与真实测量。
- residual-cache 给出可判别的反例：缓存 12 项为 1000 cm，腰围目标 108 cm，独立实际 OBJ 测量为 99.08309951462296 cm，真实 residual 为 -8.916900485377042 cm；两组 JSON/CSV 均保留真实测量和残差。
- 旧 residual-cache 执行不是只复述旧 helper：measure.py 独立解析 OBJ、逐稀疏行累积保存权重、检查全网格和拓扑、从 OBJ 测量。旧 inspector 因 False maximumTargetErrorCm 退出 2，但执行者未把该状态缓存错误当作几何无法测量，仍完成了受独立 grader 支持的交付。
- consistency-check 中资源指纹与拓扑匹配仍不足以证明 neutral 对应；独立 grader 重建显示最大误差 46.062761717058144 cm、RMS 20.00298278720461 cm，0.002 cm 阈值下 9033/13380 点超差。两组正式 JSON/CSV 都明确拒绝并给出 12 个 null。
- 旧 consistency-check 在 1e-5 cm 阈值报告 9038 点超差，新版及 grader 在 0.002 cm 阈值报告 9033 点；阈值不同，最大误差及 RMS 一致。该成功是正确拒绝不匹配输入，不代表 body/pose 匹配或照片动作验收成功。
- 新版 consistency-check TRACE 的 independently parsed 与报告的独立重算受到实现限制：reproduce.py 实际 import bundled exporter，并调用 m.parse_obj、m.reconstruct_neutral、m.triangle_identity 及其容差。它不依赖缓存/目标值，但不构成独立于 exporter 实现的第二条验证。
- 另行实施的 grader 使用自己的 OBJ parser、compact 映射、逐稀疏行标量重建与实际路径测量，没有 import exporter/runtime；该实现独立的数值核验支持新版 case3 的正确拒绝。实现独立性 claim 限制已单列，核心任务语义评分维持原样。
- 新版 saved-model 额外手写 FK/LBS 姿态回放并记录 posed 最大误差 5.01390543821e-09 cm；其中 OBJ parser 与测量仍引用 exporter。旧版只保留 posed 输入指纹且没有声称完成该校验；此额外姿态检查不是三案例既定任务成功的区分项。
- 两组共同通过的执行证据、12 项 JSON/CSV 一致、单位、定义、源指纹、输入保留及真人准确性限制是有用的交付基础，但本轮没有呈现 old/new 任务成功差异。basis=mesh_parameter 与 mesh_measurement 的字段命名差异没有被当作数值语义失败。
- grade-evidence/fault-controls.json 中将腰围主值改成 108、改成 1000、给不兼容实际几何附上成功导出的三种 scratch 错误控制都被真实 validator 判 FAIL；原执行产物未改动。
- 六份 grading 的 timing 和 execution_metrics 均为 null；执行者没有提供完整 token/time telemetry，不能从脚本运行时间、文件时间或字符数推算执行成本或宣布新版省时。
- grade-evidence/source-integrity.json 记录所有原始 outputs、inputs、两份冻结 skill snapshot 在 grader 前后逐文件 SHA 不变；执行后 eval_metadata 加 assertions 造成的哈希变化不属于模型输入变更。
- 本轮只覆盖已保存模型尺寸分支；新 ImageGen、原图重新拟合与真人尺寸准确性未运行，native Claude 触发验证受阻。三对 n=1、固定资源/拓扑及共同满分结果不能证明新版更准确、更可靠或改善上述未测分支。
