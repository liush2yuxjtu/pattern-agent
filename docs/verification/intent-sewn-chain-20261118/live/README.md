# 真实线上缝合预览验收

**线上交付与下载后重开PASS；五项缝合总结果仍BLOCKED（2通过、3缺配置）。**
网址：<https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/sewn/>。

本项目源码为 `45a1bec27df142e46883fbdd33c5cf714bccf68d`，Pages运行44229112333成功，
见 [publication.json](publication.json)。期间其他并行工作也发布了站点；实际全站build
为 `8f8c061afee6e7f19611bc02a4d196b8548818e4`，是本项目提交的后代。该子页面、转换器
和验证脚本不变，没有回退其他人的更新。

正常HTTPS逐字节核对目录、两GLB、原有对照/文档及旧首页/原型/上衣页面，8项均200且
匹配实际部署源码。三项受限GLB均404，没有旧模型兜底。见 [live-http.json](live-http.json)。
全站部署与本项目组件身份分别记录，避免将无关后续提交视为本项目文件错误。

## 实际独立浏览器

使用已授权的Firecrawl Bash独立环境，正常验证HTTPS。仅从公开固定提交读取验证代码，
从真实Pages取回39项交付并逐个核对摘要。验证器执行前SHA-256为
`087b4ebd5acc97aaf77ac3c1a247a16cd9497cf02d5be2bd044d753733e8e409`。
环境为Playwright 1.62.0、Pillow、NumPy 2.3.5、SciPy 1.17.0与 `/usr/bin/google-chrome`。
没有远端重新生成模型。

```sh
PYTHONPATH=/tmp/sewn-live-final/deps python3 /tmp/sewn-live-final/repo/experiments/intent-edit-review/sewn/verify_preview.py --base-url https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/sewn/ --output /tmp/sewn-live-final/evidence --browser /usr/bin/google-chrome
```

退出0，见 [browser-report.json](browser-report.json)。两模型真实像素不同，旋转、滚轮、
键盘、线框、复位、真实触摸、375/320窄屏、15项可见量测及受限案例无模型均通过。
精确单预览HTML在禁网context中绘制；无WebGL时明确提示且模型仍可下载。没有改变
受管浏览器策略，也没有把该离线范围写成已绕过本机file导航限制。

实际保存GLB与完整ZIP后核对字节，再独立重开实际下载GLB。报告见
[原型](baseline/downloaded-independent.json)、[袖口](03_cuff_width/downloaded-independent.json)，
均15缝、1连通、4正常开口、间隙0、严格穿插0。

## 原始证据与恢复

[actual-live-evidence.zip](actual-live-evidence.zip) 保留真实下载GLB/ZIP、下载后独立报告、
日志和截图，共19项，8792750字节。SHA-256为
`fdfab0cfbd15a94464916c991679466ff07b40ae1b71299eafcdbc165614b73f`。
分15段取回，重组摘要与ZIP CRC通过。未用本地重新生成文件替代下载结果。

用view_image检查实际[原型](baseline/actual-preview.png)、[袖口](03_cuff_width/actual-preview.png)、
[手机](catalog-375.png)和[目录](catalog-desktop.png)，显示与本次文件一致。

首轮漏装SciPy造成下载重开无法启动；原始输出保留在
[initial-dependency-blocked.json](initial-dependency-blocked.json)，分类为环境BLOCKED。
补齐既定依赖后完整检查通过。一次临时会话在取回证据前过期，最终归档来自新的完整
公开源码复跑，未混用旧截图或缺失报告。

最终Chrome/context和HTTP服务均退出，interact session成功停止。本次只补交证据，
不改变模型、阈值、配置或页面。原始纸样FAIL、毫米假定、未标定U及材料/生产/试穿
NOT_RUN均保留。
