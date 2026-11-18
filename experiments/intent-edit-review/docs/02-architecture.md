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
├── verification/             独立内嵌数据审计及故障测试
├── verify_browser.py          完整演示的真实浏览器验证
└── verify_docs.py             在线文档、目录和演示入口验证

web/intent-edit-review/
├── index.html                可单独保存的演示
├── experiment/index.html     中心README的在线总览
└── docs/index.html           无外部资源的在线文档
```

## 与仓库其他目录的关系

| 目录 | 在本项目中的作用 |
| --- | --- |
| `patterns/fitted-tshirt/` | 原始 DXF 与完整中文输入规格 |
| `experiments/intent-edit-benchmark/` | 四个具体编辑操作、真实输出和补丁重放代码 |
| `experiments/intent-edit-review/geometry/` | 由原型和四个实际输出分别构建的三维模型 |
| `docs/verification/intent-edit-review-20261118/` | 数据、浏览器、下载和线上验收证据 |
| `scripts/build_pages.py` | 复制整个 `web/` 并组装现有静态站点 |
| `.agents/skills/verify/` | 本地验证流程和可复跑的操作配方 |

独立项目集中保存自己的代码，但没有复制一套原型或基准编辑器来制造多个版本。重建时从上述明确的仓库路径读取相同源文件。

## 单文件构建过程

`build.py` 读取基准和四个输出的实际 DXF、中文 YAML、规格差异和坐标补丁。它校验规格结构、DXF 实体与规格几何的对应关系，并核对每个模型的来源摘要。

构建器将完整文件编码为 base64，把实际二维图元和 SVG 与对应模型一起写入唯一的 `app-data` JSON。最后把样式、视图绘制代码和交互代码内联到 HTML。

浏览器启动时读取内嵌数据，检查文件长度，在支持的安全上下文中检查 SHA-256，并核对模型与当前 DXF/YAML 的版次。它不通过 `fetch` 拉取模型，也不从 CDN 导入三维库。

## 为什么三维没有沿用旧模型

五个 `*.mesh.json` 分别对应基准和四个改版。每个模型保存实际二维边界顶点到局部 UV 的绑定、三角形、三维位置、法向和明确的构造信息。

衣身使用实际轮廓边界的静态映射及内部调和插值。袖片使用来源绑定的纵向参数和截面映射。领条采用明确声明的展示折叠，沿对应版次的领圈摆放。详细公式、近重复端点的处理和假设见 `geometry/README.md`。

同一展示姿态用于全部案例，未改裁片的数据保持相同。所有模型共用一套包围框和相机参照，不按每个案例分别自动缩放，从而避免把真实长度变化抵消掉。

这些映射不是等距布料展开或批准的缝制方法。三维位置的来源可以核对，物理合理性仍属于另一个验收边界。

## 浏览器绘制与状态

`viewer.js` 直接把模型三角形送入 WebGL；WebGL 不可用时，使用同一套三角形进行 CPU 投影和 Canvas2D 绘制，不替换成固定图片。

两侧共享相机的 `yaw`、`pitch` 和 `zoom`。选择案例只更换右侧的实际输出模型、二维图、文件和相关摘要；左侧完整输入文件始终相同。

完整 YAML 和补丁通过文本节点显示。保存文件时从原始 base64 恢复字节，生成 Blob 下载。页面不把浏览器内重新序列化的对象当作原始 DXF 文件。

## 哪些文件应该重新生成

- 只改视觉或文案：重建单文件演示，并复测受影响交互和显示。
- 改 DXF 或规格：先重新运行对应编辑器和独立互校，再重建相关模型、演示和全部来源验证。
- 只改文档：运行文档构建和文档浏览器验证；确认演示 HTML 的摘要未变。
- 修改三维构造公式：重建五套模型，重新检查几何响应、未改片、实际 UV 和故障控制，再验证浏览器像素。

不要直接手改发布 HTML 中的 base64、SVG 或模型摘要来跳过这些步骤。
