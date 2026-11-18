# 实验中心验收

**本地验收 PASS。** 中心为 [experiments/intent-edit-review/README.md](../../../experiments/intent-edit-review/README.md)，
在线入口为 <https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/experiment/>。
本页记录的是入口组织和导航验收；五项严格缝合流程仍为 **BLOCKED：2 PASS、3 BLOCKED**。

## 改动与来源

README 集中连接原型 YAML/DXF、四个设计意图与全部输出、编辑代码、五套三维示意、
三技能缝合流程、真实 GLB/ZIP 和独立证据。共享输入与转换器保持原路径。
`build_hub.py` 直接把该 README 渲染成总览，不另维护一份正文；在线 HTML 内记录源 README 摘要。

对照页页脚、文档页头和缝合页头均加入“实验总入口”。仓库首页、基准测试说明和缝合说明
加入中心 README 链接。无关旧页面没有在本次工作差异中修改。

候选、命令和摘要见 [receipt.json](receipt.json)。本地代码、模型、浏览器证据由本仓库
[verify](../../../.agents/skills/verify/SKILL.md) 与适用的 [操作说明](../../../.agents/skills/verify/references/intent-edit-review.md) 验收。
既有 GitHub Actions 仅用于发布，不作为本地验收替代。

## 实际检查

| 边界 | 结果与证据 |
| --- | --- |
| README 到在线总览 | Pandoc 3.1.11.1；40 个仓库链接存在且文件/目录类型正确；重建逐字节一致 |
| 总览浏览器 | [hub-report.json](hub-report.json)：9 个目录目标，1448/768/375/320 宽度无页面溢出；实际进入三个关联页面并返回 |
| 关联文档 | [docs-report.json](docs-report.json)：32 个目录目标、四章、窄屏、演示导航正常 |
| 原对照页 | [comparison-report.json](comparison-report.json)：四个案例、18 次真实下载、完整 YAML、三维控制、离线与软件绘制通过 |
| 数据独立审计 | [data-audit.json](data-audit.json)：八项本地测试及实际 HTML 故障控制通过，实际输入/文件/模型互校 |
| 缝合预览 | [sewn-report.json](sewn-report.json)：两件实际模型、下载后独立重开、触摸、离线与降级通过；整体 BLOCKED 保留 |
| 来源与更新防护 | [invariants.json](invariants.json)：对照页内嵌数据不变；旧目录报告、被改动的实际模型均遭拒绝 |
| 正常站点构建 | 通过 `scripts/build_pages.py`；四个相关 HTML 路由与已验收文件完全一致 |

本地对照页的绝对返回链接指向线上，以便单独保存的 HTML 仍可找到中心。
本地检查其真实 href 并实际后退；上线后另外点击该链接检查新标签页返回，不把两者混作一次观察。

## 图像复核

已直接查看真实截图：

- [桌面总览](hub-desktop.png)：标题、四个入口、左侧目录、资源表层次清楚。
- [手机总览](hub-mobile.png)：入口换行、目录与正文顺序清楚，没有横向页面溢出。
- [手机案例表](hub-cases-mobile.png)：四列保留，长目录名及 `PROFILE_REQUIRED` 自动换行，PASS/BLOCKED 对应正确。
- [对照页页脚](comparison-footer.png)：两侧原型/改版、二维图和下载入口保持原布局，实验总入口可见。
- [项目文档](docs-desktop.png)：新增返回入口与原四章目录并存。
- [缝合手机页](sewn-mobile.png)：返回入口可见；2/3 状态与毫米假定仍在模型之前清楚显示。

## 范围

没有重新生成或替换模型。两件严格缝合 GLB、源 DXF/YAML、完整交付 ZIP 及独立几何报告
与更新前字节一致。缝合目录的预览证明在实际浏览器复验后刷新；清单保留上次报告摘要。
原线 FAIL、U 未标定、材料/生产/试穿 NOT_RUN 均保持。

本机受管浏览器的直接 `file://` 限制沿用原记录，没有关闭浏览器策略或 TLS 检查。
发布版本、正常 HTTPS 摘要和实际线上导航在发布回读证据中单独记录。
