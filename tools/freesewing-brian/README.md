# Brian 实时 SVG 纸样

[在线拖动尺寸](https://liush2yuxjtu.github.io/pattern-agent/freesewing/brian/) ·
[全部图解](https://liush2yuxjtu.github.io/pattern-agent/freesewing/) ·
[单文件 HTML](../../web/freesewing/brian/index.html)

拖动人体尺寸后，真正的 FreeSewing Brian 4.10.2 在浏览器内重新制版。
下载按钮保存当前结果，长度单位保留为毫米。打开交付 HTML 不需要 Node、联网或构建。

## 给制版人员

| 项目 | 本工具的行为 |
| --- | --- |
| 必填尺寸 | 胸围、颈围、肩宽、肩斜、上臂围、腕围、肩到腕、肩颈点到胸线、肩颈点到后腰、腰到腋下、腰到臀 |
| 可选尺寸 | 启用上胸围后，使用 Brian 自带的 `draftForHighBust` |
| 胸围松量 | 演示固定为 10%；Brian 官方默认是 15% |
| 裁片 | 原版 Brian 后片、前片和库袖片的制版曲线 |
| 辅助线 | 胸线、腰线使用 Brian 计算出的原始点 |
| 整体大小 | 界面同步缩放各长度，保留肩斜，再重新调用 Brian；这不是工厂放码表 |
| 输出 | SVG，无缝份；技术标注收起，裁片横向排列 |

Brian 本身是胸围以下直下的基础原型，不按腰围收腰。
这里没有布料仿真、三维人体或真人合体结论。滑条范围由演示界面设定，
并未开放 Brian 全部松量、袖山与款式选项。初始尺寸是示例值。

## 给编码 Agent

需要 Node 24+。依赖版本由 `package-lock.json` 固定。

```sh
cd tools/freesewing-brian
npm ci
npm run build
npm test
```

`build.mjs` 输出 `web/freesewing/brian/index.html`，同时内嵌制版引擎、样式和许可。
`sliders-engine.mjs` 只负责厘米转毫米、调用原库、添加参考线和安排裁片位置；
`sliders-ui.mjs` 处理滑条与 SVG 下载。肩斜保持角度，不乘 10。

最小调用方式如下；`measurements` 须包含上述全部必填值。

```js
import { Brian } from '@freesewing/brian';
import { pluginTheme } from '@freesewing/plugin-theme';
const pattern = new Brian({ measurements, options: { chestEase: 0.1 } });
const svg = pattern.use(pluginTheme).draft().render();
```

`verify.mjs` 直接检查每项输入、边界、总滑条、上胸围和下载内容。
`verify-fidelity.mjs` 用独立的 `new Brian()` 对照实际 HTML 的前片、后片、袖片及导出结果；
它不复用演示的参数映射函数，并核对原版包的 10 个文件摘要。
`upstream-manifest.json` 来自官方 npm 4.10.2 压缩包逐文件读取。

运行结果写入本目录下忽略的 `work/`。提交与部署前按仓库的 `/verify` 流程执行，
再检查真实网页滑条、辅助线、SVG 下载、离线交互和手机宽度。
公开证据保存在 `docs/verification/freesewing-brian-20261118/`。

## 来源与许可

- [官方包](https://www.npmjs.com/package/@freesewing/brian/v/4.10.2)
- [官方源码](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/brian/src/)
- [官方选项](https://freesewing.eu/docs/designs/brian/options/)

FreeSewing 的 MIT 许可保存在 `LICENSE.FreeSewing`，原依赖许可随 HTML 内嵌。
本目录界面与封装代码见 `LICENSE`。其他历史图解保存在
`web/freesewing/guides/`，其源文件就是可直接打开的独立 HTML。
