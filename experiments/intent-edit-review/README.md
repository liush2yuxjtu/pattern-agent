# 纸样设计意图实验

**本目录及本 README 是整个实验的统一入口。** 原型、编辑代码、案例产物、三维预览、缝合流程和验证证据都从这里查找。相关网页的“实验总入口”也返回同一份内容。

[在线实验总览](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/experiment/) · [原型与改版对照](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/) · [详细文档](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/docs/) · [真实缝合结果](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/sewn/)

## 从这里开始

| 目的 | 直接入口 |
| --- | --- |
| 查看最小原型输入 | [输入规格 YAML](../../patterns/fitted-tshirt/input-spec.yaml) · [输入 DXF](../../patterns/fitted-tshirt/input.dxf) |
| 看设计意图如何变成新规格和新纸样 | [改版实验与四个案例](../intent-edit-benchmark/README.md) |
| 看原型与改版的二维、三维、完整规格和差异 | [打开对照页](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/) |
| 看真正焊接的数字外壳及逐缝验收 | [缝合流程说明](sewn/README.md) · [打开缝合结果页](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/sewn/) |
| 在本机复现或继续开发 | [构建、验证与部署手册](docs/04-build-and-deploy.md) |
| 审阅完整证据 | [二维改版](../../docs/verification/intent-edit-benchmark-20261117/) · [对照页](../../docs/verification/intent-edit-review-20261118/README.md) · [严格缝合](../../docs/verification/intent-sewn-chain-20261118/README.md) |

## 当前结果

- 四个具体设计意图均生成了新中文 YAML、规格差异、DXF 坐标补丁和实际 DXF，二维互校通过。当前是已实现的封闭案例目录，网页不调用任意自然语言生成服务。
- 对照页显示原型及四个改版的真实二维图和来源绑定三维几何示意。完整规格、DXF 和补丁均可下载，共18份文件。
- 严格缝合链为 `sew-pattern-to-3d → verify-seaming → verify`。原型与袖口加宽的修正外壳几何 PASS；袖长、衣长、前领三个输入缺少当前支持的配置，五项整体仍为 **BLOCKED**。
- 已通过的两个外壳分别含15条缝、1个连通组件和4个正常开口，严格穿插为0。原始缝线在当前合同下仍为 FAIL，修正记录与原文件均保留。
- 原规格的 U 未标定；缝合实验只采用明确的毫米数值假定。材料力学、生产批准和真实试穿均为 NOT_RUN。

## 原型与原始输入

原型来源是用户上传的女士贴身长袖圆领T恤纸样。最小输入对为 [input-spec.yaml](../../patterns/fitted-tshirt/input-spec.yaml) 与 [input.dxf](../../patterns/fitted-tshirt/input.dxf)。

| 文件 | 内容 | 字节数 |
| --- | --- | --- |
| `input-spec.yaml` | 完整中文语义、尺寸、接口、待确认项和可独立重建的二维几何 | 194100 |
| `input.dxf` | 原始 CAD 实体、顶点、文字与容器 | 108836 |

基准四块纸样，204条曲线/直线、27条文字、1487个多段线顶点。YAML SHA-256 为 `88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e`；DXF 为 `1f82b2c4ca094983657ce49fc73cf06aec24d3329a53dcc3472dd5ca2cee87f4`。

完整 YAML 的几何不依赖原照片才能重建；网页中的几行摘要不能代替全文。两份文件是本次二维改版的几何起点，生产仍需批准单位、材料与工艺。

## 四个改版案例

每个案例都从同一个原型开始。结果目录包含实际意图 `intent.txt`、新规格 `new-spec.yaml`、`spec-diff.json`、`geometry-patch.json` 和 `output.dxf`。

| 案例 | 意图与全部产物 | 二维互校 | 严格缝合 |
| --- | --- | --- | --- |
| 袖长增加20U | [01_sleeve_length](../intent-edit-benchmark/results/01_sleeve_length/) | PASS | BLOCKED：PROFILE_REQUIRED |
| 前后衣身缩短15U | [02_body_length](../intent-edit-benchmark/results/02_body_length/) | PASS | BLOCKED：PROFILE_REQUIRED |
| 袖口展开宽增加10U | [03_cuff_width](../intent-edit-benchmark/results/03_cuff_width/) | PASS | 修正外壳PASS |
| 前领加深10U并联动领条 | [04_front_neck](../intent-edit-benchmark/results/04_front_neck/) | PASS | BLOCKED：PROFILE_REQUIRED |

[基准测试说明](../intent-edit-benchmark/README.md)包含性能统计、三项拒绝对照和补丁重放。组合改版及任意新措辞没有因此获得自动支持。

## 代码与模型在哪里

本目录保存实验对照、几何示意、缝合编排、文档、总览生成器和浏览器验证。输入、共享服务及证据保持各自的明确位置，通过本 README 集中连接。

