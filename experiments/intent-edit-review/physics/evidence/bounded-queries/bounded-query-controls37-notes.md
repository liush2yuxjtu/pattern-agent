这份有界查询组件未用于本轮权威61帧审计。权威结果仍来自原 audit_experiment.py：baseline原两worker审计及cuff原完整61帧审计。当前audit源码未因本任务修改。

独立查询等价控制：PASS；14项解析控制，以及baseline/cuff各frame0、30、60共6帧。inside布尔数组逐元素一致；双向真实segment hit计数一致；原射线方向与随机回退/RNG语义保持；每个底层backend查询最多512条射线，无跳样。

现场真实帧查询累计耗时：原查询66.916s；分批查询79.180s。分批略慢，不宣称加速。计时为共享现场、原查询在先/分批在后的顺序控制，不是独立CPU吞吐基准。
整个顺序单进程累计RSS高水位4034328 KiB（约3.847 GiB）；它包含原大查询，不是分批查询的单独峰值。接口的工作集上界由实际max_backend_rays<=512控制及记录。

| Case | Frame | 实际点数 | inside错位 | 正/反hits旧=新 |
|---|---:|---:|---:|---|
| baseline-run37 | 0 | 21882 | 0 | 0/0 |
| cuff-run37 | 0 | 21946 | 0 | 0/0 |
| baseline-run37 | 30 | 21882 | 0 | 0/0 |
| cuff-run37 | 30 | 21946 | 0 | 0/0 |
| baseline-run37 | 60 | 21882 | 0 | 0/0 |
| cuff-run37 | 60 | 21946 | 0 | 0/0 |

源与记录绑定、逐查询耗时/内存、inside-mask摘要及backend批次统计见 bounded-query-controls37.json。该组件控制PASS不替代原61帧几何/材料/真人fit验收。
