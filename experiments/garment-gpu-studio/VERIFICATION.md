# Garment Lab 验证报告

**当前交付：PASS。** 已完成单文件离线 HTML、20 个分功能 JavaScript 模块、WASM f64 诊断内核、实际 WebGPU 预测和 CPU XPBD 碰撞校正。

## 自动验收

| 验证层 | 结果 | 实测范围 |
| --- | --- | --- |
| 模块检查 | PASS | 48 项；含方向错误、断缝、过期数据、体内点和极端压缩反例 |
| 真实浏览器 | PASS | 48 项；含实际 GPU 调度/读回、断网、改尺寸、放码、七视图、相机、回放、导出、暂停和异常保护 |
| 独立 JavaScript 几何审计 | PASS | 两档尺寸；独立 QR 主伸长、封闭人体射线奇偶、完整候选面双向相交测试 |
| 便携式 verify-garment.js | PASS | 独立读取交付 HTML，运行真实浏览器和独立几何断言 |

## 两档保存帧的独立结果

| 案例 | 胸围 mm | 主应变 p95 | 最大主应变 | 人体面横穿 | 布料自交 | 最大缝隙 mm | 结论 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 基准 | 855 | 5.61% | 17.51% | 0 | 0 | 0.00 | PASS |
| 较大胸围 | 935 | 6.34% | 22.52% | 0 | 0 | 0.00 | PASS |

两档均由人体尺寸重新生成纸样和参考人体，再在浏览器运行至第 181 步。两档人体内部顶点均为 0。独立 JavaScript 数值与 WASM 界面数值一致，误差小于 1e-8。

固定门槛：主应变 p95 ≤ 10%，最大主应变 ≤ 25%，缝隙 ≤ 2 mm，人体内部顶点/人体面横穿/非邻接布料自交均为 0。没有为取得通过而放宽门槛。

## 功能

- 按身高、胸围、腰围、臀围更新参考人体，并重新测量实际网格截面。
- 使用 FreeSewing Teagan 4.10.2 重新绘制四裁片纸样；三档放码分别重新制版。
- 检查接缝引用、配对方向、净缝长度、重复边、空间间隙和严格连接等式。
- 显示应变、参考应力、二面角、碰撞、裁片分色、网格及选择对象。
- 保存真实帧；时间轴读取已记录坐标，不推进求解器。
- 导出 1:1 SVG、打印 HTML、当前显示帧 OBJ 及包含回放的工程 JSON。
- 修改尺寸后立即失效旧结果；求解异常后停止并禁用旧结果导出。

## 计算职责

WebGPU 执行积分、四轮图着色 PBD 预测、顶点接触和每步 1 mm 的预测信赖域限制。CPU XPBD 校正真实人体接触、三角面采样、自碰撞和接缝等式。WASM 使用 f64 计算主伸长与参考应力。Three.js 负责三维显示。所有运行时代码和人体资产均内嵌在 HTML 中。

测试适配器为 SwiftShader 软件 WebGPU。已验证真实 WebGPU API、WGSL、队列提交及读回；未据此宣称物理显卡加速或实时性能。

应力是当前应变代入未标定 StVK 平面应力本构所得的参考值，采用第二 Piola-Kirchhoff 应力及其等效值。求解器使用 PBD/XPBD 几何约束。真实材料校准、真人合身、共面重叠和连续碰撞检测不属于本次自动通过结论。

## JavaScript 复现

源码目录内运行：

```bash
npm ci --ignore-scripts --no-audit --no-fund
node scripts/verify.js
```

独立文件复验：

```bash
node verify-garment.js garment-gpu-studio.html
```

独立验证器需要 Node.js 22+、Playwright 1.62.1 和可用 Chromium。HTML 本身不需要安装这些构建或验证依赖。

主证据：evidence/verification-js.json、evidence/browser-report-js.json、evidence/independent-report-js.json。回归反例与此前候选保存在 evidence/history。额外 NumPy 审计保留为交叉证据。

交付 HTML SHA-256：`a49be626c04c3d4c2b1ce6dd36b47d1bd6fec6e4dc55894d8dcbbc0b73f9821c`。

本次需用户批准的事项：无。
