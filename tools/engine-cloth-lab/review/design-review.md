# 浏览器布料引擎迁移设计复核

结论为 `CONDITIONAL_GO_A`。A 是主交付架构。B 只提供离线参考和交叉校验。此结论允许建设可运行 artifact，不代表 golden 衣样的物理结果通过。

复核范围为架构、输入真实性和验收边界。未运行大规模物理试验。最终 artifact 复核仍为 `NOT_RUN`。

## 架构选择

| 维度 | A，FreeSewing 与浏览器 Rapier JS/WASM | B，Python GarmentCode/Warp 加浏览器求解或回放 |
| --- | --- | --- |
| 单 HTML 编辑后计算 | 一个运行时可完成闭环。需要真实浏览器验证内嵌 WASM。 | 浏览器独立求解仍需第二套实现。Python 结果回放不能完成编辑后计算。 |
| 制版能力 | FreeSewing 是参数制版库。Teagan 是独立 T 恤设计，不能直接代替导入基准。 | GarmentCode 有服装部件与缝合表达，可作映射参考。仍需逐项保留 golden 几何和未批准值。 |
| 物理能力证据 | 已安装 0.21.0 的声明有 raw particles、surface、edges、dihedrals 和 self contacts。运行能力待探针。 | 官方项目使用 GarmentCode 专用 Warp fork。不能以最新通用 Warp 代替该版本并声称相同结果。 |
| 可维护性 | 一份 revision、一份 mesh mapping 和一套浏览器求解路径。 | 两套运行时、两套参数映射和结果来源需要持续核对。 |
| 当前建议 | 选定，按小探针逐级扩大。 | 保留参考价值。先不引入交付关键路径。 |

Warp 官方文档描述 Python JIT 到 CPU 或 GPU。现有证据没有提供可直接嵌入单 HTML 的 GarmentCode/Warp 浏览器路径。因此，不把 B 的离线回放包装成浏览器重算。

## 最小可靠数据结构

同一个 artifact 保存下面的数据。五个视图读取同一个状态记录，不能各自维护判定。

- `CanonicalSource` 保存原始 YAML、原始字节 SHA-256、解析结果和格式版本。
- `DesignRevision` 保存 source hash、父 revision、显式修改、单位状态、裁片角色、缝边映射、材料状态及人体来源。
- `DerivedPattern` 保存每条曲线的来源 ID、采样误差、二维 rest 坐标、三角化结果及生成器版本。
- `SimulationRun` 保存输入 revision、run ID、模式、引擎版本、参数、帧、停止原因及独立检查结果。
- `Frame` 保存 run ID、revision、step、simulation time 和粒子位置。帧数量或播放时钟不能代替 solver step。

运行模式必须区分 `LIVE_SOLVE`、`REPLAY` 和 `DEMO_ASSUMED`。事实状态至少区分 `KNOWN`、`UNKNOWN` 和 `ASSUMED`。验收判定仍使用项目的 `PASS`、`FAIL`、`BLOCKED`、`SKIP`。`NOT_RUN` 与 `STALE` 是执行状态，不能映射为 PASS。

编辑建立新 revision。正在运行的旧任务可以取消，也可以存入历史。旧任务完成时不能覆盖新 revision。Timeline 中的旧帧仍可查看，但必须显示其原 revision 和 `STALE`。

## Golden 输入必须保留

已核对 `inputs/golden-garment-1.1.yaml` 的 SHA-256 为 `88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e`。

该文件是带完整点位的导入基准。文件要求保留四块裁片二维线形、文字内容和位置、排版位置。Teagan 标准样不是这份基准的重建。

默认视图应呈现 golden 原始几何。FreeSewing 可负责表示、编辑和生成明确命名的新提案。若展示官方 testmodel，必须使用独立 source ID 和 `DEMO_ASSUMED`。切换演示不能更改 golden source hash。演示得到的验收结果不能出现在 golden 的结果栏。

原始 YAML 中的 `null` 表示未确认值。不得通过 `value || 1`、默认尺码、官方 testmodel 或静默单位转换补齐。成衣角色数量与批准裁数不是同一字段。文件明确禁止把前后身、左右袖角色数量当批准裁数。

## 单位未标定时的真实能力

| 能力 | 可以交付的结果 | 禁止的扩大解释 |
| --- | --- | --- |
| 精确二维重建 | U 单位曲线、线段、文字、布局、几何计数与 U 单位测量 | 毫米裁剪图或已批准纸样 |
| 几何检查 | 拓扑、有限数值、方向、映射完整性、同单位的长度比 | 物理尺寸和成衣合体结论 |
| 设计编辑 | 有来源的新 revision、更新几何、旧结果 STALE | 未经声明地改写基准 |
| 数值运行 | 明示归一化比例与材料假设的实验运行 | golden 的实尺度模拟 |
| 应变 | 同一长度单位下，当前三角形相对二维 rest 度量的无量纲伸长 | 使用未声明 U→mm 后算出的伸长或真实应力 |
| 应力与合体 | `UNKNOWN`，并列出缺失参数 | Pa、MPa、压强、舒适度或合体 PASS |

