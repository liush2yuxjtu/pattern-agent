# 现成开源引擎服装实验工作台

同一个工程版本提供二维纸样、设计师三维视图、物理诊断、网格调试和已计算帧回放。运行时的 JavaScript、Rapier WASM 与 MakeHuman 人体都嵌入一个 HTML。无需 MCP、CDN 或后端服务；这不等于没有使用第三方开源库。

**完整成衣仍为 FAIL。此交付是可复核的实验工作台，不是 CLO 或 Style3D 的等价替代。**

## 实际结果

| 范围 | 结果 | 证据与边界 |
| --- | --- | --- |
| Golden YAML 1.1 | 二维保真通过，物理 BLOCKED | 原始 U、排版、204 条线、27 条文字、1487 折线顶点逐项一致；U→mm 未标定，不生成实际尺寸裁剪任务 |
| FreeSewing 4.10.2 | 参数化制版通过 | Teagan 原生净样展开为前后身及两短袖；10 道缝的方向与端点角色明确。没有原生领条，不是 Golden 长袖重建 |
| Rapier 0.21.0 小试片 | 指定试验通过 | 两片原生关节缝合残差约 0.344mm；pin 漂移 0；二维结构 rest 保留。3mm 人体接触坏例仍为 FAIL，5mm 指定局部测试通过 |
| 完整样衣装配 | FAIL | 默认外置平片计算 30 步后最大缝隙 467.877mm，尚未闭合；贴体装配候选曾引发 WASM 错误，保留为已知失败入口 |
| 默认 F30 几何碰撞 | 离散检查通过 | 本帧内部顶点、人体严格面穿、布料自交均为 0。分离且远离人体的裁片可以无碰撞，因此不能推导成衣合格 |
| 应变与导出 | 独立复算通过 | 5 帧 × 800 三角形与 NumPy float64 SVD 一致；PDF 的 100mm 矢量标尺实测约 100.000000763mm |
| 应力、接触压力、真人合身 | UNKNOWN / NOT_VALIDATED | 没有已标定材料本构和真人试穿。几何应变、面夹角与材料应力分别标注 |
| 浏览器 | 已实际操作 | 启动、来源切换、五视图、30 步计算、碰撞审计、回放、输入修改失效、JSON/SVG/PDF/YAML 下载均有实际证据；当前浏览器使用 Canvas 软件深度缓冲，未验 GPU 渲染 |
| 其他实机边界 | BLOCKED / NOT_VERIFIED | file:// 协议被浏览器策略拒绝，未绕过；UI 文件导入在文件选择阶段遇到 tab 清理断线；停止按钮未赶在短程计算结束前中断，未算中断验收通过 |

## 使用

打开发布页面后，默认显示 Golden 原始纸样。在“数据来源”选择 FreeSewing 引擎样衣，等待 READY，点击“计算 30 步”，再检查当前帧碰撞。图中肩部支撑点、外置平片及开缝属于演示假设。每次增加 30 步，最多 600 步；该上限不是成衣收敛证明。

参数改变后，帧、审计、运行结果及原生统计失效，必须重新生成。时间轴只读取已记录位置，不调用求解器。导入工程只恢复完整合法输入并重建，不采信外部文件的旧 PASS 或物理帧。缺失、越界、步长不符和错误来源输入由代码检查拒绝；UI 导入实机验收尚未完成。

## 本地构建与复验

需要 Node 24、npm；独立导出复核使用 Python、NumPy 与 PyMuPDF。构建工具不是 HTML 的运行依赖。

```sh
npm ci
npm run build
npm run verify
node probes/pattern/conformance.mjs
node probes/pattern/mesh-conformance.mjs
node probes/rapier/engine-probe.mjs
node review/advisor-checks.mjs
python probes/pattern/output_oracle.py --artifact evidence/browser/browser-run-final.json --golden-svg evidence/browser/golden-pattern.svg --canonical-yaml evidence/browser/golden-garment-1.1.yaml --demo-svg evidence/browser/demo-pattern.svg --demo-pdf evidence/browser/demo-pattern.pdf --output evidence/output-oracle-final.json
```

浏览器驱动的复验方法见本目录 `.agents/skills/verify/SKILL.md`。下载工程和 HTML 的身份由 `build-manifest.json` 的源码与文件摘要绑定。原始 Golden SHA256 为 `88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e`。

## 性能解释

默认粗网格为 485 粒子、800 布料三角形、62 个原生弹簧关节，人体仍是 8000 面。Node 独立重建 5 次、各计算最初 30 步，求解 CPU 中位数 343.42ms，范围 326.01–583.54ms；5 次终态完整数组 SHA256 相同，错误数 0。没有预热，首轮慢样本保留。完整原始结果在 `evidence/native-performance.json`。

这与旧 PBD 的网格、约束、接触和步数不同，不能据此声称提速。默认开缝实验没有完成同等成衣物理任务。浏览器实际单次耗时和软件绘制成本分别保存在下载工程的性能条目中，不能当作 GPU FPS。

## 后续技术结论

保留 FreeSewing 作为二维参数化工具，保留当前 HTML 作为检查与证据入口。Rapier 原生试片通过，不足以选定它作为已验证的服装装配引擎。完整样衣需要更可靠的初始装配、缝合与接触处理。

下一条候选路线是固定版本的 GarmentCode / PyGarment 加其专用 Warp 仿真工具链，先在离线环境生成并独立审计同一份衣样，再将结果放入浏览器。离线预计算、浏览器回放和浏览器内重新求解必须继续分开标注。该参考路线本次未执行，不计 PASS。

官方来源：

- https://rapier.rs/docs/user_guides/javascript/soft_bodies/
- https://dimforge.com/blog/2026/09/25/advanced-soft-bodies-for-games-in-the-rapier-physics-engine/
- https://freesewing.dev/
- https://github.com/maria-korosteleva/GarmentCode
- https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode
- https://github.com/makehumancommunity/makehuman/blob/master/makehuman/data/3dobjs/base.obj
- https://static.makehumancommunity.org/about/license.html

开源依赖许可证和 MakeHuman CC0 来源保留在单 HTML 的“说明与来源”中。
