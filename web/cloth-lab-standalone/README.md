# Pattern Agent 单 HTML 布料应用交付目录

在线入口：<https://liush2yuxjtu.github.io/pattern-agent/cloth-lab-standalone/>。

这是现有 `liush2yuxjtu/pattern-agent` 仓库中的新文件夹。`index.html` 是完整应用，
内嵌 MakeHuman 人体、碰撞 BVH、WASM 求解器、Three.js 渲染器、界面与程序化织纹。
页面运行不需要 CDN、后端或 MCP；交付时只需要这个 HTML。

## 文件与源码

| 文件 | 用途 |
| --- | --- |
| `index.html` | 可部署、可保存状态和回放的完整应用 |
| `build.js` | 本目录的构建入口，默认输出到本目录 |
| `build.json` | HTML、WASM、人体及全部实际源码的摘要；页面不请求它 |
| `LICENSE.txt` | 许可与第三方来源说明，完整通知也内嵌在 HTML 中 |

14 个独立 JavaScript 模块与 `solver.c` 维护在 [原始源码目录](../cloth-lab/src/)，
模块职责见 [源码与构建说明](../cloth-lab/README.md)。本入口调用同一构建器，
生成相同内容的单 HTML；修改源码后重新构建即可更新本目录。

WASM 执行布料物理，WebGPU 绘制三维场景，内嵌 JavaScript 负责界面和文件处理。
默认优先使用 WebGPU，不可用时显示实际 WebGL2 回退及原因；`?renderer=webgpu`
强制 WebGPU，失败显示 BLOCKED。WebGPU 需要支持它的浏览器及 HTTPS 或 localhost。

## 现有功能

| 能力 | 实现 |
| --- | --- |
| 人体 | 159 cm MakeHuman 女性网格，13,380 顶点、26,756 三角形，CC0 |
| 布料求解 | 固定 1/120 s 的 WASM XPBD 求解器，16 MiB 固定内存 |
| 人体碰撞 | 真实人体三角面 BVH、接触约束与穿透诊断 |
| 缝合 | 前后衣片的连接、长度、方向、缺失与缝隙检查 |
| 物理调试 | 应变、柯西应力、接触压力和碰撞距离视图 |
| 试衣验收 | 腰口位置、皮肤间隙、臀部覆盖、压力与力账本检查 |
| 物理回放 | 逐步录制、时间轴、多速播放、精确继续仿真，最多 1,201 帧 |
| 文件交付 | 毫米 SVG、米制 OBJ、工程 JSON、完整录制和状态单 HTML |

默认打开先完成真实 240 步初始试衣，再显示 READY，保留实际物理时钟。
面料和接触参数仍为合成模型；腰口固定，无布料自碰撞、CCD、完整腰头／拉链、
实测面料或实体试穿认证。

## 重新构建

在仓库根目录安装构建依赖，并提供 Zig 0.14.1：

```sh
npm --prefix web/cloth-lab ci
python -m pip install -r web/cloth-lab/requirements-build.txt
ZIG=/path/to/zig node web/cloth-lab-standalone/build.js
```

自定义输出及中间目录：

```sh
ZIG=/path/to/zig node web/cloth-lab-standalone/build.js --out dist/cloth-lab.html
ZIG=/path/to/zig node web/cloth-lab-standalone/build.js --out dist/cloth-lab.html --work-dir work/cloth-build
```

`--help` 不需要编译器；`--out` 和 `--work-dir` 转发给原构建器，原始失败退出码保留。
默认输出的相邻摘要为 `build.json`，自定义文件为 `<文件名>.build.json`。
构建工具仅在开发时使用。

本目录位于 `web/` 下，由仓库现有 GitHub Pages 发布流程直接复制部署。
发布前使用 [仓库验收流程](../../.agents/skills/verify/references/cloth-lab.md)。
已有完整的 [模块化与 WebGPU 验证记录](../../docs/verification/cloth-modular-webgpu-20261118/README.md)
保留 52 项回归、61 帧独立复算、原始失败、截图与真实软件 GPU 性能日志。
本目录发布与读回结果单独记录在
[独立目录交付验收](../../docs/verification/cloth-standalone-folder-20261119/README.md)。
