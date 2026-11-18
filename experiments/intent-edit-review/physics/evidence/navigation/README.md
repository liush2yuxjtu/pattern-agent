# 文档与实验导航本地验收

结论：**PASS，仅限本次文档、导航与保留旧文件的边界**。原型与袖口的最新初始几何门 PASS，完整轨迹尚待父代理完成独立验收；本记录不签发整衣 PASS。其余三例仍为 PROFILE_REQUIRED，历史 FAIL 保留。

改动为中心 README、四份指南及对应 docs/hub 两个生成页。未修改物理 README、viewer、求解器或验证器，也未重建旧 comparison/sewn。

| 检查 | 结果与证据 |
| --- | --- |
| 文档真实浏览器 | PASS；37个目录锚点，1448/375/320px无溢出，真实对照入口；`docs-browser/report.json` |
| 中心真实浏览器 | PASS；54个本地仓库链接、10个目录锚点、5个模型/18份实际下载，demo/docs/sewn往返、软件绘制与离线；`hub-browser/report.json` |
| 中文与窄屏视觉 | PASS；已查看1448px操作指南、375px操作指南、320px七项表格截图；`navigation-readability.json` |
| 确定性重建 | PASS；docs/hub分别独立重建后逐字节一致；`local-integrity.json` |
| 旧页面保留 | PASS；旧对照HTML及sewn目录全部40文件摘要不变；`old-pages-before.json` |
| 新物理入口 | 相对链接规范目标为 `/intent-edit-review/physics/`；最终物理文件尚未落盘，真实往返待最终数据与页面完成 |
| 文档空白与补丁检查 | `git diff --check` PASS |

## 实际命令

```sh
python experiments/intent-edit-review/build_docs.py
python experiments/intent-edit-review/build_hub.py
python experiments/intent-edit-review/build_docs.py --output work/intent-physics/nav-final/docs-rebuilt.html
python experiments/intent-edit-review/build_hub.py --output work/intent-physics/nav-final/hub-rebuilt.html
python experiments/intent-edit-review/verify_docs.py --output work/intent-physics/nav-final/docs-browser
python experiments/intent-edit-review/verify_hub.py --output work/intent-physics/nav-final/hub-browser
python work/intent-physics/nav-final/review_navigation.py
git diff --check
```

`report.json`保存本轮七份文件的字节数与摘要。`initial-revision/`保留首轮状态更新前的实际检查，不用它冒充当前字节验收。最终轨迹数据到来后，更新状态说明及结果表，再核对对应构建与报告。
