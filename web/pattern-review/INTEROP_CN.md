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

1. 在 OpenSloper 0.3.0 原生 Design 打开 .sloper，再执行 opensloper-cli check PATTERN --json。
2. OpenSloper 原生修改一个袖山点，保存后导回，比较变更前后坐标和配缝。
3. 单独检查 foldEdge、notches、grainline、seam allowance 和曲线走向。
4. 通过 .slayout 排料后导出 SVG/DXF，并进行真实 CAD 回读。
5. 保留 manufacturing/human fit NOT_RUN，直到裁剪、缝制和真人试穿完成。

## 已经执行的局部验证

独立 Python 测试：634 个 OpenSloper 结构对象、4 裁片、2 条折边、4 剪口，全部坐标与输入匹配，误差小于 0.001 mm。

Chromium Playwright：实际渲染 4 裁片、SVG 8 条线、导出初版 .sloper、袖片修改 +1.2 mm 后再次导出、Undo 以及无脚本异常。浏览器测试使用隔离 HTML 载入，仍需公网真实 E2E 复测。

转换器代码和界面在 index.html；完整 Python 生成器、测试、示例 .sloper 与 .slm 随对话 ZIP 交付。
