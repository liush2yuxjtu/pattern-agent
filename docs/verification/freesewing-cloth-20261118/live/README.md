# FreeSewing single HTML 2.1: live PASS

Public artifact:
<https://liush2yuxjtu.github.io/pattern-agent/freesewing-cloth-lab.html?v=2778958>

Tested application commit: `27789580081307a900de0ac5ada6b765e654f7bd`.
HTML: 1,645,085 bytes, SHA-256
`a2caea0725050369387d639e1a8510bcb9e8674740c00bfd428e886d353e1dfc`.
Both the plain and versioned URLs matched the tested local file; the real root
build manifest named this commit. Existing Pages publication succeeded and
was observed separately from all local/public verification. No CI or PR was
added or used to establish the runtime verdict.

## Actual integration and physics

The delivered browser code really runs FreeSewing Sandy 4.10.2. Its native
half-panel Bézier curves are unfolded into four full skirt panels and directly
provide print outlines, material coordinates, rest distances and lumped masses.
The actual native SVG download is byte-identical to an independent upstream
Node re-draft. Independent Python reconstruction checks every material
coordinate, panel, tensor and mass; no app drafter or solver is imported.

Actual embedded WASM integrates damped gravity and solves XPBD constraints.
The prepared constant-data kernel retains float64 operations and 120 iterations.
Both original/prepared elastic APIs, analytic gravity and pinned-point controls
were tested on bytes captured from the actual public HTML. A coupled Node test
also requires exact equality with the original kernel. Actual MakeHuman
triangles supply body contact, with discrete cloth vertex/triangle and edge/edge
contact retained. No capsule substitutes for the 13,380-vertex human surface.

| Independently reopened state | Body intersections | Cloth self-intersections | Interior cloth vertices |
| --- | ---: | ---: | ---: |
| 120 steps | 0 | 0 | 0 |
| 240 steps | 0 | 0 | 0 |
| 360 steps | 0 | 0 | 0 |
| 480 steps, last 120 at wind slider 5 m/s² | 0 | 0 | 0 |
| Edited 650 mm, 60% circle, linen, 120 steps | 0 | 0 | 0 |

The first unsimulated arrangement is preserved separately and is not a physical
PASS. The strict independent triangle oracle keeps its 1 µm tolerance and 23
analytic controls. Four seam lengths/directions/notches and shell topology
agree; sewn gap is 0 mm through shared positional degrees of freedom. Both
current/previous coordinates and material coordinates match the original
accepted 2.0 arrays exactly at all four default/wind states. No grid-resolution,
iteration, tolerance or rendering-quality reduction was used.

## Stress, strain and wrinkle display

All 5,312 interior hinges, including sewn boundaries, are independently checked.
Signed dihedral θ uses oriented face normals, with flat = 0°. The discrete
spatial-curvature estimate is θ/current centroid-dual spacing, in m⁻¹. Each
triangle displays its strongest adjacent magnitude. The ≥15° face fraction is
a mesh-dependent geometric wrinkle indicator, not an area percentage or a
permanent-crease prediction. Raw signed fields and adjacency remain exported.

The actual downloaded HTML was reopened with its network disconnected. Readback
of the enabled color attribute on the actual garment WebGL draw compared all
32,256 RGB components per view for strain, stress, fold and curvature: 129,024
comparisons, each within 2e-6; observed maximum errors are about 2.98e-8.
Raw actual/expected arrays and unedited screenshots are retained in `heatmap/`.
Stress is an uncalibrated principal material stress S (second Piola–Kirchhoff)
from an assumed plane-stress model, not contact pressure or measured Cauchy stress.

## User boundary and performance

All **45 Playwright checks passed** on the public artifact. These include actual
run/pause and view/camera/orbit actions, native/adapted pattern and OBJ/JSON/HTML
downloads, actual option/material changes, measured SVG/DXF/A4 PDF units and
100 mm calibration, reset, mobile layout, saved-view consistency and exact
offline next-step continuation. No console exceptions or external runtime
requests were observed. Managed Chrome blocks `file://`; the actual saved HTML
was loaded as the only permitted HTTP document and then disconnected.

Chromium used actual ANGLE/SwiftShader software rendering. The managed host
exposed 5 CPUs with a 4-core quota; `run_check.py` restricted only its own process
and children to that allocation and recorded it in each log. No resources were
increased. Default solver median/p95: **74.0 / 87.4 ms per step**, passing the
unchanged <100 ms p95 gate. Actual rendered-frame/submission counters and rAF
callback intervals are retained separately; none establishes hardware GPU FPS
or real-time simulation. Desktop 1440×1100 and mobile 390×844 were exercised.

The first public 2.0 run failed this performance gate at 134.8 ms. Its failure is
preserved under `../first-live-performance-failure/`. Two cache experiments were
rejected and are not active: one introduced seven wind self-intersections; the
strict certificate had no speed benefit. The accepted changes reuse working
buffers/callbacks, precompute constant WASM data and redraw idle scenes on demand.
See `../performance-recovery-local/` for source-bound tests and rejected records.

Reviewed actual public fold/curvature/mobile images: the human is fully visible,
the wrapped toolbar clears the head, legends and numeric fields are readable,
and no horizontal overflow was observed. Wind and edited-profile states, other
maps, camera angles, printing and offline captures are retained for inspection.

## Scope and handoff

This is the Sandy skirt shell with a pinned waist support. The native SVG
includes a waistband that is not simulated; closure/hem construction, real print
hardware and wearer fit remain NOT_RUN. Default/wind local stretch reaches about
189%/193% of rest length; these large uncalibrated values remain visible.
Discrete checked states do not certify universal CCD, arbitrary designs or
real-fabric crease behavior. Numeric/geometry PASS is not manufacturing approval.

`receipt.json` binds the actual code commit, source hash, all raw results,
resource conditions, offline checks and visual review. Per-directory ZIPs retain
actual states/downloads; images are unedited. Browser contexts and their temporary
servers closed normally. The identified task-only local port-8771 server was
stopped; public GitHub Pages remains available.

This final commit changes evidence/documentation only: its executable-change
gate is SKIP, while the recorded public runtime verdict is PASS. The application
bytes remain those of the tested commit above. Root `/verify` was applied before
the direct-to-main evidence commit; no historical numeric receipt was rewritten.
