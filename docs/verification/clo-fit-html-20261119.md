# CLO Fit 0.2.1 单文件 HTML 验收

候选基线为 `f02a83d1b83d05e20ed768ca67ee93aac56f6290`，已验证的插件树为 `d3cc943cdd4d4cf2bc868627c5e985e27f8e38fd`。本地 `/verify` 对 HTML 报告生成与显示的判定为 **PASS**。使用 [CLO 导出与插件验收流程](../../.agents/skills/verify/references/clo-fit-export.md)。

- 在独立 Codex 配置注册本地仓库，执行 `codex plugin add clo-fit@pattern-agent --json`。从安装缓存运行 `python3 inline_report_images.py 草稿.html 报告.html`。18 张正文图片解码后的字节与各自原件一致。报告的 SHA-256 为 `b347eaa9d0f7660431149b6a6d376df46d97519f7fa037b32442349008a7c1f6`。
- 将 [Carlton](../cases/carlton-joost/README.md) 报告单独放进空目录。用 Playwright 驱动 Chrome 离线打开，分别检查 1440×1000 与 390×844。两个视口均显示 18 张内嵌图，线稿与垂臂普通材质正面并排，两个纸样 SVG 已解码并在截图中可见，9 张试穿章节图可见。目录跳转可用，页面无横向溢出、运行时错误或外部请求。
- 缺少本地图片和使用远程图片 URL 的反例均报错退出。没有写出报告。技能格式校验以及 `python -B -m unittest discover -s .agents/skills/clo-fit-export/scripts -p test_fold_preview.py -v` 两项折角测试通过。

报告在本地复用保存的试穿资料。新模拟与实物试穿为 NOT_RUN。验收后关闭 Chrome。
