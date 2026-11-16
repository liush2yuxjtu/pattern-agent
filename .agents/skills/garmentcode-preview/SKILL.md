---
name: garmentcode-preview
description: Run, explain, or troubleshoot GarmentCode-based garment meshing and 3D cloth draping. Use for GarmentCodeData samples, sewing-pattern JSON, existing garment OBJ/PLY/GLB previews, CPU/GPU XPBD setup, early-static failures, and simulation quality reports; also when the user asks how to implement this pipeline or wants a draped-clothing demo without supplying a sample. Covers 纸样生成网格、布料物理仿真、三维试穿预览. Do not use for generic 3D models or physics lessons, Blender-only projects, 2D/CAD-only edits, dataset statistics, paper translation, or deployment-only tasks.
compatibility: Python 3.11, GarmentCode source checkout, NumPy 1.x, CGAL, libigl, trimesh; the GarmentCode-specific Warp fork and a C++ compiler for simulation. Preview uses a WebGL browser and works offline.
---

# GarmentCode 纸样 → 物理仿真 → 三维预览

将 GarmentCodeData 纸样变成真实网格，按需运行布料下垂，交付可旋转的离线预览。默认沿用用户的语言。复用官方 `BoxMesh`、`Cloth` 和定制 Warp，保留原纸样几何。网页显示已计算的网格，视角操作不会重新求解物理。

## 1. 确定输入与目标

- 先区分用户需要原理说明、初始网格、真实下垂，还是已有结果的预览。原理与接入请求先读 [实际物理执行路径](references/simulation.md)，提供有来源的调用关系和命令，避免把说明写成已经执行。
- 网格与仿真接受 `*_specification.json` 或包含它的单个样本目录。目录有多个纸样时，列出候选并选择用户指定的文件；脚本会拒绝不明确的目录。
- 需要演示但没有样本时，使用 `assets/example-shirt_specification.json`。明确它来自官方仓库，**不是下载的数据集条目**。已有 OBJ/PLY/GLB 不需要虚构一份原始纸样来预览。
- 阅读 [输入与输出](references/formats.md)。先运行 `inspect` 验证纸样、缝合索引、尺寸单位和人体配套信息。
- 仅有设计参数 YAML 时，先用官方服装程序生成纸样。图片、PDF、DXF 不能直接作为该脚本的输入。
- 随机人体样本需要对应人体网格与测量文件；不要静默换成平均人体。数据集身体模型通常以米为单位，纸样内部以厘米处理。

```bash
python scripts/garment_preview.py inspect --pattern /data/sample
python scripts/garment_preview.py doctor --repo /path/to/GarmentCode
```

## 2. 准备环境

先读 [安装与复用](references/setup.md)。使用独立虚拟环境，不修改用户现有的 `system.json`，不把普通 `warp-lang` 当成该项目的修改版求解器。

根据目标选择模式：下垂请求用 `simulate`，它本身先生成并保存初始网格，无需预先重复运行 `mesh`。只要初始几何时使用 `mesh`。继续检查运行日志，报告有意义的进展；初次 CPU 内核编译可能比后续计算慢。

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
- `--mode simulate`：生成新网格，再调用官方 `Cloth` 和 `sim_frame_sequence`；保留 CPU 顶点快照修复，防止共享视图导致提前静止。仿真执行、稳定性、宽松配置阈值、零穿透计数、独立审计及实体合身分别报告。
- `--mode existing --existing-mesh sample_sim.ply`：只预览已有服装网格，不需要 `--pattern`、`--repo` 或 Warp。读取使用 `process=False`。GLB 默认米，OBJ/PLY 默认厘米；其他单位显式设置 `--existing-scale`。导入的 UV 接缝可能复制顶点，不能盲目映射原分割标签。
- 默认 `--resolution 1.0` 约为厘米级网格边长。更大的值更粗、更快；这是新一轮重网格化，不保证与数据集原顶点编号相同。
- 仿真默认读官方 GUI 参数；复现某个数据批次时，通过 `--sim-config` 提供其原始配置，并同时保留对应人体和材质。不要把默认预览视为原数据集的精确复现。

```bash
python scripts/garment_preview.py build --mode existing \
  --existing-mesh /data/shirt.glb --out /output/shirt-existing
```

## 4. 检查并展示

重新打开输出 `manifest.json` 和 GLB，检查来源、输入哈希、单位、有限坐标、面索引、网格数量及仿真状态。GLB 中位置以米为单位；仿真 OBJ 保持厘米约定。使用新的输出目录，脚本拒绝覆盖已有结果。

打开 `preview.html`。它内嵌几何，无 CDN 或 API 依赖，也可直接用文件打开。验证：模型可见、拖动可以旋转、滚轮可以缩放、线框开关确实显示三角网格、人体开关工作、初始／仿真切换与标注一致。有浏览器工具时实际打开检查；否则不要声称已经验证页面。

需要本地 HTTP 时使用高位端口，并遵守宿主环境的端口规则：

```bash
python -m http.server 8765 --directory /output/sample-drape
```

将主要结果以内嵌或浏览器预览展示，附可打开的 HTML 与 GLB。`preview-fragment.html` 适合支持可视化片段的聊天宿主。聊天内预览不显示时，给出真实可打开的文件或网址；发布仅在用户要求时进行。

## 5. 如实报告结果

最后简述输入、模式、是否本次生成/仿真、预览和模型位置，并从 manifest 分别引用：执行是否完成、是否稳定、相交计数、`release` 各项判定。`simulation.quality_passed` 为兼容旧格式保留，只代表上游配置阈值；即使它为 true，自相交计数大于零时零自相交门槛仍为 FAIL。完整独立审计及实体合身未经执行时维持 NOT_RUN。

退出码 0 只表示请求的计算/导出流程完成，不等于服装合格。仿真异常退出码 2，并保留已生成的诊断结果；达到帧数上限但尚未静止时，也要明确标为未稳定。说明执行失败时，不将初始或部分结果称为成功下垂。参数是研究配置，未标定真实面料，默认人体为静止碰撞体。

测试场景在 [测试用例](references/test-cases.json) 与 `evals/evals.json`，评估方法和限制见 [评估说明](references/evaluation.md)。来源及许可证见 [来源](references/sources.md)。
