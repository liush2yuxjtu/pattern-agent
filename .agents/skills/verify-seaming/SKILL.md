---
name: verify-seaming
description: "验证服装纸样的裁片连接、走缝和三维接缝；用户要求检查缝合是否正确、裁片连接 PASS、DXF 到 GLB 接缝验收，或核对接缝交互视图时使用。独立重读源 DXF 和实际导出 GLB，按请求组合几何、可视化、线上 Site 与 Pages 保存检查。单纯外观渲染、人体尺寸估计或实物试穿不由此技能认证。"
---

# 裁片连接与接缝验收

本技能属于 Pattern Agent 项目。工作目录为仓库根目录，Claude 通过
`.claude/skills/verify-seaming` 读取同一份源文件。显式请求可写为
`$verify-seaming`；文件存在不代表原生客户端已自动加载或已验证触发率。

需要从 DXF 新建接缝装配与三维形状时，先执行
[sew-pattern-to-3d](../sew-pattern-to-3d/SKILL.md)，再回到本技能检查实际新产物。

先读根目录 `AGENTS.md` 与 [项目 verify](../verify/SKILL.md)。本技能负责接缝
任务的组织，复用现有独立检查器与下面的规范配方，不复制生成算法、放宽阈值或
以图片替代断言。提交前仍执行项目 `/verify`，随后直接提交 main，再以非强制方式推送。

## 确定本次要证明什么

记录当前提交、候选文件 SHA-256、原始 DXF、实际要交付的 GLB、单位、缝合约定、
修正线及预期正常开口。原文件没有单位声明时明确说明采用的单位假定。
使用实际导出或下载的 GLB，不能换成本地重生成文件后沿用另一份下载的结论。
新纸样先建立可核对的裁片与接缝合同；本款配置不能当成通用 DXF 导入器。

| 本轮声明 | 必需检查面与规范配方 |
| --- | --- |
| 裁片连接正确 | [dxf-seams](../verify/references/dxf-seams.md)：原纸样、修正线、最终 GLB 的独立几何检查 |
| 可点击视图准确展示该模型 | 上一项及 [seam-inspector](../verify/references/seam-inspector.md)：精确数据绑定与真实本地浏览器操作 |
| 已部署的验收网站能用 | 上述检查及 [seam-sites](../verify/references/seam-sites.md)：实际生产网址、授权登录、下载与重开 |
| 已保存到 ChatGPT Page | [seam-pages](../verify/references/seam-pages.md)：原生文件回执、受保护编辑、独立读回 |

按本轮请求选择检查面，逐面给结论。本地通过不能替代生产网站登录检查；保存文件
不能替代交互嵌入验证。几何通过不能替代面料、人体碰撞、动态仿真或实物试穿。

## 独立检查实际模型

已有产物先运行独立入口；改变生成器、缝合合同或几何检查器时，再执行
`dxf-seams` 配方中的完整测试、历史复现和服务浏览器流程。
Python 3.12 与依赖见 [服务 requirements](../../../services/dxf-preview/requirements.txt)。
检查已有产物不需要 Blender、预览服务器或 Site 凭证。

以下是仓库已冻结中码样例，输出请用新的目录，保留旧失败证据：

```sh
python services/dxf-preview/verify_connections.py \
  --dxf services/dxf-preview/public/sample.dxf \
  --glb experiments/fitted_tshirt/seam_inspector/accepted-model.glb \
  --units mm --out work/verify-seaming/independent.json
```

检查器重新解析实际 float32 GLB，独立读取原 DXF，不调用生成器。要求：

1. 来源摘要、单位、五个裁片面域和全部 15 组语义配对正确；沿原始边界定位，
   原线与派生修正线分开，所有点位修正有界并可追溯。
2. 按明确的归拢、拔开与领条负松量约定比较走缝；同时检查方向、局部加工区间、
   处理后平面缝长和三维实际缝长，不能假设所有原始边长天然相等。
3. 完整二维域与面到 UV 映射正确；每条缝边真正焊接且两侧来自正确裁片。
   共用顶点编号这一项不足以证明缝合正确。
4. 一个连通组件、四个预期边界环（领口、下摆、两袖口）、欧拉特征 -2；
   无重复面、退化面、孤立顶点、非法顶点邻域、非流形边或翻面。
5. 全部导出三角面执行严格穿插检查，包括共用边和共用点的面；合法点接触或
   边接触与面积重叠分开，不能跳过相邻面来获得零穿插。

阈值以规范配方和实际合同为准：间隙不超过 2 毫米，加工后平面残差不超过
0.05 毫米，派生点移动不超过 8 毫米，三维缝长误差不超过 2 毫米；
独立穿插检查在 1 微米数值容差下要求 0。不得为了 PASS 放宽这些条件。
独立 CLI：0 为 PASS，2 为不合格或不可验证；未处理的启动/依赖错误应另报
BLOCKED，不能把任何非零退出都写成裁片 FAIL。

