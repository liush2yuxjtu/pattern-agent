# Inline WASM cloth laboratory

Working directory: repository root. Scope: `web/cloth-lab/`,
`scripts/build_cloth_lab.py`, `tools/cloth_lab/`, and its link on the Pages index.
This recipe does not approve the historical T-shirt or calibrate physical fit.

## Prerequisites and candidate

Use Python + `tools/cloth_lab/requirements.txt`, Node, system Chromium, Zig
0.14.1 and esbuild 0.25.12. Set `ZIG` and `ESBUILD` to existing executables.
Neither compiler nor Python verification packages are runtime dependencies.
The builder uses only committed MakeHuman CC0 and Three.js r180 MIT sources.
Record base commit, `web/cloth-lab/build.json` source/HTML/WASM/body hashes,
changed file hashes and raw command exit statuses before each commit.

```sh
python scripts/build_cloth_lab.py
python tools/cloth_lab/test_kernel.py
python tools/cloth_lab/verify_fit.py --output work/cloth-lab/fit
python tools/cloth_lab/verify_browser.py --output work/cloth-lab/local
python tools/cloth_lab/verify_replay.py --output work/cloth-lab/replay
python tools/cloth_lab/verify_handoff.py --output work/cloth-lab/handoff
python scripts/build_pages.py
python -m unittest discover -s scripts -p test_verify_artifacts.py -v
python scripts/verify_pages.py --output work/cloth-lab/pages
git diff --check
```

The adjacent unchanged printable/download surface retains the independent native
OpenSloper assertions in [github-pages](github-pages.md). Do not replace native
reopen with a screenshot when claiming that boundary.

## Frozen numerical and user-surface contract

- Actual exported WASM (not a fallback): fixed 16 MiB memory; unconstrained gravity
  matches the independently calculated damped recurrence within 2 µm over 12
  steps; one elastic step reduces a stretched triangle's membrane energy.
- Real Playwright clicks drive single-step, timed advance, run/pause, material
  views, faults, downloads and resets. Preserve initial/1/60/300 user-step screenshots (initial actual frame is 240 after real pre-drape),
  front/side/back, desktop/mobile accessibility snapshots and shader color data.
- Reopen the actual exported current/previous positions, UVs, seam pairs, body,
  OBJ, SVG and HTML. SVG has mm dimensions and a 100 mm bar; OBJ includes both
  actual body and cloth in metres. Two-panel test pattern, not a finished skirt.
- Independent `oracle.py` reconstructs rest UV dimensions, computes actual seam
  polyline lengths/directions and requires length mismatch <=1 mm, sewn gap
  <=2 mm, complete joins and valid orientation for the good case.
- The actual exported MakeHuman mesh must match the committed source fingerprint,
  positions and topology, be closed and consistently wound. Independently check
  4,770 cloth vertices/edge midpoints/centroids by trimesh signed distance and ray
  parity: penetration <=0.2 mm. Require zero intersections in BOTH cloth-edge →
  body-face and body-edge → cloth-face segment tests, including the moved-body
  and recovered-penetration snapshots. This is discrete, not CCD certification.
- Recompute F, C, Green strain, engineering strain and tangent-plane Cauchy stress
  with independent float64 NumPy. Stress absolute tolerance 0.15 Pa plus rtol
  3e-4; strain atol 2e-5 plus rtol 3e-4. Rest, rigid rotation, 10% warp/weft
  extension and shear coupons must agree. GPU color attributes must actually
  derive from the corresponding scalar field, within 2e-6 RGB components.
- Negative controls must be REJECTED: unequal lengths, omitted join, reversed
  sewing, actual injected body penetration with contact disabled, fabricated
  stress values and substituted body geometry. A zero gap alone is insufficient.
- Reopen the downloaded stateful HTML with network disabled: zero requests,
  exact position/previous arrays, and exact next-step continuation. No page,
  console or HTTP errors. At 390 px, no horizontal overflow. Ten reset clicks
  retain geometry/texture counts and WASM allocation.
- Log real renderer string, software/hardware classification, pixel ratio,
  frame times (median/p95), fixed solver step cost, dropped wall time and resource
  counts. Do not infer hardware FPS from SwiftShader. There is no fabricated FPS
  target. Preserve performance regressions instead of hiding them.
- High local strain remains a VISIBLE warning, not garment approval. The 20% warning threshold remains unchanged; the measured high-waist default is about 17.5%. Numerical heatmap correctness is
  different from fit acceptance. Material calibration, cloth self-collision,
  continuous collision detection, finished construction and physical fit NOT_RUN.

