# 单HTML原型与改版对照

工作目录：仓库根。源码 `experiments/intent-edit-review/`，新路由
`web/intent-edit-review/index.html`。沿用根 `/verify` 的本地验收和直接提交规则。

前提：Python 3.12，PyYAML、ezdxf、NumPy、SciPy、Pillow、Playwright；实际浏览器
`/usr/bin/chromium`。已运行版本及范围见该目录 README。

```sh
python experiments/intent-edit-review/build.py
python -m unittest discover -s experiments/intent-edit-review/verification -p 'test_*.py' -v
python experiments/intent-edit-review/verification/audit_embedded_review.py --html web/intent-edit-review/index.html --output work/intent-edit-review/data-audit.json --adversarial
python experiments/intent-edit-review/verify_browser.py --output work/intent-edit-review/browser
python experiments/intent-edit-review/build.py --output work/intent-edit-review/rebuilt.html
cmp web/intent-edit-review/index.html work/intent-edit-review/rebuilt.html
git diff --check
```

独立审计不导入页面或模型生成器；重读实际源CAD和完整中文YAML，核对18份完整文件、
5组SVG及5个模型的边界UV/公式/谐波/改未改片响应。八项测试与六种实际HTML故障控制
覆盖旧SVG、伪造所有来源摘要的旧模型、重算摘要的坐标篡改、缺案例及截断文件。

浏览器脚本自行启动临时HTTP服务， readiness 为 `body[data-ready="true"]` 以及
实际canvas非空像素。逐个切换四个案例，检查图像而非只看标签；18次真正下载必须
逐字节等于仓库文件。核对完整YAML、每次打开回到开头、差异表/两个补丁、二维放大、
来源弹窗、拖动/键盘/滚轮、共用相机和正背复位。检查1448×1086及1366/768/375/320
宽度无页面溢出，控制台和资源请求无错误。关闭WebGL实测CPU三角形绘制。

离线边界：本环境 `file://` 被受管浏览器以ERR_BLOCKED_BY_ADMINISTRATOR阻止，
不得关闭安全策略。脚本将同一HTML复制到只含该文件的目录，读取唯一文档后关闭
服务器并禁用网络，继续真实操作和文件下载。保留file导航BLOCKED，不声称已验证双击。
远程Playwright MCP连接失败、ego-browser缺失时，用户已明确允许本地Playwright。

截图须用图像查看工具检查桌面、手机、完整YAML、差异表和软件降级，并与1448×1086
布局参考图比较；记录至少五项具体视觉比较及故意偏离。图片不可替代真实模型。

脚本退出时关闭自有浏览器、浏览器context和HTTP服务。证据写入指定目录，实际下载
留在其中；不得把本次PASS扩展成生产缝合或物理试穿PASS。U未标定，三维为静态几何
装配；历史布料FAIL与fit NOT_RUN沿用根规则。

已发布路由可用同一浏览器脚本的 `--base-url https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/`
核验；独立核对正常HTTPS返回的HTML摘要与本次候选。既有发布工作流仅作发布，不能
替代本地测试或真实浏览器。证据：`docs/verification/intent-edit-review-20261118/`。
