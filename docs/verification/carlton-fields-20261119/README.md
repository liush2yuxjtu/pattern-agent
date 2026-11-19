# Carlton 试穿字段验收

候选基线 `75784dcf717506ca9f4f059b4421296bdeccc601`。此次验收覆盖 `web/carlton-workbench/`。原有缝合、2D 滑块与 3D 求解在同页联动，新增应变、应力、试穿压力和正交正面线稿对照。

## 本地结果

- Rust 六项测试通过。用发布的 WASM 在两种网格密度上跑平面载荷 480 步，理论压力与实测数值分别为 3.924 Pa 与 3.924018 Pa。分离和关闭碰撞负对照的反力均为零。
- 按 `source/README.md` 用 npm 锁文件和 wasm32 Rust 工具链重建。编辑器 SHA-256 为 `6c373a84912593457b44e53cb431e1be11b6ae9dc8595445598d2e6658e5ab45`，逐字节一致。
- Playwright 以 HTTP 在 `/pattern-agent/carlton-workbench/` 前缀运行。基准、改胸围、改衣长、恢复基准均执行 480 次 GPU 预测与 Rust/WASM 约束求解。独立比对修改后的 SVG、平面形状、装配网格和最终结果，恢复后与基准一致。
- 基准和加长版的三张热图各有不同的实际绘制像素。输入修改时旧热图清除，完成后恢复。正面线稿加载 1000 像素原图，3D 固定为正交正面。18 张报告内嵌图、真实 SVG 和压缩数据下载均通过。390 px 无 WebGPU 时仍可改缝份和生成 2D。
- 复测命令为 `node web/carlton-workbench/verify.mjs http://127.0.0.1:45288/pattern-agent/carlton-workbench/`。完整浏览器回读见 [browser.json](browser.json)。

## CLO_RUST 独立复算

在 `clo-rust` 私人快照 `bx_q8qcjfhk` 的 Linux x86_64 / Rust 1.97.1 环境运行快照验收及四组合计 23,056 个三角面的复算。每组精确设置重新出样，20 款裁片写入原生工程后重开。外层严格连通检查为单组件。核对浏览器主应变与原生 VTK、独立 Cauchy 应力特征值、逐顶点压力、反力总和、后省和口袋最大间距。[native.json](native.json)

网络传输后核对了报告和结果包的 SHA-256，独立验证器从取回的压缩包重放，同样通过。最初应变比对曾把单精度 GLB 的毫米舍入当成 WASM 数组误差。最终分别对原始米制数组和 GLB 的毫米制数组做复算，并核对了两者的单位转换。

应力和压力依赖示例材料模型。个别极小三角面存在应力数值尖峰，保留于原始字段。真实面料标定、舒适性和量产合体为 NOT_RUN。