`verify_browser.py` owns a temporary HTTP server and closes its browsers/server.
It tests the exact HTML. Raw evidence belongs in ignored `work/cloth-lab/`;
copy selected receipts, actual exports and images to `docs/verification/`.

## Full physical replay

`verify_replay.py` drives the visible record/stop/timeline/step/transport/speed/file
controls. It wraps the actual WASM integration export only to count invocations;
the solver is never replaced. A 60-step recording must have 61 exact states and
the actual solver clock. Independently decode the raw Float32 buffers and reopen
EVERY frame with `oracle.py`: full sewing, 4,770 body samples, BOTH intersection
directions, and all 1,536 triangle tensors. Seek/play must make zero integration
calls and restore current/previous/pins/contacts/clock/parameters exactly. Check
actual stress and strain GPU buffers, keyboard scrubbing, previous/next, pause,
all four playback speeds (browser click-to-completion time, excluding automation
waiting), JSON import/export, offline HTML with the timeline,
recursive saving, and bit-exact continuation including moved-body pins.

Record actual injected penetration and all three sewing faults; their replayed
frames must remain FAIL. Reject incompatible source, oversized/corrupt buffers,
invalid parameters and selected-state disagreement BEFORE altering the scene.
Run the solver beyond the actual 1,201-frame cap: recording stops, existing data
remain seekable and base position/history state-buffer bytes stay <=40,834,000; sparse pressure multipliers/normals are counted separately, with total raw bound 98,145,720 bytes. Preserve raw per-frame
oracle results and record/copy/seek/play timings; the cap excludes temporary
serialization allocations. At 390 px the replay controls must not overflow.

`verify_handoff.py` reopens a real downloaded recording with only the root JSON
parameter key order reversed: semantic equality must be accepted and all saved
arrays restored. It delays completion of the actual uploaded File.text promise
(never substitutes file bytes), starts from real running physics, and requires
all mutating controls locked plus zero additional actual WASM integration calls
until reading finishes. Successful import stays paused. A real selected-frame
parameter mismatch must still be rejected atomically; controls recover after
failure. The activity message must describe the frame displayed after seeking.
Preserve the first FAIL and corrected PASS receipts/screenshots.

Direct `file://` navigation on this managed host returned
`ERR_BLOCKED_BY_ADMINISTRATOR` on 2026-11-18. Keep this boundary BLOCKED; do not
change browser policy or claim a literal local-file open passed. The independent
offline test still executes the actual downloaded HTML bytes via set_content
with networking disabled, reopens the timeline and checks exact continuation.

## Published surface

Push a verified direct-to-main commit without force; observe the EXISTING Pages
publication workflow only. Do not add/run CI verification. After deployment:

```sh
python tools/cloth_lab/verify_browser.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/cloth-lab/ \
  --expected-commit DEPLOYED_SHA --expected-html-sha HTML_SHA \
  --output work/cloth-lab/live
python tools/cloth_lab/verify_replay.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/cloth-lab/ \
  --expected-commit DEPLOYED_SHA --expected-html-sha HTML_SHA \
  --output work/cloth-lab/replay-live
python tools/cloth_lab/verify_handoff.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/cloth-lab/ \
  --expected-commit DEPLOYED_SHA --expected-html-sha HTML_SHA \
  --output work/cloth-lab/handoff-live
python scripts/verify_pages.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/ \
  --expected-commit DEPLOYED_SHA --output work/cloth-lab/pages-live
```

The root `/build.json` binds the live app bytes and commit; the verifier must
resolve it at the project root, not the lab's own provenance `build.json`.
Read remote main back independently. A successful publication job is not a live
browser PASS. Preserve BLOCKED if the public domain/browser is unreachable.

## Observed live transport recovery

On the current managed host, Chromium can load public Pages, while its separate
APIRequestContext initially attempted an unreachable direct IPv6 connection.
`scripts/playwright_http.py` now supplies the existing inherited HTTP(S) proxy to
that client and respects NO_PROXY; TLS verification remains enabled. No network
policy, response data or assertions were changed. The live lab verifier and the
existing Pages verifier both passed with this path. Keep the first BLOCKED logs
and final receipts at `docs/verification/cloth-lab-20261117/live/`.

## First-ready clothing coverage and provided normal pressure

The previous initial pose exposed the buttocks before the user ran simulation.
Do NOT approve a post-settle frame as evidence for first-ready/reset. The app now
retains its actual 240-step initial drape clock and uses matching developable
annular-sector material coordinates. Reopen actual SVG arcs/side lengths, exact
10 mm offsets and page bounds at default and slider extremes.

