---
name: garmentcode-preview
description: Generate and preview 3D garment meshes from GarmentCodeData or GarmentCode sewing-pattern JSON. Use when users provide a dataset sample folder or *_specification.json and want meshing, cloth draping, OBJ/GLB export, wireframe inspection, or a rotatable 3D garment preview, including requests in Chinese such as 纸样生成网格、三维预览、布料仿真. Distinguish an initial sewn mesh, a newly simulated drape, and an existing dataset simulation.
compatibility: Python 3.11, GarmentCode source checkout, NumPy 1.x, CGAL, libigl, trimesh; the GarmentCode-specific Warp fork and a C++ compiler for simulation. Preview uses a WebGL browser and works offline.
---

# GarmentCode 纸样 → 网格 → 三维预览

将用户提供的 GarmentCodeData 纸样变成真实网格，并交付可旋转的预览。默认沿用用户的语言。复用官方 `BoxMesh` 和 `Cloth`，避免用猜测的衣服几何替代原纸样。

## 1. 确定输入与目标

- 接受 `*_specification.json` 或包含它的单个样本目录。目录有多个纸样时，列出候选并选择用户指定的文件；脚本会拒绝不明确的目录。
- 如果用户没有提供样本，使用 `assets/example-shirt_specification.json` 演示。明确它来自官方仓库的示例，**不是下载的数据集条目**。
- 阅读 [输入与输出](references/formats.md)。先运行 `inspect` 验证纸样、缝合索引、尺寸单位和人体配套信息。
- 仅有设计参数 YAML 时，先用官方服装程序生成纸样。图片、PDF、DXF 不能直接作为该脚本的输入。
- 随机人体样本需要对应人体网格与测量文件；不要静默换成平均人体。数据集身体模型通常以米为单位，纸样内部以厘米处理。

```bash
python scripts/garment_preview.py inspect --pattern /data/sample
python scripts/garment_preview.py doctor --repo /path/to/GarmentCode
```

## 2. 准备环境

先读 [安装与复用](references/setup.md)。使用独立虚拟环境，不修改用户现有的 `system.json`，不把普通 `warp-lang` 当成该项目的修改版求解器。

先运行网格模式以验证纸样。若用户需要下垂效果，再运行物理模式。网格生成和仿真允许耗时；继续检查日志并向用户报告有意义的进展。

```bash
python scripts/garment_preview.py build \
  --pattern /data/sample --repo /path/to/GarmentCode \
  --mode mesh --out /output/sample-mesh

python scripts/garment_preview.py build \
  --pattern /data/sample --repo /path/to/GarmentCode \
  --mode simulate --out /output/sample-drape
```

随机人体示例：

```bash
python scripts/garment_preview.py build \
  --pattern /data/random_body/rand_ABC \
  --repo /path/to/GarmentCode --mode simulate \
  --body-mesh /data/bodies/meshes/ABC.obj \
  --body-measurements /data/random_body/rand_ABC/body_measurements.yaml \
  --out /output/rand-ABC
```

## 3. 选择正确的生成路径

- `--mode mesh`：读取曲线、匹配缝边采样数量、三角剖分、三维摆放、合并缝合顶点。输出标记为“初始缝合网格，未物理仿真”。
- `--mode simulate`：先生成新网格，再调用官方 `Cloth` 和 `sim_frame_sequence`，检查静止状态与穿透统计。输出明确区分“通过检查”与“未通过检查的仿真结果”。
- `--mode existing --existing-mesh sample_sim.ply`：只预览已有数据集网格。不要说这是本次生成或仿真的结果。读取时使用 `process=False`；PLY 的 UV 接缝可能改变导入后的顶点数量，分割标签不能盲目按新顶点索引匹配。
- 默认 `--resolution 1.0` 约为厘米级网格边长。更大的值更粗、更快；这是新一轮重网格化，不保证与数据集原顶点编号相同。
- 仿真默认读官方 GUI 参数；复现某个数据批次时，通过 `--sim-config` 提供其原始配置，并同时保留对应人体和材质。不要把默认预览视为原数据集的精确复现。

## 4. 检查并展示

检查输出 `manifest.json` 中的输入哈希、来源、人体、模式、网格数量、边界范围和仿真状态。GLB 中位置以米为单位；原始仿真 OBJ 保持上游厘米约定。

打开 `preview.html`。它内嵌几何，无 CDN 或 API 依赖，也可直接用文件打开。验证：模型可见、拖动可以旋转、滚轮可以缩放、线框开关确实显示三角网格、人体开关工作、初始／仿真切换与标注一致。有浏览器工具时实际打开检查；否则不要声称已经验证页面。

需要本地 HTTP 时使用高位端口，并遵守宿主环境的端口规则：

```bash
python -m http.server 8765 --directory /output/sample-drape
```

将主要结果以内嵌预览或浏览器预览展示给用户，附 GLB、可下载技能包和交付包。`preview-fragment.html` 适合支持可视化片段的聊天宿主。

## 5. 如实报告结果

最后简述：使用哪份纸样、是否本次重新生成网格、是否真正仿真、仿真是否通过检查、可打开的预览和模型。网格模式不需要 Warp；物理路径失败时保留已完成的初始预览，并报告明确失败原因，不能将其描述为自然下垂结果。

测试场景在 [测试用例](references/test-cases.json)（开发源码另存于 `evals/evals.json`）；维护时遵循 Anthropic skill-creator 的“编写 → 真实输入测试 → 人工预览检查 → 修订”流程。来源及许可证见 [来源](references/sources.md)。
