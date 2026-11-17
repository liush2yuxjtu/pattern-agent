# 工具与证据实现

辅助脚本负责可重复的数值核验，不包含图像生成后端或完整人体拟合器。
由执行技能的 agent 根据当前工具创建网格、相机、分割和优化流程；不要声称此包自带 SMPL、
Depth Anything 权重、物理试衣引擎或云图像生成服务。

## 环境

Python 3.10+。在隔离环境按需要安装 numpy、opencv-python-headless、vtk；
Pillow/Matplotlib/SciPy 可用于图像检查、快照与优化。先检查已有环境，避免无关安装。
不需要环境变量中的图像模型密钥，除非选择的生成服务本身要求；不要记录明文密钥。

## 叠加与度量

参考掩膜与投影掩膜必须已处于同一像素坐标系。白色=前景，黑色=背景。

```bash
python scripts/verify_masks.py --reference reference-mask.png \
  --projected projected-mask.png --photo original.jpg --out evidence/front
```

脚本拒绝空掩膜或尺寸不符，不会悄悄缩放让分数变好。
生成 metrics.json 和 overlay.png。它不会检查掩膜是否正确分出人体，必须展示并检查。
IoU 包括所有前景，轮廓误差使用外轮廓；若需要衣服空隙、内部孔洞或局部躯干指标，
另定义评价区域并明确报告。不同协议的分数不能混作同一个序列比较。

## 真实网格截面

sections.json 示例（Human Studio 的 Y-up 坐标）；以下数字只是调用格式示意，按当前人体标志点改写：

```json
[
  {"name":"chest_section","origin":[0,128,0],"normal":[0,1,0],"seed":[0,128,0]}
]
```

```bash
python scripts/measure_mesh.py --mesh model/body.obj --sections sections.json \
  --unit cm --out evidence/mesh-measurements.json
```

通过 seed 选取最近的连通截面。仔细确认没有选到手臂或合并胸臂截面；
闭环检查不等于解剖位置正确。输出的 world_axis_spans 是世界坐标轴跨度，
不是任意截面平面内的长短轴；对斜切四肢不要误标为胸宽/厚度。
围度单位跟网格一致。归一化网格不能仅改 --unit 就变成厘米。

## 文件与版本

记录原图、网格的 SHA-256；测量 JSON 的 mesh_sha256 应等于最终网格哈希。
查看器可加载简化网格，但保存简化过程、版本和与源网格的差异。
初始/最终指标应复用参考掩膜与相机，并保留早期指标。
在 viewer 中更改尺寸后，旧叠加分数不再表示新人体；明确它属于哪个版本。

## 数组接口的输入边界

直接调用 compare/overlay 时，掩膜数组只能为布尔值或数值 0/1；概率、NaN/Inf 和 0/255 数组应先显式处理。
CLI 的 PNG 读取仍按 >127 二值化。叠加照片须为有限的 H×W×3 BGR 数组，通道范围 0..255。
网格截面的 origin、normal、seed 须为有限长度3向量；零法线会在调用 VTK 前被拒绝。

## Human Studio 接口与单位

优先阅读 [Human Studio 工作流](human-studio.md)，其中包含 12 个尺寸键、姿态 API、导出合同、相机限制和完整核验入口。
`scripts/inspect_human_state.py` 仅用 Python 标准库检查导出状态；有对应资源时重建中性网格带尺尺寸。
没有资源时它只能检查结构，不会把导出文件里自报的数字当作独立网格证据。
OBJ 输入本身必须已经以 cm 表示；GLB 的米坐标应由正确的导入/转换流程处理，不能只给 `measure_mesh.py` 传 `--unit cm`。
Human Studio 的 surface tape path 尺寸和 VTK 截面周长采用不同定义；分开记录 method、标志点与姿态。
