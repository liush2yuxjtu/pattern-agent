# Carlton 参数纸样与 WebGPU 试穿

[打开编辑器](https://liush2yuxjtu.github.io/pattern-agent/carlton-workbench/) · [查看验收报告](https://liush2yuxjtu.github.io/pattern-agent/carlton-workbench/review.html) · [下载逐片 JSON、字段和 VTK](https://liush2yuxjtu.github.io/pattern-agent/carlton-workbench/evidence.tgz)

`index.html` 是支持离线打开的单文件编辑器。FreeSewing Carlton 4.10.2 根据 62 个输入生成 20 款 2D 裁片，修改可装配参数会重新计算外层布料的 480 步。应用保留当前 2D SVG 导出。`sa` 为出样缝份，单位是 mm。

## 试穿检验

- **应变**显示最大主工程应变。**应力**基于示例面料显示最大主拉应力，两者标注净样面积加权 P95。
- **试穿压力**由 Cloth Lab 法向接触算法移植到 Rust/WASM。用接触反力和变形后受力面积计算刚性人台上的法向压力估算。
- **正面线稿对照**并排显示官方正面线稿和当前服装的正交正面投影。线稿垂臂，模拟为固定斜展姿势。
- 材料标定及量产合体待实测。极小三角面的应力尖峰保留在原始数据，色标显示范围有限。

Boat Linux 的 CLO_RUST 独立复算四组浏览器的第 480 步网格，各含 18 片外层和 5,764 个三角面。应力和压力也有独立张量或数值检查。平面载荷试验的两种网格均得到目标压力 3.924 Pa。

## 源码和验证

[源码构建](source/README.md) · [独立字段复核](source/verification/README.md)

从仓库根目录构建静态站点，在 `/pattern-agent/` 前缀下提供 `dist`，安装 Playwright 和 Chromium，再执行以下命令。也可提供线上 URL 和该版本的 `build.json` commit。使用系统安装的 Chrome 可设置 `CHROMIUM_EXECUTABLE`。

```sh
node web/carlton-workbench/verify.mjs http://127.0.0.1:8000/pattern-agent/carlton-workbench/ "$(git rev-parse HEAD)"
```
