# WebGL 不可用时的真实三维后备验收

最终候选：`80ccaf68114ad1d650ccfec248c812cc77d31ab5c9383e56d4904f18f617c872`，46,107,845字节。本记录的 **PASS** 只表示渲染、来源入口及数据/代码绑定通过；数学结论仍来自 run37 独立审计，材料标定和真人合身不变。

变更仅为 `physics/viewer.mjs`、`viewer.css`、`viewer.template.html` 与新增 `verify_svg_fallback.py`。没有改数学输入、轨迹、审核阈值、builder或原验收器。WebGL优先；不可用时使用已有Three的SVGRenderer、实际scene/camera、所有源网格与原保存数组。软件后备使用Lambert分面绘制，GPU统计为null，界面标明CPU后备。SVG只在状态变化时重画，原WebGL循环保留。

| 检查 | 结果 |
| --- | --- |
| 最终代码绑定 | PASS：当前入口与依赖重新bundle的JS与最终HTML内联JS逐字节相同，CSS/template也重组为相同完整HTML |
| 最终全部数据 | PASS：两case的input/audit与源文件一致，五类录制块独立解码后的全部61帧字节与原trajectory一致 |
| 完整SVG回归 | PASS：5055e14c…候选，源码与最终四个文件的SHA完全相同；两case×61帧五数组SHA、六mode颜色、旋转/缩放、实际raycast、OBJ和全部源文件下载 |
| SVG原生隐藏 | PASS：切二维时实际3D SVG带hidden属性；避免仅给SVG设置非原生hidden属性 |
| 静止开销 | PASS：相机阻尼结束后svgRenderCount稳定，静止时不按每RAF重画 |
| 最终禁GL窄确认 | PASS：两case真实SVG、完整2D/YAML及精确下载、帧0/60五数组与时钟；没有JS或console错误 |
| 视觉复核 | 已查看最终桌面实际SVG、375px完整中文YAML；完整回归另查看了真实场色与二维源图 |

## 证据

- `receipt.json`：最终HTML的代码/全部数据绑定及禁GL窄确认。
- `verify_final.py`：最终窄确认与独立字节绑定脚本；没有写入最终HTML。
- `expected-viewer.js`：从当前源码重新bundle的精确比较对象。
- `../svg-fallback-v3/full/receipt.json`：完整SVG回归及逐帧五数组SHA，绑定5055候选和当前源码。
- `../svg-fallback-v3/summary.json`：完整回归及截图复核摘要。
- `baseline-actual-svg.png`、`03_cuff_width-actual-svg.png`、`mobile-full-yaml.png`：最终字节的真实截图。
- 公共环境原失败证据保持在 `/workspace/shared/physics-public-review/webgl-disabled-before.{jpg,json}`。

## 实际运行

```sh
python experiments/intent-edit-review/physics/verify_svg_fallback.py --html web/intent-edit-review/physics/index.html --run work/intent-physics/baseline-run37 --run work/intent-physics/cuff-run37 --output work/intent-physics/svg-fallback-v3/full
python work/intent-physics/svg-fallback-final/verify_final.py
node --check experiments/intent-edit-review/physics/viewer.mjs
git diff --check
```

完整SVG回归在收据metadata写入前运行；最终窄确认额外证明相同源码、相同完整数学数据和最终实际HTTP字节。没有用旧字节冒充最终候选验收。
