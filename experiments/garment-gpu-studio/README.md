# Garment Lab：单文件 GPU 服装工作台

下载并打开 `dist/garment-gpu-studio.html`。运行时不需要 Node、MCP、API、账号或 CDN。使用支持 WebGPU 的 Chrome 或 Edge。浏览器必须提供可用的 WebGPU 适配器。

先调整人体与服装尺寸，再点击「应用尺寸」。点击「计算 60 步」或「运行仿真」计算后续布料状态。默认每步执行 128 次约束迭代。右侧的 PASS、FAIL 和 NOT_RUN 分别表示通过、失败和未运行；初始摆放不等于求解完成。

## 功能与源码

| 功能 | 独立 JavaScript 模块 | 计算与检查 |
| --- | --- | --- |
| 根据人体尺寸重新制版 | `src/pattern.js`、`src/body.js` | FreeSewing Teagan 4.10.2 重新制版；真实 MakeHuman 网格变形后重新切面测量 |
| 缝合关系检查 | `src/seams.js` | 裁片/缝边引用、方向、配对点、重复边、实际净缝长度及空间间隙 |
| 人体碰撞 | `src/collision.js`、`src/intersections.js` | 实际人体三角网格 BVH、内部顶点、边中点/面心、双向严格三角面横穿 |
| 应变及参考应力热图 | `src/strain.js`、`src/wasm-binary.js` | 每个三角面的形变梯度；WASM f64 主伸长、Green-Lagrange 应变及平面应力本构 |
| 衣服折角 | `src/folds.js` | 相邻面的有符号二面角；平面为 0° |
| 物理回放 | `src/replay.js` | 保存真实 Float32 坐标；拖动时间轴不推进求解器 |
| 物理调试视图 | `src/debugger.js`、`src/viewer.js` | 网格、裁片分色、接缝、顶点/面 ID、失败项定位及热图 |
| 布料连接约束 | `src/constraints.js`、`src/solver-gpu.js` | 独立二维 UV 保留休止度量；接缝节点采用严格等式；图着色防止同次 dispatch 写冲突 |
| 自动放码 | `src/grading.js` | 按胸/腰/臀每档 40 mm 分别重新制版；输出 S/M/L 叠图 |
| 1:1 纸样及当前帧导出 | `src/exports.js` | 带 100 mm 校准框的 SVG、整幅打印 HTML、真实显示帧 OBJ、包含回放的工程 JSON |

`src/app.js` 只负责状态与界面组织。所有功能读取同一份纸样、人体、网格和当前帧。尺寸或精度发生变化时，旧物理结果立即变为 STALE，导出被禁用。重建后建立新版本并清空旧回放。

## WASM、WebGPU 和 CPU 的职责

WebGPU 实际执行 Verlet 积分、四次按颜色分批的 PBD 预测、弯曲距离近似和顶点接触投影。每步通过 GPU 队列提交，再读回候选坐标。随后，内嵌的 `src/solver-corrector.js` 用 CPU XPBD 校正实际人体接触、三角面采样、自碰撞顶点–面/边–边约束和接缝等式。校正后的坐标回写 GPU，并作为下一步的共同状态。重力只在 GPU 积分阶段执行一次。

CPU 对实际人体三角网格执行 BVH 窄相位查询，并生成离散人体接触约束。CPU XPBD 还执行离散布料自碰撞约束。完整检查另行测试人体和布料的三角面横穿。该程序采用混合计算；不是所有计算都在 GPU 上运行。

WASM 包含五个 f64 数值函数。每个三角面的主伸长和参考应力都调用这些函数。本构参考应力为材料坐标中的第二 Piola-Kirchhoff 应力及其等效值，不是真实穿着压力。`scripts/build-wasm.js` 可确定地生成二进制，`assets/strain-kernel.wat` 提供可读的等价文本。求最小主伸长时使用叉积面积平方，避免 `F=diag(1,1e-9)` 因相减消去而被误算为零。

这是 GPU + CPU 混合求解，不是全 GPU cloth solver。GPU 预测位移限制为每步 1 mm，避免先穿过布料后再交给校正器。CPU 校正包含数值移动上限和接触重查询；这些稳定措施不等于真实面料标定或连续碰撞检测。纯 GPU 研究候选未通过完整面审计，失败记录保留在历史目录。

## 数据和单位