| 内容 | 仓库位置 |
| --- | --- |
| 完整原型输入与原始资料 | [patterns/fitted-tshirt](../../patterns/fitted-tshirt/) |
| 自然语言案例、编辑代码、规格/DXF差异与输出 | [intent-edit-benchmark](../intent-edit-benchmark/) |
| 本实验显示与打包代码 | [build.py](build.py) · [app.js](app.js) · [viewer.js](viewer.js) |
| 五套来源绑定的静态三维示意 | [geometry](geometry/README.md) |
| 三技能缝合编排、状态与复跑 | [sewn](sewn/README.md) |
| 共享DXF到GLB转换器与独立检查器 | [services/dxf-preview](../../services/dxf-preview/README.md) |
| 可单独保存的对照HTML | [web/intent-edit-review/index.html](../../web/intent-edit-review/index.html) |
| 真正缝合的GLB、完整ZIP、原线/修正线和报告 | [web/intent-edit-review/sewn](../../web/intent-edit-review/sewn/) |

[使用指南](docs/01-user-guide.md)、[项目结构](docs/02-architecture.md)、[数据与互校](docs/03-data-and-audit.md)、[构建与发布](docs/04-build-and-deploy.md)、[视觉设计约定](DESIGN.md)提供进一步说明。

## 完整验证证据

| 检查边界 | 证据入口 |
| --- | --- |
| 设计意图到YAML/DXF、补丁重放与拒绝对照 | [二维改版基准](../../docs/verification/intent-edit-benchmark-20261117/) |
| 内嵌18份文件、五套二维/三维、完整YAML阅读和离线 | [对照页验收](../../docs/verification/intent-edit-review-20261118/README.md) |
| 项目文档与部署 | [文档发布验收](../../docs/verification/intent-edit-review-20261118/project-publication/README.md) |
| 本轮新GLB、独立15缝/拓扑/UV/穿插、27项服务测试 | [三技能缝合验收](../../docs/verification/intent-sewn-chain-20261118/README.md) |
| 实际线上下载后重开、触摸、窄屏和原始证据包 | [缝合线上验收](../../docs/verification/intent-sewn-chain-20261118/live/README.md) |
| README中心、页面往返与导航更新 | [实验中心验收](../../docs/verification/experiment-center-20261118/README.md) |

每个结论必须对应具体文件与检查边界。二维互校、预览交付和数字缝合的 PASS 不能替代生产或试穿批准。历史 FAIL 与环境限制仍保留在原记录中。

## 两条工作流

**建立原型包：** 二维DXF → 完整中文规格 → 二维重建与互校 → 来源绑定的三维示意 → 保存原型输入和证据。

**以意图改版：** 原型YAML + 原型DXF + 明确设计意图 → 新YAML与规格差异 → DXF补丁和新DXF → 二维互校 → 三维示意 → 支持范围内的新缝合外壳与独立验收。

原型包的早期流程和参考示例还可在 [prototype-package参考页](https://liush2yuxjtu.github.io/pattern-agent/prototype-package/) 查看。当前统一入口以本 README 为准。

## 复跑与发布

以下命令从仓库根执行。常用环境为Python 3.12、PyYAML、ezdxf、NumPy、SciPy、Pillow、Playwright及现有Chromium；文档与本README在线总览使用Pandoc 3.1.11.1。页面运行不依赖这些Python包。

```sh
python experiments/intent-edit-review/build.py
python experiments/intent-edit-review/build_docs.py
python experiments/intent-edit-review/build_hub.py
python experiments/intent-edit-review/verify_hub.py --output work/experiment-center/browser
python experiments/intent-edit-review/verify_browser.py --output work/experiment-center/comparison
```

独立数据审计、三维重建和严格缝合的完整命令分别在 [数据说明](docs/03-data-and-audit.md)、[三维说明](geometry/README.md) 与 [缝合说明](sewn/README.md)。

在线总览由本 README 生成，数据和链接只有这一份维护入口。改文档或页面导航后须重建对应的 `web/intent-edit-review/` 产物并执行适用的本地 `/verify`。按根 [AGENTS.md](../../AGENTS.md) 直接提交main、非强制推送，沿用既有Pages发布流程，再检查实际线上文件；不新增CI或覆盖无关页面。

## 范围和待确认项

对照页是约5.9MB的自包含HTML，完整规格、DXF、补丁、SVG、五套示意模型与脚本内嵌。单独保存后不需要旁边的资源；“实验总入口”是用户选择访问的在线文档链接。

严格缝合是另一个检查边界。三项超出当前模板的输入需要新的配置与缝合合同，不能通过放宽阈值、改来源标签或沿用旧模型来变成PASS。原型及袖口模型只证明明确修正线的静态单层外壳连接。

原文件没有物理单位声明；U尚未标定。后身数量2与完整单片装配假定、领条隐藏内层、缝份叠层、材料力学、人体碰撞和真实试穿均待确认。完整中文规格、原始文件、修正对照和所有历史失败保持可查。
