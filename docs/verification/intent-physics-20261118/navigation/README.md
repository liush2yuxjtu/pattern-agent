# 最终文档与物理入口导航验收

结论：**PASS，限于本轮文档、真实导航、来源全文阅读与旧页面保留**。未提交、未修改物理源码；只更新中心 README、四份指南和 docs/hub 两个生成页。

本轮数学结论来自 `baseline-run37`、`cuff-run37` 的独立报告：两案例各61/61帧离散数值验收 PASS。其他三例仍为 BLOCKED：PROFILE_REQUIRED；材料标定和真人试穿 NOT_RUN。`run37-source-status.json`记录实际审计摘要、每二进制10组机制对照、新进程0/30/59帧继续结果及全部帧统计。

应变统计口径已区分：原型全程峰值185.610519%位于第29帧，末帧139.511564%；袖口全程峰值138.876516%位于第60帧。文档不将末帧写成全程最大，也不据此批准面料耐受或合身。

| 检查 | 结果与证据 |
| --- | --- |
| 最终物理HTML | 实际HTTP字节及最终文件SHA一致：`571fd1460f037ba1d498cc8147f175d7508ce9f484616834d579ec141163ac05`，46,088,590字节 |
| 真实路由往返 | docs → physics → 案例库/实验说明 → docs；`navigation-regression.json` PASS |
| 两个案例与全文 | 原型194100字节、袖口196859字节YAML实际全文与源文件相同，下载逐字节相同；SVG各204线/27文字；Escape恢复焦点 |
| 文档原验证器 | `docs-browser/report.json` PASS；37锚点，1448/375/320px无溢出，实际旧演示入口 |
| 窄屏与视觉 | 已查看桌面3D/2D、320px全文YAML、375px物理入口及桌面/手机中心结果；无横向溢出 |
| 生成确定性 | docs/hub独立重建逐字节一致；`local-integrity.json` |
| 旧页不变 | 原 comparison HTML 与 sewn 目录全部40文件前后SHA一致；`old-pages-before.json` / `old-pages-after.json` |
| 文本补丁 | `git diff --check` PASS |

## 实际命令

```sh
python experiments/intent-edit-review/build_docs.py
python experiments/intent-edit-review/build_hub.py
python experiments/intent-edit-review/build_docs.py --output work/intent-physics/nav-final-release/docs-rebuilt.html
python experiments/intent-edit-review/build_hub.py --output work/intent-physics/nav-final-release/hub-rebuilt.html
python experiments/intent-edit-review/verify_docs.py --output work/intent-physics/nav-final-release/docs-browser
python work/intent-physics/nav-final-release/navigation_regression.py
git diff --check
```

大型物理HTML使用仓库HTTP客户端对同一实际URL获取字节摘要，再正常导航；未替换响应或绕过浏览器策略。回归只检查导航与两案例来源入口，不重复父代理的61帧全功能验收。`draft-before-final-receipts/`如实保留收据重建前一轮：功能已完成，但末尾字节不变断言捕获了父代理重建，因此没有当作最终PASS。
