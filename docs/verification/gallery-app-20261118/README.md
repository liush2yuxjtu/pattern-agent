# 案例库从文档入口改为应用

**线上核心交互 PASS。** 已部署提交 `0f589e5cbde64a43531a36fa73011fc464d749a3`；
正常HTTPS文件回读、实际云端Chrome操作和原生DXF下载相符。
见 [线上验收说明](live/README.md)、[实际交互报告](live/report.json) 及 [发布回读](live/publication.json)。

本轮针对“画廊看起来像文档”的实际问题：旧入口默认只有目录、长段说明和资源表，
第一屏没有可查看的案例。当前默认首屏改为五个真实案例的交互画廊，实验README
继续作为资料中心，并在同页“实验说明”完整保留。

## 验收对象与结果

**本地验收 PASS。** `/verify` 检查画廊、原对照页、独立数据审计和文档导航。具体候选、命令与
摘要见 [receipt.json](receipt.json)。原型、四个改版的二维与三维数据没有改变；严格缝合
仍为2项修正外壳PASS、3项配置受限，材料/生产/试穿NOT_RUN。

## 实际用户流程

案例库 → 组合搜索与缝合筛选 → 二维/三维预览 → 打开案例 → 阅读完整意图/YAML →
下载实际文件 → 进入所选改版对照。手机详情关闭后恢复焦点及页面滚动。
空结果可恢复；不支持的缝合保留BLOCKED，没有伪造生成按钮或模型。

报告保存实际五个模型的像素、五个案例导航、18份下载的字节数与摘要、拖动/键盘/
滚轮/复位、1487/1280/768/375/320宽度、CPU绘制和断网下载。说明页继续检查全部
资源链接、九个目录目标及三个关联页往返；原对照页的18份下载与独立审计也复跑。

实际报告：[画廊和资源导航](gallery-report.json)、[原对照](comparison-report.json)、
[项目文档](docs-report.json)、[独立数据审计](data-audit.json)、[八项测试](unit-tests.log)。

## 视觉比较

[概念图](concept.png)、[改前](before-desktop.png)、[改后](after-desktop.png)、
[手机375](after-mobile.png)、[手机320](after-320.png)、[二维视图](gallery-2d.png)、
[详情桌面](case-detail-desktop.png)、[详情手机](case-detail-mobile.png)、[CPU绘制](software-gallery.png)。

采用完整应用概念图，原尺寸1487×1058；真实浏览器按同尺寸捕获，另查375/320手机。
已对照并检查：

| 项目 | 旧入口问题 / 修复 |
| --- | --- |
| 首屏与布局 | 长正文和资源表改为左侧应用导航、紧凑工具栏和三列五案例；首屏直接看到真实模型 |
| 文案层级 | “设计案例”标题和真实案例意图成为主信息；README正文收进“实验说明” |
| 字体 | 标题34px、案例22px、控件14–16px；删除旧article样式误加给案例标题的下划线 |
| 颜色和容器 | 纯白背景、深绿选中态、浅灰模型区、1px边线与小圆角；无装饰渐变或假指标 |
| 真实资产 | 概念图中的拟真衣服与通用纸样只指导布局；成品使用原有五套来源绑定模型和实际CAD SVG |
| 操作 | 真实筛选、空状态恢复、预览切换、详情、18份下载、正确改版跳转；没有仅改变外观的假控件 |
| 手机 | 顶部导航、换行工具栏、单列案例；详情可滚动，Escape关闭后恢复焦点与页面滚动 |

概念允许的可见文案及必要偏离见 [GALLERY-DESIGN.md](../../../experiments/intent-edit-review/GALLERY-DESIGN.md)。
真实源模型保留其几何特征；不把概念服装当成验收产物。搜索框按可用宽度伸缩，
真实CAD缩略图保留原布局；详情中的完整规格和下载沿用相同组件系统。

## 环境与范围

远程Playwright MCP返回Connection failed；按用户已授权的fallback使用本机Playwright
和 `/usr/bin/chromium`。本地测试由仓库 `.agents/skills/verify/SKILL.md` 及
`references/intent-edit-review.md` 编排，不使用CI作为验收。既有Pages工作流仅负责发布。

独立上线检查、提交身份和正常HTTPS文件回读在发布后另记录；不把本地PASS当作线上证据。
本机直接file URL的受管策略没有改动，断网检查使用同一自包含HTML，不绕过策略。
