# 线上与真正离线单HTML验收

**PASS。** 实际公开路由为
https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/ 。

既有Pages发布运行 [44220590148](https://github.com/liush2yuxjtu/pattern-agent/actions/runs/44220590148)
成功，部署源码 `54c8d8280f5c732be109722bbe2d11037619c6bb`。正常HTTPS返回200，
实际HTML为5,938,482字节，SHA-256
`aa7328e3a176a90dc217270779f042c6bab77fd27f5440b0d5ae454a78f377d4`，
与本地及浏览器收到的原始字节完全一致。见 [publication.json](publication.json) 与
[live-http.json](live-http.json)。发布回执没有用来替代浏览器验证。

## 实际独立浏览器

本机Chromium在线访问发生ERR_CERT_AUTHORITY_INVALID，原始失败报告保留在
[local-tls-blocked/](local-tls-blocked/)，没有关闭TLS校验。使用Firecrawl技能的interact
Bash环境，仅从已公开的固定提交下载源码，不传输任何未公开附件或凭据。

独立环境为Python 3.11.2、Playwright 1.62.0、Pillow、Google Chrome 156.0.8078.73。
实际步骤如下：

1. 在 `/tmp/pattern-intent-review/deps` 安装临时Playwright和Pillow，不安装或修改浏览器。
2. 从上述固定公开提交的raw URL读取 `experiments/intent-edit-review/verify_browser.py`，
   执行前核对摘要
   `df41b9a317c2c2dbcf98c6f47755f26a8a744062d76da0958c9b9f01d2e32fc4`。
3. 从真实公开Pages下载HTML并核对候选摘要，解析内嵌文件清单；从同一固定公开提交下载
   18份对应文件，逐个核对摘要。工作副本保持仓库相对目录，不使用替代产物。
4. 执行以下完全相同的公开验证器，退出0且verdict为PASS：

```sh
PYTHONPATH=/tmp/pattern-intent-review/deps python3 /tmp/pattern-intent-review/repo/experiments/intent-edit-review/verify_browser.py --base-url https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/ --browser /usr/bin/google-chrome --output /tmp/pattern-intent-review/evidence
```

见 [browser-report.json](browser-report.json) 和 [browser.log](browser.log)：四案例真实
三维像素不同、原型保持；18次文件保存逐字节一致；完整YAML、差异和补丁、来源与二维
放大均通过；指针/滚轮/方向键、正背复位、同步相机通过；1366/768/375/320宽度无页面
溢出；无页面异常或额外网络资源。软件三角形降级也通过。

此脚本的 `offline.direct_file_url` 字段记录本机已知受管策略，并非声称独立主机也阻止
file导航。额外真正file测试单列于下一节，不能混淆两台主机的观察。

## 真正断网的file导航

又启动一次独立Chrome，使用 `browser.new_context(offline=True, accept_downloads=True)`，
直接 `page.goto` 到 `file:///tmp/pattern-intent-review/evidence/isolated/原型与改版对照.html`。
目录中只有这一份HTML，实际文件摘要与线上相同。复用已核对源码中的ready、select、
pixels、interactions、full_document与download函数：

- 四个案例均可切换，四组实际渲染像素不同。
- 指针、滚轮、键盘、两侧同步与正背复位通过。
- 完整中文YAML阅读/关闭和DXF真正保存通过；保存字节等于对应公开源文件。
- 请求记录只有初始 `file:` 文档，没有HTTP、字体、脚本或模型请求，无pageerror。

完整记录见 [file-offline-report.json](file-offline-report.json)，实际截图见
[file-offline.png](file-offline.png)。此项PASS来自独立Chrome，不覆盖本机策略BLOCKED。

## 原始证据与视觉检查

[actual-live-evidence.zip](actual-live-evidence.zip) 保留33项原始文件，包括18份线上实际
下载、离线下载、完整浏览器报告和截图。归档2,006,267字节，SHA-256
`be67fdeaea03530e1ce307feaeee4d0adfaa30bfb102c3e2db8834667a0a01ee`。
以四个base64分段取回本地，重组后摘要与ZIP CRC均通过；不是只取远程代理的结论。

用图像查看工具打开了实际[1448宽桌面图](desktop-1448.png)、
[375宽手机图](mobile-375.png)及[离线file图](file-offline.png)，中文字体、双栏/单列、
控件、真实模型、实际二维线条均正常。它们与先前已打开的1448×1086布局参考保持一致；
完整六项以上视觉差异记录见[主验收报告](../README.md)。

同时正常HTTPS读取旧首页、旧fitted-tshirt页、旧prototype-package页，全部200且逐字节
匹配现有仓库文件。见 [old-pages-live.json](old-pages-live.json)。本次应用提交的web差异
只有新 `intent-edit-review/index.html`，没有修改原页面或导航。

所有自有Chrome、context、临时HTTP服务已退出，Firecrawl interact session已成功停止。
本次补充只保存文档、配方和证据，运行时HTML及Python/JS/CSS源码保持已验收版本。
生产批准、实际材料与试穿仍未由此静态三维示意验证。
