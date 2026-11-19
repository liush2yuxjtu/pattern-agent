---
name: clo-rust-boat-fit-review
description: 从 Boat 的 clo-rust 私人快照启动 Linux，用 CLO_RUST 核查裁片和缝合，复算已有多姿势服装网格的应变和褶皱折角，并交付直接显示线稿和图像的离线 HTML 报告。
---

# CLO_RUST 多姿势试穿评估

用已知来源的裁片、缝合数据及姿势网格做 Linux 原生验收。从本地保留工程原件，默认交付单文件 HTML、逐片 JSON 和 VTK 调试数据。在线稿与服装网格之间记录来源和视角。运行前确定网格的姿势、同版裁片、场景坐标轴和单位。

- FreeSewing 纸样用项目中版本固定的出样适配器，随后用 Rust 的 `draft-import` 和 `audit` 写入并重开工程。以已有缝合定义运行 `audit` 和 `constraints`，有同版连通参照时运行 `connectivity --strict`。
- 只上传任务所需的明示文件清单。服装 GLB 用 `scripts/prepare_meshes.py` 提取坐标、平面坐标和索引，并核对跨姿势拓扑。现有实现使用毫米位置和公制纸样 UV、Y 向上、+Z 向前；原始数据须有单位和坐标轴依据。人体、贴图、CLO 程序和源工程留在本机。
- 使用 `boat new --personal --no-env --from clo-rust` 启动私人 Linux 沙箱。记录快照、沙箱和版本。先运行快照内的 `verify-boat.sh`，再在沙箱用 `scripts/run_review.py` 跑具体案例。单独运行验证时，从终端观察结果和退出码。
- `python scripts/run_review.py <CLO_RUST目录> <输入目录> <输出目录>` 使用输入中的 `manifest.json`。可选 `seams/` 包含 `edges.json`、`edge-map.json`、`seams.json` 和 `connectivity.json`；可选 `line-art.png` 为正面设计图。Carlton 案例可指定 `--carlton`。如果快照尚未带 Carlton，先传入 `vendor/draft-carlton.mjs` 和相应的两个 npm 清单文件，在沙箱执行 `npm ci --prefix vendor --ignore-scripts`。渲染用 Python 的 NumPy 和 Matplotlib，可安装在沙箱虚拟环境中。几何计算用 Rust。
- 有同姿势的人台 GLB 时，可在本地使用新版的 `avatar-import 人台GLB 网格名 单位 [姿势OBJ]` 导入蒙皮，再用 `collision-avatar 人台GLB 网格名 单位 服装GLB 服装网格名 单位 [碰撞VTK]` 核查人衣静态相交。分别确认人体与服装的单位和共同坐标原点。相交结果保留对应姿势和来源。
- 逐姿势核对写入的 JSON 与 VTK、裁片数和面数，存在同网格独立数值时比对。离线浏览器打开最终 HTML 检查图像、色标和窄屏。取回结果后停止自己创建的沙箱。
- 已有姿势 GLB 的外观和数值反映其来源求解器的状态。报告注明网格来源。把主应变、折角和材料应力分别标注。当前快照的独立动态试穿、合体分类、接触压力和材料应力处于未生成状态。静态相交检查只在有匹配的授权人衣网格时使用。

运行前看 [Boat 批处理与验证](references/boat-run.md)，其中包含文件清单、
依赖、上传边界和批量回执核对。
