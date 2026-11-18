# 单 HTML 成品独立复核

最终候选复核结论为 `PASS_INDEPENDENT_CODE_REVIEW`。允许的交付范围仅为实验工作台。完整成衣没有 PASS。Golden 实尺度物理验收仍为 BLOCKED。

本轮 HTML SHA-256 为 `9cc3b57e3f7d4dc5bca2eb004c54f7ec33751348ee1532e45a4b564b303b74bf`。源码哈希和逐项结果保存在 `advisor-checks-result.json`。第一轮失败证据保存在 `artifact-review-round1.md`、`artifact-review-round1.json` 和 `advisor-checks-result-round1.json`。

## 缺陷关闭证据

| ID | 原问题 | 当前结论 | 本轮证据 |
| --- | --- | --- | --- |
| R01 | Golden SVG 改变原排版。 | RESOLVED | 四片相对位移与 YAML 精确一致。4 片、126 折线、78 直线、27 文字和 1487 折线顶点保持。 |
| R02 | 审计将另一帧结果标为原帧。 | RESOLVED | 未变更的 F0 正常提交。frame、source、job 或 auditJob 改变时，审计不运行也不提交。 |
| R03 | 小探针报告源码哈希过期。 | RESOLVED | 当前 engine、native-seam、人体和 WASM 四个哈希均匹配。3 mm 接触 FAIL 仍保留，5 mm 接触 PASS 不扩展到其他参数。 |
| R04 | 导入不完整 settings 沿用旧控件值。 | RESOLVED | 完整合法输入通过。缺字段、错误网格、错误 profile、非有限值和不符合控件步长的 8 项输入均被拒绝。 |
| R05 | 日志混合不同来源的同名 revision。 | RESOLVED | 日志含 source、artifact ID、instance ID、revision 和 run ID。独立检查确认新来源界面不显示旧来源记录。导出按当前 instance 过滤。 |
| R06 | 坏数值帧仍记录为 COMPLETED。 | RESOLVED | 空数组、NaN 和 Infinity 帧均被拒绝。合法坐标通过。COMPLETED 另带 garmentVerdict，不表示成衣通过。 |
| R07 | F0 初始装配被误读为引擎结果。 | RESOLVED | `draw3D` 对 INITIAL_ASSEMBLY 显示 `ASSUMED 初始装配`。该项为源码复核。 |

本轮执行 `node review/advisor-checks.mjs`，12 项独立检查均 PASS。另核对代码中的人体渲染和碰撞同源、未知应力、帧回放和导入重建行为。未修改产品源码。

## 复核限制

独立浏览器操作未完成。默认 Playwright 浏览器未安装。本机 Chromium 启动时被环境拒绝 socket 创建。Playwright MCP 连接也不可用。因此本报告没有独立浏览器 PASS。

root 仍须对最终 HTML 运行项目 verify 和真实浏览器检查。范围包括离线启动、源切换、编辑、重新生成、求解、停止、Timeline、导入和导出。若最终代码或 HTML 改变，应记录新哈希并重跑受影响检查。

本轮不重跑大规模成衣物理。小探针报告是已有当前源码报告的独立哈希与范围核对。原生两片缝合与 5 mm 接触通过，只支持对应 fixture。3 mm 接触失败不得被删除。

## 架构结论

保留 A 为实验入口。默认 40 mm 平面摆片、gentle 原生 spring 和每次 30 步可以暴露真实装配过程。界面必须继续显示未闭合的缝隙。短程无交叉不代表完成缝制，也不代表后续稳定。

当前 gentle 候选的历史报告在 30 步时仍有约 467.88 mm 最大缝隙。其他候选出现穿模、自交或数值爆炸。完整成衣没有 PASS。Golden 的单位、裁数、净裁线、材料和人体尺寸未确认，继续 BLOCKED。

B 保留为离线参考路线。使用固定版本 GarmentCode 和其指定 Warp fork。先针对同一组已知单位裁片建立装配基准，再比较初始摆片、缝合安排和碰撞。交换记录应包含 panel ID、二维 rest 坐标、seam 映射、人体 hash、单位、材料假设、step 和引擎参数。

浏览器展示 Python 计算结果时必须标 REPLAY。编辑后该结果立即 STALE。只有重新运行实际 Python 求解并取得当前 revision 的结果，才能称重算。B 的结果不能代替 Rapier 的验收，两个结果均应交给同一个独立几何审计。

交付名称应保持“现成引擎实验工作台”。产品检查、小引擎探针、完整成衣和 Golden 生产条件分别报告。任何层级的 PASS 都不能向其他层级继承。

## 最终候选冻结核对

已针对冻结候选重跑原有 12 项检查，全部 PASS。实际 HTML 哈希与 build-manifest 一致。manifest 中全部源码哈希也与磁盘文件一致。第二轮证据另存为 `*-round2`，未覆盖第一轮失败记录。

本轮仅复核限定改动。CSP 禁止外连，允许内联 WASM 和 Blob Worker。页顶分开显示计算结束与缝合 FAIL。人体面穿和内部顶点分别列出。DOM 与工程 JSON 均记录 build source hash。Timeline 当前帧步号与累计求解步数分开显示。

root 报告已通过真实浏览器 30 步运行、4000 个三角形帧样本的独立数值 oracle，以及 PDF 标尺检查。这些属于 root 提供的证据，本 reviewer 未独立操作浏览器。`file://` 被浏览器协议策略拒绝，验收保持 BLOCKED，未绕过。真实 garment FAIL 与 Golden BLOCKED 均保持。

## 最后两项实机修正复核

已核对 invalidate 清空 native、inputs 和审计元数据。无 frame 时显示“无当前求解帧”。refreshControls 更新导入后的参数标签。进度帧更新累计 stepCount。仅复核这些指定变化，未扩展功能。原有 12 项独立检查再次全部 PASS，HTML 与 manifest 一致，全部源码哈希匹配。

UI 导入的真实浏览器验收因 file chooser 期间 tab 清理断线而 BLOCKED，未绕过。`file://` 仍 BLOCKED。root 提供的 F30 结果为最大缝隙 467.877 mm，人体面穿、内部顶点和自交均为 0。该结果仍为 garment FAIL，不能因三个碰撞计数为 0 升为成衣 PASS。前轮证据保留为 `*-round3`。
