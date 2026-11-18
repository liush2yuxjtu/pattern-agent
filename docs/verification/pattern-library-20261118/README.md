# 纸样与三维图册验证 · 2026-11-18

本地候选通过。候选基线、暂存文件哈希及两次捕获的比较见 [candidate.json](candidate.json)。静态站使用实际 GitHub Pages 项目路径 `/pattern-agent/` 运行。[浏览器记录](browser-report.json)

- 用当前 FreeSewing Sandy 运行时重做两款裙装。与首次捕获相比，四片裁片、坐标、三角面、面角 UV 和 FreeSewing 参数逐项相等。每个 OBJ 包含 1,856 顶点及 3,584 三角面。独立检查得到 0 三角面人体穿透和 0 网格自交。三维无腰头，实物试穿为 NOT_RUN。
- T 恤袖口的静态 GLB 含 25,958 顶点及 51,546 三角面。对应 DXF 与 GLB 哈希及独立检查记录一致，有 15 对缝合接边。页面的 +23 U 二维袖长样例来自存档中的可重放补丁。
- 本地编辑器的 10 个测试通过。从浏览器下载的编辑器 ZIP 解压，执行 `python -m pattern_tool compile --intent samples/intent.yaml --output compiled` 和 `python -m pattern_tool apply --patch compiled/edit.patch.yaml --output applied`。7 个输出和包内样例逐字节匹配。袖长实测从 593.272857 U 变为 616.272857 U。
- `verify_gallery.py` 检查 29 个带哈希的文件、9 个实际视角、3 个改版状态、键盘放大与焦点恢复、深链接、错误参数回退、390/375/320 px 宽度和 8 次浏览器下载。无页面、控制台或网络错误。
- `scripts/verify_pages.py` 的首页与旧直裙、T 恤工作台流程通过。原有纸样 6 个回归测试、OpenSloper CLI 及 MCP 重开通过。首次运行直裙测试时缺少 `dist/`，按现有流程先构建后重新执行，通过全部 6 项。
- 本地浏览器截图：[桌面](sandy-standard.png) · [320 px 手机](mobile-320.png)。本地浏览器、HTTP 服务及渲染进程均已结束。

[复现命令](../../../web/pattern-library/README.md) · [验收流程](../../../.agents/skills/verify/references/pattern-library.md)
