# 已保存人体模型的实际尺寸交付

12 项主数值均直接取自提供的 `neutral.obj` 顶点，单位 cm。控制目标仅作对照，未重新拟合、归一化或更改形体、姿态、原始文件。未生成图片。

## 文件对应关系

资源 SHA-256 与状态 `asset` 精确一致；版本 `makehuman-cm-rig-v1`，资源/状态声明 cm，Y 轴向上。以保存的 morphWeights 从资源重建 neutral，仅按通用运行时定义减去最低表面 Y。将资源原顶点经 `bodyVertexIds` 映射到 OBJ 紧凑顶点后，13,380 顶点全部对应，26,756 三角形索引及顺序完全一致。最大对应顶点距离 5.02199100036e-09 cm，小于事先在复现代码中固定的 1e-7 cm 容差。因此当前状态、匹配资源与实际 neutral OBJ 的对应关系可核实；尺寸导出具备对应的几何来源。

bundled `inspect_human_state.py` 另行执行并重建 neutral，输出见 `state-check.json`；其缓存比对只是辅助核验，本次主数值没有读取缓存作为测量值。全 163 个骨骼的姿态表与资源完整匹配；posed.obj 仅哈希保存，未验证其蒙皮，也未用于中性尺寸。

## 网格实测与目标

差值 = OBJ 实测 − 控制目标；以下保留 9 位小数便于审计，不代表真实人体测量精度。

| 项目 | OBJ 实测 cm | 控制目标 cm | 差值 cm | 定义类别 |
| --- | ---: | ---: | ---: | --- |
| height | 169.999979070 | 170 | -0.000020930 | standing_height |
| bust | 90.000031115 | 90 | +0.000031115 | surface_tape_path |
| waist | 72.000001272 | 72 | +0.000001272 | surface_tape_path |
| hips | 96.000040441 | 96 | +0.000040441 | surface_tape_path |
| shoulders | 36.999999576 | 37 | -0.000000424 | landmark_distance |
| upperArm | 27.000002331 | 27 | +0.000002331 | surface_tape_path |
| thigh | 54.000007994 | 54 | +0.000007994 | surface_tape_path |
| neck | 32.000011908 | 32 | +0.000011908 | surface_tape_path |
| upperArmLength | 29.000000825 | 29 | +0.000000825 | landmark_distance |
| forearmLength | 23.000002030 | 23 | +0.000002030 | landmark_distance |
| thighLength | 40.000032057 | 40 | +0.000032057 | landmark_distance |
| calf | 36.000000818 | 36 | +0.000000818 | surface_tape_path |

完整精度、单位、定义、标志顶点、1-based OBJ 顶点路径、输入指纹、缓存差值见 `measurements.json` / `measurements.csv`。`target-comparison.json` 单列目标对照。最大绝对目标差 4.04407064707e-05 cm，原样保留，不把目标写成已实现数值。

## 定义与限制

身高为 neutral 全表面 Y 最大值减最小值。七个围度采用资源指定的闭合表面带尺路径，各相邻顶点欧氏距离求和，并非水平截面周长。肩宽为资源双侧肩峰标志点直线距离；上臂、前臂、大腿长度为相应资源表面标志点直线距离，并非骨头段长。完整标志点在 JSON/CSV 中提供；定义来源为 old skill 的 Human Studio 合同与所给资源的 controls.path，数值来源为提供的 OBJ。

basis 为 `mesh_parameter`，mesh_checked 为 true。这些是通用人体先验模型的几何尺寸，不能升级为照片人物实测或真人准确性认证。不声称验证照片拟合、关节碰撞、组织或服装物理效果。输入 state/neutral/posed/asset 在执行前后 SHA-256 一致。

## 复现

在仓库根目录执行：

```bash
bash work/model-size-skill-evals-20261118/iteration-1/eval-1-saved-model/old_skill/run-1/outputs/reproduce.sh
```

仅依赖 Python 标准库。实际执行结果见 `execution.log`，测量实现为 `measure_saved_model.py`，来源/输入 SHA、Python 环境和未改变输入证明见 `provenance.json`。执行过程与边界见 `TRACE.md`。tokens 与 time_seconds 未取得可靠统计，均为 null；未进行评测自评分。
