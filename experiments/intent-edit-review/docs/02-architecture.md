# 项目结构与重建 {#architecture}

## 独立项目目录

本实验的中心目录为 `experiments/intent-edit-review/`，其中 `README.md` 是统一入口。发布目录是 `web/intent-edit-review/`，文档源稿位于项目的 `docs/` 子目录。原始输入、编辑基准、共享转换器和证据按下面的资源关系连接；在线总览从中心README直接生成。

```text
experiments/intent-edit-review/
├── README.md                 项目入口与常用命令
├── DESIGN.md                 视觉布局、范围和必要差异
├── build.py                  生成完整单文件演示
├── build_docs.py             从文档源稿生成在线文档
├── build_hub.py              从中心README生成在线实验总览
├── template.html             演示结构
├── app.js                    案例、文档、差异和下载交互
├── viewer.js                 WebGL及软件三维绘制
├── style.css                 演示样式
├── docs/                     本文档的四份Markdown及HTML模板
├── geometry/                 五套模型、生成器与自检
├── physics/                  独立物理输入、求解、审计与单文件实验台
├── verification/             独立内嵌数据审计及故障测试
├── verify_browser.py          完整演示的真实浏览器验证
└── verify_docs.py             在线文档、目录和演示入口验证

web/intent-edit-review/
├── index.html                可单独保存的演示
├── experiment/index.html     中心README的在线总览
├── docs/index.html           无外部资源的在线文档
└── physics/index.html        含完整规格、二维图和实际记录的物理实验台
```

## 与仓库其他目录的关系

| 目录 | 在本项目中的作用 |
| --- | --- |
| `patterns/fitted-tshirt/` | 原始 DXF 与完整中文输入规格 |
| `experiments/intent-edit-benchmark/` | 四个具体编辑操作、真实输出和补丁重放代码 |
| `experiments/intent-edit-review/geometry/` | 由原型和四个实际输出分别构建的三维模型 |
| `experiments/intent-edit-review/physics/` | 来源核对、实际数值求解、准备门、完整轨迹、逐帧审计、恢复与独立界面 |
| `docs/verification/intent-edit-review-20261118/` | 数据、浏览器、下载和线上验收证据 |
| `docs/verification/intent-physics-20261118/` | 本次物理机制、初始/轨迹几何、界面与历史失败证据入口 |
| `scripts/build_pages.py` | 复制整个 `web/` 并组装现有静态站点 |
| `.agents/skills/verify/` | 本地验证流程和可复跑的操作配方 |

独立项目集中保存自己的代码，但没有复制一套原型或基准编辑器来制造多个版本。重建时从上述明确的仓库路径读取相同源文件。

## 单文件构建过程

`build.py` 读取基准和四个输出的实际 DXF、中文 YAML、规格差异和坐标补丁。它校验规格结构、DXF 实体与规格几何的对应关系，并核对每个模型的来源摘要。

构建器将完整文件编码为 base64，把实际二维图元和 SVG 与对应模型一起写入唯一的 `app-data` JSON。最后把样式、视图绘制代码和交互代码内联到 HTML。

浏览器启动时读取内嵌数据，检查文件长度，在支持的安全上下文中检查 SHA-256，并核对模型与当前 DXF/YAML 的版次。它不通过 `fetch` 拉取模型，也不从 CDN 导入三维库。

## 独立物理项目怎样连接

