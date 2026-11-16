# GarmentCode 纸样网格与三维预览

在线预览：<https://liush2yuxjtu.github.io/pattern-agent/garmentcode-preview/>

本目录独立保存技能、官方输入纸样、本次生成的网格和静态网页。页面可旋转、缩放、查看线框、隐藏人体，并比较初始网格和仿真结果；不在浏览器中重新计算物理。

## 文件

- `index.html`：GitHub Pages 入口，无外部 CDN 依赖。
- `offline-preview.html`：内嵌几何的独立离线预览。
- `garmentcode-preview.skill`：按 Anthropic skill-creator 指南构建的技能包。
- `skill/garmentcode-preview/`：可读技能源码、运行脚本、环境说明及测试场景。
- `example-shirt_specification.json`：官方仓库的输入示例，保持原始字节。
- `garment-initial.glb`、`garment.glb`：本次初始网格和仿真网格，以米为单位。
- `demo/`：上游输出的 OBJ、纸样图、材质、标签和配置，几何保持上游厘米单位。
- `simulation-result.json`：输入哈希、上游版本、仿真计数与验收界限。

## 实际结果与边界

输入来自 GarmentCode 官方仓库的 `assets/Patterns/shirt_mean_specification.json`，
不是从 GarmentCodeData 下载的某个条目。人体来自该仓库的 `mean_all.obj`。
本次以 1.5 cm 的网格目标间距得到 3,569 顶点和 6,958 三角形；使用项目修改版 Warp XPBD 在 CPU 上运行 232 帧，约 164 秒。

上游检测计数：人体穿透 0，自穿透 2，满足上游 GUI 的宽松默认阈值。
**本仓库的零自穿透标准未满足；严格几何发布为 FAIL，实体试穿为 NOT_RUN。**
网页与下载功能的验收，与服装几何及实际合身的验收分开记录。
没有为本次发布修改求解结果、放宽仓库验收阈值或宣称生产适用。

CPU 路径对上游静止检测作了快照修正，避免共享内存视图导致提前停止。
修改说明与复现指令在 `skill/garmentcode-preview/references/setup.md`。
技能支持 `mesh`、`simulate` 和 `existing` 三种路径；随机人体仿真需要匹配的人体文件，不会静默替换为平均人体。

## 本地预览与验证

在仓库根目录执行：

```sh
python3 scripts/build_pages.py
python3 scripts/verify_garmentcode_preview.py --output work/verify-garmentcode-preview
```

验证器直接读取 GLB 二进制结构，核对纸样和下载 SHA-256，并在真实 Chromium 中测试旋转、缩放、线框、人体开关、初始／仿真切换、下载、离线重新打开及手机布局。它不把上游检测计数当成独立物理验证。

## 来源

- GarmentCode：<https://github.com/maria-korosteleva/GarmentCode>，提交 `d449629979028123a5c4dc9e732a2ec19b7fce31`。MIT 许可证副本见 `LICENSE-GarmentCode.txt`。
- 修改版 Warp：<https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode>，提交 `63baf6855efdd89b2834b74640f84b3bb0d86b50`。本目录不分发求解器二进制，按上游 NVIDIA 许可证安装。
- 人体来源说明：`BODY-SOURCES.md`。
- GarmentCodeData：<https://doi.org/10.3929/ethz-b-000690432>，引用 Korosteleva 等人的 ECCV 2024 论文。
- 技能设计指南：<https://github.com/anthropics/skills/tree/main/skills/skill-creator>。
