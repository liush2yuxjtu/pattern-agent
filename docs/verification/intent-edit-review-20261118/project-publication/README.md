# 独立项目与详细文档发布

本次沿用独立项目目录 `experiments/intent-edit-review/`，补齐四份可阅读的中文文档、
文档生成器、模板和真实浏览器验证器，并新增 `web/intent-edit-review/docs/index.html`。
演示保持 `/intent-edit-review/`，文档使用 `/intent-edit-review/docs/`，没有重复创建同一演示。

源码入口：`experiments/intent-edit-review/README.md`。文档涵盖使用与两条流程、四个实际
案例、目录与依赖、完整中文YAML、两个补丁格式、来源绑定三维、独立互校、离线边界、
构建命令、main分支与正确Pages路径、发布顺序和排错。明确区分当前封闭案例展示与未来
新意图生成，保留U未标定及生产/物理试穿未批准的范围。

## 本地 /verify

**PASS。** 证据与候选摘要见 [receipt.json](receipt.json) 和
[candidate-files.json](candidate-files.json)。本次未改主演示或几何代码，因此保留之前
针对完整演示的独立审计和18份下载证据，不重复把文档测试当成几何验收。

- Pandoc 3.1.11.1 构建四份Markdown，在线文档33,585字节，SHA-256为
  `398bd45a7e273360e00afcf63282b42c099790c734113c5c49176e79275e2201`。
- 文档另写到新路径后cmp逐字节一致。
- 主演示重建到新路径后cmp逐字节一致，SHA-256仍为
  `aa7328e3a176a90dc217270779f042c6bab77fd27f5440b0d5ae454a78f377d4`。
- 站点使用原有构建器完整构建；生成站点的演示和文档分别与web源文件一致。
- 本地Playwright读取实际文档响应，核对32个目录目标、四章目录点击、1448/375/320
  布局无页面溢出、项目源码链接和从文档进入真实演示的相对路径。演示四案例及两个
  三维canvas均就绪，浏览器后退可回到文档；无控制台错误或HTTP失败。
- 使用图像查看工具检查桌面、手机、数据章和发布章的真实视口。长代码仅在自身区域
  水平滚动，页面不溢出。超长整页截图遇到环境GPU拼接伪影，改用分章实际视口并核对
  DOM只有一份header和四个章节，未修改产品内容来掩盖截图问题。

原始命令输出见本目录日志，浏览器原始报告与截图见 [browser/](browser/)。本地自有
Chromium、context和临时HTTP服务均已关闭。没有新增CI、PR、Issue或改变浏览器策略。

## 发布与读回

发布使用既有 `Publish GitHub Pages` 工作流；其作用仅为复制与发布已提交的静态产物。
发布后的实际HTTPS读回与部署身份记录保存在 `live/`，没有把工作流成功当作浏览器验收。
