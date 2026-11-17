# 单文件 WASM 布料实验室

入口：[GitHub Pages](https://liush2yuxjtu.github.io/pattern-agent/cloth-lab/)。
`index.html` 是完整交付文件：嵌入求解器、人体、BVH、渲染器与程序化织纹；
无需 CDN、后端、模型 API 或 MCP。页面可导出包含当前坐标、速度历史及材料状态的
单文件 HTML，离线重新打开后继续模拟。SVG 和 OBJ 是同一工程的另外两种输出。

## 实现边界

- 人体复用仓库 `web/human-studio/assets/human.json` 的 MakeHuman 成人女性
  CC0 资产，只做 cm → m 和落地平移，没有用基本几何体替代人体。
  13,380 顶点 / 26,756 三角形；这是通用数字人体，不是某人的扫描。
- 纸样是两片梯形测试片：腰口单片 420 mm、默认下摆单片 650 mm、裙长 600 mm，
  10 mm 缝份。虚拟腰口固定；没有完整腰头、拉链或成衣工艺。850 顶点 / 1,536
  三角形，原始二维材料坐标保留；材料 U 沿纵向丝缕（裙长），V 沿横向。不能把测试 SVG 当作已批准的生产纸样。
- WASM 中以 1/120 s 固定步长、24 次交替方向迭代求解正交各向异性 StVK
  膜能量的 XPBD 约束。理想缝合共享位置自由度，纸片 UV 独立保留。
  弯曲是独立的距离约束近似；没有完整壳单元或经过测量的面料标定。
- 碰撞是对实际人体三角形 BVH 的最近点投影，目标间隙 6 mm，包含顶点和三角形
  重心采样。距离缓存只有在“上次外部距离 − 位移 > 目标间隙”时跳过查询；这是
  距离函数的 Lipschitz 界，不是随机省略碰撞。验证器会关闭缓存做同状态 A/B，
  要求最终位置逐位相同，再用独立 trimesh 做双向边/面相交检查。
- 没有布料自碰撞、连续碰撞检测、软组织人体、实测接触摩擦或实体试穿验证。
  碰撞检查只证明所采样的离散状态，不保证任意高速运动无穿透。

## 应力、应变和热图

`F = Ds Dm⁻¹`；`C = FᵀF`；`E = (C−I)/2`。
页面“应变”显示 `sqrt(max_eigenvalue(C))−1` 的百分比，零变形为 0%。
经、纬工程应变和 Green 应变也保存在导出的三角形数据中。

材料法则：`S11 = Q11 E11 + Q12 E22`、`S22 = Q12 E11 + Q22 E22`、
`S12 = 2 G E12`，再计算 `σ = F S Fᵀ / sqrt(det(C))`。
“应力”显示表面切平面内最大主柯西应力，单位 kPa；不是人体接触压力。
三角形标量平均到顶点后驱动真实 GPU 颜色属性。热图固定量程之外会饱和，
数值面板仍显示真实极值；不得从颜色饱和推断极值大小。

默认材料为**合成参数**：E经 200 kPa、E纬 120 kPa、G 30 kPa、ν 0.2、
厚 0.5 mm、220 g/m²。它不是某款真实梭织面料的标定。更软预设也只是合成示例。
当前示例局部主应变可超过 20%，页面保留警告，不能视为成衣适体通过。
数值/热图计算正确、碰撞通过，与面料适体和生产批准是不同结论。

膜能量分解为三个标量约束：`E11+(Q12/Q11)E22`、`E22`、`2E12`，
刚度分别为 `Q11`、`Q22−Q12²/Q11`、`G` 乘以三角形面积与厚度。
XPBD 的 compliance 除以时间步长平方；每个时间步重新初始化 λ。
数值阻尼系数为每步 0.993；它不是测得的面料黏性参数。

## 源码、构建与许可

```sh
# 需要本地 Zig 0.14.1、esbuild 0.25.12 和 numpy；构建不联网。
ZIG=/path/to/zig ESBUILD=/path/to/esbuild python scripts/build_cloth_lab.py
```

`src/solver.c` 是可审查的计算内核，`src/app.js` 是实际 UI/导出/渲染入口。
构建器使用仓库中已固定的 Three.js r180（MIT）和 MakeHuman CC0 资产。
`build.json` 记录源码/渲染器/人体/WASM 的组合指纹和 HTML SHA-256；根站点的
`build.json` 另记录部署 commit。不要混淆这两个文件。
许可文本保存在 HTML 内，来源指向 Human Studio 的现有 provenance 文件。
本目录原创源码及 `tools/cloth_lab/`、构建脚本采用 MIT，见 `LICENSE.txt`。

## 本地验证 /verify

遵循 `.agents/skills/verify/references/cloth-lab.md`。不添加或依赖 CI：

```sh
python -m pip install -r tools/cloth_lab/requirements.txt
python tools/cloth_lab/test_kernel.py
python tools/cloth_lab/verify_browser.py --output work/cloth-lab/local
```

Playwright 真正操作单步、定时运行、故障选择、移动人体、下载和恢复；保存逐步
截图、真实颜色属性、无障碍快照及 FPS/帧时间/资源日志。独立 `oracle.py`
不调用运行时检测逻辑，会重新读取实际导出的身体/衣片与材料坐标：

- 重新计算缝合长度、方向、闭合；检查漏缝和反向缝合。
- 重新计算 4,770 个顶点/边中点/面重心的距离及 ray parity；同时检查衣片边→
  人体面和人体边→衣片面两种方向的相交，包含移动人体、恢复穿透的状态。
- 用 float64 重新计算所有三角形应力应变，并检查静止、刚体旋转、10% 经/纬
  拉伸和剪切试片。独立解析重力递推和初始拉伸释放能量测试实际 WASM。
- 反例必须失败：错缝长、漏缝、反向缝、关闭碰撞后的真实穿透、伪造应力、替换人体。
- 下载的 HTML 在断网环境下恢复坐标、上一帧坐标与下一步结果；不以截图代替验证。

实际物理印刷尺寸、面料试验、完整成衣适体和自碰撞均为 NOT_RUN。
历史 T 恤的 FAIL 结果保持原样，本实验不覆盖或修复那个独立边界。

参考：
- [WebAssembly.instantiate](https://developer.mozilla.org/en-US/docs/WebAssembly/Reference/JavaScript_interface/instantiate_static)
- [XPBD, Macklin 等，2016](https://matthias-research.github.io/pages/publications/XPBD.pdf)
- [CLO 缝合长度检查](https://support.clo3d.com/hc/en-us/articles/115012226027-Check-Sewing-Length)
- [CLO 服装适体图](https://support.clo3d.com/hc/en-us/articles/360000436368-Garment-Fit-Maps)
