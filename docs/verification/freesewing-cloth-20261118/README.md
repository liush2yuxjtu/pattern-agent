# FreeSewing single HTML: local verification PASS

New artifact: `web/freesewing-cloth-lab.html`. Source and runnable tests:
[`experiments/freesewing_cloth_lab`](../../../experiments/freesewing_cloth_lab).
Old HTMLs and their failure receipts are preserved. This new version is an
engineering prototype; the PASS scope is the exact boundaries below.

Base commit: `801c256d982fe4814a94d186fde3ba041bc561ee`. Exact HTML SHA-256: `d684ec0289a8f04648a2e38a8ca8310d7259d9b109286130343dea06d4f17e3f`.
Size: 1,642,115 bytes. Source digests are in `candidate-files.json`.
Root `/verify` and the new package-scoped verifier were invoked before commit.
No CI or PR was added or used for verification. Existing Pages automation is
publication only. Concurrent remote changes were fast-forwarded; they did not
change this new app, its MakeHuman source or the independent geometry oracle.

## Real upstream integration

The browser really calls pinned FreeSewing Sandy 4.10.2. The actual source
Bézier half-panel is unfolded into four full skirt panels and supplies every
material coordinate, structural rest length and lumped mass. Source-native SVG,
adapted SVG/DXF/A4, sewn topology and OBJ all come from this model. Native SVG
also includes a waistband; this is not simulated. Waist support is pinned and
includes collision offset; other measurements are fixed for this profile.

An independent Node consumer imports only upstream Sandy. Python de Casteljau
reconstruction verifies the material coordinates to
2.486899575e-16 m and lumped masses to
4.440892099e-16 relative error. The actual
native SVG download is byte-identical to the independent upstream re-draft.
The original tensor/geometry/sewing/export checks remain; source-curve, fold
and curvature forgeries are additionally rejected (nine controls total).

## Physics and geometry

Actual distributed WASM is captured and separately instantiated. Analytic
12-step damped gravity, a fixed point and a distance constraint pass. Gravity
maximum error: 2.220446049250313e-15 m. Dynamic states use actual
WASM integration/constraints, actual MakeHuman BVH contacts and discrete cloth
vertex/triangle plus edge/edge contacts. No capsule replaces the body.

| State | Body intersections | Cloth self-intersections | Sampled clearance, mm |
| --- | ---: | ---: | ---: |
| step-120 | 0 | 0 | 3.051389 |
| step-240 | 0 | 0 | 3.069020 |
| step-360 | 0 | 0 | 3.034813 |
| wind-step-480 | 0 | 0 | 3.101161 |

The first three states use zero wind; the final state follows 120 steps at the
real slider maximum, 5 m/s². The initial unsimulated arrangement is preserved
separately, including its penetration; it is not a physical PASS. Each accepted
state has no interior cloth vertices and passes the strict independent triangle
oracle with 23 analytic controls. Four seam directions, lengths and notches
agree; gap is 0 mm through shared sewn positional degrees of freedom.

The independently re-drafted, actually edited 650 mm / 60% / linen profile also
passes after 120 steps: body intersections 0, cloth self-intersections 0. Its
actual state and screenshots are retained separately.

## Four fields and real GPU readback

Strain comes from F and Green strain. Material stress S uses an assumed
isotropic plane-stress law (second Piola–Kirchhoff), not contact pressure or a
calibrated Cauchy-stress result. Fold angle is the signed oriented dihedral,
flat = 0°. Spatial curvature proxy is θ/current centroid-dual spacing, m⁻¹.
Each face shows its strongest adjacent magnitude. The 15° face fraction is a
mesh-dependent geometric wrinkle indicator, not a permanent-crease law.

The independent reopener validates all 5312 hinges, normals,
adjacency, dual spacing, signed per-edge values and per-face maxima. Unit
controls cover flat, ±60°, rigid motion and spatial scaling. GPU validation
reopens the actual downloaded HTML, disables networking and reads the enabled
color attribute from the actual WebGL garment draw. It restores the buffer
binding and forwards draws unchanged. Required error <2e-6 per component:

| View | RGB components | Maximum linear-RGB error |
| --- | ---: | ---: |
| strain | 32256 | 2.978614955e-08 |
| stress | 32256 | 2.97897581e-08 |
| fold | 32256 | 2.980498703e-08 |
| curvature | 32256 | 2.979222868e-08 |

## User boundary, visual review and performance

All 44 Playwright checks pass, including real run/pause,
source/2D/3D/JSON/HTML downloads, native SVG, measured A4 pages and 100 mm square,
actual upstream option changes, all views, seam trace, cameras, orbit, reset,
mobile and exact offline next-step continuation. Browser plugin was absent;
Playwright was explicitly requested. Chromium/SwiftShader was used at
1440×1100 and 390×844. No console errors or external runtime requests.
Managed Chrome blocks file URLs; the downloaded HTML was served as the only
document, then the browser context was disconnected.

The first mobile screenshot exposed toolbar/head overlap despite passing
structural tests. The first camera adjustment was still insufficient; both
raw images are preserved. Responsive framing was corrected and the entire
final browser suite rerun. Review final desktop/mobile/fold/curvature images
before acceptance. A test-driver exact-label timeout is also retained; the
locator was corrected to the actual wrapping label, preserving physical checks.

Default solver median/p95: 71.7 /
79.6 ms/step. The existing <100 ms p95 gate
is unchanged. Wall-frame p95: 599.9 ms.
Four draw calls and 30,726 triangles. This software-rendered run does not
establish real-time performance or real-device GPU FPS. High strain/stress
values remain visible and uncalibrated; numeric field agreement is not fit
approval. Full states and raw metrics, including wind, remain in the receipts.

After remote-main reconciliation, root Pages build and all six artifact
regressions passed. Logs and source-bound receipts are retained. Raw arrays
and actual downloaded files are in per-directory ZIP archives; screenshots
are unedited. The local server is retained only until public verification.
The separate `live/` evidence will identify the application commit actually
published and repeat all relevant checks against the public file.
