# 本地运行、验证与发布 {#release}

## 环境要求

运行演示只需要现代浏览器；完整 HTML 无 CDN 或模型服务器依赖。

重新构建演示使用 Python 3.12、PyYAML、ezdxf；重建三维还使用 NumPy 和 SciPy。浏览器验证使用 Playwright、Pillow 和 Chromium。此前实际版本与原始证据见项目 README 和仓库验证目录。

在线文档构建使用现有 Pandoc，本次环境为 3.1.11.1。它只在本地把四份 Markdown 与模板转换为已提交的 HTML；GitHub Pages 发布过程不安装或执行 Pandoc。

以下命令均从仓库根目录执行。`work/` 用来保存临时重建与证据，不能拿旧日志代替本次实际运行。

## 构建与预览

```sh
python experiments/intent-edit-review/build.py
python experiments/intent-edit-review/build_docs.py
python experiments/intent-edit-review/build_hub.py
python -m http.server 8000 --directory web
```

本机演示地址为 `http://127.0.0.1:8000/intent-edit-review/`，文档地址为 `http://127.0.0.1:8000/intent-edit-review/docs/`。生产 URL 多一层 `/pattern-agent/` 前缀，因此文档中的返回演示链接使用相对路径，不硬编码站点根。

如果要重建三维模型，先运行：

```sh
python experiments/intent-edit-review/geometry/build_meshes.py
python experiments/intent-edit-review/geometry/verify_meshes.py --output work/intent-edit-review/geometry-check.json
```

模型生成器和自检不能代替独立审计；构造公式变化时，两者都必须重新运行。

## 原型与输出验证

```sh
python -m unittest discover -s experiments/intent-edit-review/verification -p 'test_*.py' -v
python experiments/intent-edit-review/verification/audit_embedded_review.py --html web/intent-edit-review/index.html --output work/intent-edit-review/final-audit.json --adversarial
python experiments/intent-edit-review/verify_browser.py --output work/intent-edit-review/browser
```

真实浏览器必须检查四案例的实际像素、原型保持、完整文档、差异、18次文件保存、旋转和缩放、窄屏及 WebGL 不可用时的软件绘制。截图还要用图像查看工具检查，不能只看退出码。

受管环境出现本地文件策略或证书问题时，保留 `BLOCKED`。不要关闭证书校验或浏览器策略来制造通过。已验证的独立 Chrome 路线、公开源码固定摘要及真正离线文件证据保存在 `docs/verification/intent-edit-review-20261118/live/`。

## 文档与确定性重建

```sh
python experiments/intent-edit-review/build_docs.py --output work/intent-edit-review/docs-rebuilt.html
cmp web/intent-edit-review/docs/index.html work/intent-edit-review/docs-rebuilt.html
python experiments/intent-edit-review/verify_docs.py --output work/intent-edit-review/docs-browser
python experiments/intent-edit-review/build.py --output work/intent-edit-review/demo-rebuilt.html
cmp web/intent-edit-review/index.html work/intent-edit-review/demo-rebuilt.html
git diff --check
```

文档验证器检查真实 HTML、桌面和手机布局、目录锚点、演示入口、项目源码链接及控制台错误。只修改文档时，确认主演示 HTML 的摘要不变，避免意外引入数据或模型改版。

## GitHub Pages 的正确位置

| 项目 | 正确值 |
| --- | --- |
| 仓库 | `liush2yuxjtu/pattern-agent` |
| 提交分支 | `main` |
| 项目源码目录 | `experiments/intent-edit-review/` |
| 演示发布文件 | `web/intent-edit-review/index.html` |
| 文档发布文件 | `web/intent-edit-review/docs/index.html` |
| 演示 URL | `https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/` |
| 文档 URL | `https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/docs/` |
| 中心README | `experiments/intent-edit-review/README.md` |
| 在线总览 | `https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/experiment/` |

不另建仓库，也不更改现有主页或其他项目页面。静态站点构建器会复制整个 `web/`；新增此子目录即可进入同一个项目站点。

## 发布顺序

1. 查看当前工作区和远端 `main`，保留其他并行工作，不覆盖或强制推送。
2. 根据本次修改重建演示或文档，按 `.agents/skills/verify/` 执行适用的本地验证并保存候选摘要、命令、结果和截图。
3. 用 `scripts/build_pages.py` 在仓库内的独立临时目录构建，确认新路由及旧页面都保留。
4. 直接提交并非强制推送到 `main`。仓库规则要求本地验证；不创建 PR、Issue 或新的 CI。
5. 观察既有 `Publish GitHub Pages` 发布工作流的部署回执。它只构建和发布，不是验收测试。
6. 正常 HTTPS 读取新 URL，核对 HTML 实际字节摘要、站点 `build.json` 的部署身份，并验证文档到演示的相对导航。
7. 检查旧首页、旧原型页和旧 T 恤页仍可访问；保存部署与线上读回证据。

`web/**` 的变更会触发现有发布流程。只有项目源码或 Markdown 修改时，先重建并提交对应 `web/` 产物；不要因为文档已经提交就声称新发布文件自动变化。

## 常见问题

**页面打开了，但三维空白。** 等待文件校验完成，查看页面错误提示和浏览器控制台。模型来源不匹配时应修复输入配对并重建，不删除校验。WebGL 不可用时应由实际三角形软件绘制降级。

**修改了 YAML，却还是旧图。** 先生成并互校对应 DXF，再重建当前模型和 HTML。只改摘要或标签不会生成新纸样。

**要输入一个新的自然语言设计。** 当前选择器只显示四个已实现案例。先将新意图规范为可量测目标、单位、保持区域和联动约束，再实现或审核对应编辑代码，生成全套产物并独立核验，最后加入展示清单。

**几何通过，是否可以发给工厂直接生产？** 仍需要批准单位标定、材料、裁数、净裁角色、缝制与折边等；几何示意没有完成物理试穿验收。

**上线后看到旧页面。** 核对具体部署提交和返回 HTML 的摘要。发布工作流成功、缓存或旧截图均不能证明浏览器正在运行新产物。
