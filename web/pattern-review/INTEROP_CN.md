# OpenSloper + Seamly2D｜互操作约束（实验）

## 已完成：OpenSloper 格式候选

中文审阅器：https://pattern-agent-review.vercel.app/

网页选择 T 恤裁片，修改缝合线坐标，点击「导出 OpenSloper .sloper」生成 documented pattern v1 JSON：

- 四个裁片：Front、Back、Sleeve、Neckband。
- 独立 freePoint、line、piece 对象，单位 mm。
- 前后衣身 foldEdge；袖片 count=2，mirrored=true。
- 四个定位剪口投影至采样边，偏离超过 0.1 mm 阻止导出。
- 从缝合线生成轮廓，保留名义 10 mm 缝份字段。

**限制：** 转换是已离散轮廓的静态几何，并非完整可随人体测量更新的参数公式。OpenSloper 原生 Design/CLI 导入、check、DXF 再导出仍为 NOT_RUN。真实材料、实体样衣、真人合身均未测试；状态 DRAFT_NOT_APPROVED。

官方资料：
- https://github.com/opensloper/opensloper/blob/development/docs/reference/files.md
- https://github.com/opensloper/opensloper/blob/development/docs/reference/cli.md
- https://github.com/opensloper/opensloper

## Seamly2D：不能直接使用 DXF 作为可编辑工程

Seamly2D 原生纸样为 .sm2d；测量文件为 .smis/.smms。维护者明确说明 DXF 不能直接导入为可编辑纸样。尚未生成并原生验证 .sm2d；不得将重命名扩展名当作格式兼容。

- https://github.com/FashionFreedom/Seamly2D
- https://forum.seamly.io/t/importing-pattern-files/16547

## 必须完成的原生验收

1. 在 OpenSloper 官方当前发布版 v0.2.0（2026-11-14 标记为 Pre-release；development 分支已有 83 个后续提交）原生 Design 打开 .sloper，再执行 opensloper-cli check PATTERN --json。
2. OpenSloper 原生修改一个袖山点，保存后导回，比较变更前后坐标和配缝。
3. 单独检查 foldEdge、notches、grainline、seam allowance 和曲线走向。
4. 通过 .slayout 排料后导出 SVG/DXF，并进行真实 CAD 回读。
5. 保留 manufacturing/human fit NOT_RUN，直到裁剪、缝制和真人试穿完成。

## 已经执行的局部验证

独立 Python 测试：634 个 OpenSloper 结构对象、4 裁片、2 条折边、4 剪口，全部坐标与输入匹配，误差小于 0.001 mm。

Chromium Playwright：实际渲染 4 裁片、SVG 8 条线、导出初版 .sloper、袖片修改 +1.2 mm 后再次导出、Undo 以及无脚本异常。浏览器测试使用隔离 HTML 载入，仍需公网真实 E2E 复测。

转换器代码和界面在 index.html；完整 Python 生成器、测试、示例 .sloper 与 .slm 随对话 ZIP 交付。

## 2026-11-16 新增：受限 OpenSloper 回读

用户可在中文工作台导入由本工作台生成的静态 .sloper（或其点坐标仍为数值的原生修改版本）；解析 freePoint、line 和 piece，逐段检查边界连续性、闭合性、4 个裁片完整性。含曲线对象、公式依赖、未知部件或非数值坐标时明确拒绝，不静默丢弃。导回以后**删除旧裁剪线（并隐藏显示）**，状态置为需要重新走缝；必须由专业软件重新生成缝份和检查剪口。这不是任意 OpenSloper 原生项目的无损读取。

本地 Chromium 已完成从网页导出 → 修改 → 导回静态 .sloper → 隐藏失效裁剪线的实际控件测试；尚未在 OpenSloper 原生运行时生成/修改/重新导回文件。

## 2026-11-16 补充：Seamly2D 原生格式已有可复用 XML 样例

最新官方 GitHub release 为 **v2026.11.16.133**（2026-11-16）；Linux x86_64 提供 AppImage。Seamly2D 源码仓库包含正式的 pattern XML Schema **v0.7.6**，并包含可参考的 T 恤样例 tshirt_test.sm2d。这说明可研究从 Pattern Agent 结构化几何生成原生 XML，而不只是停留在“DXF 无法直接导入”的结论。

- [Seamly2D v2026.11.16.133 release](https://github.com/FashionFreedom/Seamly2D/releases/tag/v2026.11.16.133)
- [pattern v0.7.6 XSD](https://github.com/FashionFreedom/Seamly2D/blob/develop/src/libs/ifc/schema/pattern/v0.7.6.xsd)
- [官方 T 恤样例 tshirt_test.sm2d](https://github.com/FashionFreedom/Seamly2D/blob/develop/src/test/CollectionTest/share/tshirt_test.sm2d)
- [Seamly2D 原生 XML 解析器](https://github.com/FashionFreedom/Seamly2D/blob/develop/src/libs/ifc/xml/vpatternconverter.cpp)

已从源码与样例确认的结构：根节点 pattern；版本与单位；每个 draw 包含 calculation、modeling、details；几何可由计算点、线、spline 和 detail contour 节点关联。原生格式不是 DXF，也不是简单的 SVG 包装。

**新路线**：为四个 T 恤裁片建立独立 draw block，以静态点和 detail contour 生成 .sm2d 候选；先按 v0.7.6 XSD 校验，再用 Seamly2D v2026.11.16.133 打开、保存、关闭重开、导出 DXF，并回读比较。第一阶段是静态轮廓可编辑候选，不伪装成有尺寸公式、人体测量关联或放码规则的参数化版型。

**本轮未完成的原因**：当前执行容器无法解析外网 DNS；Mac mini MCP 返回 429；Boat sandbox API 探针内部失败。没有可用的原生 GUI/CLI 执行环境。因此 OpenSloper 原生 check、Seamly2D XSD/GUI 实测仍 NOT_RUN。没有安装收费软件、启动付费计算或改变安全配置。

## 2026-11-17 样本范围澄清

另一个独立的基础直身裙样本已在 OpenSloper 0.2.0 CLI/MCP 原生检查与导出 PASS。该结果**不转移**到本文件的 PA-TSHIRT-001 T 恤样本。本 T 恤的 .sloper 原生打开、GUI 修改袖山、保存并导回仍为 NOT_RUN；Seamly2D .sm2d 生成和原生 GUI 往返也仍为 NOT_RUN。