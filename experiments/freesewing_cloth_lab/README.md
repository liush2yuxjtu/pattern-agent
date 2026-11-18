# FreeSewing → single-file cloth and wrinkle laboratory

Version 2.4 artifact: `web/freesewing-webgpu.html`.
The 2.3 zero-pin reference remains `web/freesewing-free-waist.html`. The historical pinned
2.2 artifact remains `web/freesewing-cloth-lab.html`. Earlier HTML files and their
historical failures are preserved. No runtime CDN, MCP or server dependency.

The browser really instantiates `@freesewing/sandy@4.10.2`, using the pinned
FreeSewing core/plugins. Its actual Bézier waist/hem curves supply both the 2D
printable outlines and every triangle's material coordinates. A native Sandy
half-panel is mirrored across its cut-on-fold line into a full panel; four full
panels form the simulated skirt. Changing length/circle ratio re-drafts Sandy.
The native source SVG also contains a waistband; that waistband is NOT simulated.
The waist circumference is the MakeHuman support-ring length including collision
offset. The other measurements are fixed for this supported straight-waistband
profile; this is not an automatic personal body-measurement service.

WASM integrates damped gravity and solves XPBD distance constraints. Bending
uses rest-distance approximations, not a calibrated shell law. Rest lengths and
lumped particle masses come from the actual material-coordinate triangles.
The existing body contact queries the actual 13,380-vertex MakeHuman CC0 mesh;
discrete vertex/triangle and edge/edge cloth contacts are retained.

Version 2.3 removes all 64 waist pins: all 1,856 particles have finite positive
mass and move under gravity (-9.81 m/s²). The reinforced closed waist edge uses
mass-weighted rigid shape matching, preserving free translation/rotation and
mass center. It is a stiff belt approximation, not a simulated native waistband.
Body-normal projection and accumulated Coulomb friction (μ=0.6), coupled inside
all 120 cloth iterations, carry the weight. No world/body anchors are stored.
The initial waist is at 1.09 m; circle ratio defaults to 60%. The native waist
perimeter follows the 5 mm body-offset section, with a 3 mm assembly gap.
Velocity drag is 0.98 per 1/120 s (uncalibrated dissipative damping); the prior
0.992 candidate oscillated above the unchanged 12-second settling threshold.
Exported support arrays permit independent mass/force/COM and Coulomb audits.
Removing the actual collider must cause the whole garment to fall under gravity.
Exact-position body-query memoization reuses only bit-identical queries on the
immutable body. Equal-mass WASM corrections reuse an identical division; the
self-contact sweep tests other-axis bounds before loading edge endpoints, with
the same candidate order/set. No cloth resolution or iteration count is reduced.

Strain/stress diagnostics reconstruct F = Ds Dm⁻¹ and Green strain. Stress is an
assumed isotropic plane-stress material estimate (maximum tensile principal second Piola–Kirchhoff stress S). It is not contact pressure or a calibrated Cauchy-stress result.
100% stretch means rest length (0% engineering extension).

New fold fields cover every interior edge, including sewn panel boundaries:

- signed dihedral θ = atan2(ê·(n₁×n₂), n₁·n₂); flat = 0°;
- current dual spacing d = (h₁ + h₂)/3, with h measured perpendicular to the edge;
- discrete spatial curvature estimate κ = θ/d, in m⁻¹;
- each face displays the strongest adjacent |θ| or |κ|;
- the fraction of faces with |θ| ≥15° is a mesh-dependent geometric wrinkle
  proxy. It is not an area percentage or a permanent-crease predictor.

Signed per-edge/per-face values, adjacency, current/previous coordinates, UVs,
upstream drafting settings and sewing relationships are exported in JSON.
SVG/DXF/A4 use millimetres; OBJ uses metres. Saved HTML retains exact state and
next-step continuation. Body geometry, WASM, libraries and licenses are embedded.

## Hardware WebGPU rendering and compatibility

The new default artifact requests a high-performance WebGPU adapter. Hardware
adapters use Three.js WebGPURenderer and TSL-generated WGSL, including the
procedural weave and all five diagnostic maps. Software/fallback adapters,
unavailable WebGPU and initialization denial select the WebGL2 compatibility
renderer. The UI/export identify the actual renderer, adapter and fallback
reason. `?renderer=webgpu` forces the diagnostic software path;
`?renderer=webgl` selects compatibility explicitly. Both engines are embedded.

Physics is still **WASM Float64 on the CPU**, not a WebGPU cloth solver. Its
120 iterations, gravity, contacts and reinforced waist model are retained.
Three's GPU upload widens indices in place: a value-identical body render clone
protects the collision BVH's immutable indices. Pinned Three math for collision
is isolated from renderer math, while both collision geometries share the same
BufferAttribute implementation. Immutable face normals and frozen broad-phase
bounds are cached without changing arithmetic or candidate order. Actual state
arrays are checked bit for bit against the accepted 2.3 trajectory.

