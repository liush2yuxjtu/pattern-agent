# 单文件 WASM 布料与试衣验收

入口：<https://liush2yuxjtu.github.io/pattern-agent/cloth-lab/>。
`index.html` 嵌入真实 MakeHuman 网格、BVH、WASM、Three.js 与程序化织纹，运行时不需要
CDN、后端、模型 API 或 MCP。SVG、OBJ、工程 JSON 和包含完整回放的单 HTML 来自同一状态。

## 模块源码与单文件发布

开发时按功能维护独立 ES 模块；发布时 `build.js` 将它们与 WASM、人体和渲染器一起
打包进一个 HTML。WASM 执行布料物理，WebGPU 绘制三维场景；浏览器界面与文件处理
使用内嵌 JavaScript。

| 源文件 | 职责 |
| --- | --- |
| `src/app.js` | 组装模块依赖 |
| `src/runtime-context.js` | 共享运行状态、最初 HTML 捕获 |
| `src/simulation.js` | 布料初始化、WASM 缓冲区、固定步进 |
| `src/rendering.js` | WebGPU／WebGL、人体与布料网格、热图、相机与真实后端诊断 |
| `src/diagnostics.js` | 缝合、碰撞、覆盖、腰位、压力与性能判定 |
| `src/replay.js` | 每步录制、时间轴、无积分回放 |
| `src/persistence.js` | JSON 校验与恢复、OBJ／单 HTML 导出、递归保存 |
| `src/controls.js` | 界面控件与事件 |
| `src/lifecycle.js` | 初始化、实际首帧就绪、公开 API、动画循环 |
| `src/pattern.js` | 二维扇环纸样与真实尺寸 SVG |
| `src/trajectory.js` | 轨迹格式、参数校验、Float32 编解码 |
| `src/contact-state.js` | 接触乘子／法向保存、恢复与压力字段 |
| `src/pressure.js` | 同 WASM 已知载荷试片 |
| `src/wear.js` | 实际腰口位置、间隙与纸样边长诊断 |

`src/solver.c` 编译成一份 WASM；原始人体资产、`avatar-fit.json`、模板与 CSS 单独维护。
单 HTML 发布包包含所有运行数据，无需部署这些源文件供页面加载。

默认 `?renderer=auto` 优先使用 WebGPU；不可用时明确显示实际 WebGL 回退及原因。
`?renderer=webgpu` 强制使用真实 WebGPU，失败显示 BLOCKED；`?renderer=webgl` 强制
使用 WebGL。WebGPU 需要浏览器支持和安全上下文。首次真实绘制完成后才发布 ready；
设备错误有独立的渲染状态，阻止过期的物理 PASS 覆盖渲染失败。

本地 Dawn／SwiftShader 属于软件 GPU。该适配器的透明 MSAA 曾出现白色边缘，因此
仅软件 WebGPU 关闭 MSAA，并在诊断中记录实际配置；硬件分支保留抗锯齿，未将软件
测试结果宣称为硬件性能。

## 打开即完成初始试衣

此前原始摆放在臀部穿透，用户还没点击运行就能看到皮肤。现在默认打开、重置、修改
正常纸样／材料，均先由真实 WASM 完成 240 个固定时间步，再显示结果；实际时钟保留为
约 2 秒，没有把求解后的状态伪装成物理第 0 帧。移动人体也会暂停并完成重新试衣。
录制中发生的重新试衣，所有真实物理步仍会逐步保存。

人体坐标与索引保持原始完整、不透明、正常深度测试，统一使用灰色模特材质；实际裙子
使用独立布料网格。身体为仓库 MakeHuman 成人女性 CC0 资产，159 cm、13,380 个顶点、26,756 个
三角形；仅 cm→m 和落地平移。它是通用刚体数字人体，不是个人扫描或软组织模型。

## 实际腰线装配

旧版腰口是固定的 840 mm 圆环，局部离体约 56.55 mm；虽然臀部覆盖和碰撞通过，衣服
仍然悬空。现在用原始 MakeHuman 腰围测量路径确定自然腰位，再上提 35 mm 并取整到
5 mm，得到本例 1.000 m 的高腰截面。直接切真实人体三角形，获得 666.06 mm 截面周长。
前／后弧分别采样并沿真实表面法向外置 7 mm；前腰约 406.684 mm，后腰约 300.237 mm，
裙腰合计约 706.921 mm。自然腰围 711.55 mm 属于更低的另一条测量路径。

