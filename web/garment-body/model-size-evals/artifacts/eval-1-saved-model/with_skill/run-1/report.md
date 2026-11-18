# 保存人体模型的12项实际测量

已实际执行技能附带导出器，交付 [主要JSON](measurements.model.json)、[主要CSV](measurements.model.csv) 与 [目标差值表](target-comparison.csv)。数值直接取自给定 neutral.obj；dimensions 仅作目标对照，measuredNeutral 缓存不作来源。未重新拟合、修改输入或生成图片。

|尺寸|网格实测 cm|控制目标 cm|实测−目标 cm|
|---|---:|---:|---:|
|站立身高 (`height`)|169.99997907|170.000|-0.0000209300|
|胸部带尺围度 (`bust`)|90.00003112|90.000|+0.0000311152|
|腰部带尺围度 (`waist`)|72.00000127|72.000|+0.0000012719|
|臀部带尺围度 (`hips`)|96.00004044|96.000|+0.0000404407|
|双肩峰标志点直线距 (`shoulders`)|36.99999958|37.000|-0.0000004240|
|上臂带尺围度 (`upperArm`)|27.00000233|27.000|+0.0000023309|
|大腿带尺围度 (`thigh`)|54.00000799|54.000|+0.0000079940|
|颈部带尺围度 (`neck`)|32.00001191|32.000|+0.0000119079|
|上臂表面标志点直线距 (`upperArmLength`)|29.00000082|29.000|+0.0000008246|
|前臂表面标志点直线距 (`forearmLength`)|23.00000203|23.000|+0.0000020304|
|大腿表面标志点直线距 (`thighLength`)|40.00003206|40.000|+0.0000320574|
|小腿带尺围度 (`calf`)|36.00000082|36.000|+0.0000008183|

站立身高为 neutral 表面的 Y 向极差。7项围度为资源声明的闭合表面带尺折线长度，并非平面截面周长；4项肩/肢体长度为资源指定两个表面标志点的欧氏直线距离，并非骨骼段长。JSON逐项保留完整原始顶点编号、compact网格索引、实际路径点坐标、方法、定义和单位。

对应关系已核对：资产SHA与状态asset字段相等，版本makehuman-cm-rig-v1，OBJ为cm、X左右/Y向上/Z前后。neutral含13,380顶点、26,756三角面，compact编号映射及朝向拓扑与资源一致；仅重放保存的morphWeights所得中性表面与OBJ最大误差 5.02199100036e-09 cm（阈值0.002 cm）。额外从同一资源/保存权重及163个关节角独立执行FK/LBS，posed拓扑相同，最大顶点误差 5.01390543821e-09 cm。因此本次可接受neutral为所给状态对应测量源。没有调用目标校准/拟合求解器。

主要JSON的 `posed_geometry_checked: false` 是附带导出器自身的边界：其仅绑定posed指纹。独立姿态复核结果另见 [geometry-verification.json](geometry-verification.json)，其中包含neutral/posed对应误差、软件版本、前后输入指纹及公开通用runtime源码指纹。将内存副本的全部measuredNeutral改为−12345后，重算结果逐项完全相同，实证未消费缓存主值。

来源指纹（SHA-256）：

- state: `d1eadea6343a897e5c6bbf838f1970c6086eece37f9786336dce2f2e3be40a68`
- human.json: `a75b6a2d59b2fa60ea29393e380182174627ba66d0993c649c8c571a6ccecda6`
- neutral.obj: `bafc6090e5fff755bcd797161e70fb83592bca29efd1fe585bbbb79e9d696755`
- posed.obj: `b139c4f4e09ecbf3267dce1bd0cc0cb408b1346852ca164ebefc32a47a03b46f`

原始四份输入的前后SHA均相同。实测与目标的最大绝对差为 4.04407064707e-05 cm；这是数值模型残差，不是真人准确度或统计置信区间。模型形体参数来源在本输入中只能记为prior_or_fitted_parameter，不能反推照片真人尺寸。仅验证几何对应和数值测量，未验证医学解剖准确性、真人照片、碰撞或物理试衣。

复现：在仓库根目录运行 `bash work/model-size-skill-evals-20261118/iteration-1/eval-1-saved-model/with_skill/run-1/outputs/reproduce.sh`。完整命令/读取边界见 [TRACE.md](TRACE.md)，执行代码为 [export_body_measurements.py](export_body_measurements.py)（技能脚本原样副本）与 [verify_saved_geometry.py](verify_saved_geometry.py)。tokens及耗时无可靠记录，均为null；无自评分。
