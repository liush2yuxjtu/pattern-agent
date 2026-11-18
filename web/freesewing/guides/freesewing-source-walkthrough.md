# FreeSewing 源码导读：制版规则怎样成为参数化程序

核对日期：2026-11-18。固定版本：4.10.2。固定提交：`3d290d25d0b6a65852dd31aec125c97bc8ca6e2c`。

结论：作者把制版方法写成带尺寸输入、款式选项和几何约束的程序。改变输入后，程序重新计算定位点、控制点、曲线、省道和裁片结构。Core 提供执行与几何工具，版型知识主要在各设计的 `draft` 函数中。

本次读取了 8 个原型的关键起版函数与调用关系。26 个相关源码文件已从上述提交取回，并与本地运行的 npm 4.10.2 文件逐字节比较，全部相同。另完成 10 组公式与单项参数变化验证。结论只覆盖这里列出的函数和样例。

## 1. 规则从哪里来

| 层次 | 人的工作 | 源码中的表达 |
|---|---|---|
| 制版体系 | 选定起版方法和目标体型 | 定义测量位置、构造顺序、省道与分片方式 |
| 几何关系 | 四分围度、肩斜交点、胸点位置 | 尺寸公式、直线求交、旋转和平移 |
| 版型经验 | 选松量、曲线饱满度、最小布量 | 默认系数、可调选项、上下限和分支 |
| 配缝校正 | 量袖窿、核对袖山或裆弧 | 曲线长度目标、残差、迭代与失败处理 |

官方设计说明明确：Brian 受 Gareth Kershaw 方法启发；Bella 是意大利行业女装基础版的参数化实现；Sarah 基于 W. Aldrich 的自然腰线裙原型。它们有不同的方法来源，不存在一套对所有衣服通用的胸围公式。

