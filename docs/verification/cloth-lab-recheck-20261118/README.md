# 2026-11-18 single-HTML physics recheck

The new artifact is [`web/cloth-lab-self-contact.html`](../../../web/cloth-lab-self-contact.html).
Its source and runnable local verifier are in
[`experiments/single_html_cloth_self_contact`](../../../experiments/single_html_cloth_self_contact).
This is an additional file. The original `web/cloth-lab.html` and its previous
evidence remain unchanged. `/cloth-lab/` is a separate, previously published app.

## Claim and candidate

**PASS for the new file's tested discrete states, browser interactions, real
downloads and exact offline continuation.** This is not a physical fit,
calibrated fabric, arbitrary-motion collision or manufacturing certificate.
Candidate base and exact source/HTML digests are in `candidate-files.json`.
The base was reconciled to `46430f5a02caeb7c413d765f6b8a38536b1b755a` before commit;
the concurrent changes did not change the original HTML, body OBJ or cloth code.

Invoked root `.agents/skills/verify/SKILL.md` and the new source directory's
scoped verifier. Local results were obtained before commit. Existing Pages
automation is used only to publish; no CI or PR was added or used for testing.

## First failure preserved

The original single HTML passed all 38 existing UI/download checks and the
independent default-state geometry/export audit again. The added dynamics test
found **11 proper cloth self-intersections** after 360 zero-wind steps followed
by 120 steps at the real wind slider maximum, 5 m/s². Body intersections were 0.
The original in-app PASS covers sewing/topology/body samples; it did not detect
these self-intersections. Its extended-dynamics verdict is **FAIL**.

`original/dynamics/receipt.json` and its archive preserve actual arrays,
intersecting triangle pairs, screenshots, captured distributed WASM and logs.
The initial arrangement is also recorded separately; it is not a settled PASS.
Other failed prototypes and their actual saved states remain under
`failed-candidates/`. These archives preserve independent-audit reproduction;
they are not complete source snapshots of each transient prototype.

## Correction in a new file

The new app adds inverse-mass vertex/triangle and edge/edge self-contact,
immutable pre-step history, linearized swept vertex/triangle checks, and
rest-triangle-derived bending distances. Self-contact uses a 3 mm numerical
separation. The existing actual WASM gravity/distance solver runs 120 iterations.
Body contact still uses the embedded MakeHuman triangles, not a capsule proxy.
After self-contact, affected body-contact neighborhoods are checked again.

An adaptive-axis, deterministic AABB sweep avoids duplicate edge pairs. A dense
all-pairs unit oracle checks candidate completeness and uniqueness. Allocation
optimizations and a deterministic saved-state ordering were added. One earlier
allocation-only optimization preserved positions bit for bit; this does not
claim that the later broad-phase ordering preserves every earlier trajectory.

Saved HTML includes current and previous positions, enabling exact next-step
continuation. The builder reparses the actual embedded JS to catch replacement
token corruption. No external runtime scripts, model requests or MCP are needed.

## Numerical and geometry evidence

| Candidate state | Body intersections | Cloth self-intersections | Min. sampled body clearance |
| --- | ---: | ---: | ---: |
| Step 120 | 0 | 0 | 3.006 mm |
| Step 240 | 0 | 0 | 3.017 mm |
| Step 360 | 0 | 0 | 3.027 mm |
| Step 480, last 120 with wind 5 m/s² | 0 | 0 | 3.005 mm |

All four exported states passed the independent NumPy/SciPy triangle oracle at
1 µm geometric tolerance; no cloth vertices were inside the body. The actual
MakeHuman source fingerprint, closed/wound body topology, four sewn panel
boundaries, two intentional garment openings and tensor values were checked.
Seam gap is 0 mm because paired boundary points share solver vertices; equal
length, orientation and topology are also independently checked.

The actual distributed 793-byte WASM was captured and instantiated separately.
Its 12-step gravity trajectory agreed with an independent damped recurrence to
`2.220446049250313e-15 m`; a fixed point did not move, and the distance constraint
reduced a 2 m separation to 1 m. Wind/no-wind trajectories differ numerically.
These are real integration and constraint checks, not only visual animation.

The full default-state export reopener also rejected all six injected faults:
reversed sewing, swapped panel, gap, bad UVs, body penetration and overlapping
faces. Its 23 analytic geometric controls passed before testing the garment.
OBJ coordinates/faces exactly match the simulation export; SVG and DXF match
the intended panels, units and 10 mm cut allowance. A4 PDF page size and its
100 mm calibration line were measured from the actual download.

## Browser, visual review and performance

Playwright drove the real page using Chromium/SwiftShader, with 1440 × 1100
desktop and 390 × 844 mobile viewports. All **39 checks passed**: run/pause,
verification dialog, strain/stress/seam/contact views, seam trace, camera/orbit,
actual downloads, changed dimensions/material, reset, PDF, mobile and offline.
No console errors or external runtime requests were observed.

The actual downloaded HTML was served as the only permitted document, then its
browser context was disconnected. Positions and the next simulated step matched
exactly. Managed Chrome blocks `file://`, so that transport was not claimed.

Raw screenshots were visually reviewed: default front, strong wind front,
stress heatmap, and the entire mobile layout. Head/feet are visible, panels and
controls are readable, heatmap colors change, and no horizontal overflow was
observed. Other camera, seam, contact and print captures are retained.

Default solver median: **78.1 ms/step**; p95: **93.6 ms/step**, below the existing
100 ms gate. Recorded wall-frame p95: **583.3 ms**. Four draw calls, 30,726
triangles. This software-rendered run does not establish 60 FPS or hardware GPU
performance. Earlier slower candidate logs remain preserved.

High deformation is intentionally not hidden: peak stretch is **153.48% of rest
length** by step 360 and **273.32% of rest length** in the wind snapshot (engineering
extension 53.48% and 173.32%, respectively). Estimated stress is 65.32 kPa and
294.66 kPa under the assumed plane-stress model. These large values are a reason
to calibrate and improve the material model, not an approval of realistic cotton.
The numeric heatmap agrees with the exported tensors; fabric accuracy is NOT_RUN.

## Commands and evidence

See the source README for exact reproducible build/browser/dynamics/reopener
commands. Raw logs are in `logs/`; all four dynamics states and actual WASM are
in `self-contact-local/dynamics/raw-state-and-evidence.zip`; real downloads and
browser states are in `self-contact-local/actual-evidence.zip`.

`node .../test_self_contact.mjs`: PASS, proximity, swept crossing, edge/edge and
dense broad-phase controls. `verify_dynamics.py`: PASS, 15 checks.
`verify_browser.py`: PASS, 39 checks. `independent.py`: PASS, geometry, tensors,
real exports and six adversarial controls. After the remote-main reconciliation,
`python scripts/build_pages.py` and the six `test_verify_artifacts.py` regression
tests passed. No existing threshold or old receipt was weakened or overwritten.

The unchanged enhanced `/cloth-lab/` app was also rechecked on its actual public
URL; its separate kernel and live receipt passed. Those results do not add
self-contact to that app and are not substituted for this new-file verification.

Post-publication hashes, repeated public browser/dynamics checks and final
screenshots will be added under `live/`, naming the actual application commit.
Temporary browsers are closed by their scripts; the task-owned HTTP server is
kept only until the public recheck completes and will then be stopped.

Material calibration, finished closures/waistband construction, real print
hardware calibration, universal CCD/self-contact, arbitrary user inputs and
wearer fit remain **NOT_RUN**. The current waist support is pinned.
