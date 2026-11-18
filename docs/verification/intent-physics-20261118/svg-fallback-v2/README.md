# 无WebGL时仍可使用的物理实验台

候选基线a351a52；最终HTML SHA-256：
`80ccaf68114ad1d650ccfec248c812cc77d31ab5c9383e56d4904f18f617c872`，46,107,845字节。

首次公开实测的云浏览器关闭了WebGL，旧571版本在初始化时抛错，连二维与完整规格也无法使用。保留了[原始截图](webgl-disabled-before.jpg)及[错误记录](webgl-disabled-before.json)。没有调整浏览器安全设置或禁用证书校验。

修复优先使用WebGL2；失败时以同一scene、camera、全部实际网格和保存帧进行SVG软件三维绘制。它提供较简化的分面光照和遮挡，仍可旋转、缩放、切帧、查看字段；不替换成固定图片或其他模型。二维与完整YAML照常初始化。GPU统计在软件路径为null，另报实际SVG面数，不伪造硬件信息。静止时不反复重画；SVG显隐以真实hidden属性控制。

| 验收 | 结果 | 原始证据 |
| --- | --- | --- |
| 当前源码WebGL：两个案例、完整文件、61帧、导出及离线 | 每例11/11 PASS | [原型](webgl/baseline/receipt.json)、[袖口](webgl/cuff-width/receipt.json) |
| 强制无WebGL：两案例全部61帧及五类f32数组、视角/字段/选面/文件/手机 | PASS | [完整SVG](svg/receipt.json) |
| 最终字节与当前bundle/CSS/template完全对应，全部录制数组不变；最终SVG端点和文件功能 | PASS | [最终SVG](final-svg/receipt.json) |
| 实际GL绘制后color VBO读回，对比原记录独立颜色 | 36/36 PASS，最大误差1.493e-7 ≤ 2e-6 | [GL收据](actual-gl/receipt.json) |
| 旧571→新80cc数学载荷、610数组、265归档及原模型Git字节 | 全部不变 | [不变性](data-invariance/report.json) |
| 更新文档的实际浏览器检查 | 37锚点PASS | 项目原日志与源码 |

早期颜色界面检查读取的是CPU BufferAttribute；本轮另加真实WebGL2 getBufferSubData读回，原检查没有被冒充为GPU读回。探针只观察真实draw后当前program的颜色VBO，验证连续FLOAT3布局、还原ARRAY_BUFFER绑定并等待新draw；保存36份原始f32及12张真实场截图。使用SwiftShader软件GL，不认证硬件GPU性能。

[候选及源码摘要](candidate.json)绑定本次版本。原型/袖口各61/61帧的独立物理数学报告沿用原始版本，没有重新模拟、裁掉坏帧或调整门槛。原型峰值Green应变185.61%，面料标定和真人合身仍NOT_RUN，另三例PROFILE_REQUIRED仍BLOCKED。

公开发布及实际页面操作均已完成，详见[线上验收、六份真实下载与截图](live-public/README.md)。公开HTML与本地最终摘要一致，云浏览器在禁用WebGL条件下实际完成三维、字段、回放、二维和完整YAML操作。此结论由页面实测及文件读回支持，未从发布状态推断。
