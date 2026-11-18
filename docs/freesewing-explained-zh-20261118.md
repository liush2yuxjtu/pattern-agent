# FreeSewing 是什么，以及它如何用于 Pattern Agent

你前面说的「freeSwing」应当是 **FreeSewing**。Sewing 指缝纫／制衣。
它是一个开源的、用 JavaScript 编写的**参数化服装制版工具链**：把人体尺寸、
款式选项和事先编写的制版规则，转换成可打印的二维纸样。

官方入口：[制作者网站](https://freesewing.eu/)、[开发者文档](https://freesewing.dev/)、
[当前源码仓库](https://codeberg.org/freesewing/freesewing)。仓库采用 MIT 许可证。
本说明核对了官方文档；没有把 FreeSewing 安装或接入现有单文件演示。

## 1. 把纸样变成一段可重复运行的程序

传统制版师会根据人体尺寸决定点的位置、肩线、领口、袖窿、胸腰分配、省道等。
FreeSewing 允许开发者把这些规则写成程序。人体尺寸改变后，它重新计算相应几何，
因此可以按不同尺寸集生成不同纸样，而不仅是把一张图片整体放大。

可以把一次调用理解为：

> 某个已经实现的款式＋这个人的测量值＋该款式支持的选项 → 各个裁片的二维几何。

例如，一个示意的四分之一胸围宽度公式可以写成
`胸围 × (1 + 松量比例) / 4`。960 mm 胸围加 8% 松量，对应 259.2 mm。
**这只是解释参数化思路，不是 FreeSewing 某一款服装的完整制版算法。**
实际规则还要处理前后片分配、肩斜、曲线、省道与材料／结构要求。

## 2. 它包含三个使用层次

| 层次 | 作用 | 使用者 |
| --- | --- | --- |
| 制作者网站 | 选择现有款式、填写尺寸、调整选项、下载纸样 | 裁缝、服装爱好者、定制业务 |
| 现有款式包 | 用程序生成某款已经实现的服装 | 开发者、自动化业务系统 |
| 核心制版库 `@freesewing/core` | 用点、路径、曲线、裁片等对象编写自己的制版规则 | 新版型开发者、Pattern Agent |

官方款式集合中有 Aaron A-shirt（无袖背心）、Brian body block（上身基础版）、
Sandy circle skirt（圆裙）、Sarah skirt block（裙子基础版）等。
它们提供不同的测量要求和可调选项，不能假定所有款式共用一套参数。

来源：[官方款式列表](https://freesewing.eu/docs/designs/)、
[Core API](https://freesewing.dev/reference/api/)。

## 3. 三类输入不要混淆

**人体尺寸 measurements** 描述人，例如胸围、臀围、肩宽、背长和肩斜。
官方规定长度输入使用 **毫米**，肩斜等角度输入使用 **度**。不能把 96 cm
胸围直接填成 `chest: 96`；应当填写 `chest: 960`。

**款式选项 options** 描述服装，例如胸围松量或领口深度。可用选项由该款式的
作者实现，并有各自的默认值。输入一个从未实现的「泡泡袖」选项，并不会自动生成
泡泡袖的制版算法；需要对应的设计规则。

**通用设置 settings** 描述输出／制图要求，例如缝份、布局和是否显示相关标注。
`sa: 10` 表示要求 10 mm 缝份，但官方特别说明：**款式代码本身必须实现相应缝份
绘制逻辑**。设置一个数值，不等于每个自定义款式都已经正确生成缝份。

来源：[测量值](https://freesewing.dev/reference/settings/measurements/)、
[款式选项](https://freesewing.dev/reference/settings/options/)、
[缝份设置](https://freesewing.dev/reference/settings/sa/)。

## 4. 开发者怎样调用它

核心流程是实例化设计、传入尺寸、制图，再输出 SVG：

```js
const pattern = new Aaron(settings)
const svg = pattern.draft().render()
```

下面是按官方 Node.js API 写法整理的说明示例。尺寸是示例数据，需替换成真实量体
结果；这里没有宣称已经在本项目中运行过这段代码。

```sh
npm install @freesewing/core @freesewing/aaron @freesewing/brian \
  @freesewing/plugin-bundle @freesewing/plugin-theme
```

保存为 `draft.mjs`：

```js
import { writeFileSync } from 'node:fs'
import { Aaron } from '@freesewing/aaron'
import { pluginTheme } from '@freesewing/plugin-theme'

const settings = {
  sa: 10,
  measurements: {
    biceps: 300,
    chest: 960,
    hips: 1000,
    hpsToBust: 230,
    hpsToWaistBack: 420,
    neck: 380,
    shoulderSlope: 13,
    shoulderToShoulder: 440,
    waistToArmpit: 250,
    waistToHips: 200,
  },
  options: { chestEase: 0.08 },
}

const svg = new Aaron(settings)
  .use(pluginTheme)
  .draft()
  .render()

writeFileSync('aaron.svg', svg, 'utf8')
```

然后运行 `node draft.mjs`。实际项目应固定一组兼容的包版本。这里的 `render()`
是生成**二维 SVG 字符串**，与 Three.js 中的三维渲染含义不同。

官方参考：[Node.js 使用方式](https://freesewing.dev/howtos/environments/nodejs/)、
[`draft()`](https://freesewing.dev/reference/api/pattern/draft/)、
[`render()`](https://freesewing.dev/reference/api/pattern/render/)。

想编写自己的款式，可以从官方推荐的 `npx @freesewing/studio` 开发环境开始。
核心 API 有 Point、Path、Part、Pattern 等对象以及曲线、交点等几何工具。

## 5. 能输出什么，哪些输出需要另外处理

SVG 是其原生纸样输出。官方制作者网站还提供 A4、A0 等分页／大幅 PDF、整张 PDF，
以及款式参数的 JSON／YAML 导出。

需要注意：网站的 JSON／YAML 参数导出，不等于已经得到完整的三维布料网格、
每条边的缝合对应关系、材料本构参数和仿真状态。工业裁床所需的 DXF／AAMA／ASTM
数据也不能仅凭「它能输出 SVG」就视为已支持；具体转换和机器适配要另做验证。

来源：[官方导出说明](https://freesewing.eu/docs/editor/views/export/)。

## 6. 与 CLO 3D、MakeHuman、Three.js 的分工

| 组件 | 核心任务 |
| --- | --- |
| FreeSewing | 根据人体和款式参数计算二维纸样 |
| MakeHuman | 提供可调整的人体网格与体型基础 |
| 我们的转换层 | 保存裁片、布纹、单位、缝合关系，生成仿真网格并安排初始位置 |
| WASM／WebGPU 布料求解器 | 根据材料、重力、约束和碰撞计算形变与运动 |
| Three.js／WebGL | 显示人体、布料、缝合线和数值热力图 |
| CLO／Style3D | 在完整产品中集成制版、缝合、仿真和服装工作流 |

FreeSewing 本身不预测布料怎样落下、不处理人体碰撞，也不自动计算应力和应变。
它也不会仅凭一张照片就恢复真实人体尺寸和精确服装纸样。它的优势是把已经明确的
制版知识变成可重复、可检查和可参数化的几何程序。

## 7. 在我们的单文件 HTML 项目里怎么用

当前 `/cloth-lab.html` 的四片裙子使用项目自编的参数化裙片规则；新 `/cloth-lab/`
页面采用另外的测试裙片和求解器。它们都不应被描述为已经集成了 FreeSewing。

未来可采用下面这条数据流：

```text
用户需求／服装 Agent
        ↓
已确认的人体尺寸＋款式与松量选项
        ↓
FreeSewing：生成二维裁片几何
        ↓
转换层：缝合图、布纹、毫米单位、材料坐标、三角网格
        ↓
WASM／WebGPU：布料形变和人体碰撞
        ↓
Three.js：三维预览、缝合检查、应力应变热图
```

若人体来自 MakeHuman，自动量取胸围、臀围或背长也需要自己的量体算法和验证。
不能把人体包围盒宽度直接当作胸围。

**可以做成单文件 HTML。** 开发时用 Node 工具把选定款式、核心库、求解器、人体数据
和界面打包；运行时在浏览器中生成纸样和模拟。FreeSewing 不要求 MCP，也不要求
必须调用云端 API。浏览器端集成和单文件打包仍需要我们完成。

建议把 FreeSewing 作为可选的**二维制版层**，保留独立的缝合数据、材料坐标和物理
求解层。这样裁片修改后，可以重新检查缝长、缝合方向、碰撞和拉伸，而不只更新画面。

## 8. 怎样判断是否适合我们

如果希望根据量体数据生成基础版、扩展已有款式、让 Agent 用代码修改制版规则，
FreeSewing 值得采用。如果目标是立即得到完整 CLO 工作流、实测面料精度和工业生产
批准，则仍需要额外的 CAD／仿真／验证工程。量体误差、版型适用范围、面料特性和
实际试样都会影响最终合体性，不能单凭 SVG 成功生成就确认成衣合格。
