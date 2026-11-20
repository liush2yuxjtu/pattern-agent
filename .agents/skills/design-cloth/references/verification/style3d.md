# Style3D MCP 与原生 API 操作约定

- **发现和执行。** 在 `mcp__style3d` 用 `GetApiList` 查实际注册的方法，再用 `GetApiSchemas` 核对输入、输出和前置条件。`CallApi` 以 `method` 和 `data` 执行原生 JSON 方法。只查工具时停在目录和 schema。注册状态、项目可用性以及 Fitting、导出等权限分别核对。
- **固定候选。** 记录工程版次、Style3D 版本、尺码、人台、姿势、闭合、面料和当前模拟状态。快照和拟合图需要停止模拟与录制。按片读取时保持工程状态不变，分开的调用没有共同求解帧 ID。原生对象 ID 是十进制字符串，换项目、撤销或改拓扑后重新获取。
- **校验拟合图。** 第一次或网格变化后传 `includeMesh: true`。查 `valid`、`status`、`error`、`unit` 及顶点与数值数量，保存 `source` 和指纹。只有匹配 `meshFingerprint` 才复用几何。失败的空数组记待验证。裁片 API 按主裁片覆盖，核对对称副片和特殊构件是否需要补证。
- **采图与读数。** 原生图的数值取自 `Simulation.Get…Map`，也可把有效原始值映射到匹配网格生成有单位的图。`View.SetFittingCheckState` 只改动作勾选状态，采原生画面时需要实际核实图层与色标。对照视图固定尺码、姿势、闭合、相机与比较口径。

按 [验证方法索引](index.md) 进入对应手册。这些步骤依据 MCP 注册目录和 schema，执行前以当前版本返回的定义为准。
