# 纸样到物理回放：实验台

这里是本次物理实验的代码、条件、运行方法与证据入口。上一级 [实验总入口](../README.md) 集中连接原型、四个设计意图、规格差异、DXF、静态缝合与本目录。

[打开独立物理实验台](https://liush2yuxjtu.github.io/pattern-agent/intent-edit-review/physics/) · [提交的完整记录](results/) · [机制及失败对照](evidence/) · [可复现负例输入](fixtures/)

**运行成功、热图能显示、某个试片通过，都不能替整件衣服签发 PASS。** 本实验分别保存计算机制、初始穿着状态、完整轨迹及真人试穿的结论。历史失败保留；没有实测的数据写明估计或未验证。

## 本轮实际结果

| 检查 | 原型 | 袖口展开宽+10U |
| --- | --- | --- |
| 原二维来源、15条缝、全部633条位置连接 | PASS | PASS |
| 准备末态独立几何 | PASS | PASS |
| 完整逐帧离散验收 | 61/61 PASS | 61/61 PASS |
| 全程最大接缝间隙 / 人体离散穿入 | 0 / 0 mm | 0 / 0 mm |
| 双向人体交叉 / 严格布料自交 | 每帧均0 / 0 | 每帧均0 / 0 |
| 张量、折角、数字穿臂关系 | 每帧均PASS | 每帧均PASS |
| 新进程从0、30、59帧续算六类状态 | 全部逐字节一致 | 全部逐字节一致 |
| 实际binary的机制控制 | 10/10 PASS | 10/10 PASS |
| 全程最大主Green应变 | 185.61% | 138.88% |
| 材料实测 / 真人合身 | NOT_RUN | NOT_RUN |

[完整摘要](results/summary.json)、[原型全部证据](results/baseline/README.md)和[袖口全部证据](results/cuff-width/README.md)保存实际输入、输出、报告及摘要。高应变没有被隐藏或裁掉；Green应变百分数也不是尺寸伸长百分数。本轮通过只针对明确估计条件下的离散几何和计算数学。连续时间无碰撞、实测材料承受能力及真人合身没有获得批准。其他三个设计意图仍是 `PROFILE_REQUIRED`，没有继承这两例的三维结论。

| 本机记录耗时 | 原型 | 袖口加宽 |
| --- | --- | --- |
| 实际顶点 / 三角面 | 4387 / 7186 | 4399 / 7206 |
| 24轮准备 | 126.223秒 | 117.530秒 |
| 60步记录及两次续算证明 | 291.325秒 | 298.037秒 |
| 记录脚本总壁钟时间（含准备门检查） | 430.118秒 | 427.982秒 |

这是本次同机并行运行下的实际壁钟记录，不是独占硬件基准，也不是实时求解帧率。60个1/120秒步对应0.5秒模拟时间；页面播放速度控制保存状态的重放。上表不把网格生成、编译、后续独立审计或浏览器验收算进记录脚本时间。

## 我们实际输入什么

二维改版的最小输入仍是 [完整中文规格 YAML](../../../patterns/fitted-tshirt/input-spec.yaml) 和 [原型 DXF](../../../patterns/fitted-tshirt/input.dxf)。规格包含可独立重建的二维几何，不能以网页摘要代替。

后续设计意图在 [改版基准](../../intent-edit-benchmark/README.md) 中变成新 YAML、规格 diff、几何 patch 与实际输出 DXF，再互相核对。本目录接收这些已经绑定来源的文件，进行三维计算；不把一个漂亮的三维外形反写成已经批准的二维规格。

用户补充的 [领子、袖子原始文件与独立中文 YAML](../../../patterns/fitted-tshirt/components/20261118/README.md) 已另行归档。重复的整件文件按原始字节核对。新旧 M 码表冲突被保留，没有自动用第二张表覆盖第一张表；面料照片也没有被当作拉伸、剪切或弯曲测试。

```mermaid
flowchart LR
  A[原型 DXF + 完整中文 YAML] --> B[自然语言及二维设计意图]
  B --> C[新 YAML + 规格 diff]
  C --> D[坐标 patch + 新 DXF]
  D --> E[二维双向互校]
  E --> F[来源绑定网格及15条缝]
  F --> G[初始穿着状态准备]
  G --> H{独立几何检查}
  H -->|通过| I[实际物理步及保存状态]
  H -->|失败| J[保留失败并停止候选回放]
  I --> K[每帧独立检查及三维回放]
```

这条链沿用 `sew-pattern-to-3d → verify-seaming → verify`。目前严格静态配置支持原型及袖口加宽；袖长、衣长、前领三个输入仍需自己的配置。它们不会继承原型的三维 PASS。

## 七项引擎怎样验证

| 项目 | 真实计算与检查 | 通过不能证明什么 |
| --- | --- | --- |
| 缝合关系 | 原 DXF 与保存网格独立重开；15 条语义缝、方向、二维走缝、全部位置别名、4 个正常开口；漏缝及反向故障对照 | 面料实测、真人合身 |
| 人体碰撞 | 原始 MakeHuman 全部三角面；最近点/法线实际 WASM 对照；射线奇偶性判内外；双方的边穿面检查 | 顶点不入体不代表整张三角面不入体 |
| 应力应变 | 从实际材料坐标重算变形梯度、Green 应变与 Cauchy 应力；经纬拉伸、剪切及刚体试片；浏览器读回实际颜色数组 | 照片成分不能标定模量；颜色正确不代表数值适合生产 |
| 折角 | 有向二面角及曲率；正负折叠、接近180°折返对照；每帧独立重算 | 不预测永久折痕、熨烫或疲劳 |
| 物理回放 | 保存实际坐标、上一时刻坐标、场、接触和时钟；逐帧 seek 不积分；新进程恢复后精确重现下一步 | 播放器可用不代表该轨迹通过几何验收 |
| 物理调试视图 | 实际人体/衣片、网格、接触、15条缝、面片选择、二维 UV、应力/应变/折角、真实导出；桌面、移动端、离线验证 | 截图不是碰撞或力学证明 |
| 布料连接约束 | 原生容量与实际数量核对；全部别名激活；固定点、逆质量与故障注入；不静默遗漏最后一条约束 | 闭合间隙为零不能替代其余检查 |

浏览器中的颜色取自实际保存数组。应力使用 Pa 计算、以 kPa 显示；应变以百分比显示；折角以度显示。二维顶点仍标 U。只有本次明确声明的数值试验把 1 U 当作 1 mm，原规格的单位状态没有因此变成已标定。

## 条件从哪里来

[experiment-config.yaml](experiment-config.yaml) 用中文逐项记录参数、单位、来源与假设。每次生成输入时将其完整复制到该次 `input.json`，因此之后修改默认文件不会篡改旧实验的条件。

| 内容 | 来源与状态 |
| --- | --- |
| 纸样单位 | DXF 未声明；本次假定 1 U = 1 mm，属于实验假设 |
| 人体 | 库内 MakeHuman 标准人体；固定实际位置与全部8000个三角面，非用户扫描 |
| 面料照片 | 1253号40支棉氨纶料；挂牌95.5%棉、4.5%氨纶、155 g/m² |
| 厚度、图面横纵模量、剪切、泊松比 | 为实验估计；没有从成分或克重推导实测力学 |
| 纱向 | 未确认；图面横纵方向不自动等于真实经纬方向 |
| 摩擦与阻尼 | 数值估计，完整写入条件；不能据此预测真实摆动速度 |
| 真人试穿、生产批准 | NOT_RUN |

两张尺码表是成衣参考尺寸，不能拿来代替人体尺寸。照片指向白色也不能证明最终选布、缩水或力学曲线已经批准。

## 一次实验保存什么

以下是运行目录的合同。`work/` 中可保留较大的调试过程；交付时选取精确来源、完整记录、独立报告和复现所需文件。

| 文件 | 用途 |
| --- | --- |
| `input.json` | 完整条件、实际材料 UV、全部面、缝合别名、折角铰链、真实人体数据及原 DXF/YAML 哈希 |
| `solver-capacity.c` / `solver.wasm` | 本次真正编译和运行的核心，不以另一套 Python 模型冒充 |
| `frozen-source/manifest.json` | 本次开始前冻结的实际源码哈希与对应字节 |
| `source-reference.glb` | 只用于从原二维来源独立核对的静态外壳，不是物理计算结果 |
| `source-independent.json` | 独立 CAD/UV/15条缝/拓扑/来源报告，绑定完整本次输入 |
| `preparation-final.bin` | 准备过程结束时的实际 float32 坐标 |
| `preparation-gate.json` | 正式回放之前的独立几何结论；不能只检查原生顶点统计 |
| `preparation-rejected.json` | 准备失败时保留原因和诊断；默认不生成正式轨迹 |
| `trajectory.json` | 若生成，包含每个真实保存状态；失败研究记录明确标为 failure benchmark |
| `resume-independent.json` | 另启 WASM 与 BVH 进程，从保存帧继续，逐字节比较下一帧 |
| `audit.json` | 所有保存帧的独立几何、张量、折角、时钟和来源检查 |
| `index.html` | 内嵌数据和渲染脚本的单文件查看器；保存后能离线回放 |

正常记录为60个固定的1/120秒步，加初始状态共61帧。准备迭代不是物理回放时间；不将120次准备伪装成正式的1秒运动。

浏览器重放保存状态，未在浏览器中重新求解物理。新进程续算的证明来自原生WASM命令，不把播放器的“播放”按钮写成实时模拟。页面可以切换原型与袖口加宽，读取完整中文规格、原二维图、实际三维帧及热图；袖口案例另外下载规格差异和DXF改版补丁。

三维优先使用WebGL2；浏览器禁用它时，自动使用同一scene、camera、全部实际网格和保存帧进行SVG软件投影，仍能旋转、缩放、切帧和查看字段。界面标示“CPU三维”，不会伪造GPU统计或替换成静态图。软件路径只在画面状态变化时重画；二维、全文规格及原文件功能始终可以初始化。

两条绘制路径分别验收。WebGL界面每例11组通过；强制禁用WebGL时，两案例的全部61帧、五类实际数组、字段、相机、二维及全文下载同样通过。另从实际WebGL2绘制后的颜色VBO读回36组数据，与原记录独立计算的颜色比较，最大误差1.493e-7，小于2e-6。该测试使用SwiftShader软件GL，不认证硬件GPU性能；它与仅比较CPU颜色属性的早期检查分开保存。

`results/` 中的输入与轨迹采用无损gzip，不减少帧、不四舍五入坐标。每个包保存原DXF/中文YAML、实际条件、生成C、实际WASM、来源壳、准备末态、完整独立报告及源码快照。`frozen-source/` 是计算前的来源记录；`frozen-verifier/` 保存验收程序的具体版本，方便在仓库副本中恢复原检查。

折角图报告真实邻面二面角，包括自由接缝。配置中的120°是有限迭代的试验约束参数，不是全网格折角永远小于120°的认证。高应变和应力数值保留原值；缺少实测材料极限时不把数值计算通过解释为面料耐受通过。

`--record-rejected-preparation` 只供保留负例。它不会改变准备结论，也不会让完整轨迹获得 PASS。仅抽查若干帧的报告仍为 FAIL：其余帧尚未验证。

## 数值方法及已发现的问题

### 材料坐标与网格

每片保持原二维材料坐标，边界按共同弧长参数同步采样。材料坐标为减少 float32 消差按片平移，原点另外保存；它能还原原 CAD 坐标，未改变纸样尺寸。物理网格使用 Triangle，单层缝合别名共享位置；缝份叠层、隐藏领条内层与缝线转动刚度未标定。

初始化的 [UV-FEM 混合方法](initial_placement.py) 使用原二维材料度量重求内部定位。衣身解 XYZ，袖子解原管面的 `(u, θ)` 后再映射，领条保持。固定边界只表示这一种子的构造约束；真实准备过程仍允许边界按原缝合组一起移动。

初始化不能被当成已经穿好的衣服。独立分析发现，旧固定边界自身就有入体点，仅优化内部顶点在数学上无法消除它们。本目录的初始状态必须另过实际人体与严格自交检查。

[手臂定位](arm_placement.py) 进一步使用与碰撞人体相同原始 OBJ 的骨架 helper，把袖管搬到实际肩—肘—腕路径。它保留袖窿连接和非袖位置，不改变人体、UV或原参考壳。不能直接使用另一个叠加女性宏形体的 human.json 顶点作该标准人体的坐标；复用的是同源 helper 索引，变换及36.9微米的预处理差异写在 [关节来源记录](proxy-arm-joints.json) 中。

独立穿臂诊断区分“从袖窿进入并连续覆盖肘腕”和“从真实袖面穿出”。肩关节位于袖窿的躯干侧可以合理，不能机械要求整条骨链的每点都在虚拟封闭袖管内。这仍不是实测合身批准。

### 膜能量

材料能量仍采用声明的正交各向异性 StVK。旧的逐分量线性投影在接近压扁的真实袖片上严重过冲。单约束缩步修复虽然降低了本分量残差，却不能保证其余分量及共享邻面的能量下降，因此没有把该项 PASS 写成整步稳定。

[全局隐式膜更新](implicit-membrane.c) 对同一材料能量与质量惯性目标做 L-BFGS 和实际 float32 坐标的 Armijo 线搜索。预测位置、质量、材料与步长均独立核对；外部接触/折角投影改变状态时清除优化历史，预测目标不重置。

这个下降保证只覆盖膜更新。人体、布料接触及折角修正单独检查，不能把它们默认为同一个已证明收敛的能量最小化器。

### 接触

[MeshContact](mesh-contact.mjs) 在每一轮使用同一不可变坐标快照收集 VF/EE 修正，按顶点聚合后限幅，再一次应用及 refit。避免查询树仍在旧位置、点却已连续移动造成的约束累积过冲。每轮限幅与多轮累计位移分开记录。

原始 typed-array 索引曾导致 BVH 实际遍历零个三角面。适配器现在要求真正的 BufferAttribute，并实际遍历所有面；仅构造树成功不算通过。

默认只排除实际 primitive 共用顶点/端点。旧的一整圈排除会屏蔽真实折回接触，不能用于独立验收。显式 legacy 自定义排除只留作兼容控制，不在本次实际碰撞响应中启用。

[扫掠边模块](swept-edge.mjs) 与[扫掠点面模块](swept-vertex.mjs) 检查线性运动区间中的有限线段或三角面距离；终点已分开不能排除中途穿越。浮点保守推进保留 `contact`、`conservative`、`uncertain`，预算或精度耗尽不能静默视为无碰撞。旧VF移动平面近似曾产生实际距离7–8mm的误报，现已替换。这不是精确区间算术或通用严格 CCD 认证。

[真实人体面特征](body-feature-contact.c) 由双方实际边面交点生成约束，不能再仅增加固定采样点。历史侧只有在整片上一状态真实可行时才优先；四个候选方向的局部支持代价还用实际人体 BVH 出口射线校正。每轮按真实写回的float32位移累计限幅，不钳遥测冒充限幅成功。该组件的解析及局部对照通过，并不保证整个非凸衣服迭代一定收敛。

[triangle-contact.mjs](triangle-contact.mjs) 是另存的真实布料三角面交错研究模块，**尚未集成实际响应**。局部解析/六点对照可消穿，完整网格的朴素恢复却产生新相交；与旧VF/EE直接叠加也存在方向冲突。这些失败保留，不能拿其单项测试PASS来替代整衣验收。

[离散状态保护](self_step_guard.mjs) 通过 `--self-step-guard` 显式启用。在原生步、每轮接触及末次人体修正后，对全部实际float32三角面检查自交和退化；若候选不合法，沿上一合法状态缩步，保留全部顶点、面及位置别名。人体检查仍独立执行。该方法不修复已自交的参考，也不证明两帧之间连续无碰撞。任一phase非零提议却因回退而无实际存储进度，正式物理步即拒绝；准备阶段的尝试另行记录。正常接触平衡可以保持位置不变，不能因此误判。保护回退位移与接触单轮限幅分别记录。

对8000面人体的有限点采样同样不能证明整张衣片不穿体。正式检查另外执行 cloth-edge→body-face 和 body-edge→cloth-face 两方向的实际穿越检测。

### 回放与独立检查

[audit_experiment.py](audit_experiment.py) 不导入 C 求解器或 JS 接触响应；从保存坐标独立重算。严格三角面检查包含 incident faces，接触响应中的排除回调不能进入验收。

[verify_resume.py](verify_resume.py) 另起进程恢复保存状态。坐标、上一时刻坐标、张量场、接触标志和时钟全部要求精确一致。单文件查看器的 seek 则只读取保存数组，不进行积分。两者是不同的检查。

## 不变的验收门槛

- 最大接缝间隙不超过2 mm。
- 独立离散人体穿入不超过0.2 mm，且**两个方向的边面穿越均为0**。
- 全部衣片三角面的严格穿插为0，几何容差1 µm；不丢弃坏面、不隐藏局部片、不用接触排除掩盖失败。
- 一个连通组件、4个预期开口；无非流形边、冲突绕向、重复面、孤点或退化面。
- 实际材料张量与独立 float64 复算一致；GPU颜色误差不超过2e-6。
- 每帧折角/曲率独立一致，所有61帧及时钟完整，真实保存状态能在新进程继续。
- 原人体、原 DXF、原 YAML、实际输入、实际可执行文件及报告哈希完整绑定。

高应变单独显示；它不会因为几何检查通过而成为舒适、合身或材料安全批准。旧T恤的7.6455 mm缝隙及20处穿插历史 FAIL 也没有被覆盖。

## 本机复现

从仓库根运行，使用 Python 3.12、Node、现有 Chromium。页面本身不依赖 Python、Node 或联网。

```sh
python -m venv work/intent-physics/venv
work/intent-physics/venv/bin/pip install -r experiments/intent-edit-review/physics/requirements.txt
npm ci --ignore-scripts --prefix experiments/freesewing_cloth_lab
```

`ziglang` 包内的 `zig` 是已经验证的0.14.1编译器。把以下 `ZIG` 替换为该虚拟环境内的绝对路径，另给运行目录一个新名字，不覆盖旧实验。

```sh
work/intent-physics/venv/bin/python experiments/intent-edit-review/physics/prepare_experiment.py \
  --case baseline --preparation-iterations 24 --self-step-guard \
  --output work/intent-physics/MY-RUN --zig /absolute/path/to/zig
work/intent-physics/venv/bin/python experiments/intent-edit-review/physics/verify_source_mesh.py \
  work/intent-physics/MY-RUN
work/intent-physics/venv/bin/python experiments/intent-edit-review/physics/freeze_sources.py \
  work/intent-physics/MY-RUN
PHYSICS_PYTHON=/absolute/path/to/venv/bin/python \
  node experiments/intent-edit-review/physics/run_native.mjs work/intent-physics/MY-RUN
```

若初始几何门失败，先阅读 `preparation-gate.json`，修复对应原因并用新目录重跑。不要修改报告或打开负例记录选项来代替通过。

有完整实际记录时，再执行：

```sh
node experiments/intent-edit-review/physics/derive_folds.mjs work/intent-physics/MY-RUN
work/intent-physics/venv/bin/python experiments/intent-edit-review/physics/verify_resume.py work/intent-physics/MY-RUN
work/intent-physics/venv/bin/python experiments/intent-edit-review/physics/audit_experiment.py \
  work/intent-physics/MY-RUN --workers 2 --output work/intent-physics/MY-RUN/audit.json
```

`--frames 0,60` 只供诊断，不产生全轨迹 PASS。其他严格缝合配置未支持的案例会停在来源检查，而不是偷用原型模型。

### 核心控制与查看器

```sh
work/intent-physics/venv/bin/python experiments/intent-edit-review/physics/test_physics_kernel.py \
  work/intent-physics/MY-RUN --output work/intent-physics/kernel.json
work/intent-physics/venv/bin/python experiments/intent-edit-review/physics/test_implicit_membrane.py --help
node experiments/intent-edit-review/physics/test_hinges.mjs work/intent-physics/MY-RUN/solver.wasm
node experiments/intent-edit-review/physics/test_mesh_contact.mjs
node experiments/intent-edit-review/physics/test_swept_edge.mjs
node experiments/intent-edit-review/physics/test_swept_vertex.mjs
node experiments/intent-edit-review/physics/test_self_step_guard.mjs
node experiments/intent-edit-review/physics/test_runtime_acceptance.mjs
node experiments/intent-edit-review/physics/test_contact.mjs
node experiments/intent-edit-review/physics/test_swept_bounds.mjs
```

独立试片、刚体、质量/步长、固定点、容量、漏约束、穿体及伪造字段都需要故障对照。浏览器验证需覆盖每一帧、真实GPU颜色、15条缝、点击面片、导出后重开、递归离线保存及390px布局；原生 `file://` 被环境策略拦截时单独记 BLOCKED，不更改策略。实际下载的HTML字节仍用断网上下文验证，不能把该测试写成原生文件协议已通过。

实际网格自交控制可用已提交负例，不依赖临时工作目录：

```sh
SELF_GUARD_REAL_FIXTURE=experiments/intent-edit-review/physics/fixtures/self-contact-negative \
  node experiments/intent-edit-review/physics/test_self_step_guard.mjs
python experiments/intent-edit-review/physics/verify_controls.py work/intent-physics/MY-RUN \
  --body-fixture experiments/intent-edit-review/physics/fixtures/body-contact-negative \
  --output work/intent-physics/MY-RUN/controls
```

人体负例是明确标记的稀疏单帧见证，不是完整物理轨迹；自交负例是明确失败的准备末态。两者不会出现在通过的回放里冒充合格衣服。每次独立完整审计仍要求全部61帧。并发五个未分批的大射线检查曾触发16GB内存限制，没有产生PASS；复核时应限制总并发，保留失败日志后完成全量重试。

[bounded_queries.py](bounded_queries.py) 另行提供每批最多512条底层射线的内存有界组件。14项解析控制及两个真实案例的0、30、60帧共6项对照通过；原内外布尔数组、双向交叉计数、射线方向和随机回退状态精确一致。它主要控制内存，不宣称提速。**本轮两套权威61帧报告仍使用原独立检查器，两worker、逐案例完成；该可选组件没有替换它们。**

最终页面的独立绘制检查：

```sh
python experiments/intent-edit-review/physics/verify_svg_fallback.py \
  --html web/intent-edit-review/physics/index.html \
  --run work/intent-physics/MY-BASELINE --run work/intent-physics/MY-CUFF \
  --output work/intent-physics/svg-review
python experiments/intent-edit-review/physics/verify_gpu_buffers.py \
  --expected-html-sha256 80ccaf68114ad1d650ccfec248c812cc77d31ab5c9383e56d4904f18f617c872 \
  --run work/intent-physics/MY-BASELINE --run work/intent-physics/MY-CUFF \
  --output work/intent-physics/actual-gl-review
```

上面的摘要对应本轮交付；重建新页面应使用独立冻结的新摘要。原生公开HTTPS导航如遇环境证书限制，保留BLOCKED及错误证据，不关闭证书校验。实际发布字节单独核对，公开页面再用可用浏览器操作检查。

构建和发布只走仓库现有的本地 `/verify`、直接提交 main、非强制 push 与既有 Pages 发布。新实验放在独立路径，不覆盖无关旧页面；发布成功也不能代替实际公开网页的再次检查。
