# README 中文入口整理 · 2026-11-24（北京时间）

## 候选与范围

基于 `main` 的 `f166843824100e63d772d8e3e95018ccb24e8c62`。只改根 README、完整历史归档、贡献说明、两张静态说明 SVG 与本记录；不改运行代码、技能行为、阈值、依赖、CI 或部署。

按 `.agents/skills/verify/SKILL.md` 的 docs-only 规则，**运行行为验收 verdict = SKIP**：没有新可执行行为需要观察。这不表示验证了新模拟、客户端路由或线上全部交互。下列补充文档检查均通过，没有 FAIL/BLOCKED 被绕过。

## 实际执行

- `python3 -m unittest discover -s .agents/skills/verify-sleeve-creases/scripts -p test_inspect.py -v`：退出 0，15 项通过。含已知坏模型、退化/翻面、170°反折、来源哈希及 CLI 退出码等正负控制。[原始日志](unittest.log)
- README 的 `inspect.py --input .agents/skills/verify-sleeve-creases/fixtures/after-basic.json.gz --out /tmp/pattern-agent-creases.json --trace /tmp/pattern-agent-creases-trace.json`：退出 0；`status=PASS`、`sharpCount=0`；真实写出 JSON 与 Chrome Trace。只是当前袖片硬折角检查，不是整衣或物理通过。
- 在 box 隔离环境用 markdown-it-py + 本机 Chrome/Playwright 渲染 README：全部相对链接目标存在；3 张图片加载；5 个 details 实际逐项打开；主导航锚点存在；桌面与 390 px 手机预览已查看。[结构结果与根 README 摘要](docs-check.json)
- 完整旧 README 与归档逐字对照：除新增历史说明和相对 Markdown 链接加 `../` 外，正文完整保留。归档同时链接固定 SHA 原文，便于保留旧锚点。
- SVG XML、标题/描述、原图及放大图实视检查通过。二维对照直接复用原始矢量，仅更换视窗，没有修改坐标；新流程图简化自 `design-cloth/SKILL.md` 的现有 Mermaid，明确标作示意。
- 5 个 README 公开目标 HTTP GET 均 200：[链接结果](public-links.json)。只证明可达，没有注册、下载或与远端工具交互。
- `git diff --check`：退出 0。

本地渲染器初版未加 GitHub 风格表格横向滚动，导致手机预览溢出。修正预览器的表格容器后重新检查无页面级溢出；这是测试夹具呈现差异，不冒充 GitHub 原生渲染认证。SVG 的局部视窗在实视后调整，原始几何未变。

## 媒体与历史边界

- `docs/assets/readme/workflow.svg`：静态工作流示意，非界面或录像。
- `docs/assets/readme/pattern-comparison.svg`：全版与袖口放大；源 `web/pattern-library/editor/example-output/before-after.svg`，SHA-256 `90ec9c5c198dc900845ab751c22a93b3581d0bae5627bced05379f6a8d041085`。
- `web/garmentcode-preview/preview.png`：复用原有历史截图；源 SHA-256 `f5331d2a1bc6a4ccd801f079e7d1edb077ab2278240602470f1e8973cf4d123c`。保留该案例零自穿透未通过的结论。
- 没有 GIF 或视频，不声称看过完整动态过程。未实测 GitHub 原生代码复制按钮，未验证原生客户端自动触发或 CLO/Style3D 接入。
- 历史 T-shirt FAIL、实物 NOT_RUN 与各实验的 UNKNOWN / NOT_VALIDATED 均保留。

## 发布与清理

提交前核对远端 main 未变化，仅暂存本轮明确文件，不覆盖其他改动。仓库唯一现有 Actions 文件 `.github/workflows/pages.yml` 的 push paths 只覆盖 `web/**`、`patterns/**`、`scripts/build_pages.py` 与自身；本轮文件不匹配，不修改或手动触发该工作流，也不依赖 CI。

渲染器临时 HTTP server 与浏览器均已退出。完整本地证据、静态截图和检查脚本留在 box 的 `/workspace/pattern-agent-readme-evidence/`；临时输出 `/tmp/pattern-agent-creases*.json` 未加入仓库。没有启用云端代理、付费算力或远端部署。
