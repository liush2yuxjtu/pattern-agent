# 安装与复用

参考上游安装文档，建议 Python 3.11 和隔离环境。示例使用 `uv`，也可以用 `python -m venv` 与 `pip`。

```bash
git clone https://github.com/maria-korosteleva/GarmentCode.git work/GarmentCode
git -C work/GarmentCode checkout d449629979028123a5c4dc9e732a2ec19b7fce31
uv venv --python 3.11 work/venv
uv pip install --python work/venv/bin/python \
  'numpy<2' scipy pyyaml svgwrite svgpathtools psutil matplotlib CairoSVG \
  trimesh libigl cgal 'pyglet<2' pyrender setuptools wheel
```

本次验证过的直接依赖版本也记录在 `requirements-mesh.txt`，可用 `uv pip install --python work/venv/bin/python -r references/requirements-mesh.txt` 安装。

仅生成网格不需要 Warp、CUDA 或 NiceGUI。离线浏览器预览不需要 npm，也不需要服务器端 OpenGL。

## 物理仿真

```bash
git clone https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode.git work/NvidiaWarp-GarmentCode
git -C work/NvidiaWarp-GarmentCode checkout 63baf6855efdd89b2834b74640f84b3bb0d86b50
cd work/NvidiaWarp-GarmentCode
../venv/bin/python build_lib.py
cd ../..
uv pip install --python work/venv/bin/python -e work/NvidiaWarp-GarmentCode usd-core
```

CUDA 可用时运行 GPU 路径；无 CUDA 时可以编译 CPU 路径。CPU 同样需要 Warp 的运行时编译库 `warp-clang.so`。单独使用 `--no_standalone` 只生成 `warp.so`，不够运行 CPU 内核。

本次 Linux x86_64 演示中，CPU 核心使用官方修改版源码编译；运行时编译器 `warp-clang.so` 从 `warp-lang==0.15.1` 的官方 manylinux2014 轮子中提取。编译器调用需要补充第六个 `verify_fp` 参数；只复用编译器，不用轮子覆盖修改版求解器。此兼容路径经过本次实际求解测试；其他平台优先完整构建。

```bash
work/venv/bin/python scripts/setup_cpu.py \
  --warp-repo work/NvidiaWarp-GarmentCode --cache work/compiler-cache
```

将 `warp.config.kernel_cache_dir` 指向任务目录，不把缓存写到用户主目录。脚本在每次输出目录中自动设置。

网格器上游有一个粗网格警告路径引用不存在的 `Edge.name`；脚本仅为该类补充显示名称，避免警告导致异常，不改变生成算法。libigl 2.6 的显示用简化接口返回值与旧版不同，脚本支持两者。

CPU 下，Warp 的 `numpy()` 返回共享内存视图；上游按帧比较顶点时可能读到同一缓冲区而错误判断静止。脚本在每帧前复制快照，仅修正静止判断，不改变 XPBD 求解内核。

## 原脚本映射

| 目的 | 上游文件 | 本技能调用 |
|---|---|---|
| 读取纸样并生成缝合网格 | `pygarment/meshgen/boxmeshgen.py` | `BoxMesh.load()`、`serialize()` |
| 初始化布料和人体 | `pygarment/meshgen/garment.py` | `Cloth(...)` |
| XPBD 时间推进和停止 | `pygarment/meshgen/simulation.py` | `sim_frame_sequence(...)` |
| 参数与输出命名 | `pygarment/meshgen/sim_config.py` | `SimConfig`、`PathCofig` |
| 原始一键仿真 | `test_garment_sim.py` | 作为参考；避免其中固定人体与全局配置假设 |

本技能绕过服务器端图片渲染，使用离线 WebGL 预览，所以没有 EGL 显示依赖。物理求解仍然是修改版 Warp。