- 2D 纸样：mm；3D：m；时间：s；默认固定时间步：1/120 s。
- 人体：4,002 顶点、8,000 三角面。显示和碰撞共用变形后的全部网格。
- 研究上衣：前身、后身、左右短袖；约 1,430 个纸样顶点、约 2,550 个三角面及 10 条接缝。
- 人体不是用户扫描。胸、腰、臀在指定水平面上测量。其他缺失的制版测量仍有估计值。
- 身高范围：145–195 cm；胸围：800–1,100 mm；腰围：580–1,000 mm；臀围：800–1,200 mm。
- 三档放码要求三档尺寸全部处于支持范围。靠近边界时会拒绝超范围档位。
- 材料参考值：Young 模量 100 kPa、泊松比 0.3、厚度 1 mm、面密度 180 g/m²。材料未标定。当前 PBD 使用等质量节点；面密度只作为元数据保留。

## 验证

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm run verify
```

`node scripts/verify.js` 会构建 HTML、运行模块测试、启动临时本地服务器、执行真实浏览器验收，再执行独立 JavaScript 几何审计。全部通过才返回退出码 0。只运行模块检查时，使用 `node scripts/verify.js --unit-only`。

主验证脚本包括 `tests/strain.test.js`、`tests/body.test.js`、`tests/seams.test.js`、`tests/collision.test.js`、`tests/replay.test.js`、`tests/browser-verification.js` 和 `tests/independent-geometry.js`。Python / NumPy 版本保留作额外交叉审计，不是主验证入口。

浏览器验收需要 Node.js Playwright 和 Chromium。测试使用隔离的临时浏览器配置，允许 SwiftShader 软件 WebGPU。它验证真实 WGSL、队列提交及坐标读回，不证明物理显卡加速或实时运行速度。普通用户无需修改浏览器安全配置；在正常支持 WebGPU 的设备上直接打开 HTML 即可。

`tests/audit.py` 不调用产品的 JS 数学或碰撞代码。它用 NumPy SVD、独立射线奇偶和双向三角相交算法重查真实 GPU 坐标。最终结果见 `VERIFICATION.md`、`evidence/verification-js.json`、`evidence/browser-report-js.json` 和 `evidence/independent-report-js.json`。历史失败保存在 `evidence/history`，包含“顶点检查为零但实际三角面横穿”的反例。

## 边界

本项目是研究工作台。FreeSewing Teagan 的上游曲线被采样为四片多边形研究网格。它不是未经修改的生产纸样，也没有完整领口工艺。

应力热图是明确给定材料模型的参考结果，不能用于真实面料受力或真人合身结论。离散面相交检测不包括共面重叠和连续碰撞检测。弯曲采用对顶点距离近似。接缝采用预装配的严格等式，没有模拟针线逐点闭合。

回放保存坐标并逐帧读取。重新继续求解从 GPU 最新内部状态开始；拖动时间轴不会恢复历史速度。没有声称跨设备浮点逐位一致。

## 来源

- [FreeSewing Teagan](https://freesewing.eu/docs/designs/teagan/) / 4.10.2 / MIT。
- [Three.js](https://github.com/mrdoob/three.js) / 0.186.0 / MIT。此项目自行实现 GPU PBD，不将 Three.js 渲染称为 cloth solver。
- [MakeHuman](https://github.com/makehumancommunity/makehuman/blob/master/LICENSE.md) / CC0 参考人体。处理后资产的原始字节、哈希、来源限制保留在 `assets/body.json`。
- 纸样适配、BVH 最近点和参考人体继承已有 Pattern Agent Studio / Garment Artifact 研究代码。新 GPU 求解、功能拆分和独立验证保留在本项目。
- 完整第三方声明见 `licenses/BASE_NOTICES.txt`。

## 单独复验交付 HTML

`dist/verify-garment.js` 已把浏览器验证和独立几何审计打包为单个 JavaScript 文件。它不需要源码目录、Python 或 MCP。准备 Node.js 22+、Playwright 1.62.1 和 Chromium 后，运行：

```bash
node verify-garment.js garment-gpu-studio.html
```

它会启动仅绑定本机的临时服务器，自动验证两档尺寸，输出 PASS 和证据目录。验证器内保留固定门槛；没有通过时退出码为 1。

## GitHub Pages

- [打开工作台](https://liush2yuxjtu.github.io/pattern-agent/garment-gpu-studio/)
- [查看验收和下载独立验证器](https://liush2yuxjtu.github.io/pattern-agent/garment-gpu-studio/verification.html)

仓库的 `web/garment-gpu-studio/index.html` 与 `dist/garment-gpu-studio.html` 字节一致。验收页采用站内相对链接。历史碰撞样本在 Git 中保留断言读取的原始人体、纸样和坐标。完整回放和历史记录见原始交付压缩包。