## 核对交互视图

仅在本轮涉及交互视图或需复现完整展示时执行。依赖已有 Playwright 与
`/usr/bin/chromium`，不需要下载新浏览器。先运行现有正反例，再走真实控件：

```sh
SEAM_INSPECTOR_CONTROL_EVIDENCE=work/verify-seaming/controls.json \
  python -m unittest discover -s scripts -p test_seam_inspector_binding.py -v
python scripts/verify_seam_inspector.py \
  --html experiments/fitted_tshirt/seam_inspector/inspector.html \
  --glb experiments/fitted_tshirt/seam_inspector/accepted-model.glb \
  --dxf services/dxf-preview/public/sample.dxf --units mm \
  --output work/verify-seaming/inspector
```

实际 Site 构建产物可用 `--artifact-dir /absolute/selected-site/dist` 替换
`--html ...`；此入口没有线上 URL 模式。退出 0/2/3 分别为 PASS/FAIL/BLOCKED。

程序先独立重开模型，再核对 HTML 的每个未舍入三维位置、面索引、来源标签、
二维原/修正曲线、接缝全局编号、全部测量和开口。二维显示坐标舍入至 0.01 毫米，
验收使用未舍入数值；图示圆点不是被检查的顶点数量。

随后实际操作全部 15 个按钮、二维边与三维缝线，检查可见数值和选中状态；
验证鼠标/键盘/触摸旋转、正背切换、原线开关、刷新恢复、报告与 HTML 下载、
下载 503 后重试、320 像素窄屏、禁网运行下载 HTML、内嵌报告及无 WebGL 回退。
该程序从真实本地文件提供测试请求，不能将这组结果写成线上 HTTP 或登录验收。
保留意外控制台错误；预期注入的 503 单独记录。

## 线上与 Page 保存

需要发布或检查线上 Site 时，读取当前已安装 Sites 技能，沿用现有项目、
源码仓库和访问范围；检查部署的准确提交与归档逐文件摘要，并以授权会话操作
真实网址。发布成功只能证明发布，无法导航或登录应按该检查面报告 BLOCKED。
服务端归档内容不能读回时保留 BLOCKED，不能用本地 tar 代替，也不能从容器
哈希不同直接认定内容损坏。禁止使用绕过令牌或改变分享范围来通过验收。

需要写入 Page 时，读取当前 Pages 写作技能及编辑规范，先读已有目标内容与
指令。上传实际文件并核对大小/摘要及文件访问回执；用新读回的块 ID/哈希
保护编辑，保留原文件、旧 FAIL 与无关内容。逐项检查回执后独立读回文本和引用。
普通 HTML 文件链接不等于执行中的嵌入；嵌入仅按原生能力及其实际限制交付。
凭证、会话、签名网址与无关账户信息不进入证据或仓库。

## 出具结论与保留证据

每个声明保留候选提交与文件摘要、原始命令/退出码、独立报告、逐缝测量、
正反例、真实截图和实际下载文件；将本次记录存入新的 `docs/verification/`
目录。总体结果只覆盖本次所需范围；任何必需面受阻时不得宣称整体通过。

- PASS：当前候选在本轮所需检查面全部通过。
- FAIL：真实断言或产品行为失败；修复后重测，并保留最初失败。
- BLOCKED：依赖、启动、授权会话或必需表面不可达。
- SKIP：本轮没有该可执行变化，明确理由；未执行的实物/材料检查保留 NOT_RUN。

历史通过数据只作复现参照，不能贴到新文件上。冻结样例见
[清单](../../../experiments/fitted_tshirt/seam_inspector/manifest.json)：
修正版静态外壳 25,758 顶点、51,150 面、15 对接缝、四开口，独立几何 PASS；
原纸样按当前合同仍为 FAIL。旧 v1 的 9 组件/340 对穿插和更早布料实验
7.6455 毫米间隙/20 处穿插分别保留；实物合身性、材料力学和生产批准 NOT_RUN。
单片完整后身是装配假定，源标注数量 2 未解决；领条隐藏内层与缝份叠层不在该
单层外壳 PASS 范围内。

复现证据：[原几何验收](../../../docs/verification/dxf-seams-20261117/README.md)、
[交互与保存检查面](../../../docs/verification/seam-surfaces-20261117/README.md)。
程序会关闭自身浏览器；若为服务检查启动了进程，只停止本次创建的进程。
提交前记录 `/verify` 结论，核对最新远端 main、保留他人变更，再非强制推送。