物理代码和发布路径均位于 `physics/` 子目录，不替换对照演示或静态缝合结果。详细实现见 [物理实验说明](https://github.com/liush2yuxjtu/pattern-agent/blob/main/experiments/intent-edit-review/physics/README.md)。

| 阶段 | 实际职责 |
| --- | --- |
| `prepare_experiment.py` / `verify_source_mesh.py` | 读取实际 DXF/YAML、材料坐标、支持配置、15条缝及真实人体，另行核对来源、CAD/UV和拓扑 |
| `run_native.mjs` | 运行本次冻结并编译的 WASM 核心和接触组件；保存准备状态与独立几何门，失败保留原因 |
| `derive_folds.mjs` / `audit_experiment.py` | 从真实保存坐标派生折角，并独立复算每帧几何、张量、折角和时钟 |
| `verify_resume.py` | 新建进程从保存状态继续，核对实际下一步；与界面的只读 seek 分开 |
| `build_viewer.py` / `recording-codec.mjs` | 校验输入、记录和报告摘要，进行无损记录编码，把实际文件、二维图、脚本和轨迹内嵌到单份 HTML |
| `verify_viewer.py` | 在真实浏览器检查原文/原字节、全部帧、GPU颜色、面片、接缝、导出重开与窄屏；收据绑定本次代码和数据 |

构建器从已验收对照数据读取 `source_package`：完整 `files`、实际 `twoD`、自然语言 `intent` 与 `changes`。文件逐一与仓库原始字节核对，二维来源与物理输入的 DXF/YAML 摘要一致，不能把旧模型换个标签套到新输出。

物理输入另存本次条件副本和实际可执行文件摘要；更改默认参数不会改写历史实验。本轮原型和袖口各61/61帧离散数值验收 PASS，另外三个案例仍为 `BLOCKED：PROFILE_REQUIRED`。正式候选轨迹不能绕过初始几何门；历史失败研究记录也不改判。通过范围限于实际保存状态与估计材料模型，材料耐受及真人合身不在本轮通过范围内。

## 为什么三维没有沿用旧模型

五个 `*.mesh.json` 分别对应基准和四个改版。每个模型保存实际二维边界顶点到局部 UV 的绑定、三角形、三维位置、法向和明确的构造信息。

衣身使用实际轮廓边界的静态映射及内部调和插值。袖片使用来源绑定的纵向参数和截面映射。领条采用明确声明的展示折叠，沿对应版次的领圈摆放。详细公式、近重复端点的处理和假设见 `geometry/README.md`。

同一展示姿态用于全部案例，未改裁片的数据保持相同。所有模型共用一套包围框和相机参照，不按每个案例分别自动缩放，从而避免把真实长度变化抵消掉。

这些映射不是等距布料展开或批准的缝制方法。三维位置的来源可以核对，物理合理性仍属于另一个验收边界。

## 浏览器绘制与状态

静态对照的 `viewer.js` 直接把模型三角形送入 WebGL；WebGL 不可用时，使用同一套三角形进行 CPU 投影和 Canvas2D 绘制，不替换成固定图片。

两侧共享相机的 `yaw`、`pitch` 和 `zoom`。选择案例只更换右侧的实际输出模型、二维图、文件和相关摘要；左侧完整输入文件始终相同。

完整 YAML 和补丁通过文本节点显示。保存文件时从原始 base64 恢复字节，生成 Blob 下载。页面不把浏览器内重新序列化的对象当作原始 DXF 文件。

物理页的 `physics/viewer.mjs` 使用自己的完整画布切换：二维显示真实 SVG，三维显示实际轨迹与场。完整中文 YAML 弹层、原始文件下载、意图、补丁、相机和回放状态都属于该单文件；三维需要 WebGL，不能把旧对照页的软件降级能力推断给它。回放读取保存数组，切帧不会积分或修改源文件。

## 哪些文件应该重新生成

- 只改视觉或文案：重建单文件演示，并复测受影响交互和显示。
- 改 DXF 或规格：先重新运行对应编辑器和独立互校，再重建相关模型、演示和全部来源验证。
- 只改文档：运行文档构建和文档浏览器验证；确认演示 HTML 的摘要未变。
- 只改中心 README 或导航：重建 docs/hub 并验证目录、真实页面往返及旧 comparison/sewn 文件摘要；不必重建旧模型。
- 修改三维构造公式：重建五套模型，重新检查几何响应、未改片、实际 UV 和故障控制，再验证浏览器像素。
- 修改物理求解、接触或条件：使用新运行目录冻结源码、重新计算和独立验收；修改物理界面则重建物理 HTML 并更新匹配代码/数据的浏览器收据。

不要直接手改发布 HTML 中的 base64、SVG 或模型摘要来跳过这些步骤。
