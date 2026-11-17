# Pattern Agent

Runnable Blender garment experiments and independent geometry checks. This is a
research repository; physical garment fit has not been verified.

## Style3D Studio integration

The [Style3D integration record](docs/style3d-integration.md) preserves the official
8.0.513 installation and Wine login-screen evidence, V10.1 MCP and CPU simulation
references, licensing limits, and the remaining DXF/sewing/simulation acceptance.
The [read-only MCP discovery CLI](tools/style3d/README.md) lists actual server tools
without modifying a garment. Its local protocol tests do not establish that
Style3D MCP or garment simulation works; the real integration remains BLOCKED
pending target-version installation and account login.

## Human Studio — articulated model with cm controls

[Open Human Studio](https://liush2yuxjtu.github.io/pattern-agent/human-studio/)
to adjust an anatomical MakeHuman adult-female mesh with 12 centimetre dimensions
and 163 bones. Change body shape, pose individual joints or use presets, then
save/import the model, render a 2×PNG, or export a posed centimetre OBJ and rigged
GLB (metres). Dimensions are calibrated from neutral-pose mesh tape paths and
landmarks; they remain separate from joint angles.

The old loft figures remain archived synthetic evaluation fixtures. The current
editor uses detailed anatomical geometry and authored skin weights.
[Source and measurement definitions](web/human-studio/README.md) ·
[verification evidence](docs/verification/human-studio-20261117/README.md).

## Apparel six-view and adjustable-body skill

The [garment-body-six-view skill](.agents/skills/garment-body-six-view/SKILL.md)
connects original apparel photos, six independent images, an adjustable neutral
body, actual 3D snapshots, OpenCV overlays and provenance-qualified parameters.
The `.claude/skills/garment-body-six-view` symlink points Claude’s skill path at the canonical source.
Download the [installable skill package](skill-packages/garment-body-six-view.skill)
or read the [installation guide](.agents/skills/garment-body-six-view/INSTALL.md).
The [published skill workflow and download](https://liush2yuxjtu.github.io/pattern-agent/garment-body/skill/) now use Human Studio: anatomical mesh, 12 cm dimensions, 163 bones, versioned state, OBJ cm / GLB m and independent neutral-mesh checks.

The [real garment case gallery](https://liush2yuxjtu.github.io/pattern-agent/garment-body/product-case/eval.html) shows the original ASOS reference, six separate native Image Gen outputs, actual anatomical renders and OpenCV before/after overlays. It preserves the failed first generation and separates conditional avatar fitting from real-person measurements. The case model opens directly in Human Studio with editable cm dimensions and joint angles.

The [single-state functional review](https://liush2yuxjtu.github.io/pattern-agent/garment-body/single-state-evals/eval.html) compares the clarified skill with its frozen predecessor in six actual subagent executions: joint cm/bone/pose/camera fitting, same-action editor persistence, and original-photo fitting. Each final body's views share one pose and mesh; numerical, browser and visual checks are reported separately.
Historical loft evaluations retain their original scope and scores.

[Native trigger evaluation tools](tools/skill_evals/README.md) include the pinned
Anthropic skill-creator, 20 balanced routing queries, a reserved final holdout and
unmeasured description candidates. Current local helper tests and CLI controls
pass; native Claude routing/hill climbing is **BLOCKED** because this execution
environment has no authenticated Claude CLI. File installation is not proof of
live auto-triggering. See the [verification receipt](docs/verification/garment-body-six-view-20261116/receipt.json).

[The subagent hill-climb benchmark](docs/verification/garment-body-subagent-hillclimb-20261117/README.md)
compares four prior descriptions and a shorter v4 candidate on development data
and a new blinded holdout. It reports explicit routing judgments, not native
Claude trigger rates; installed v0 is retained.

[Functional evaluation and review](https://liush2yuxjtu.github.io/pattern-agent/garment-body/eval.html)
contains12 real subagent executions across two iterations, actual mesh/browser
evidence, a targeted cache-state improvement and downloadable review feedback.
The current skill body includes that verified guard; its original trigger
description is retained. [Evidence and limitations](docs/verification/garment-body-functional-20261117/README.md)
separate synthetic software checks from human anatomy and image-generation quality.

Generated side/back views establish internal consistency only; their agreement
with a body proxy does not validate real anatomical dimensions or physical fit.

## 女士紧身长袖上衣原型

[打开原型预览与下载](https://liush2yuxjtu.github.io/pattern-agent/fitted-tshirt/)。原始中码裁剪文件驱动的参数化外观重建，提供三面渲染、可旋转模型、可编辑场景和完整资料包。[源码、重现步骤与限制](experiments/fitted_tshirt/README.md)保留面料差异、未解码工程文件和所有待确认项目。它不是校准的布料仿真；物理试穿和严格接缝／自交发布门槛 **NOT_RUN**，不覆盖历史实验的失败记录。

[在线上传纸样生成预览](https://pattern-agent-convert.vercel.app/) · [接口文档](https://pattern-agent-convert.vercel.app/docs) · [函数源码与部署说明](services/dxf-preview/README.md)。该服务提供独立的 Linux／Vercel FastAPI 接口：上传已支持拓扑的 DXF，返回本次计算的 GLB、报告或可断网打开的预览包。第一版仅支持上述上衣的 126 条多段线结构，显式指定单位，支持受限的平移、重排及等比缩放；不同款式需要新的裁片配置。它不运行物理布料仿真，也不创建持久任务。

## Printable straight skirt and GitHub Pages

The static download site is prepared for
[GitHub Pages](https://liush2yuxjtu.github.io/pattern-agent/). It includes the
EU40 straight-skirt preview, A4 and full-size PDFs, Chinese instructions and a
complete editable source bundle. The existing T-shirt review workbench remains
at `/pattern-agent/pattern-review/`.

The [skirt source and measurement assumptions](patterns/straight-skirt-eu40/README.md)
are tracked separately from the older T-shirt experiments. Its digital geometry
checks pass; sewn-sample and human-fit verification remain NOT_RUN.

```sh
python3 scripts/build_pages.py
python3 -m pip install -r scripts/requirements-verify.txt
python3 -m unittest discover -s scripts -p test_verify_artifacts.py -v
python3 scripts/verify_artifacts.py --cli /path/to/opensloper-cli
python3 scripts/verify_pages.py --output work/verify-pages
```

For OpenSloper on Linux x86_64, run `bash scripts/install_opensloper.sh`. It checks
the pinned official release archive and installs under ignored `work/tools/`.
The project `.mcp.json` starts the installed CLI through
`scripts/opensloper-mcp.sh`. Set `OPENSLOPER_CLI` to use another installation.

`.github/workflows/pages.yml` performs publication only: build static files,
upload the Pages artifact, and deploy. Generic verification stays local. GitHub
Pages must use **Settings → Pages → Source → GitHub Actions**; this workflow does
not change account permissions, enable paid services, or bypass environment rules.
The working verification recipe and receipt are in `.agents/skills/verify/`
and `docs/verification/`.

## GarmentCode mesh and 3D preview

[Open the GarmentCode 3D preview](https://liush2yuxjtu.github.io/pattern-agent/garmentcode-preview/)
to rotate the generated garment, inspect its wireframe, compare the initial and
CPU-simulated meshes, and download the skill, GLB, input pattern or offline viewer.
The [separate handoff folder](web/garmentcode-preview/README.md) includes readable
skill source and simulation provenance. This is an official repository example,
not a downloaded GarmentCodeData row. The 232-frame result has two self-intersection
counts: strict zero-intersection geometry release is **FAIL**, physical fit **NOT_RUN**.

The installable [agent skill](.agents/skills/garmentcode-preview/SKILL.md) has a
Claude discovery link and a generated, byte-checked web download.
[Optimization evidence](docs/verification/garmentcode-skill-optimization-20261116/README.md)
records real old/new CPU runs, standalone existing-mesh preview, missing-body
controls, and routing-proxy evaluations. Native activation remains separately BLOCKED.

## Aster developable dress studio

[Open the Three.js studio](https://aster-pattern-studio-161126.liushiyuxjtu.chatgpt.site/)
or [open expert 3D and 2D review](https://aster-pattern-studio-161126.liushiyuxjtu.chatgpt.site/#review).
The [self-contained handoff](experiments/aster_dress/README.md) preserves the HTML,
readable source, full-scale SVG, seam map checks, decisions and verification record.
It models 8 conical bodice sectors and 8 skirt gores with 24 releasable seam pairs.

Geometry checks and 13 DOM integration checks pass. Real-browser visual/GPU
verification is BLOCKED in the build environment; fabric mechanics and human fit
are NOT_RUN. This is a developable concept study, not a production garment block.
The [repository handoff receipt](docs/verification/aster-20261116/receipt.json)
records the candidate source manifest, commands and verification limits.

### Vercel deployments

- **Current Aster production:** [3D studio](https://aster-dress-pattern-studio.vercel.app/) · [expert 3D/2D review](https://aster-dress-pattern-studio.vercel.app/#review).
- **Downloads:** [standalone HTML](https://aster-dress-pattern-studio.vercel.app/aster-studio.html) · [complete handoff ZIP](https://aster-dress-pattern-studio.vercel.app/aster-handoff.zip).
- **Original Sites publication:** [Aster on Sites](https://aster-pattern-studio-161126.liushiyuxjtu.chatgpt.site/) remains available.

| Published | Variant | Vercel project | Artifact source | Fixed deployment URL |
| --- | --- | --- | --- | --- |
| 2026-11-16 | Aster 01 developable dress | `aster-dress-pattern-studio` | [8555490](https://github.com/liush2yuxjtu/pattern-agent/commit/855549017ec7bdf92c1dccca303c9cfcfe2042e7), `experiments/aster_dress/` | [Aster 01 snapshot](https://aster-dress-pattern-studio-fagpddri4-nyn5255-8475s-projects.vercel.app/) |

Deployment ID: `dpl_CSyNWEo8fVhkX2UEkcLuMaK94UCb`. This is a manual static-file
publication, with no Git-connected CI or automatic build pipeline. The production
alias may point to a later release; the fixed URL identifies this deployment.
For subsequent releases, append a dated row with its artifact commit and fixed
URL. Keep distinct design variants in separately identified projects and preserve
older rows. The related `pattern-agent-review` and `first-skirt-pattern-9gla3`
projects are separate from Aster and were not replaced.

**Deployment verification:** Vercel reports READY. Connector HTTP retrieval returned
200 for the production HTML, fixed-deployment HTML and baseline SVG; their full
contents matched the uploaded artifacts exactly. These are publication/integrity
checks, not browser or garment acceptance. The live Playwright command
`node verify-live.mjs` using Chromium at the fixed URL stopped at
`page.goto: net::ERR_TUNNEL_CONNECTION_FAILED`, before any interaction ran.
Real-browser application acceptance remains **BLOCKED**. The earlier 30,720
geometry-edge comparisons, 96 seam-pair checks and 13 DOM checks retain their
limited scope; cloth behavior and physical fit remain NOT_RUN.

## Current full-arm experiment

Code is in `experiments/full_arm/`. It creates a complete synthetic mannequin and
preassembled T-shirt, runs real Blender Cloth, exports measured meshes, checks
every saved frame, and creates a portable replay with independent reload checks.

The preserved 241-frame experiment has **arm-routing checks PASS in all 241
frames**, but **cloth geometry FAIL in 161 frames**. Cloth self-intersections peak
at 535 pairs; cloth/body and body self-intersections are zero. These numbers do
not establish armhole sizing, calibrated material behavior, or physical fit.

```sh
cd experiments/full_arm
python3 -m unittest discover -s verification -p test_pipeline_gate.py -v
blender -b -t 1 --python-exit-code 2 --python verification/test_geometry.py
python3 run_pipeline.py --out runs/full-arm --frames 241 --render-video
```

Prerequisites: Python 3.11+, Blender 4.3.2 with NumPy, and FFmpeg for video.
The selected full-motion baseline intentionally exits 2 for quality failure;
execution completion is separate from the physical and geometric verdict.
Use a fresh output directory to preserve evidence.

## Controlled verification experiment

The completed [one-shot control experiment](experiments/oneshot_control/README.md)
includes a standalone full-body model and T-shirt, independent geometry code,
input fixtures and results. Four positive controls pass; eight invalid cases
are rejected by the independent static gate.

**Both problems are real:** the strict v2 audit of all241 old frames confirms161
frames with garment self-crossings and a595-pair peak. Earlier v1 evidence is
historical and incomplete because v1 also excluded shared-vertex pairs.
new controls expose false approvals for a displaced body with stale paths and
64 coplanar overlaps omitted by the legacy Blender BVH. A clean static mesh does
not establish cloth simulation or physical fit. Download the two files in
[`experiments/oneshot_control/assets/`](experiments/oneshot_control/assets/).

The exact recovered single-file dynamic generators and a newly executed121-frame
reproduction are in [`experiments/oneshot_motion`](experiments/oneshot_motion/).
Its portable model/cloth files, all saved meshes and independent reload evidence
are retained separately from the analytic rectangular controls.

## Verification and history

The [one-shot pattern roundtrip](experiments/pattern_roundtrip/README.md) separates
the human/cloth into pure standalone files, unwraps4 actual2D panels and challenges
armhole fit independently. Representation checks pass, each armhole/cap has a
23.27mm transfer mismatch, and the forward solver fails atlas invariance. Real
fit remains UNKNOWN; the source patterns have no seam allowance.

Follow `AGENTS.md` and `.agents/skills/verify/SKILL.md` before committing.
Runtime recipes and observations are recorded under `docs/verification/`.
No generic GitHub Actions verification workflow is used.

The recovered original documentation is preserved in
[`docs/historical-tshirt-readme.md`](docs/historical-tshirt-readme.md). Its referenced
paper-pattern implementation and original assets are not currently restored in
this checkout. Its historical 7.6455 mm seam gap and 20 self-intersection FAIL
remain separate from the newer synthetic experiment.

Private workspace notes and connected-storage artifacts are maintained outside
this public repository.


The [anatomical skill functional review](https://liush2yuxjtu.github.io/pattern-agent/garment-body/anatomical-evals/eval.html) contains 14 executed subagent runs, real mesh fits, OpenCV overlays, projected joints and raw depth checks. The selected core instructions are 40.03% shorter; this is not an end-to-end clothed image generation benchmark or a native Claude trigger score.

## 单文件 WASM 布料实验室

[在线打开](https://liush2yuxjtu.github.io/pattern-agent/cloth-lab/) ·
[实现与复现](web/cloth-lab/README.md) ·
[本地验证配方](.agents/skills/verify/references/cloth-lab.md)。

同一份毫米纸样驱动二维 SVG 和三维材料坐标；单个 HTML 内嵌 WASM、Three.js
以及 MakeHuman 成人女性资产。实际人体三角形 BVH 碰撞、理想缝合、正交各向异性
StVK 应力应变、故障对照与状态化离线 HTML 导出均有独立数值及浏览器验证。
材料是合成参数，局部高应变保留可见警告；没有布料自碰撞、实物标定或实体适体批准。
这不改变历史 T 恤 FAIL，也不将几何/热图验证升级为生产批准。
