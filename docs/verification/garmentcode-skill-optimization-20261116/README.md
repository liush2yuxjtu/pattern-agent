# GarmentCode 仿真技能：旧版对照与优化

规范源码：[.agents/skills/garmentcode-preview](../../../.agents/skills/garmentcode-preview/SKILL.md)。
Claude 发现路径链接到同一目录；网页源码副本与下载包由
scripts/sync_garmentcode_skill.py 生成，其 --check 防止交付漂移。

- [技能与三维预览](https://liush2yuxjtu.github.io/pattern-agent/garmentcode-preview/)
- [Anthropic 官方工具生成的功能审阅页](https://liush2yuxjtu.github.io/pattern-agent/garmentcode-preview/evals/functional-review.html)
- [可编辑的 20 条触发测试](https://liush2yuxjtu.github.io/pattern-agent/garmentcode-preview/evals/trigger-review.html)

## 本轮结果

| 验收项 | 原版 v0 | 优化版 v1 |
| --- | --- | --- |
| 实际 CPU 仿真产物的 6 项断言 | 3/6 | 6/6 |
| 仅有已有 GLB 的 4 项断言 | 0/4 | 4/4 |
| 缺少匹配人体的 3 项断言 | 3/3 | 3/3 |
| 合计（按断言计） | 6/13 | 13/13 |
| 描述路由代理：训练集 | 35/36 | 36/36 |
| 描述路由代理：留出集 | 24/24 | 24/24 |

功能只比较各版本随附 CLI 的可用性、真实几何和状态交付，不代表一般模型能力
或物理求解精度的提升。每个场景每种版本只执行一次。benchmark 的按场景平均值
为 50% → 100%，不同于按断言加权的 6/13 → 13/13。

两版均实际运行 CPU XPBD 232 帧，3,569 顶点/6,958 三角形，人体相交计数 0、
自相交计数 2。独立重读的初始/最终拓扑一致，最大位移约 0.292777 米。求解器
及输出几何没有改变。新版记录耗时 112.023 秒，旧版 112.297 秒；并行执行、
不同辅助步骤与工具等待使时间不可比，不据此宣称加速。

**服装结论仍为：严格零自相交 FAIL，完整独立服装审计与实体合身 NOT_RUN。**

## Hill climb 过程

先保存原版快照。基线与执行脚本哈希见 executed-source.json。根据固定训练反馈
和真实功能缺口修订：

1. 原描述未明确“解释实现、给可执行接入命令”，三名独立评审一名漏选。v1 增加
   run/explain/troubleshoot、无样本演示、诊断与明确的相近任务排除范围。
2. 原版已有网格模式仍强制索要纸样和源码。v1 提前分流，只需网格；GLB 自动
   按米，OBJ/PLY 默认厘米，其他单位显式设置。
3. 原版宽松阈值通过时默认标签为“通过质量检查”，manifest 未分开严格/audit/fit
   状态。旧版执行者在中文说明中正确指出严格 FAIL，失败来自随附程序交付，
   并非执行者完全误解了结果。
4. v1 保留兼容的 quality_passed 语义，新增 scope、upstream_threshold_passed
   及 release。未稳定、异常和相交非零时分别标注；CPU 快照修复及原几何保留。
5. 候选重跑三组真实功能，全部 13 项通过；再执行 6 项 consumer CLI 回归、
   原有网格路径 3 项检查及真实 Chromium 离线交互。

描述在查看留出反馈前冻结（selection.json）。固定测试集已无未解决的功能/
训练路由错误，停止本轮优化。人工反馈尚未收集，未伪造 feedback.json 或批准。

## 触发评估边界

20 条中英请求含 10 正例、10 相近负例。seed=42 分层划分 12 训练、8 留出。
每版三名独立子代理不读取标签、分割、技能正文或其他答案。每位评审一次处理
完整清单，因此是三个独立评审的代理路由判断，不是 60 个原生独立会话。

环境没有 Claude CLI；Codex CLI 的模型连接被代理 HTTP CONNECT 403 拒绝并停止。
**原生触发测试 BLOCKED。** 不把代理测试称为 Claude/Codex 已触发。
输入、划分、原始理由与汇总见 trigger-evals.json、trigger-split.json、
trigger-v0/、trigger-v1/、trigger-results.json 与 native-trigger-status.json。

在可用且已登录的 Claude CLI 环境，按技能 references/evaluation.md 的
python -m scripts.run_loop 命令补跑原生优化，填写实际模型 ID。

## 功能、浏览器与证据

官方示例是真实仓库输入，不是已下载的数据集条目；缺失人体用例明确标注为合成
夹具。两版输出隔离，没有修改求解器或为旧版补造输入。断言检查真实 GLB 字节、
全量位置/索引、输入哈希、执行与状态边界。

新仿真和已有网格 HTML 经真实 Chromium 检查：WebGL、线框像素变化、鼠标旋转、
滚轮缩放、适用的初始/最终切换、375px 布局，无 JS/console 错误。
Browser 插件不可用、ego-browser 命令缺失，使用仓库已有 Playwright 路径。
宿主策略阻止 file:// 导航，首个失败保留；没有关闭策略，按现有验证器的 offline
context + set_content 路径渲染实际 HTML 字节。**原生文件 URL 导航仍为 BLOCKED，
不能声称已验证双击打开。**

官方审阅生成器直接内嵌 HTML 时，预览中的 script 结束标签会截断外层报表。
首次真实浏览器检查暴露了这个失败。新增 build_garmentcode_eval_review.py 仍调用
固定官方生成器，只对嵌入 JSON 做 HTML 安全转义，验证前后数据完全相同；
没有修改 vendor 源码、断言、评分或几何。随后重新打开报告检查 Outputs/Benchmark。

- benchmark.json：官方 aggregate_benchmark 输出，随后按新版/旧版排序、校正
  差值方向；metadata 明确一次执行、token 不可得及人工反馈未收集。
- functional/：各组真实评分、元数据和墙钟记录。
- functional-review-inputs.zip：标准 eval-*/configuration/run-1 审阅输入，含
  命令、结果、manifest、预览；排除原生缓存和无关文件。
- fresh-preview-browser-report.json 与截图：本轮新产物的浏览器证据。
- receipt.json：最终本地 /verify 门禁及候选来源哈希。

官方汇总工具的 token 零是缺失值占位，非测得零消耗；不报告 token 或速度优势。
没有完整独立服装审计、真实面料标定或实体试穿。

## 复跑

先按技能 setup.md 准备 Python/CGAL/libigl/trimesh 与定制 Warp，使用新输出目录。

~~~sh
GARMENTCODE_PYTHON=/absolute/venv/bin/python \
  python -m unittest discover -s scripts -p test_garment_preview_skill.py -v
python -m unittest discover -s scripts -p test_verify_garmentcode_preview.py -v
python scripts/sync_garmentcode_skill.py --check
python scripts/grade_garmentcode_skill_evals.py --workspace work/garmentcode-preview-workspace
python scripts/verify_garmentcode_skill_outputs.py \
  --preview /output/simulation/preview.html --preview /output/existing/preview.html \
  --output work/fresh-preview-browser
~~~

实际命令、上游版本、人体与配置在证据包中。解压后，从 Anthropic skill-creator
源码根目录运行 aggregate_benchmark，再用 eval-viewer/generate_review.py
的 --benchmark 与 --static 生成同类审阅页。指南固定来源为 anthropics/skills
提交 1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064。

## 发布后回读

应用提交 a3af391 已推送并在公开 build.json 确认。新预览的 12 项线上检查、
4 项下载及两份评估页面均通过。旧站完整回归在不存在 PDF 的最终探针上两次
收到 GitHub 503，应为 404，因此旧站线上回归为 FAIL；断言未改。详见
[发布后回执](hosted-receipt.json)。原生触发仍 BLOCKED；本补充只记录事实，
不修改应用、技能或旧站。远程截图未导出归档，不宣称已有完整线上截图包。
