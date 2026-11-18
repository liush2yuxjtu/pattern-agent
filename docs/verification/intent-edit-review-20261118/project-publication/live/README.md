# 详细文档的线上验收

**PASS。** 既有Pages运行44224243096成功发布源码
`3f69ad8213bf1a53ae995c04364cb1f4439f4638`。新文档URL为
https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/docs/ ，演示仍为
https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/ 。

部署身份见 [publication.json](publication.json)。正常HTTPS逐字节核对文档、演示、
旧首页、旧prototype-package和旧fitted-tshirt页面，五项全部200且与仓库文件一致；
`build.json`的部署提交与本次发布一致。原始记录见 [live-http.json](live-http.json)。

本机线上浏览器的已知证书限制没有通过关闭验证来绕过。使用已验证的Firecrawl interact
Bash独立环境，从公开固定提交下载同一验证脚本和两份HTML，分别核对摘要后，使用
Playwright 1.62.0和 `/usr/bin/google-chrome` 执行：

```sh
PYTHONPATH=/tmp/pattern-intent-docs/deps python3 /tmp/pattern-intent-docs/repo/experiments/intent-edit-review/verify_docs.py --base-url https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/docs/ --browser /usr/bin/google-chrome --output /tmp/pattern-intent-docs/evidence
```

公开验证器执行前摘要为
`8f1c38eca3dd9a8a6c2b72b6fdff6f787dcc3b704d1d29ad50e8e24ed36579e5`。
完整脚本退出0，见 [report.json](report.json) 和 [browser.log](browser.log)。
实际检查32个目录目标、四章点击、1448/375/320布局、文档来源链接及进入真实演示再
后退的导航。演示四案例和两个三维canvas均就绪，无页面异常或失败HTTP响应。

文档实际返回的SHA-256为
`398bd45a7e273360e00afcf63282b42c099790c734113c5c49176e79275e2201`；
演示仍为
`aa7328e3a176a90dc217270779f042c6bab77fd27f5440b0d5ae454a78f377d4`。
文档测试不替代之前对原型文件、18份实际下载和物理边界的独立记录。

原始截图与报告见 [actual-live-evidence.zip](actual-live-evidence.zip)，975780字节，
SHA-256为 `2c35ff00c03e18818ea9e246044eece6d19529a8a564d33d423d82bc2cc2553a`。
分两段取回后重新校验了摘要和ZIP CRC；使用图像查看工具检查了实际
[桌面](docs-1448.png)与[手机](docs-375.png)截图。源码阅读、目录和页面布局正常。

所有自有Chrome/context与HTTP服务已退出，独立interact session已成功停止。本次
补充提交仅保存文档与证据，不改变已经验收的演示、在线文档或任何原页面。
