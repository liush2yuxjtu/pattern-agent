# Carlton 参数纸样与 WebGPU 试穿

[打开编辑器](https://liush2yuxjtu.github.io/pattern-agent/carlton-workbench/) · [查看验收报告](https://liush2yuxjtu.github.io/pattern-agent/carlton-workbench/review.html) · [下载 JSON 和 VTK](https://liush2yuxjtu.github.io/pattern-agent/carlton-workbench/evidence.tgz)

`index.html` 是可离线运行的单文件编辑器。保存后用支持 WebGPU 的浏览器打开。页面用 FreeSewing Carlton 4.10.2 的同一份草图生成 20 款二维裁片和外层试穿输入。修改可装配的参数会重新运行 480 步，模拟时长 4 秒。SVG 从当前尺寸导出。

## 输入

- 43 个 Carlton 原生打版选项，包括胸围松量、袖窿深度、领高和口袋位置。
- 17 个人体量体项，包括 16 项必填和 1 项可选。页面预设 M 示例量体。
- `sa` 是出样缝份，单位为毫米。设为 10 时，适用边在净缝线外保留 10 mm 缝份。部分边沿用裁片自身的处理规则。
- 前片衣长的毫米输入映射到 Carlton 的原生 `length` 比例。

## 求解与验收

WebGPU 负责重力和惯性的运动预测以及渲染。Rust/WASM 负责布料变形、缝合、人台接触和外层自碰撞。试穿网格沿用 Joost 参考装配，18 片外层使用同一个参考人台的网格显示与碰撞。口袋和袋盖按原 CLO 的前片配对连接。

CLO_RUST 在 Boat Linux 上复算四组浏览器第 480 步的外层网格，并独立核查原 CLO 留存的三姿势。在四组浏览器案例中，口袋约束最大间距为 0.26 mm，后省最大间距为 1.64 mm。领座几何主应变 P95 为 47.3%–50.5%。参考人台保持固定，面料参数为示例值。材料应力标定、压力、逐帧回放和量产合体仍待验收。改变裁片结构的选项可能超出参考装配范围，2D 编辑和导出仍可使用。

`review.html` 包含线稿、纸样、主应变及折角图。`evidence.tgz` 提供逐片数据和调试 VTK，`review-summary.json` 提供机器可读摘要。

## 浏览器复测

从仓库根目录构建网站，并用 HTTP 在 `/pattern-agent/` 前缀下提供 `dist`。安装 Playwright 和 Chromium 后，运行以下命令。使用已安装的 Chrome 时，可通过 `CHROMIUM_EXECUTABLE` 指定它的路径。测试覆盖四轮 480 步、下载、报告内嵌图、窄屏和无 WebGPU 时的 2D 出样。

```sh
node web/carlton-workbench/verify.mjs http://127.0.0.1:8000/pattern-agent/carlton-workbench/ "$(git rev-parse HEAD)"
```

直接测试 GitHub Pages 时，替换 URL 并传入 `build.json` 中发布的提交 SHA。脚本同时核对实际响应与仓库资产的字节摘要。