`src/avatar-fit.json` 固定来源人体摘要、腰线高度、实际装配点与两片腰口尺寸；
`tools/cloth_lab/build_avatar_fit.py` 可由源资产重建。人体资产摘要改变时构建会拒绝过期
装配。腰口沿这条真实高腰线固定，裙身继续由 WASM 求解；不是自由穿脱或弹性腰头模型。

页面验收同时要求：腰口到真实皮肤间隙为 3–10 mm、装配点定位误差 ≤1 mm、前后纸样
与实际腰口边长误差 ≤1 mm。独立 NumPy 验收从源资产重新切出闭合截面并查询实际皮肤，
不导入渲染器的腰线文件；皮肤最近点腰位误差还必须 ≤2 mm。悬空或错位即 FAIL，
即使缝合为零、没有穿透且臀部仍被覆盖。极端尺寸的 >20% 应变警告保持显示。

## 同源纸样与物理材料坐标

两片扇环高腰 A 字测试纸样：前／后腰口按各自人体弧段制版，默认下摆弧长各 650 mm、径向裙长 600 mm，
10 mm 缝份。扇环角为 `(下摆弧长−腰口弧长)/裙长`，内半径为 `腰口弧长/扇环角`。
装配从真实腰口过渡到对齐骨盆的下摆初始圈，随后实际求解；展开 UV 与打印纸样使用
同一组前后尺寸，材料变形从展开坐标计算。

850 个衣片顶点、1,536 个三角形；材料 U/V 为真实展开平面坐标，丝缕沿面板中央纵向。
SVG 使用 mm，含 100 mm 校验尺；顶部和下摆缝份为同心圆偏移，侧缝为精确平行 10 mm
偏移。页面高度随扇环曲率调整，极短／大下摆时也不裁掉裁剪线。
虚拟腰口固定，尚无完整腰头、拉链或生产工艺，不是可直接批准的成衣。

## 应力、应变、碰撞和压力

WASM 以 1/120 s 求解正交各向异性 StVK 膜能量的 XPBD 约束，24 次膜迭代，随后 16 次
接触收敛迭代。理想缝合共享位置自由度，展开 UV 独立保留；弯曲仍为距离约束近似。
实际人体三角形 BVH 提供最近点和几何距离梯度，没有球、胶囊或径向代理。
缓存仅使用距离函数的保守位移界，关闭缓存的同状态对照必须逐位一致。

`F=Ds·Dm⁻¹`、`C=FᵀF`、`E=(C−I)/2`。工程最大主应变为 `sqrt(λmax(C))−1`。
正交 StVK 的 `S` 变换为切平面柯西应力 `σ=F S Fᵀ/sqrt(det(C))`，显示单位 kPa。
应力不是试衣压力，两种热图使用不同的真实标量数组。

试衣压力复用仓库 `web/pattern-pressure-bench.html` 提供的单边法向 XPBD 模块，来源
摘要在 `src/PRESSURE_PROVENANCE.json`。乘子必须非负，实际法向力为 `λ/Δt²`，压力为
该力除以当前布面节点面积。缝合节点共享接触自由度，按各面板当前面积分摊；三角形
重心保护约束的反力也计入力账本，不会漏算。

合成接触层：目标偏移 6 mm，单位面积法向刚度 1,000,000 Pa/m；面重心另有 3 mm
保护层。实际导出乘子、法向、当前面积、节点力与压力、总反力和向量合力。
检查压力面积积分等于总反力、真实接触位置与法向，以及接触方程残差 ≤0.25 mm。
腰口固定约束的反力没有计作人体接触压力；该边界仅为装配约束。

“校验 1 kPa 载荷”用同一份 WASM 的新实例计算 0.04 m² 试片，预期反力 40 N；另检验
悬空重力对照。完整验证还包含 500/1000/2000 Pa、零载、倾斜、网格细化和关闭碰撞。
这些是数值载荷校验，不是实测面料或临床舒适度标定。默认材料仍是合成参数：
E经 200 kPa、E纬 120 kPa、G 30 kPa、ν 0.2、厚 0.5 mm、220 g/m²；更软预设也未实测。

## 覆盖与真实可见结果

页面同时检查臀部／大腿上段的真实人体与布料三角面深度关系，前、后、左、右四个方向
不得露出目标皮肤。独立验收不调用这份光栅代码：从原始 MakeHuman 骨骼权重选取骨盆、
脊柱及上腿的解剖表面，在 8／16 个方位投射真实网格射线。另读取真实前／侧／背面织物
截图的臀部像素，并核对完整人体坐标、索引、统一灰色材质、不透明度及正常深度测试。
有露出即 FAIL；接缝间隙为零不再单独代表穿好了。