`verify_fit.py` must pass first READY without a user step, reset, dimensions, both
materials, moved avatar, recorded/reopened pressure and offline HTML. Require
zero exposed anatomical pelvis/upper-thigh ray samples, actual fabric skin-pixel
checks at front/side/back, and unchanged complete opaque MakeHuman geometry, skin
colors and normal depth testing. The independent ray oracle selects the region
from original source skin weights and uses additional horizontal azimuths; it
never imports the runtime coverage raster.

Pressure is the supplied `pattern-pressure-bench.html` unilateral XPBD module,
with force = multiplier/dt² and current cloth nodal areas. Independently reopen
all vertex/centroid contacts, forces, directions and pressure: nonnegative, unit
normals, area integral matches total force, geometric normal alignment >0.90,
contact equation residual <0.25 mm. The original three final contact sweeps
failed long/narrow at 0.469 mm; 16 sweeps must pass without widening tolerance.
Run SAME embedded-WASM zero, gravity, 500/1000/2000 Pa, inclined, refined, detached
and disabled coupons; 0.04 m² at 1 kPa must produce 40 N. A coherent fabricated
contact far from the body and fabricated pressure values must both be rejected.

Pressure multipliers/normals must survive every recorded frame, snapshot,
recursive save and exact next-step continuation. Every one of the 61 replay
frames now goes through independent pressure AND anatomical coverage checks in
addition to the original tensors and BOTH intersection directions. Two spawned
numeric worker processes may reopen immutable exported states, with at most six
in flight; browser actions stay sequential and ALL results are required. These
are numeric processes, not model subagents, and no solver is mocked.

After publication also run:

```sh
python tools/cloth_lab/verify_fit.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/cloth-lab/ \
  --expected-commit DEPLOYED_SHA --expected-html-sha HTML_SHA \
  --output work/cloth-lab/fit-live
```

Preserve first exposure screenshots/rays and failed contact-convergence state.
Synthetic normal-layer/material parameters are not measured physical-fit or
comfort certification; do not relabel that boundary as approved manufacture.

Run the software-rendered browser suites sequentially when collecting timing
assertions. Four concurrent SwiftShader browsers caused an observed 0.657 s
playback of a 0.5 s clip to fail the unchanged 0.15 s tolerance. An isolated
eight-run probe and the complete isolated replay suite must pass; retain the
first failure and actual timing log. Numerical worker processes may independently
reopen immutable snapshots, but all frame results are required before PASS.

The first-ready exposure, pressure-convergence failure, original PNGs, exact
local/public buffer comparisons and final public receipts are retained in
[the dated verification record](../../../../docs/verification/wasm-cloth-first-ready-20261118/README.md).

## Actual waist placement, beyond coverage

The old 840 mm circular fixture passed coverage but detached up to 56.55 mm from
the avatar. `anatomical-sector` uses separate front/back waist arcs from the real
MakeHuman high-waist section. The source-body-bound `src/avatar-fit.json` is
rebuilt by `python tools/cloth_lab/build_avatar_fit.py` (same verification deps).
The main builder rejects a stale source-body hash. It does not scale or cut the
body. The complete mannequin is gray; the independent mesh is the actual skirt.

`verify_fit.py` now requires actual upper-edge clearances 3–10 mm, skin-projected
waist height within 2 mm of the independently reconstructed anatomical plane,
and each panel's current waist edge within 1 mm of its printed arc. The independent
oracle cuts raw source triangles in float64 and requires one closed torso loop;
do not assume an arbitrary minimum mesh resolution (the current cut has 84
segments). It never imports renderer profile/anchor code. Every one of the 61
saved states must also pass this waist test.

Record two explicit negative controls: move only the waist radially outward, or
move it 30 mm upward, including saved pins/history. Require zero sewn gap and
zero exposed hip raster samples while BOTH UI and independent waist checks
reject the states. Keep unchanged 20% warnings for extreme parameter choices;
a covered waist and correct tensor calculation do not approve an overstretched
garment. Save same-camera side closeups and all three original viewport images
before/after, plus actual SVG, numeric source/skin measurements, offline replay
and console/performance logs. Current project/trajectory schema is v3; old HTML
continues with its own embedded code, old JSON fingerprints remain rejected.

Run `tools/cloth_lab/verify_waist.py --project ACTUAL_EXPORT.json --output REPORT.json`
on a real browser export. Its four probes include an incorrect waist level that
still follows the real skin within 3–10 mm, so the independent height boundary
must reject it, as well as an isolated 20 mm paper/waist mismatch. Retain the
command and raw report with the browser suite.

Same-camera closeups and full local/public results are retained in
[the waist placement record](../../../../docs/verification/cloth-waist-placement-20261118/README.md).
