# 试穿技能同步验证

基线提交 `f7adfa12cd903d44fbef7325dd0f4d10a2fd0073`。本次通过仓库的 `/verify` 验证三套技能。已验技能树为 `55c35e250ad481dd8473f23509860b67c651c414`，对应候选的 `.agents/skills`。

| 检查 | 方法 | 实测 |
| --- | --- | --- |
| 技能及本机安装 | 用 Codex `quick_validate.py` 检查三份入口。逐文件比较安装目录和 Git 暂存区。 | 三份入口通过。三个目录共 199 个文件与 Git 暂存区逐字节一致。另核对了 5 个折角依赖文件。 |
| V2.3 展示与图像 | 从每套技能的模板构建历史露肩样衣评审。运行各技能的 `publish_report.py`。用 Chrome 打开相对路径版和脱离素材目录的内嵌版。 | 六份预览均显示首页三图和独立原图。折叠可展开。每份报告的六张图与源文件逐字节一致。末节检查通过。 |
| 报告回归 | 运行 `design-cloth/evals/test-report-follow-up.py` 和 `design-cloth/evals/test-standalone-html.py`。 | 20 项报告回归和 13 项 HTML 回归通过。 |
| 四尺码十动作 | 分别以两套动作脚本运行 `design-cloth/evals/test_clo_motion_batch.py`。调用 `clo-motion-batch.py --help`。 | 两套脚本各通过 9 项回归。批处理入口可用。 |
| 二维纸样试穿评分 | 用 `pattern-to-fit/evals/grade-fit.py` 重放原有 22 个合成用例。 | 22 个用例的证据判定、报告判定和退出码符合预期。 |
| Boat 操作入口 | 读取 `boat new --help`、`codex mcp add --help` 和 Boat 命名快照清单。 | 命名快照 `clo3d-2026-1-382-backup` 返回 `ready`。指南参数符合本机 CLI。 |

上述交付检查判定为 PASS。新 Boat 虚拟机启动、CLO MCP 现场连接、原生求解和 Codex 侧栏渲染未在本轮复跑。历史样衣用于验证报告展示。原始设计图与旧试穿证据保存在本地，仓库接收可复用模板和技能实现。

## 设计师报告规则同步复验

基线提交 `ea3ad0fd4f23d48223e26aea471a6a02c1127686`。本轮技能树为 `0e08cf4f710b18939600769256f3677f568582e8`。
V2.3 保留原始设计、修前和修后对照。设计师与版师版使用服装语言。原始求解记录留在内部。相关历史测试图通过 `DESIGN_CLOTH_REPORT_FIXTURES` 提供。

- 报告末节与导出检查通过 20 项。独立 HTML 检查通过 13 项。设计师报告检查通过 13 项。
- 重放已有的 19、35、43 三个报告用例。每个用例 8/8。
- Chrome 复验六份报告。首页对照、折叠、内嵌图和相对路径图可用。
- `pattern-to-fit` 重新评分 22 个用例。各用例的判定和退出码符合预期。

复验判定为 PASS。Boat 原生求解和 Codex 侧栏仍未验证。
