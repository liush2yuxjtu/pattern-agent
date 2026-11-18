# 纸样设计意图实验

**本目录及本 README 是整个实验的统一入口。** 原型、编辑代码、案例产物、三维预览、缝合流程和验证证据都从这里查找。相关网页的“实验总入口”也返回同一份内容。

在线入口默认打开可操作的案例库：五个真实预览、设计意图搜索、缝合状态筛选、二维/三维切换和案例文件下载。完整实验说明由本 README 生成，放在“实验说明”中；不再用长文档作为首页。界面来源与交互约定见 [画廊设计说明](GALLERY-DESIGN.md)。

[在线实验总览](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/experiment/) · [原型与改版对照](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/) · [独立物理实验台](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/physics/) · [详细文档](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/docs/) · [真实缝合结果](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/sewn/)

## 从这里开始

| 目的 | 直接入口 |
| --- | --- |
| 查看最小原型输入 | [输入规格 YAML](../../patterns/fitted-tshirt/input-spec.yaml) · [输入 DXF](../../patterns/fitted-tshirt/input.dxf) |
| 看设计意图如何变成新规格和新纸样 | [改版实验与四个案例](../intent-edit-benchmark/README.md) |
| 看原型与改版的二维、三维、完整规格和差异 | [打开对照页](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/) |
| 看真正焊接的数字外壳及逐缝验收 | [缝合流程说明](sewn/README.md) · [打开缝合结果页](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/sewn/) |
| 检查实际物理记录、应力应变、折角、接触与完整规格 | [物理实验台及复现方法](physics/README.md) · [打开物理实验台](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/physics/) |
| 在本机复现或继续开发 | [构建、验证与部署手册](docs/04-build-and-deploy.md) |
| 审阅完整证据 | [二维改版](../../docs/verification/intent-edit-benchmark-20261117/) · [对照页](../../docs/verification/intent-edit-review-20261118/README.md) · [严格缝合](../../docs/verification/intent-sewn-chain-20261118/README.md) |

## 当前结果

- 四个具体设计意图均生成了新中文 YAML、规格差异、DXF 坐标补丁和实际 DXF，二维互校通过。当前是已实现的封闭案例目录，网页不调用任意自然语言生成服务。
- 对照页显示原型及四个改版的真实二维图和来源绑定三维几何示意。完整规格、DXF 和补丁均可下载，共18份文件。
- 严格缝合链为 `sew-pattern-to-3d → verify-seaming → verify`。原型与袖口加宽的修正外壳几何 PASS；袖长、衣长、前领三个输入缺少当前支持的配置，五项整体仍为 **BLOCKED**。
- 已通过的两个外壳分别含15条缝、1个连通组件和4个正常开口，严格穿插为0。原始缝线在当前合同下仍为 FAIL，修正记录与原文件均保留。
- 原规格的 U 未标定；缝合实验只采用明确的毫米数值假定。材料实测与标定、生产批准和真人试穿均为 NOT_RUN。
- 独立物理实验台保存真实求解器记录、完整中文 YAML、二维 SVG、每帧张量与折角。**本轮原型与袖口两个案例各61/61帧离散数值验收 PASS**；其余三例因 `PROFILE_REQUIRED` 仍 BLOCKED。七项机制/界面检查与整衣轨迹分别判定，材料标定及真人合身仍未验证。

## 独立物理实验台

[打开 `/intent-edit-review/physics/`](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/physics/)，或查看 [代码、条件与复跑方法](physics/README.md)。该页面使用独立发布路径，旧对照页、静态缝合页和历史 FAIL 均保留。

- “二维纸样”显示当前文件的完整 SVG，可平移、缩放和复位；“完整规格 YAML”显示原始中文全文，可滚动阅读并下载。
- 展开“本款设计意图与变化”核对自然语言要求。可下载实际 YAML、DXF；袖口案例另有实际 `spec-diff.json` 与 `geometry-patch.json`。独立 `intent.txt` 在对应案例结果目录中。
- “三维物理”读取实际保存状态，提供布料、应变、应力、折角、接触、接缝六种显示，检查15条缝及所选面片的二维材料坐标；记录 JSON、当前网格 OBJ 和完整 HTML 可保存。
- 原型 `baseline` 与袖口加宽 `03_cuff_width` 有本次支持的来源配置。袖长、衣长、前领三个案例仍为 `PROFILE_REQUIRED`，不能借用原型的模型或结果。

| 本轮实际案例 | 已独立验收的保存帧 | 离散数值结论 | 全程最大主应变 |
| --- | --- | --- | --- |
| 原型 `baseline` | 61/61 | PASS | 185.61%（第29帧；末帧139.51%） |
| 袖口加宽 `03_cuff_width` | 61/61 | PASS | 138.88%（第60帧） |

两个案例的全程最大接缝间隙、离散人体穿入、双向边面穿越及严格自交均为0，张量、折角与数值穿袖检查逐帧通过。来源检查各含15条缝、4个预期开口；两份实际二进制各有10组机制对照通过，从0/30/59帧在新进程继续的六项状态逐字节一致。上述高应变来自估计材料模型，**不证明面料耐受、舒适或真人合身**；结论限定于本轮记录的离散状态。

