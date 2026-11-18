# 从最终人体模型输出实测尺寸

输入的身高/尺码先验用于初始化，`dimensions` 是可调控制目标；它们都不是尺寸导出结果。
结果应由保存的最终裸模几何计算，输入目标只用于对照。即使两者接近，也必须真正重测。

## 实际运行

在 Pattern Agent 项目根目录，使用同一最终版本：

```sh
python .agents/skills/garment-body-six-view/scripts/export_body_measurements.py \
  --state model/final-state.json \
  --asset-json web/human-studio/assets/human.json \
  --neutral-mesh model/neutral.obj --posed-mesh model/posed.obj \
  --out measurements.model.json --csv measurements.model.csv
```

工具读真实 compact OBJ 顶点，将资源的原始顶点编号映射到 compact 表面。12项测量包括：
站立身高、胸/腰/臀/颈/上臂/大腿/小腿带尺围度，肩部/上臂/前臂/大腿标志点直线距离。
保留具体路径编号与定义，不把带尺路径改称截面，不将肢体表面标志点距离称为实际骨头长度。

工具按已保存 morphWeights 独立重建资源网格，仅核对中性 OBJ 是否对应；不调用尺寸求解器
将几何重新拟合到目标。不从 `dimensions` 或 `measuredNeutral` 取实测值。资产/单位/顶点/
拓扑不符、非有限坐标及不对应的姿态网格应拒绝，不能返回伪造的先验表作为回退。

## 输出与来源

- `measured_values_cm`、逐项 `value_cm` 是主要模型实测输出。
- `target_dimensions_cm`、逐项目标和残差仅为控制参数对照。
- `basis: mesh_measurement`、`measurement_source: neutral_mesh` 指明实际数值来源。
- `parameter_basis` 描述形体参数仍来自先验或拟合；它与测量方法独立。
- 保存模型/状态/资源指纹、原始与 compact 顶点映射、定义、单位和几何一致性证据。
- `person_accuracy_verified: false` 表明未据此验证照片真人的真实围度。

JSON 保留实际计算精度；显示可四舍五入为两位小数。模型经M先验校准后测得90cm胸围，
表示这个模型约90cm，不能说原照片的人被独立测得90cm。单张衣物照片的真实尺度/松量仍可能不确定。

## 编辑器与评阅页

Human Studio 输入框是目标，其下持续显示实际中性网格测量。Export measurements、CSV 和
Neutral OBJ 导出同一捕获版本；形体更新未完成时等待，不混合新目标与旧网格。保存动作独立。
实际改厘米后网格和测量响应；只改关节时中性尺寸保持不变。下载后用独立 OBJ 测量重开核验。

官方 eval.html 的 Output 中并列模型实测/控制目标，提供主要实测 JSON/CSV 下载。对历史
执行重测时，将新文件放到 review/ 并标为事后几何复量；不覆盖旧输出、评分、旧技能快照。
这只是测量导出功能修正，不把此前功能分数改说成新技能的照片拟合或六图质量提升。
