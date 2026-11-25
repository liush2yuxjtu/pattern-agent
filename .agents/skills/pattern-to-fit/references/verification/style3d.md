# Style3D MCP 与原生 API 操作约定

- **发现和执行。** 在 `mcp__style3d` 用 `GetApiList` 查实际注册的方法，再用 `GetApiSchemas` 核对输入、输出和前置条件。`CallApi` 以 `method` 和 `data` 执行原生 JSON 方法。只查工具时停在目录和 schema。注册状态、项目可用性以及 Fitting、导出等权限分别核对。
- **固定候选。** 记录工程版次、Style3D 版本、尺码、人台、姿势、闭合、面料和当前模拟状态。快照和拟合图需要停止模拟与录制。按片读取时保持工程状态不变，分开的调用没有共同求解帧 ID。原生对象 ID 是十进制字符串，换项目、撤销或改拓扑后重新获取。
- **校验拟合图。** 第一次或网格变化后传 `includeMesh: true`。核对 `valid`、`status`、`error`、`unit`，保存 `source` 和指纹。`values` 长度应等于 `vertexCount`；返回 `actualValueCount` 时也须相符。原始采样数不符时保留原始响应并记待验证，即使状态是 `ok`、返回数组恰好与网格等长。只有匹配 `meshFingerprint` 才复用几何。裁片 API 按主裁片覆盖，核对对称副片和特殊构件是否需要补证。
- **采图与读数。** 原生图的数值取自 `Simulation.Get…Map`，也可把有效原始值映射到匹配网格生成有单位的图。`View.SetFittingCheckState` 只改动作勾选状态，采原生画面时需要实际核实图层与色标。对照视图固定尺码、姿势、闭合、相机与比较口径。

按 [验证方法索引](index.md) 进入对应手册。这些步骤依据 MCP 注册目录和 schema，执行前以当前版本返回的定义为准。

## 本地批量取证

在技能目录用 Python 3 运行 [style3d-audit.py](../../scripts/style3d-audit.py)。脚本通过本机 Style3D MCP 读取当前已打开且停止模拟的工程，按尺码、姿势和版次分目录保存。只复查压力时选择 `--section pressure`；只复查缝合时选择 `--section seams`。`--section fit` 采集应力、应变、布侧及人体侧压力。默认采集 `fit` 和 `seams`。可用 `--expected-project` 防止读错当前工程。

```sh
python3 scripts/style3d-audit.py ./work/standing-pressure --section pressure --expected-project '当前工程名' --case 'M 码 自然站姿 复验版'
```

先读 `summary.json` 的问题列表，再按需打开原始数据。退出码 2 表示存在待复核项；`requests.jsonl` 记录逐次请求与结果。脚本采集的是数值、网格和缝合记录。做正式验收时继续按各手册采集原生外观图、核对设计参考、运行碰撞查询并作出逐项判定。

## 连续动作取证

已有静态试穿或原生动作时，可用[动作取证模板](style3d-motion.md)自动采样截图、布料与人体表面交叉及应变统计。它也支持在已正确穿着的工作副本上录制指定姿势过渡。