来源：[Brian 设计说明](https://freesewing.eu/docs/designs/brian/#designer-notes)、[Bella 设计说明](https://freesewing.eu/docs/designs/bella/#designer-notes)、[Sarah 设计说明](https://freesewing.eu/docs/designs/sarah/#designer-notes)。

Sarah 特别清楚地展示了从固定尺寸到参数的转换：文档把原方法中 120 mm 的前省长，对应为随腰线至臀线距离变化的比例选项，默认 58%。这表示选用一个可随人体变化的模型；不能从这个默认值推断其适合所有体型。

来源：[Sarah 选项](https://freesewing.eu/docs/designs/sarah/options/#front-dart-length)。

## 2. 一套设计的程序结构

| 名称 | 含义 | 读源码时看什么 |
|---|---|---|
| `Design` | 组合若干 Part 的设计构造器 | 设计入口的 parts 列表 |
| `measurements` | 必填人体尺寸 | 每个 Part 声明的量体字段与单位 |
| `optionalMeasurements` | 可选量体声明 | 实际值仍从 measurements 读取 |
| `options` | 设计者已经实现的可调规则 | 默认值、范围、换算依据与条件 |
| `draft` | 真正起版的函数 | 如何从输入计算 points 与 paths |
| `from` | 继承并注入另一 Part 的几何 | 被复用的点和路径来自哪里 |
| `after` | 执行依赖 | 哪些 Part 必须先画 |
| `Store` | 中间结果与日志 | 袖窿长度、目标缝长、迭代残差 |
| `hide` | 构造结果的显示控制 | 隐藏的基础 Part 不能当成需裁剪的裁片 |

Core 在配置阶段递归解析依赖并生成 draftOrder，起版时按该顺序调用各 Part 的 draft。继承时把已完成的父 Part 几何注入子 Part，再执行子 Part 的修改。

Brian 实际执行顺序是：`brian.base → brian.back → brian.front → library.sleeve`。

来源：[Design](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/packages/core/src/design.mjs#L15)、[依赖解析](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/packages/core/src/pattern/pattern-config.mjs#L143)、[执行与注入](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/packages/core/src/pattern/pattern-drafter.mjs#L107)、[官方 Part API](https://freesewing.dev/reference/api/part/)。

## 3. Brian：画版步骤如何写成坐标公式

以不启用 highBust 替换的情况为例，胸围 C、胸围松量 e 决定四分之一身宽 W：

`W = C × (1 + e) ÷ 4`

源码把它写入腋下侧点的 x 坐标。腰、髋和下摆侧点继承同一个 x，所以 Brian 的身片从胸线以下直落。

胸围 1000 mm、松量 10%：W = 275 mm。把胸围改成 1100 mm 后，W = 302.5 mm；同一测试的腰线高度仍为 470 mm。各尺寸分别驱动各自的构造，不能理解成把整张纸样按一个倍率缩放。

肩点的求法也很具体：从肩颈点作一条具有肩斜角的线，再与由半肩宽和肩部松量确定的竖线求交。前后领口与袖窿使用由这些点进一步生成的控制点。

源码：[身宽与直身规则](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/brian/src/base.mjs#L125)、[肩点求交](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/brian/src/base.mjs#L81)。

## 4. 曲线如何画出来

FreeSewing 的 Path 保存直线与三次 Bézier 曲线操作。曲线由起点 P0、控制点 P1/P2 和终点 P3 决定：

`B(t) = (1−t)^3 P0 + 3(1−t)^2 t P1 + 3(1−t)t^2 P2 + t^3 P3`

人体尺寸先确定关键点；设计规则再确定控制点的方向、距离和比例。改变关键点后，曲线随控制点重算。

Brian 的袖窿把腋下点、袖窿凹点、袖窿控制位置和肩点连接成多段曲线。Bibi 的髋部侧缝更进一步：求控制点，让曲线通过或位于髋、臀等限制点外侧；没有合理解时，会调整末端位置再尝试。

这部分有纯几何计算，也有作者选定的曲线比例和边界规则。可计算性不能单独证明版型质量。

源码：[Path.curve](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/packages/core/src/path.mjs#L338)、[Brian 袖窿路径](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/brian/src/shared.mjs#L6)、[Bibi 髋部曲线求解](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bibi/src/shared.mjs#L221)。

## 5. Bibi：参数化同时包含“目标”和“边界”

在其前片初始构造中，四分之一腰宽候选值由腰围和腰部松量计算；同时设定一个由腋下身宽乘 waistAdjustment 得到的下限，最终取较大者。

本次测试关闭 FBA，以单独观察侧缝规则。胸围 1000 mm、胸松 10%、腰围 700 mm、腰松 5%：

| 规则 | 四分之一腰宽 |
|---|---:|
| 仅按腰围候选值计算 | 183.75 mm |
| waistAdjustment = 95% | 261.25 mm |
| 把下限改为 50% | 183.75 mm |
| 关闭 fitWaist，使用上述测试输入 | 275 mm |

因此，腰围选项不能直接等同于最终每条侧缝的精确尺寸承诺。后续的 FBA、曲线和其他条件也应一起追踪。

FBA 是另一组规则：bust 插件保留原 full bust，并可改用 highBust 起版。Bibi 的前片在相关量体齐全时，根据差额计算平移和旋转，把胸部空间补回前片；相关点和袖窿控制点也随之转换。

源码：[初始腰宽下限](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bibi/src/shared.mjs#L51)、[关闭收腰的处理](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bibi/src/shared.mjs#L430)、[bust 插件](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/plugins/plugin-bust/src/index.mjs#L7)、[FBA 调用](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bibi/src/front.mjs#L90)、[FBA 旋转计算](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bibi/src/shared.mjs#L134)。

## 6. 8 个原型各自怎样表达规则

| 原型 | 关键算法 | 主要源码 |
|---|---|---|
| Brian | 用量体定位肩颈、胸线和袖窿；胸线以下侧点共用宽度 | [base.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/brian/src/base.mjs#L74) |
| Bent | 复用 Brian 身片、覆盖默认选项；两片袖用肩到肘长定位肘线，以旋转与求交形成预弯 | [设计组合](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bent/src/index.mjs#L7)、[弯肘几何](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/library/src/two-part-sleeve/shared.mjs#L27) |
| Bibi | 腰髋臀侧点、宽度下限、受控侧缝曲线与基础 FBA | [shared.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bibi/src/shared.mjs#L33) |
| Bella | 每次旋转 0.5°，最多 80 次，为胸部扩展到目标宽度；按腰部目标长度计算剩余省量，非正省量时可省略腰省 | [扩胸](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bella/src/front-side-dart.mjs#L82)、[腰省](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bella/src/front-side-dart.mjs#L171) |
| Breanna | 先有 06:00 胸省，以胸点为旋转中心移动主省；按分配比例把一部分转到副省；按位置选路径模板 | [front.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/breanna/src/front.mjs#L37)、[插省位置](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/breanna/src/dart-utils.mjs#L1) |
| Noble | 注入 Bella 几何，隐藏原路径；按肩部/袖窿选择切分位置，创建公主线两侧与新的闭合裁片，并对部分曲线做配长迭代 | [继承与切分](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/noble/src/frontpoints.mjs#L166)、[配长](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/noble/src/frontpoints.mjs#L433)、[前中片路径](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/noble/src/frontinside.mjs#L33) |
| Sarah | 在自然腰位的基准情形，把臀腰差按比例转换为省宽；省长取腰至臀线距离的比例；重建腰口和侧缝 | [base.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/sarah/src/base.mjs#L94) |
| Titan | 量裆弧误差，用旋转和移动裆点修正；先存后片内外侧缝长，再让前片比较并调整，保留失败告警 | [后片校正](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/titan/src/back.mjs#L173)、[前后缝长差](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/titan/src/front.mjs#L107) |

Breanna 的“钟面”是选项标签，源码会把标签映射到具体几何位置；不应把标签机械地当作普通屏幕极坐标。其省道转移的核心是：改变开口位置，并围绕胸点旋转相应的一组边界点，而非仅移动绘制出来的两根省线。

## 7. 袖山配袖窿：带目标的数值校正

Brian 身片先计算前后袖窿长度并写入 Library 所用的 Store。袖片的目标长度为：

`目标袖山长 = (前袖窿长 + 后袖窿长) × (1 + 袖山吃势比例)`

一片袖算法重画袖山、计算实际长度与目标之差，再修改内部系数。它会在条件满足时继续迭代，直到误差不超过 2 mm 或达到最多 50 次等停止条件。内部系数会影响宽度、袖山高度及其控制点。

本次运行：袖窿总长 546.9276 mm。吃势 0% 时，实际袖山 546.0816 mm，残差 −0.8460 mm。吃势 3% 时，目标 563.3354 mm，实际 562.9690 mm，残差 −0.3664 mm。

2 mm 是此处算法的停止条件，不是工厂统一验收标准。达到次数上限也不代表已经满足目标。上述 fit 指二维几何目标，不是人体上的三维合身。

源码：[身片交接](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/brian/src/front.mjs#L150)、[袖山目标](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/library/src/sleeve/index.mjs#L157)、[调整系数](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/library/src/sleeve/index.mjs#L10)、[迭代停止](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/library/src/sleeve/index.mjs#L223)。

## 8. 对我们的 Pattern Agent 有什么含义

下面是从源码结构得出的实施建议：制版师需要提供量体定义、净尺寸目标、构造步骤、省量分配、曲线形状、适用范围和验收标准；Coding Agent 把它们写成带版本的 Part、选项、依赖与验证函数。

工厂基码轮廓可作为几何基准，但要让它在新人体尺寸下重算，还需要把“为什么点在这里、尺寸变化时应该怎样移动”写出来。可以建立自己的工厂 Design，不必强行套进 Brian。

每一条规则最好同时保留：输入字段、计算或几何操作、经验系数、约束、失败行为和对应样例。比如“腰围减小”必须明确应由侧缝、腰省还是其他结构消化。

二维规则验收后，再接三维缝合、面料与人体仿真。这里读取的起版函数没有提供应力应变、碰撞或真实穿着验收证据。

## 9. 可复现实测

以下脚本是本次编写并运行的独立验证代码，不是原仓库文件。使用 Node.js 24 与固定依赖。它检查源码所表达的若干规则和具体样例，不是整个 FreeSewing 的完整测试集。

```bash
npm install @freesewing/brian@4.10.2 @freesewing/bibi@4.10.2 @freesewing/sarah@4.10.2 @freesewing/models@4.10.2 @freesewing/core@4.10.2 @freesewing/config@4.10.2 @freesewing/plugin-theme@4.10.2 @freesewing/plugin-transform@4.10.2
node verify-source-rules.mjs
```

```javascript
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Brian} from '@freesewing/brian';
import {Bibi} from '@freesewing/bibi';
import {Sarah} from '@freesewing/sarah';
import {cisMaleAdult38,cisFemaleAdult34} from '@freesewing/models';
import {pluginTheme} from '@freesewing/plugin-theme';

const close=(a,b)=>assert(Math.abs(a-b)<1e-7,`${a} != ${b}`);
const measurements={...cisMaleAdult38,chest:1000,waist:700,hips:1000,seat:1000,seatBack:520};
function run(C,measurements,options){
 const p=new C({measurements:{...measurements},options,sa:0,complete:false}).draft();
 p.render();
 const logs=p.getLogs();
 assert.equal(logs.pattern.error.length+logs.sets.reduce((n,s)=>n+s.error.length,0),0);
 return p;
}
const results=[];
for(const [chest,waist] of [[1000,600],[1000,900],[1100,600]]){
 const p=run(Brian,{...measurements,chest,waist},{chestEase:.1});
 const pts=p.parts[0]['brian.front'].points;
 close(pts.armhole.x,chest*1.1/4);close(pts.waist.x,pts.armhole.x);
 results.push({design:'Brian',chest,waist,chestEase:.1,armholeX:pts.armhole.x,waistX:pts.waist.x,waistY:pts.cfWaist.y});
}
assert.equal(results[0].waistX,results[1].waistX);
assert.equal(results[0].waistY,results[2].waistY);
for(const [label,fitWaist,waistAdjustment] of [['default guard',true,.95],['relaxed guard',true,.5],['waist fitting off',false,.5]]){
 const options={draftForHighBust:false,chestEase:.1,waistEase:.05,fitWaist,waistAdjustment};
 const p=run(Bibi,measurements,options),pts=p.parts[0]['bibi.front'].points;
 const unconstrained=700*1.05/4;
 const guarded=Math.max(unconstrained,pts.armhole.x*waistAdjustment);
 const expected=fitWaist?guarded:Math.max(pts.armhole.x,guarded);
 close(pts.waist.x,expected);
 results.push({design:'Bibi',label,options,unconstrainedWaistX:unconstrained,armholeX:pts.armhole.x,waistX:pts.waist.x,expected});
}
for(const waist of [700,750]){
 const p=run(Sarah,{...cisFemaleAdult34,waist,seat:1000},{waistDrop:0});
 const frontDartWidth=p.setStores[0].get('sarah.frontDartWidth');
 close(frontDartWidth,(1000-waist)*.1);
 results.push({design:'Sarah',waist,seat:1000,frontDartWidth,seatWaistDiff:1000-waist});
}
for(const capEase of [0,.03]){
 const p=new Brian({measurements:{...cisMaleAdult38,chest:1000},options:{chestEase:.1,sleevecapEase:capEase},sa:10,complete:true}).use(pluginTheme).draft();
 p.render();
 const store=p.setStores[0].get('library.sleeve');
 const armhole=store.frontArmholeLength+store.backArmholeLength;
 const target=armhole*(1+capEase);
 const actual=p.parts[0]['library.sleeve'].paths.sleevecap.length();
 const residual=actual-target;
 assert(Math.abs(residual)<=2);
 results.push({design:'Brian/Library sleeve',capEase,armhole,target,actual,residual});
}
const report={version:'4.10.2',scope:'Specific drafting formulas and one-factor changes; not physical fit validation',pass:true,cases:results};
fs.writeFileSync('source-rule-verification.json',JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));

```

运行结果：

```json
{
  "version": "4.10.2",
  "scope": "Specific drafting formulas and one-factor changes; not physical fit validation",
  "pass": true,
  "cases": [
    {
      "design": "Brian",
      "chest": 1000,
      "waist": 600,
      "chestEase": 0.1,
      "armholeX": 275,
      "waistX": 275,
      "waistY": 470
    },
    {
      "design": "Brian",
      "chest": 1000,
      "waist": 900,
      "chestEase": 0.1,
      "armholeX": 275,
      "waistX": 275,
      "waistY": 470
    },
    {
      "design": "Brian",
      "chest": 1100,
      "waist": 600,
      "chestEase": 0.1,
      "armholeX": 302.5,
      "waistX": 302.5,
      "waistY": 470
    },
    {
      "design": "Bibi",
      "label": "default guard",
      "options": {
        "draftForHighBust": false,
        "chestEase": 0.1,
        "waistEase": 0.05,
        "fitWaist": true,
        "waistAdjustment": 0.95
      },
      "unconstrainedWaistX": 183.75,
      "armholeX": 275,
      "waistX": 261.25,
      "expected": 261.25
    },
    {
      "design": "Bibi",
      "label": "relaxed guard",
      "options": {
        "draftForHighBust": false,
        "chestEase": 0.1,
        "waistEase": 0.05,
        "fitWaist": true,
        "waistAdjustment": 0.5
      },
      "unconstrainedWaistX": 183.75,
      "armholeX": 275,
      "waistX": 183.75,
      "expected": 183.75
    },
    {
      "design": "Bibi",
      "label": "waist fitting off",
      "options": {
        "draftForHighBust": false,
        "chestEase": 0.1,
        "waistEase": 0.05,
        "fitWaist": false,
        "waistAdjustment": 0.5
      },
      "unconstrainedWaistX": 183.75,
      "armholeX": 275,
      "waistX": 275,
      "expected": 275
    },
    {
      "design": "Sarah",
      "waist": 700,
      "seat": 1000,
      "frontDartWidth": 30,
      "seatWaistDiff": 300
    },
    {
      "design": "Sarah",
      "waist": 750,
      "seat": 1000,
      "frontDartWidth": 25,
      "seatWaistDiff": 250
    },
    {
      "design": "Brian/Library sleeve",
      "capEase": 0,
      "armhole": 546.9276028055392,
      "target": 546.9276028055392,
      "actual": 546.0816444403437,
      "residual": -0.8459583651955427
    },
    {
      "design": "Brian/Library sleeve",
      "capEase": 0.03,
      "armhole": 546.9276028055392,
      "target": 563.3354308897054,
      "actual": 562.9690324434291,
      "residual": -0.366398446276321
    }
  ]
}
```

## 10. 版本与源码校验记录

以下文件的官方固定提交字节均与本次运行的 npm 4.10.2 一致。SHA-256 用于明确本次解释依据的源码版本。

| 文件 | SHA-256 |
|---|---|
| [designs/brian/src/base.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/brian/src/base.mjs) | `72a35301f89d85a34c47ee97a3eb036a78765bf26d9841fe7c9e620a9f2f107d` |
| [designs/brian/src/front.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/brian/src/front.mjs) | `8111ae2e7b27035f417ad0bc362ed721a8274f9c0a564a36640bc92a1575f5c8` |
| [designs/brian/src/back.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/brian/src/back.mjs) | `2e821abba7b3ebf4a58019e24549f4a41b997a92c714e2e0d31d3ba001aadccf` |
| [designs/brian/src/shared.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/brian/src/shared.mjs) | `f75a9af26e2a6a8d7bc2e53842ceb05ac09947592dd06bbec94d949167caca2f` |
| [designs/bent/src/index.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bent/src/index.mjs) | `88adac49792e7c7385e3f20fe6fe9cb8599fec066f0f9ad0f09a3acbbc693c3b` |
| [designs/bibi/src/front.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bibi/src/front.mjs) | `7556b8978caa3140b4f421f4ced6764b6a5b596d1fc4f39dae455eedc595862e` |
| [designs/bibi/src/shared.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bibi/src/shared.mjs) | `49886bc3a5f7a2e8d0290bd304fa0c21789d2b6f0b367102862df47da480589b` |
| [designs/bibi/src/waistband.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bibi/src/waistband.mjs) | `41f11dfe0e95d92ab17c37940ca9c8ea392c8752f749fb13fe7866ec6319ff1b` |
| [designs/bella/src/front-side-dart.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bella/src/front-side-dart.mjs) | `06aec0926c2ecf98ed70a64cce1443e2a39bcd8c6bb1e39aebd9945b5cb29e3c` |
| [designs/bella/src/back.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/bella/src/back.mjs) | `b5c26dd023012f26c21f2185584dbbd234e295e2f57a2d708d01b256a62f55f1` |
| [designs/breanna/src/front.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/breanna/src/front.mjs) | `95dbf0b0fddcc2d81b7aa6a85bf09fcf2543f19e643ba09c60132367eb90ec67` |
| [designs/breanna/src/front-base.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/breanna/src/front-base.mjs) | `d4533319539fc895a7189163936269b726c21951df28d5691e994a5cfd500dbf` |
| [designs/breanna/src/dart-utils.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/breanna/src/dart-utils.mjs) | `f8e08b1f9c84087fb7366e64c97d80b5de0558c2b0a58ed69ab378975d9e1bb6` |
| [designs/noble/src/frontpoints.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/noble/src/frontpoints.mjs) | `d60060dc4262e45b2031752d60db0ded24aaeda7bce8936ee6f8087039596d94` |
| [designs/noble/src/frontinside.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/noble/src/frontinside.mjs) | `395d5a810893c1cc47e3eb010021719eff1c5307607d17fb22224ff1cc8556d8` |
| [designs/noble/src/frontoutside.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/noble/src/frontoutside.mjs) | `5c210f2bcdd7d107c035bfa69a5815b357e5bd21546daca3b2d1152264e91646` |
| [designs/sarah/src/base.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/sarah/src/base.mjs) | `78fa47b82536fd2f621319cfc4427157a2c2ac728db77b80dd7f0563065e9a39` |
| [designs/titan/src/back.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/titan/src/back.mjs) | `787c73c32621a0b2dabdc64560ac93bbf7f0e17b2f7d0550f79a7263a3821b55` |
| [designs/titan/src/front.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/titan/src/front.mjs) | `46103dd7dbf479e7bbf050e05a709cb417c7f7fd670300be89a95516649dd31b` |
| [designs/library/src/sleeve/index.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/library/src/sleeve/index.mjs) | `8e0f75f0102fdb102fd0e93fdad6ddda1fb19d8bb0d824db71f427cabb986ca8` |
| [designs/library/src/two-part-sleeve/shared.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/designs/library/src/two-part-sleeve/shared.mjs) | `81a08f17b11d986825182435930384dc89f04706051a1c15ec7b72e6740fba94` |
| [packages/core/src/design.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/packages/core/src/design.mjs) | `5355105d73ce196cae766fba00ba73f177f245d412c726816fa9aaf4b9af9421` |
| [packages/core/src/path.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/packages/core/src/path.mjs) | `c3834fb1a3ac527203714260c9033a2627a6f4430d30685a4f70acd8ee0fffce` |
| [packages/core/src/pattern/pattern-config.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/packages/core/src/pattern/pattern-config.mjs) | `31e5d207ae76b46be462c7dee10a2ce590c559a9d8371a6b11509e0febbfb0ab` |
| [packages/core/src/pattern/pattern-drafter.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/packages/core/src/pattern/pattern-drafter.mjs) | `e3ccc7e4d74d1c3f5ec13c431e90b5d93c87b05e8a04cc5deb995681d03ea835` |
| [plugins/plugin-bust/src/index.mjs](https://codeberg.org/freesewing/freesewing/src/commit/3d290d25d0b6a65852dd31aec125c97bc8ca6e2c/plugins/plugin-bust/src/index.mjs) | `69ce8f07a29c8b7aca5232c6e5cad45a36061a0d0a15acb9922ba4c2dbaa35eb` |
