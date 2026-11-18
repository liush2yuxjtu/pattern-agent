# WASM 布料实验室：首次打开露臀与真实接触压力修复

页面：<https://liush2yuxjtu.github.io/pattern-agent/cloth-lab/>。本证据只对应 `web/cloth-lab/`，不代表其他实验页面通过。

本地及公开页面 `/verify`：**PASS**。候选源码、父提交、HTML/WASM/人体摘要、命令和退出码见 [candidate.json](candidate.json)。本地及线上分别通过 50 项真实 Playwright 检查；另有 3 项实际 WASM 内核测试。61 个保存帧均经独立 NumPy/trimesh 重开。代码提交 `6af2cd271ff1323f5ee25e46a1d8d2dabf354fb8`，原有发布流程 [44260517629](https://github.com/liush2yuxjtu/pattern-agent/actions/runs/44260517629) 成功；它只负责发布，验证全部在本地执行。

## 公开页面验收

[线上最终结果](live/closing-readback.json)：首次打开、重置、尺寸／材料、移动人体、真实压力与离线 HTML 14 项；常规物理与热图 15 项；回放 15 项；文件交付 6 项，全部通过。实际公开 HTML 与本地完整 SHA-256 一致。默认、短宽、长窄、移动人体四种工况的 12 组物理字段，以及全部 61 个记录帧的物理缓冲、压力乘子、法向、时钟和参数，均与本地逐值完全相同。

线上 61 帧：接缝间隙最大 0 mm，检测到的人体交叉为 0，臀部覆盖射线外露为 0；最大压力接触方程残差约 0.00002746 mm，压力积分误差约 5.15 × 10⁻⁸ N。查帧中位约 10 ms、p95 约 15.53 ms；软件渲染帧间隔中位约 66.7 ms、p95 约 116.6 ms。所有页面／控制台错误数组为空。每项实际命令、退出码、原始日志、DOM 快照与截图在 [live/](live/)；[原始截图目视复核](live/visual-review.json)也已记录。

验收期间另一个已授权发布将根 `build.json` 推进至 `e835ae7fbedd9426b159bfed17d6eae43a7cf23a`。该发布 [44260595146](https://github.com/liush2yuxjtu/pattern-agent/actions/runs/44260595146) 同样成功。已独立检出该提交的本页 HTML，确认仍与本次候选完整摘要一致，并重新对该根提交运行全部根站点交互／下载流程，[结果 PASS](live/publisher-closing/browser-report.json)。没有仅修改期望提交值来获得通过。[源码核对](live/concurrent-publication-source-proof.json)保留。

新版真实背面：[线上截图](live/fit/first-ready-back.png)；[压力](live/fit/first-ready-pressure.png)、[应变](live/browser/strain.png)、[应力](live/browser/stress.png)、[碰撞距离](live/browser/contact.png)。真实公开页面下载的完整回放 [单 HTML](live/replay/downloaded-replay.html.gz) 和 [JSON](live/replay/downloaded-replay.json.gz) 以 gzip 保留原字节；物理回放和离线恢复均已通过。

## 用户看见的问题与修复

旧页面把与臀部相交的原始摆放直接作为暂停初始画面。之前只检查运行数百步后的结果，遗漏了用户第一次看见的状态。[原始背面截图](before/back-0.png)确实露出臀部。相同背面 ROI 中有 2,548 / 3,224 个皮肤像素；独立解剖覆盖检查发现 3,531 / 27,344 条射线露出。

默认打开、重置、修改正常纸样或材料，现在由真实 WASM 先求解 240 步，再显示衣服；保留实际物理步 240 和约 2 秒时钟。移动人体也暂停并重新试衣，录制时逐个保存真实求解步。下载状态直接恢复，不重复求解。人体原始坐标、索引和皮肤颜色保持一致，完整、不透明、正常深度测试，没有裁掉臀部或增加遮挡模型。

纸样改为与圆锥初始摆放对应的可展开扇环，UV、材料、SVG 与三维网格同源，避免直边梯形强行映到圆锥导致额外拉伸。实际导出的两片 SVG 含精确 10 mm 平行侧缝份与同心弧缝份，默认 1420 × 705 mm，极端尺寸也独立检查页面边界。

## 实际测量

| 检查 | 修复前 | 当前默认首次打开 |
| --- | --- | --- |
| 背面同一臀部 ROI 皮肤像素 | 2,548 / 3,224，FAIL | 0 / 3,224 |
| 16 个方向解剖表面覆盖射线 | 3,531 / 27,344 露出，FAIL | 0 / 27,344 露出 |
| 独立接缝间隙 | 初始状态未构成试衣验收 | 0 mm |
| 独立人体交叉 | 初始摆放穿透 | 0；最小采样间隙约 3.000 mm |
| 最大主应变 | 初始画面不应批准 | 14.3134%，原 20% 警告阈值保持 |
| 最大主柯西应力 | 原版本无真实法向压力 | 29.7917 kPa |
| 峰值法向接触压力 | 无实际接触乘子压力 | 47.4887 Pa |
| 法向接触力总量 | 无力账本 | 1.0792536 N |
| 压力面积积分与总力差 | 未验证 | 约 5.1 × 10⁻⁸ N |

[当前背面](local/fit/first-ready-back.png)、[正面](local/fit/first-ready-front.png)、[侧面](local/fit/first-ready-side.png)、[压力图](local/fit/first-ready-pressure.png)均为原始浏览器截图，未修改图片。[16 方位覆盖结果](local/fit/coverage-16-views.json)与 [首次打开原始工程](local/fit/first-ready.json.gz)可复查。

## 使用提供的压力物理模型

复用仓库 `web/pattern-pressure-bench.html` 内的单边法向 XPBD 模块及同 WASM 载荷试片；[源码溯源](../../../web/cloth-lab/src/PRESSURE_PROVENANCE.json)固定原始摘要。压力来自实际乘子 `λ / (Δt² A)`，并独立保存、导出与回放；柯西应力、距离和压力使用不同字段。顶点和面重心接触的反力均计入；缝合共享自由度按当前面积分摊。

使用相同 WASM 校验：零载、重力、500 / 1000 / 2000 Pa、30° 倾斜、网格细化、悬空和关闭碰撞。0.04 m²、1000 Pa 试片的实际反力为 39.9999957 N；悬空和关闭碰撞对照为 0 N。独立 NumPy 重算当前面积、乘子总力、压力积分、合力、接触距离和法向；还注入“力账本正确但接触位置伪造”的故障，必须拒绝。

验收中曾发现长裙窄下摆压力方程残差 0.468619 mm，超过原 0.25 mm 阈值。[失败证据](pressure-convergence-fail/)保留。接触收敛迭代由 3 次增至 16 次后残差为约 0.173138 mm，阈值没有放宽。

## 完整验收与性能

| 实际入口 | 结果 | 证据 |
| --- | --- | --- |
| 首次打开、重置、尺寸极端、软材料、移动人体、压力与可见覆盖、真实单 HTML 离线恢复 | 14 项 PASS | [fit](local/fit/receipt.json) |
| 单步、构成本构试片、真实人体交叉故障及恢复、缝合故障、SVG/OBJ、热图颜色、资源与性能 | 15 项 PASS | [browser](local/browser/receipt.json) |
| 所有 61 帧独立复验、无积分查帧、不同播放速度、真实下载重开、错误导入、人体移动、故障回放、1,201 帧实际录制上限 | 15 项 PASS | [replay](local/replay/receipt.json) |
| JSON 字段顺序、异步读取锁定与暂停、实际上传恢复、原子拒绝错误、回放活动状态 | 6 项 PASS | [handoff](local/handoff/receipt.json) |
| 实际 WASM 导出、固定内存、弹性能下降、自由落体递推 | 3 项 PASS | [kernel](local/kernel.log) |
| 相邻根站点：原生制版文件、MCP 本地重开、真实 PDF 与浏览器下载 | PASS | [publisher](local/publisher/) |

Playwright 使用系统 Chromium / SwiftShader，桌面及 390 px 移动视口；Browser 插件不可用，使用用户明确指定的 Playwright。浏览器无页面或控制台错误。软件渲染性能不代表实际 GPU。

四个软件渲染浏览器并行曾令 0.5 秒回放用时约 0.657 秒，超过原计时容差。[原失败及隔离探测](timing-diagnosis/)保留；未修改产品或放宽阈值。完整回放单独运行后通过，0.25× / 0.5× / 1× / 2× 分别约 2.048 / 1.075 / 0.551 / 0.257 秒，回放没有物理积分。保存一帧耗时中位约 0.10 ms，查帧中位约 9.70 ms、p95 约 13.59 ms。原始日志和真实下载 HTML/JSON 以 gzip 原字节归档。

实际录制上限测试保存 1,201 帧：基础 40,834,000 字节，压力 2,715,820 字节，合计 43,549,820 字节；理论原始缓冲总上限 98,145,720 字节。序列化与浏览器其他内存另计。大型移动人体故障轨迹保留在忽略目录，已记录 [原文件摘要](local/replay/large-raw-artifact.json)；提交的实际下载包含全部 61 个稳定帧。

构建重复运行得到完全相同 HTML SHA-256：`7af91417abb80a1f0563b1ed977bdc86c0b63135248168fa1654a1febda12234`，WASM SHA-256：`9bf573ba1f2197ff073e3f81d7cd63983dab6440eddaf4d8e034a2d4369e7a5b`。MakeHuman 资产摘要保持 `a75b6a2d59b2fa60ea29393e380182174627ba66d0993c649c8c571a6ccecda6`。

本次 PASS 限于所述离散物理模型、测试参数与采样；没有布料自碰撞、连续碰撞、实测材料/摩擦/软组织或实物适体验证。试衣压力为合成接触层结果，不能解释为临床舒适度认证。实体 fit 和生产批准为 NOT_RUN。历史 T 恤 7.6455 mm 接缝与 20 处交叉 FAIL 保持，不以本次结果覆盖。