数值实验可以帮助验证引擎接线，但不解除生产条件。比例、裁数、净裁轮廓、材料、人体尺寸和袖山映射尚缺时，golden 物理验收保持 `BLOCKED`。

## 缝合语义和 rest 状态

第一优先是被探针证实的引擎原生连接。`setEdges` 和 `addEdges` 接收粒子索引。当前声明没有暴露 seam rest length setter。若边在分离摆片位置创建，rest length 可能等于初始分离距离。必须读 `edgeRestLength` 验证，不能把存在一条 edge 当缝合成功。

共享粒子索引可以表达已焊接接缝。该结构的零间隙是构造事实，不证明动态缝合、材料应变或接缝强度通过。保留 panel-local 顶点和每个三角角点的二维 rest 坐标，再用映射指向 solver 粒子。接缝两侧可以有不同的二维坐标，不可强制合成一个 rest UV。

每条 seam 保存两侧 panel、edge ID、方向、端点、对位点、采样位置、批准状态和匹配方式。镜像、吃势或袖山前后尚未确认时，映射必须标为假设。不得通过最近点吸附悄悄生成批准映射。

单个三维 rest 形状无法同时保留任意二维裁片度量和缝边共点条件。若使用预装配衣形创建约束，应核对所有结构边的 rest 长度与二维裁片长度。偏差必须报告。不能以三维初始形状重置应变零点来消除坏版型。

## 应力、碰撞和独立检查

Rapier `edgeStress` 的声明定义是载荷相对撕裂阈值的比值，1 表示撕裂。它不是 Pa 或 MPa。`edgeImpulse` 也是求解器边冲量，不能直接标为连续体应力。若没有标定的材料模型、单位、厚度、方向和验证样本，真实应力保持 `UNKNOWN`。

现有 `reference/src/seam-analysis.js` 把二维坐标乘以 `.001`，并输出 MM 和 M2。该文件假设每个粒子只属于一个 panel，并把 seam 中 `a===b` 判为无效。它不能直接检查 U 单位 golden 或共享顶点网格。复用时必须建立显式单位与 panel-local 映射适配，保留原校验器作历史证据。

人体渲染与碰撞必须引用同一份处理后网格、同一坐标变换和同一 revision。保留资产 hash。低模或胶囊碰撞只能作为单独命名的实验，不能冒充同网格检查。

surface 审计必须检查非相邻三角形穿插，并明确排除规则。还需区分人体穿透、衣片自交、退化三角形与真实接触。不要仅用顶点距离或最终一帧外观证明无穿插。旧衣样 FAIL 保留。新引擎新结果独立报告，不继承 PASS。

## 最小交付顺序

1. 核对 golden 哈希和完整二维重建。保持未知值。五视图先共享 revision。
2. 分别跑 raw cloth、平面或球体碰撞、已知 seam 连接及自接触小探针。每项记录引擎和输入 hash。
3. 交付单 HTML 的离线启动、真实 solver step、停止、重置、编辑作废及历史帧回放。
4. 接入人体同网格和独立 audit。报告数值与限制，不要求捏造全物理 PASS。
5. 在基准参数获准后才进行 golden 实尺度装配与物理验收。

求解采用固定 dt。每次调度限制 step 数和耗时，保持停止按钮可用。首次版本可以分批在主线程运行。若实际测量发现阻塞，再移到 Worker。记录粒子数、三角形数、接触选项、dt、substeps、求解耗时和审计耗时。不要把渲染 FPS 当求解速度。不能为追求 FPS 静默关掉自接触。

## 验收方式

机器可读清单见 `design-review.json`。验收者先核对候选 artifact 哈希，再在实际浏览器中重做 G01 至 G12。不是每项都要求物理 PASS。缺输入时，正确的 `BLOCKED` 和完整理由也是可验证的软件行为。

本复核应用了 Model the Domain，将 revision、运行模式和未知值写成显式记录。应用了 Prove It Works，将最终通过条件放到实际 artifact、真实 solver step 和独立审计上。本轮仅做独立设计审查，不扩展子代理树，不改产品源码。

## 证据

- `REPOSITORY-AGENTS.md`，main-only、本地 verify、历史 FAIL。
- `inputs/golden-garment-1.1.yaml`，单位、完整几何、待批准参数和原型定义。
- `node_modules/@dimforge/rapier3d-compat/dist/dynamics/soft_body.d.ts`，已安装 0.21.0 的 API 声明。
- `node_modules/@freesewing/teagan/src/index.mjs`，Teagan 的 back、front、sleeve 设计入口。
- `reference/src/seam-analysis.js`，旧独立应变与 seam 检查的单位和映射前提。
- `reference/benchmarks/collision/surface-audit.mjs`，独立表面检查。
- [Rapier SoftBodyDesc 官方 API](https://www.rapier.rs/javascript3d/classes/SoftBodyDesc.html)。
- [GarmentCode 安装说明](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Installation.md)。
- [GarmentCode 数据生成说明](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Running_data_generation.md)。
- [Warp 官方文档](https://nvidia.github.io/warp/stable/index.html)。