One GPU node material switches between weave and diagnostic colors using a
uniform. Shadow resources are created by the actual first render (not a separate
precompile pass); readiness waits for that frame. Resize ignores zero dimensions.
The frame queue applies backpressure. An actual device-loss pauses physics and
lets the reader recover to WebGL2 with exact state retained. Saved HTML selects
its renderer again for the next reader's capabilities.

`render.triangles` records submitted passes, including shadows (and GPU output
presentation); `sceneTriangles` counts the unchanged scene geometry once.
The original 50,000-scene-triangle budget applies to the latter; the 100 ms p95
solver threshold is unchanged. CPU submit time, fenced completed-frame latency
and hardware GPU-only time are different metrics. This host has only software
GPU support; actual hardware speedup remains NOT_RUN. Forced software WebGPU
performance failures are retained and never labeled as a full UI PASS.

## Build and run

Node 24 was used. FreeSewing 4.10.2 additionally needs its `config` and
`plugin-transform` packages explicitly installed because upstream packages
reference them without complete npm dependency declarations. They are pinned
in this package and lockfile. Build tools run only during development and bundling; the delivered HTML does not load them.

```sh
npm ci --ignore-scripts --prefix experiments/freesewing_cloth_lab
node experiments/freesewing_cloth_lab/test_pattern_fold.mjs
node experiments/freesewing_cloth_lab/test_self_contact.mjs
node experiments/freesewing_cloth_lab/build.mjs
node experiments/freesewing_cloth_lab/test_prepared_solver.mjs
node experiments/freesewing_cloth_lab/test_waist_ring.mjs
python -m http.server 8771 --bind 127.0.0.1 --directory web
```

Open <http://127.0.0.1:8771/freesewing-webgpu.html>.

## Verify the actual artifact

Use the root `/verify` workflow and this package's scoped verifier. Python needs
NumPy, SciPy, PyMuPDF and Playwright; system Chromium is used. The project geometry
oracle supplies independent triangle intersections and solid-angle membership.

```sh
python experiments/freesewing_cloth_lab/run_check.py browser \
  --url http://127.0.0.1:8771/freesewing-webgpu.html --out work/fs-browser
python experiments/freesewing_cloth_lab/run_check.py independent \
  work/fs-browser/simulation.json --repo . --out work/fs-browser/independent.json
python experiments/freesewing_cloth_lab/run_check.py gpu \
  --html work/fs-browser/downloaded.html --output work/fs-heatmap
python experiments/freesewing_cloth_lab/run_check.py dynamics \
  --url http://127.0.0.1:8771/freesewing-webgpu.html --output work/fs-dynamics
python experiments/freesewing_cloth_lab/run_check.py variant \
  --url http://127.0.0.1:8771/freesewing-webgpu.html --output work/fs-variant
python experiments/freesewing_cloth_lab/run_check.py support \
  --url http://127.0.0.1:8771/freesewing-webgpu.html --output work/fs-support
```

The independent reopener imports no application drafter or solver. A separate
Node consumer runs the upstream Sandy design; Python uses de Casteljau evaluation
to reconstruct all material coordinates and panels, checks lumped masses, then
recomputes tensors, oriented hinges, dual spacing and per-face fields. It also
compares the real native SVG download byte for byte to the independent re-draft.
Original fault controls remain; forged upstream curves/fold/curvature are added.

The GPU test reads the enabled color attribute on the actual garment draw,
restores the previous buffer binding and compares all RGB components against
independently validated fields. It covers strain, stress, fold and curvature.
The dynamics test checks actual WASM gravity/pins/elasticity and 120/240/360 steps
plus 120 more at the real 5 m/s² wind slider maximum. A separate real-input
variant changes length to 650 mm, circle ratio to 60% and material to linen.

No fit/manufacturing/calibration/real-time claim follows from numeric PASS.
Large deformation remains visible. Universal continuous collision detection,
arbitrary designs/parameters, physical print hardware, waistband/closure/hem
construction and real-fabric wrinkle or crease behavior remain unvalidated.

Libraries are bundled at build time. This is not a zero-third-party-code claim:
FreeSewing, Three.js, three-mesh-bvh and their runtime dependencies are third-party
open-source code with embedded license notices. No third-party service or MCP
is required to run the delivered HTML.

## Performance recovery (2.1)

The first public 2.0 run failed the unchanged 100 ms p95 solver gate despite
passing functional checks. Its raw failure is preserved. Two query-cache
prototypes were rejected: geometric exclusion changed the trajectory and caused
seven wind self-intersections; the stricter plane certificate preserved the
trajectory but its construction cost erased the performance benefit. Neither
cache is active in the delivered solver. Their tests, source and states are
archived with the performance-recovery evidence.

