# 来源绑定的纸样物理实验台

工作目录：仓库根；代码 `experiments/intent-edit-review/physics/`。先读该目录
README 的边界。引擎对照、初始几何、完整轨迹、界面、真人合身是不同结论。
不要将机制 PASS 或界面 PASS 写成整衣 PASS。

前提：Python 3.12及该目录requirements、Node、既有FreeSewing实验的npm依赖、
Zig 0.14.1、现有Chromium。使用新运行目录；不覆盖旧负例。原单位仍为U，
1U=1mm、标准人体和力学参数仅为明确记录的本次数值假设。

```sh
python experiments/intent-edit-review/physics/prepare_experiment.py --case baseline \
  --preparation-iterations 24 --self-step-guard \
  --output work/intent-physics/NEW-RUN --zig /absolute/path/to/zig
python experiments/intent-edit-review/physics/verify_source_mesh.py work/intent-physics/NEW-RUN
python experiments/intent-edit-review/physics/freeze_sources.py work/intent-physics/NEW-RUN
PHYSICS_PYTHON=/absolute/path/to/python \
  node experiments/intent-edit-review/physics/run_native.mjs work/intent-physics/NEW-RUN
```

初始gate失败时默认exit2，保留实际checkpoint与独立报告，不生成正式候选轨迹。
`--record-rejected-preparation` 仅用于明确标注的失败研究记录，不改判定。
gate必须从真实f32 checkpoint复核body射线及双方边面交叉、全cloth三角严格
自交、全部别名及拓扑。不能只读native顶点maxPen，也不能省略incident faces。

有完整实际记录时：

```sh
node experiments/intent-edit-review/physics/derive_folds.mjs work/intent-physics/NEW-RUN
python experiments/intent-edit-review/physics/verify_resume.py work/intent-physics/NEW-RUN
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python experiments/intent-edit-review/physics/audit_experiment.py work/intent-physics/NEW-RUN \
  --workers 2 --output work/intent-physics/NEW-RUN/audit.json
python experiments/intent-edit-review/physics/verify_controls.py work/intent-physics/NEW-RUN \
  --body-fixture /path/to/frozen/baseline-negative-run --output work/intent-physics/NEW-RUN/controls
```

并行仅调度同一独立逐帧oracle；已有0/60序列/并行全字段精确对照，不能抽查代替61帧。
body fixture要有完整input与保存坏帧；它是组件负例，不是NEW-RUN轨迹。
控制报告绑定实际WASM/C源码；C片段有变需重新准备/编译，不能套旧PASS。

```sh
python experiments/intent-edit-review/physics/build_viewer.py RUN-A RUN-B --output work/intent-physics/review
python experiments/intent-edit-review/physics/verify_viewer.py \
  --html work/intent-physics/review/index.html --run RUN-A --output work/intent-physics/ui-A
```

对每个实际case分别驱动同一HTML；随后可把这些通过且代码/数据匹配的收据传给
builder的 `--viewer-receipt`，再对最终字节复验。必须覆盖完整YAML与SVG、原文件
精确下载、输出diff/patch、每帧全数组及时钟、实际GPU颜色、15缝、真实面片点击、
速度、OBJ/JSON/HTML重开、递归离线及移动端。查看桌面、二维、完整YAML、手机截图。

大HTML的CDP Response.body可能被inspector cache逐出；用仓库
`scripts/playwright_http.new_api_context` 对同一真实URL取SHA，再正常导航。
保持TLS校验。原生file导航被管理策略拦截时记BLOCKED，断网set_content验证的
是实际下载字节，不能冒充file协议已通过。

只发布独立新路由。按根规则本地 `/verify`、直接main、非强制push；既有Pages
仅作发布。公开路由用同一verifier的 `--base-url` 再驱动，要求与候选HTML摘要一致。
记录并保留实际FAIL；历史T恤及fit NOT_RUN不得改写。

物理页还须强制无WebGL验证，不能只看软件GL正常的headless环境：

```sh
python experiments/intent-edit-review/physics/verify_svg_fallback.py \
  --html web/intent-edit-review/physics/index.html --run RUN-A --run RUN-B --output SVG-RECEIPT
python experiments/intent-edit-review/physics/verify_gpu_buffers.py \
  --expected-html-sha256 INDEPENDENTLY-FROZEN-SHA --run RUN-A --run RUN-B --output GL-RECEIPT
```

前者令getContext(webgl*)返回null，必须出现同一真实网格的SVG三维，检查切帧、字段、
相机、2D↔3D真正hidden、全文及下载；GPU统计必须为null。后者只在真实draw后读当前
color VBO，核对FLOAT3连续布局、还原绑定，等待新draw token，再与原记录NumPy颜色比较。
CPU BufferAttribute比较不能被称为GL读回；SwiftShader也不能被称为硬件GPU。

公开API取回字节和本机浏览器导航是不同证据；后者曾被环境TLS阻断，禁止ignoreHTTPS。
已连接Playwright工具若不可用，可对用户明确要求的公开app使用云浏览器实测，保留
具体工具限制。云浏览器关闭WebGL不意味着网站被bot拦截，也不能更改安全/图形设置；
页面自身应能软件绘制及读取原规格。公开测试不得用本地截图冒充。
