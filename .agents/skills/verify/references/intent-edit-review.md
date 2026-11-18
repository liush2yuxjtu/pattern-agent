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

本机线上出现ERR_CERT_AUTHORITY_INVALID时，保留BLOCKED，不关闭TLS校验。已验证的
独立路径为Firecrawl interact的Bash环境：只从已公开的固定提交下载同一验证器及18份
源文件，核对脚本和HTML摘要后，用临时目录安装的Playwright 1.62.0/Pillow与
`/usr/bin/google-chrome`运行同一 `--base-url` 命令。随后对隔离HTML直接用
`browser.new_context(offline=True)` + `page.goto(file_uri)`检查四案例、实际像素、
交互、完整YAML和DXF保存。成功证据与公开源码固定SHA、命令、压缩包校验见该目录
`live/README.md`。完整浏览器脚本的file-BLOCKED字段记录的是本机已知策略；独立
真正file导航的结果单列 `file-offline-report.json`，不能把两台主机混成一次观察。
返回的ZIP应校验SHA和CRC后再提取；最后停止Firecrawl interact session释放资源。

## 独立项目文档

源稿 `experiments/intent-edit-review/docs/`，由本机Pandoc 3.1.11.1生成
`web/intent-edit-review/docs/index.html`。运行 `python experiments/intent-edit-review/build_docs.py`；
用 `--output work/intent-edit-review/docs-rebuilt.html`另写一份并cmp，确认确定性。
`python experiments/intent-edit-review/verify_docs.py --output work/intent-edit-review/docs-browser`
实际检查32个目录目标、1448/375/320布局、目录点击、来源链接、文档返回演示的真实导航
及演示四案例/两个canvas就绪。它自行关闭浏览器与HTTP服务；无需新增CI或浏览器策略变更。
用视图工具检查桌面、手机、数据章和发布章的分屏截图；超长fullPage截图在本环境可能
出现GPU拼接伪影，因此直接保存各章节的真实视口，不将该伪影误报为DOM重复。
只改文档时，演示HTML应仍逐字节等于已验收版本。正常站点构建后核对两个新子路由，
不修改现有主页面或导航。线上可用同一脚本的 `--base-url` 指向公开docs路由再验收。

## README 统一入口与关联导航

中心为 `experiments/intent-edit-review/README.md`；`build_hub.py` 用现有 Pandoc
从该文件生成 `web/intent-edit-review/experiment/index.html`，不维护第二份正文。

```sh
python experiments/intent-edit-review/build_hub.py
python experiments/intent-edit-review/build_hub.py --output work/experiment-center/hub-rebuilt.html
cmp web/intent-edit-review/experiment/index.html work/experiment-center/hub-rebuilt.html
python experiments/intent-edit-review/verify_hub.py --output work/experiment-center/hub-browser
python experiments/intent-edit-review/verify_docs.py --output work/experiment-center/docs
```

`verify_hub.py` 自行启动真实HTTP服务并关闭，核对README摘要、全部仓库链接和目录
类型、九个目录目标、1448/768/375/320布局，以及总览到对照/文档/缝合页的往返。
对照页的返回链接为绝对线上地址，方便独立HTML访问；本地只核对该地址并实际后退，
线上须再点击它、检查新标签确实回到总览。其他两页本地与线上都实际点击返回链接。
用图像工具检查桌面、手机和表格区域；已有对照与缝合浏览器验收仍须适用地运行。

只更新缝合目录导航时，先运行 `sewn/verify_preview.py`，再执行：

```sh
python experiments/intent-edit-review/sewn/publish_review.py --refresh-existing web/intent-edit-review/sewn --verification work/experiment-center/sewn/report.json
```

该模式要求新报告匹配实际目录HTML、完整通过案例及实际模型摘要，并拒绝任意模型、
源文件或交付包变化；只刷新目录导航证明与文件清单。不能借此重新宣告几何或生产PASS。
本轮结果见 `docs/verification/experiment-center-20261118/README.md`。

发布后可运行 `verify_public_hub.py --source-revision <公开完整提交SHA> --output <证据目录>`。
它从该固定提交取README及四个HTML摘要，核对真实线上响应，再实际点击三个往返
（包括对照页新标签）并检查四种宽度；不替代本地40个资源路径审计。
本机线上TLS环境受限时，沿用上文独立Firecrawl Bash浏览器路径、现有Google Chrome，
公开固定源码和Playwright 1.62.0，无需下载模型或关闭TLS。返回ZIP先验SHA/CRC，
再保存报告与截图并停止会话。实际成功命令和环境见本轮 `live/README.md`。
