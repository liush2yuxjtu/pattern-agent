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
python tools/cloth_lab/verify_browser.py --output work/cloth-lab/local
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
  views, faults, downloads and resets. Preserve step 0/1/60/300 screenshots,
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
- High local strain remains a VISIBLE warning, not garment approval. Current
  default synthetic example can exceed 20%; numerical heatmap correctness is
  different from fit acceptance. Material calibration, cloth self-collision,
  continuous collision detection, finished construction and physical fit NOT_RUN.

`verify_browser.py` owns a temporary HTTP server and closes its browsers/server.
It tests the exact HTML. Raw evidence belongs in ignored `work/cloth-lab/`;
copy selected receipts, actual exports and images to `docs/verification/`.

## Published surface

Push a verified direct-to-main commit without force; observe the EXISTING Pages
publication workflow only. Do not add/run CI verification. After deployment:

```sh
python tools/cloth_lab/verify_browser.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/cloth-lab/ \
  --expected-commit DEPLOYED_SHA --expected-html-sha HTML_SHA \
  --output work/cloth-lab/live
python scripts/verify_pages.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/ \
  --expected-commit DEPLOYED_SHA --output work/cloth-lab/pages-live
```

The root `/build.json` binds the live app bytes and commit; the verifier must
resolve it at the project root, not the lab's own provenance `build.json`.
Read remote main back independently. A successful publication job is not a live
browser PASS. Preserve BLOCKED if the public domain/browser is unreachable.
