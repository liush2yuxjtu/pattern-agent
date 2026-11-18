# Public single HTML: repeated verification PASS

Application commit: `58f8300371621a4328d4e2aa69d27e0ef91227e4`.

Public URL: <https://liush2yuxjtu.github.io/pattern-agent/cloth-lab-self-contact.html>.
Public HTML SHA-256:
`5e035050cf7a940c81928c98073bd412beb6114bfe8e37f7cb25ef3e6252cf83`.
Size: 1,427,149 bytes. The plain and cache-busted public responses matched the
locally tested file, and the actual root `/build.json` names this application
commit. The existing publication job succeeded; it did not run verification.
One pre-publication 404 while the deploy step was in progress is preserved.

Before the evidence commit, remote main advanced to
`ddfb02905e5ea66dea1423580621d54a9a4b28ac`, adding only the separate
`web/pattern-fitting-bench.html`. It was fast-forwarded locally. The final public
root build names that newer commit; the public self-contact HTML still has the
exact same SHA-256. Our runtime/source diff from the tested application commit
is empty. See `final-public-readback.json`; the final Pages build and six root
artifact regressions were repeated after reconciliation and passed.

Root `/verify` and the source directory's scoped verifier were followed again
before this evidence/test commit. No application bytes changed after the
application commit. This commit adds the GPU verifier and its passing evidence,
documents its working command, and corrects two rounded clearance numbers in
this run's newly written local report. No pre-existing HTML or old failure
receipt was changed.

## Real public browser and discrete physics

All **39 Playwright checks passed** on the public URL, including actual clicks,
downloads, offline next-step equality, changed dimensions/material, PDF and
mobile layout. The actual exported OBJ/SVG/DXF were independently reopened and
matched the simulation and source patterns. The six adversarial faults were
rejected again. Browser exceptions and console errors: 0.

| State | Body intersections | Cloth self-intersections | Interior vertices | Min. sampled clearance |
| --- | ---: | ---: | ---: | ---: |
| 120 steps | 0 | 0 | 0 | 3.005609 mm |
| 240 steps | 0 | 0 | 0 | 3.017321 mm |
| 360 steps | 0 | 0 | 0 | 3.026554 mm |
| 480 steps, last 120 at 5 m/s² | 0 | 0 | 0 | 3.005452 mm |

All four public states' current AND previous coordinates were bit-identical to
the accepted local run. The actual public WASM gravity probe, pinned point,
elastic constraint, gravity movement and real wind-input response passed.
Triangle intersection detection is independent of the runtime BVH and contact
solver, with analytic controls run before the physical mesh audit.

Default solver median/p95: **76.3 / 92.6 ms per fixed step**, below the unchanged
100 ms p95 gate. Wall-frame p95: **633.3 ms**, using SwiftShader software
rendering. Draw calls: 4. Triangles: 30,726. These measurements do not demonstrate
real-time simulation or hardware GPU frame rate. The dynamics run's separate
performance data is retained in its raw receipt.

## Heatmap data reaches the actual GPU draw

The new `verify_heatmap_gpu.py` reopens the real public page's downloaded HTML
and disables the browser context's network. It forwards each WebGL draw call
unchanged, then reads the active `color` attribute's actual GPU buffer with
`getBufferSubData`. The previous buffer binding is restored.

NumPy independently reconstructs F, C, Green strain and the assumed principal
plane stress from the saved positions and material coordinates. It then
independently interpolates the documented ramp in linear RGB after converting
the six sRGB endpoint colors. All **32,256 RGB components per view** agree:

| Field | Maximum linear-RGB error | Gate | Result |
| --- | ---: | ---: | --- |
| Principal stretch | 2.9777832422084316e-8 | <2e-6 | PASS |
| Estimated principal stress | 2.978502178230258e-8 | <2e-6 | PASS |

The attribute is an enabled three-component FLOAT input on the actual garment
draw. Raw actual/expected arrays are in `heatmap/*.npz`. The saved HTML hash is
bound to the real browser download, and its restored coordinates/next step
were already checked exactly. The restored page starts with READY and requires
fresh verification; the heatmap check itself does not grant a new fit approval.

## Visual evidence and limits

Reviewed the raw public fabric/contact/mobile screenshots, public strong-wind
fabric, and both GPU-readback heatmap screenshots. The full human and garment
are visible; gold/teal contact regions and legends are visible; the mobile page
has readable controls and no horizontal overflow. The stress/strain fields show
localized high-deformation regions. Screenshots are unedited.

Local and public collision checks agree, but high stretch remains: 153.48% of
rest length at step 360 and 273.32% with wind. The estimated stress is 65.32 kPa
and 294.66 kPa. These are uncalibrated-model estimates; they do not validate cotton
behavior, sewing manufacture, physical print hardware or wearer fit. The waist
is pinned. Four discrete states do not certify arbitrary motion or universal
continuous collision detection. The original strong-wind self-intersection
failure remains a separate FAIL in the parent evidence directory.

Commands and exact outcomes are recorded in `receipt.json` and the original
logs. Actual exported files/states are in the per-directory
`actual-arrays-and-downloads.zip` archives. Browser contexts and the heatmap
script's temporary server closed normally. The task-owned local port 8770
server is stopped after verification; public Pages remains available.