## 物理回放与离线文件

开始录制 → 单步／运行／移动人体 → 停止录制 → 拖动时间轴或前后查帧，支持
0.25× / 0.5× / 1× / 2× 播放。回放恢复保存的当前／上一时刻位置、固定点、接触状态、
时钟、参数以及稀疏法向接触乘子与法向，不进行物理积分。应力应变、覆盖与压力从对应
真实状态重新分析；可以从过去帧精确继续。真正的物理积分入口计数验证查帧没有重算。

JSON 和单 HTML 都包含完整轨迹及压力。格式为 v3，含前后分别定义的腰口；来源指纹不兼容的工程会拒绝导入；
旧独立 HTML 保留它自己的旧代码。最多 1,201 帧：基础状态缓冲区 40,834,000 字节；
压力稀疏样本的理论最坏总原始缓冲上限 98,145,720 字节，约 93.6 MiB。序列化有额外临时
内存，不能把这个上限解释为浏览器总内存。导入文件上限 160 MiB。

同值参数的 JSON 字段顺序不影响判断。读取文件时暂停仿真、锁定编辑，校验完成后才
原子恢复；失败保留原工程，成功和失败后均保持暂停。修改纸样／材料和重置会清空录制。
压力在碰撞关闭、人体移动未解算或风载变化后失效时会明确标为待求解，不冒充零压力通过。

## 构建与 /verify

在仓库根目录执行，先安装仅用于构建的依赖并提供 Zig 0.14.1：

```sh
npm --prefix web/cloth-lab ci
python -m pip install -r web/cloth-lab/requirements-build.txt
ZIG=/path/to/zig node web/cloth-lab/build.js
ZIG=/path/to/zig node web/cloth-lab/build.js --out dist/cloth-lab.html
```

默认生成 `web/cloth-lab/index.html` 与 `build.json`，可直接发布到 GitHub Pages。
自定义输出生成指定 HTML 及相邻的 `<文件名>.build.json`；`index.html` 对应 `build.json`。
交付时只需 HTML；相邻 JSON 用于核对构建来源，页面运行不会请求它。
`--work-dir` 可指定中间文件目录；`--help` 无需编译器即可查看用法。`ZIG`、`ESBUILD`
和 `PYTHON` 可选择现有本地工具；esbuild 也可从本地 `node_modules/.bin` 或 PATH 查找。
构建过程不会下载工具或资产。

旧的 Python 入口继续转发到同一 Node 构建器：

```sh
ZIG=/path/to/zig ESBUILD=/path/to/esbuild python scripts/build_cloth_lab.py
```

构建递归绑定源码、实际 bundle 依赖、人体／BVH、渲染器出处和许可证摘要；先完成临时
产物，再原子替换发布文件。来源不兼容或构建失败会保留原输出。release 去掉机器路径
相关的 WASM custom 元数据，可在不同源码根目录重建相同 HTML；物理可执行 sections、
ABI、16 MiB 内存和真实数值与拆分前逐字节对照。

完整本地验收：

```sh
python tools/cloth_lab/build_avatar_fit.py  # 人体资产变化时重建装配
python tools/cloth_lab/verify_modular.py --output work/cloth-lab/build-verify
python tools/cloth_lab/verify_webgpu.py --output work/cloth-lab/webgpu
python tools/cloth_lab/verify_resize.py --output work/cloth-lab/resize
python tools/cloth_lab/test_kernel.py
python tools/cloth_lab/verify_fit.py --output work/cloth-lab/fit
python tools/cloth_lab/verify_browser.py --output work/cloth-lab/browser
python tools/cloth_lab/verify_replay.py --output work/cloth-lab/replay
python tools/cloth_lab/verify_handoff.py --output work/cloth-lab/handoff
```

已使用 Zig 0.14.1、esbuild 0.25.12、Three.js r180；编译器和 Python 验证包不是运行依赖。
完整操作遵循 `.agents/skills/verify/references/cloth-lab.md`，所有检查本地执行，不依赖 CI。
源码和许可在本目录，构建摘要包含源码／人体／WASM／渲染器组合指纹及实际 HTML SHA。
根站点 `build.json` 另外记录部署 commit，不能与本目录的构建摘要混淆。

仍无布料自碰撞、CCD、完整壳弯曲、实测摩擦、面料标定或实体适体验证。压力、应变和
可见覆盖均只证明所述模型与采样状态；生产批准和 physical fit 为 NOT_RUN。
20% 局部应变警告保留，没有为了让状态变绿而提高阈值。历史 T 恤 FAIL 保持原样。
