# 来源绑定物理实验：验收记录

候选工作目录：`experiments/intent-edit-review/physics/`；
[统一实验入口](../../../experiments/intent-edit-review/README.md)；
[代码、参数和复现方法](../../../experiments/intent-edit-review/physics/README.md)。

本轮使用真实保存的 WASM 计算状态、原始二维规格及 DXF。单位、人体和材料
采用明确声明的研究假设，材料标定与真人合身均为 **NOT_RUN**。

候选基线：`2724fe6`，工作分支main；最终单文件HTML摘要
`571fd1460f037ba1d498cc8147f175d7508ce9f484616834d579ec141163ac05`，
46,088,590字节。完整代码及构建来源另见 `candidate.json`。

## 数值验收

| 边界 | 原型 | 袖口展开宽+10U |
| --- | --- | --- |
| 原DXF/中文YAML、15条语义缝及633条位置连接 | PASS | PASS |
| 准备状态：人体、严格自交、穿袖及拓扑 | PASS | PASS |
| 全部保存状态 | 61/61 PASS | 61/61 PASS |
| 最大接缝间隙、人体离散穿入 | 0mm、0mm | 0mm、0mm |
| 两方向人体交叉及严格布料自交 | 每帧均0 | 每帧均0 |
| 独立张量、折角、穿袖及正常开口 | 每帧PASS | 每帧PASS |
| 新进程恢复0、30、59帧后继续 | 六类状态逐字节一致 | 六类状态逐字节一致 |
| 实际WASM机制控制 | 10/10 PASS | 10/10 PASS |

完整报告、实际二进制、全部帧和来源快照：
[原型](../../../experiments/intent-edit-review/physics/results/baseline/README.md) ·
[袖口加宽](../../../experiments/intent-edit-review/physics/results/cuff-width/README.md) ·
[机器可复核摘要](../../../experiments/intent-edit-review/physics/results/summary.json)。

原型全程最大主Green应变185.61%（第29帧），袖口案例138.88%。数字原样保留；
没有用几何PASS替代面料承受能力。连续时间无碰撞、实测材料、真人合身均未批准。
另三例仍为 `PROFILE_REQUIRED`，没有借用这两例的结果。

## 实际命令与复现

从仓库根、Python3.12虚拟环境执行，完整命令见
[项目README](../../../experiments/intent-edit-review/physics/README.md)及归档收据。
本轮每例采用24轮准备、60个1/120秒真实步、离散自交保护；新进程续算后才做全帧审计。

```sh
python experiments/intent-edit-review/physics/prepare_experiment.py --case baseline \
  --preparation-iterations 24 --self-step-guard --output work/intent-physics/MY-RUN --zig /absolute/path/to/zig
python experiments/intent-edit-review/physics/verify_source_mesh.py work/intent-physics/MY-RUN
python experiments/intent-edit-review/physics/freeze_sources.py work/intent-physics/MY-RUN
PHYSICS_PYTHON=/absolute/path/to/python \
  node experiments/intent-edit-review/physics/run_native.mjs work/intent-physics/MY-RUN
node experiments/intent-edit-review/physics/derive_folds.mjs work/intent-physics/MY-RUN
python experiments/intent-edit-review/physics/verify_resume.py work/intent-physics/MY-RUN
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python experiments/intent-edit-review/physics/audit_experiment.py work/intent-physics/MY-RUN \
  --workers 2 --output work/intent-physics/MY-RUN/audit.json
```

对应袖口案例参数为 `--case 03_cuff_width`。轨迹gzip完全无损，压缩与原始摘要均在各包
`artifact-manifest.json`；不是只保留截图或统计摘要。`frozen-verifier/` 保存实际验收版本，
`frozen-source/` 保存计算前的来源；当前程序和历史快照分开审阅。

两例记录脚本总壁钟约430.12秒、427.98秒，含准备及准备门检查；
它不是独占硬件性能、完整端到端耗时或实时模拟帧率。详细分项见项目README。

## 保留的负例和回归

- 旧33准备末态人体为0但布料自交6，保持FAIL。全网格单次回退虽可去自交，
  却重新产生人体穿插，仍FAIL；没有把它放进通过轨迹。
- 自交保护有15组、18个独立断言；验收策略另测“一阶段拒绝不能被后续位移掩盖”
  和“正常接触静止不能被误拒”，均针对真实函数。
- 人体接触稀疏负例保存原27第60帧精确字节；它不是61帧回放。两实际binary的便携负例复测均PASS。
- 袖子初始化5项、穿袖8项及5组读回通过；人体原几何、原UV、袖窿和非袖位置保持合同。
- 同时5个大射线worker触发16GB限制，未产生PASS；权威结果改为每例2worker，完整重试61帧。
  可选分批查询另做14项解析、6真实帧的逐点和双向交叉等价控制；略慢，不宣称加速，
  也没有替换本轮权威报告。
- 默认服务27项回归通过，默认原型/袖口静态GLB摘要仍匹配旧交付；旧comparison/sewn共40文件不变。

[负例及回归证据](../../../experiments/intent-edit-review/physics/evidence/)保留原始失败与解释。

## 页面与发布

页面是可操作实验台：两个案例、完整中文YAML、真实204条二维图元及27条文字、
应力/应变/折角/接触/接缝、真实面片选择、61帧、原文件下载和保存HTML重开。
播放器读取真实保存状态，未把动画当成重新积分。

双案例候选的每例11组真实浏览器检查均PASS：逐帧全数组、GPU颜色、15条缝、
输入及输出文件精确字节、JSON/OBJ重开、递归离线及390px手机操作。
最终收据版同样完成每例11/11检查，均PASS，绑定上方同一最终HTML摘要：
[原型收据](local-browser/baseline/receipt.json) · [袖口收据](local-browser/cuff-width/receipt.json) ·
[本地总收据与源码摘要](candidate.json) · [最终导航与视觉复核](navigation/report.json)。
一次固定100ms的渲染统计读取过早导致失败，原日志保留；改为等待实际渲染计数达到
同一个严格期望值后，原型全部11组重试通过，未改几何或颜色门槛。
原生file导航受环境策略限制，记BLOCKED；实际下载字节的断网重开通过，不改安全策略。

公开发布只使用既有Pages工作流作发布，本地 `/verify` 是验收依据。线上字节和真实浏览器
回归在发布后补存，不把发布成功当成应用通过。

历史T恤 FAIL（7.6455mm接缝间隙、20处穿插）继续保留。新页面使用独立
`/intent-edit-review/physics/` 路径，不覆盖旧对照页或静态缝合页。
