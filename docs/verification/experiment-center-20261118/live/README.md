# 线上中心与导航验收

**PASS。** 真实 GitHub Pages 浏览器导航与正常 HTTPS 回读均指向公开提交
`f9b59a94b4f1e87f70a82acdd792fbc7c6b25141` 的实际文件。

[report.json](report.json) 记录真实浏览器动作：

- 1448/768/375/320 宽度无横向页面溢出，实际点击目录。
- 从总览进入对照页，等待四个案例及两个三维画布就绪，点击页脚“实验总入口”；新标签页确实回到总览。
- 从总览进入文档页、缝合页，再分别点击页头“实验总入口”返回。
- 对四份实际浏览器文档响应逐一计算摘要，与公开固定提交的源文件核对。
- 控制台、页面异常与 HTTP 错误均为零；缝合总 BLOCKED 文字及两件模型入口保留。

本机运行本地完整路径审计；独立 Firecrawl interact Bash 主机运行正常 HTTPS 浏览器观察。
它只下载公开固定提交的 [verify_public_hub.py](../../../../experiments/intent-edit-review/verify_public_hub.py)，
用 Python 3.11.2、Playwright 1.62.0 和 `/usr/bin/google-chrome` 运行：

```sh
python verify_public_hub.py --source-revision f9b59a94b4f1e87f70a82acdd792fbc7c6b25141 --browser /usr/bin/google-chrome --output evidence
```

脚本 SHA-256、命令、七份线上交付文件逐字节回读及发布工作流地址见
[publication.json](publication.json)。独立主机返回六份真实文件的 ZIP，551354 字节、
SHA-256 `b9394a9b0b11dcdb0261f397d9cab48d2619bb8186148bb13577a09bb7620dc9`；
提取前核对摘要与 ZIP CRC。浏览器和交互会话均已关闭，没有禁用 TLS 或浏览器策略。

已直接查看 [线上桌面](public-hub-1448.png) 和 [线上手机](public-hub-375.png)，
与本地相同源文件的标题、入口、目录及表格相符。[真实对照页页脚](public-comparison-footer.png)
同时保留原型/改版展示与实验总入口。

这是部署和导航证据；源资源完整路径、18 次真实下载和两件模型的下载后独立重开，
对应上级目录的本地完整报告。没有把本轮导航检查扩展为材料、生产或试穿验收。