| 检查边界 | 如何读结论 |
| --- | --- |
| 七项机制对照与界面验收 | 分别核对缝合、人体碰撞、应力应变、折角、回放、调试视图和布料连接约束的本次证据；未执行项保持 NOT_RUN |
| 穿着准备与整衣轨迹 | 本轮两个案例的初始状态及各61帧离散数值验收 PASS；仅覆盖实际来源、条件与保存状态，不能由机制或界面 PASS 代替 |
| 材料标定、生产批准与真人试穿 | 仍为 NOT_RUN；1U=1mm 只是本次数值假设，未改写原规格的单位状态 |

## 原型与原始输入

原型来源是用户上传的女士贴身长袖圆领T恤纸样。最小输入对为 [input-spec.yaml](../../patterns/fitted-tshirt/input-spec.yaml) 与 [input.dxf](../../patterns/fitted-tshirt/input.dxf)。

| 文件 | 内容 | 字节数 |
| --- | --- | --- |
| `input-spec.yaml` | 完整中文语义、尺寸、接口、待确认项和可独立重建的二维几何 | 194100 |
| `input.dxf` | 原始 CAD 实体、顶点、文字与容器 | 108836 |

基准四块纸样，204条曲线/直线、27条文字、1487个多段线顶点。YAML SHA-256 为 `88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e`；DXF 为 `1f82b2c4ca094983657ce49fc73cf06aec24d3329a53dcc3472dd5ca2cee87f4`。

完整 YAML 的几何不依赖原照片才能重建；网页中的几行摘要不能代替全文。两份文件是本次二维改版的几何起点，生产仍需批准单位、材料与工艺。

补充上传的领子、袖子分别保存在 [独立部件原型包](../../patterns/fitted-tshirt/components/20261118/README.md)：原始 DXF/EMF/PRJ、完整中文 YAML、重建 DXF 和双向核对报告均在该目录。新旧尺码表的冲突保留，没有悄悄改写原型规格。

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
| 实际物理输入、求解、接触、独立逐帧审计与恢复 | [physics](physics/README.md) · [run_native.mjs](physics/run_native.mjs) · [audit_experiment.py](physics/audit_experiment.py) · [verify_resume.py](physics/verify_resume.py) |
| 单文件物理实验台、完整规格/二维入口与界面验收 | [build_viewer.py](physics/build_viewer.py) · [viewer.mjs](physics/viewer.mjs) · [verify_viewer.py](physics/verify_viewer.py) |
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
| 可操作案例库、筛选、完整文件与视觉复核 | [画廊应用验收](../../docs/verification/gallery-app-20261118/README.md) |
| 物理机制、初始几何、完整记录、单文件界面与历史失败 | [物理实验验收](../../docs/verification/intent-physics-20261118/README.md) |

每个结论必须对应具体文件与检查边界。二维互校、预览交付和数字缝合的 PASS 不能替代生产或试穿批准。历史 FAIL 与环境限制仍保留在原记录中。

## 两条工作流

**建立原型包：** 二维DXF → 完整中文规格 → 二维重建与互校 → 来源绑定的三维示意 → 保存原型输入和证据。

**以意图改版：** 原型YAML + 原型DXF + 明确设计意图 → 新YAML与规格差异 → DXF补丁和新DXF → 二维互校 → 三维示意 → 支持范围内的新缝合外壳与独立验收。

物理实验从来源已核对的实际文件继续：完整材料坐标与缝合网格 → 穿着准备 → 独立几何门 → 真实物理记录 → 逐帧审计与回放。准备失败时保留失败原因；明确保存的负例回放也不变为整衣 PASS。

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

独立数据审计、三维重建、严格缝合和物理实验的完整命令分别在 [数据说明](docs/03-data-and-audit.md)、[三维说明](geometry/README.md)、[缝合说明](sewn/README.md) 与 [物理实验说明](physics/README.md)。只更新文档和导航时只重建 docs/hub，核对旧对照页与缝合文件的摘要不变。

在线案例库从已验收对照页读取同一份原型、案例和完整文件，缝合状态核对实际交付清单；“实验说明”由本 README 生成。改文档或页面导航后须重建对应的 `web/intent-edit-review/` 产物并执行适用的本地 `/verify`。按根 [AGENTS.md](../../AGENTS.md) 直接提交main、非强制推送，沿用既有Pages发布流程，再检查实际线上文件；不新增CI或覆盖无关页面。

## 范围和待确认项

对照页是约5.9MB的自包含HTML，完整规格、DXF、补丁、SVG、五套示意模型与脚本内嵌。单独保存后不需要旁边的资源；“实验总入口”是用户选择访问的在线文档链接。

严格缝合是另一个检查边界。三项超出当前模板的输入需要新的配置与缝合合同，不能通过放宽阈值、改来源标签或沿用旧模型来变成PASS。原型及袖口模型只证明明确修正线的静态单层外壳连接。

原文件没有物理单位声明；U尚未标定。后身数量2与完整单片装配假定、领条隐藏内层、缝份叠层、面料实测、实际人体条件和真人试穿均待确认。完整中文规格、原始文件、修正对照和所有历史失败保持可查。

物理实验已实际计算标准人体接触及数值材料响应，本轮仅原型和袖口两个案例通过各61帧离散数值验收。高应变不能据此认定面料耐受、舒适或合身；估计参数下的计算也不等于实测材料、已批准人体条件或生产工艺。此前准备失败和旧 T 恤的7.6455mm接缝间隙、20处穿插 FAIL 均保留。
