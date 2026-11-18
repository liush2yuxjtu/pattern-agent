# Brian 原生人体尺寸输入

[在线工具](https://liush2yuxjtu.github.io/pattern-agent/freesewing/brian/) ·
[机器可读输入规则](../../web/freesewing/brian/input-contract.json) ·
[单文件 HTML](../../web/freesewing/brian/index.html)

本页的输入契约来自原始 `@freesewing/brian@4.10.2`，不是重写的制版算法。

| 规则 | 实现 |
| --- | --- |
| 字段及顺序 | 直接读取 `Brian.patternConfig.measurements` 和 `optionalMeasurements` |
| 必填 | biceps、chest、hpsToBust、hpsToWaistBack、neck、shoulderToShoulder、shoulderSlope、waistToArmpit、waistToHips、shoulderToWrist、wrist |
| 选填 | highBust |
| 单位 | 长度原生 mm；肩斜原生度，单位类型来自 `@freesewing/config` |
| 精度 | 数字直接传入；不转换为厘米、不取整、不截断小数 |
| 人体数值边界 | Brian 的配置没有定义 min/max，本页数值框也不添加人体上下限 |
| 滑条 | 只有显示窗口；直接输入窗口外数值时自动扩展，不拒绝或夹取数值 |
| 初始人体尺寸 | 明确标注的演示数据；不是 Brian 的标准身材或默认身材 |
| 缺失尺寸 | 根据原库 required 声明提示；不拿示例值补齐，不下载失效纸样 |
| highBust | 提供此数值不会自动启用 `draftForHighBust` |
| 按上胸围制版 | 独立映射 `options.draftForHighBust`；缺少 highBust 时保留原库回退行为 |
| 设计默认值 | 全部由 Brian 加载，胸围松量是官方默认 15% |
| 整体大小参数 | 已移除；它不是 Brian 的原生人体字段 |
| 下载输入 | 实际传入 Brian 的完整 JSON，保留毫米、小数及显式选项 |

Brian 没有为人体尺寸提供自动填值，也没有在 SDK 中替调用者检查所有缺失值。
例如缺失胸围可能生成 NaN 而没有错误日志。因此界面根据原库的 required 声明
检查就绪状态，并在原生结果含非有限数值时阻止导出。这个界面检查与 Brian 原库
的实际行为分别测试，不将原库未报错解释为有效纸样。

`draftBrian(input)` 直接执行 `new Brian(input).use(pluginTheme).draft().render()`，
不改写输入、不钳制选项、不删除额外字段。制版后才由独立的 `present()` 安排
左右顺序和两条参考线。展示颜色、排版和辅助线不改变原版裁片路径。
Brian 本身不按腰围收腰；本工具不提供工厂放码表、布料仿真或实物合体结论。

## 复现与验证

需要 Node 24+：

```sh
cd tools/freesewing-brian
npm ci
npm run build
npm test
```

构建输出是 `web/freesewing/brian/index.html` 和自动生成的 `input-contract.json`。
HTML 内嵌引擎、样式和许可，离线直接打开。JSON 是给编码 Agent 的可重用输入。

`upstream-manifest.json` 绑定 npm 原包全部十个文件。独立对照直接调用原始 Brian，
检查 47 组输入、141 片裁片、13,066 个坐标以及原生 SVG 的逐字一致；坐标容差为零。
原先的 22 项成人范围端点检查保留为回归向量，并加入旧范围外人体、小数、缺失、
上胸围两种设置、额外原生字段和显式选项。数字范围不再被当作人体合法性规则。

软件对照、界面就绪检查和真实浏览器验收分别记录。历史版本的 10% 演示结果
保存在原归档中，当前版本使用官方默认值。

[本次输入契约记录](../../docs/verification/freesewing-brian-input-contract-20261118/README.md) ·
[历史发布记录](../../docs/verification/freesewing-brian-20261118/README.md)
