# TRACE

任务：实际完成指定eval_metadata.json中的saved-model请求；不commit。

读取边界：祖先/仓库AGENTS.md；本案例eval_metadata.json；skill-new/SKILL.md及其model-measurements、tools-and-evidence、human-studio、geometry-evidence引用；skill-new/scripts/export_body_measurements.py；指定inputs/saved-model三份文件及inputs/human.json；公开通用web/human-studio/body-engine.js和tools/human_fit/pose_guided/runtime.py。未读取canonical、skill-old、其他run输出、private grader、历史测量报告或测量UI app.js。没有调用工具/skill_evals评分器。

1. 实际运行技能附带命令（repository root）：

```sh
python work/model-size-skill-evals-20261118/skill-new/scripts/export_body_measurements.py --state work/model-size-skill-evals-20261118/inputs/saved-model/final-state.json --asset-json work/model-size-skill-evals-20261118/inputs/human.json --neutral-mesh work/model-size-skill-evals-20261118/inputs/saved-model/neutral.obj --posed-mesh work/model-size-skill-evals-20261118/inputs/saved-model/posed.obj --out work/model-size-skill-evals-20261118/iteration-1/eval-1-saved-model/with_skill/run-1/outputs/measurements.model.json --csv work/model-size-skill-evals-20261118/iteration-1/eval-1-saved-model/with_skill/run-1/outputs/measurements.model.csv
```

实际exit 0，输出12项mesh_measurement主值。复制该脚本原样到本输出目录，便于复现。

2. 编写verify_saved_geometry.py并实际执行。只消费保存权重，不调用Runtime.shape/evaluate（其中含拟合入口），用NumPy直接实现公开通用runtime的frames、局部XYZ旋转、FK和四权重归一化LBS，按同一表面最低点落地。对照原posed.obj全部顶点/面。另在内存副本中污染缓存证明导出值独立于缓存。记录四份输入执行前后sha，断言不变。

3. 再次实际运行完整可复现入口：

```sh
bash work/model-size-skill-evals-20261118/iteration-1/eval-1-saved-model/with_skill/run-1/outputs/reproduce.sh
```

实际exit 0。neutral最大误差 5.02199100036e-09 cm；posed最大误差 5.01390543821e-09 cm；缓存污染后测量一致；原输入不变。没有重新拟合，没有更改或重写state/neutral/posed/human.json，没有生成图片。

产物：主要JSON/CSV、单独target-comparison.csv、geometry-verification.json、原样导出器、独立复核代码、reproduce.sh、report.md、本TRACE、artifact-sha256.json。JSON保留全精度，报告仅显示时四舍五入。完整测量定义/路径/指纹位于主要JSON。

AGENTS中的commit前/verify要求无此处提交动作可适用；本任务遵从明确不得commit约束，未commit、push或运行CI。未进行自评分或读取privateoracle。tokens: null；elapsed_time_seconds: null。