Version 2.1 reuses the per-step history, contact masks and vectors, and evaluates
the same barycentric sums/projections without temporary arrays or callbacks.
All body queries, margins, constraint iterations and grid dimensions are kept.
An actual baseline/candidate A/B requires exact current/previous/material
coordinate equality; the full geometry matrix is rerun on the final artifact.

Idle scenes redraw only when geometry, material, camera or viewport changes.
`renderedFrames` counts actual submitted draws, `render_submit_ms_p95` measures
CPU submission time, and `frame_ms_p95` records rAF callback intervals. These
are not interchangeable with hardware FPS or GPU frame time. Saved HTML now
restores its selected heatmap and wire view as well as its physical state.

Historical 2.1/2.2 A/B only (not applicable to changed 2.3 boundary conditions):
save the actual 2.0 HTML from application commit
`94d41253442400afb6d8a0bcee4c8a45f5d7e62b`, then run:

```sh
python experiments/freesewing_cloth_lab/verify_allocation_ab.py \
  --url http://127.0.0.1:8771/freesewing-cloth-lab.html \
  --baseline-html work/baseline-2.0.html --output work/allocation-ab
```

The fixed-timestep WASM kernel additionally prepares constant addresses, masses,
compliance and denominators once per draft. Its float64 iteration preserves the
original operation order. A five-frame coupled unequal-mass/compliance test
requires bit-identical positions/previous coordinates against the original
WASM export; the actual prepared export is also probed by the dynamics verifier.

Use `run_check.py` for repeatable headless QA. On the observed host, five CPUs
were visible while the cgroup quota was four. The wrapper limits only its own
process and children to the allocated CPU count; it grants no extra resources.
It logs the exact affinity/quota and leaves all geometry, render quality and
performance gates unchanged. Report these software-rendering conditions with
results; they are not a hardware frame-rate measurement.

## Coverage and contact pressure (2.2)

Previously the first screen showed an unrelaxed arrangement: 52 of 153 posterior
body vertices were visible through the skirt. Normal startup, UI reset and
pattern changes now complete 120 actual gravity/body/self-contact steps before
showing the mesh. The explicit API `reset()` still exposes the raw diagnostic
state for regression tests. Camera presets render immediately so a saved Back
screenshot cannot silently contain the previous Front frame.

`independent_contact.py` projects actual cloth triangles into XY and checks -Z
visibility against 153 posterior body vertices plus 313 body-triangle centroids.
It uses no runtime BVH/raycaster. The raw arrangement has 150 exposed samples;
accepted states require zero. Removing cloth must also fail. This is a bounded
sampling check in the stated posterior pelvic region, not universal coverage.

The Pressure view uses per-step accumulated positive body-normal projection
corrections. For free vertices its estimated reaction is F = m Δn / Δt² and
p = F / A (kPa after /1000), with area lumped from material triangles and mass
from areal density. In historical 2.2 it excludes pinned waist reactions; 2.3 has no pins and includes
all waist reactions. The independent audit
reconstructs A and m from upstream UV triangles and checks the exported forces,
pressures and actual GPU colors. Saved HTML retains these fields exactly.
This estimate depends on timestep/projection order and lacks calibrated fabric,
contact compliance and wearer measurements. It must never be presented as
validated medical/comfort pressure or confused with material stress.

Stress/strain/fold calculations and geometry acceptance do not establish garment
fit: e.g. the default 360-step state still has a peak principal stretch of 189.5%
and uses uncalibrated material parameters. Real material/fit acceptance remains
NOT_VALIDATED.


WebGPU acceptance adds native WGSL/queue/draw proof, readback of the exact color
buffer bound by the cloth draw (32,256 components per view), five distinct canvas
images, GPU body buffer/collider identity, saved-file reopening, actual device
destruction and exact recovery, and missing/null/denied adapter fallbacks:

```sh
CLOTH_WEBGPU=1 python experiments/freesewing_cloth_lab/run_check.py webgpu \
  --url http://127.0.0.1:8771/freesewing-webgpu.html --output work/fs-webgpu
CLOTH_WEBGPU=1 python experiments/freesewing_cloth_lab/run_check.py webgpu \
  --url http://127.0.0.1:8771/freesewing-webgpu.html --output work/fs-webgpu --timing-only
```

Run timing alone, after other browsers finish. This test-only environment uses
SwiftShader/Vulkan with its surface enabled; readers need no Chromium flags.
The normal UI suite now has 52 checks, including actual backend and nonblank
mobile canvas. Forced software WebGPU is a separate diagnostic: preserve a FAIL
when its p95 exceeds 100 ms. Do not silently omit that check or describe it as
hardware acceleration. See `docs/verification/cloth-webgpu-20261118/`.
