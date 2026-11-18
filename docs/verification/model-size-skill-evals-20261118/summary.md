# 六次真实执行的独立评分

| Case | old_skill | with_skill |
| --- | --- | --- |
| saved-model | 7/7 | 7/7 |
| residual-cache | 7/7 | 7/7 |
| consistency-check | 5/5 | 5/5 |

两组均为 19/19；共 38/38。每个 case/arm 只运行一次（n=1）。评分依据冻结的 7/7/5 条用户语义，允许 JSON 字段命名不同，不用 executor 的 PASS 字样或 schema 名称代替数值核验。

独立 grader 使用自己的 OBJ 解析、资源 bodyVertexIds 路径映射及逐稀疏行 morphWeights 重建；没有 import 任何 exporter/runtime 作为 oracle。saved-model 最大几何误差 5.021991000355831e-09 cm；residual-cache 为 7.858154371883555e-06 cm，均通过 0.002 cm 对应阈值。case 1/2 两技能实际 JSON/CSV 的 12 项主值均与独立实测相符（0.01 cm 阈值），单位与真实 residual 完整。

residual-cache 的腰围是 99.08309951462296 cm，目标 108 cm，差值 -8.916900485377042 cm；颈围 42.887834209521614 cm，目标 44 cm。输入缓存的 1000 是 reported cached claim，不是模型实测值。两技能都没有用它污染主值。

consistency-check 实际 OBJ 虽有相同拓扑和匹配资源指纹，但其与保存中性形体的最大顶点误差 46.062761717058144 cm，RMS 20.00298278720461 cm；0.002 cm 阈值下 9033/13380 点超差。两技能明确拒绝，正式 JSON/CSV 均为 12 个 null，诊断/重建值没有冒充成功交付，没有替换 refit。旧执行用更紧的 1e-5 cm 阈值记录 9038 点，两者统计口径不同而非矛盾。

source-integrity.json 独立确认所有原始 outputs、inputs 和两个冻结 skill snapshot 在本次 grader 前后逐文件 SHA 不变；原 input hashes 对上冻结 private-oracle。保存权重、完整 163 骨骼/5 非零姿态及 case 1 的 posed.obj 指纹保留。旧技能没有声称执行完整 posed LBS 校验；新 case 1 有额外 posed 校验，但该额外能力不是本组任务成功的差异。

fault-controls/ 保存独立 scratch 产物，经同一个真实 validator 运行的五项错误控制全部得到 FAIL：将腰围主值改为目标 108、改为缓存 1000，将成功中性导出附于不兼容实际几何并声明 success、删除测量 definition、以及在 scratch 完整拷贝中修改 TRACE 造成固定人工审计 SHA 绑定过期。原产物没有修改。数值结果在 *-numeric.json；人工 TRACE/代码判断在 *-manual.json，互相分开。

## 实际能说明与尚缺的判别项

这三种输入充分排除了仅复制 target/cache、只看文件名/状态重建 PASS、不检查实际 OBJ 的伪完成；本次旧执行均额外写了 bespoke geometry validator，因此两组 task-success 存在共同满分基础。本次不能宣称新版比旧版更准确或更可靠；应另测无需临时补代码的可复用 helper 行为、额外工具调用/代码量、更多独立重复数，以及新输入拓扑/单位/权重/路径边界。

新 case 3 的复现代码实际 import exporter 的 parser/reconstruct 函数，故其“独立 audit”不是实现独立，已在 grading claims 单独标记；本 grader 的实现独立核验仍支持其正确拒绝，不凭此扣除用户语义的成功判据。旧 helper 的 state+asset PASS 不能证明 OBJ 正确，旧执行已明确识别此限制。

六份当前 eval_metadata 的 prompt 相同，实际模型 inputs 未变；执行后 metadata 添加 assertions 导致 SHA 改变，不应误报为模型输入篡改。全流程 photo/ImageGen 为 NOT_RUN；native Claude trigger 为 BLOCKED。缺少完成 telemetry 的 timing/metrics 保留 null，不能推算省时或 token 收益。

复现评分（不会覆盖任何 run outputs）：

```sh
python tools/skill_evals/grade_model_size_skill.py --workspace work/model-size-skill-evals-20261118
```

人工审计已固定为六份 *-manual.json（findings + 全递归 artifact SHA 绑定）。CLI 只读取并验证，绝不自动创建或覆盖结论；审计缺失/过期时所有断言不得 PASS。scope 同时依赖人工语义审读和定义检查。所有 artifact/source inventories 递归记录相对路径并排除 __pycache__ 与 .pyc。冻结实现及最终评分指纹见 freeze.json。
