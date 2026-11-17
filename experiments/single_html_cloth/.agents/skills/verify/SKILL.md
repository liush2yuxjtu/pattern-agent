---
name: verify-single-html-cloth
description: Verify the new single-file MakeHuman skirt surface, real exports, printing and independent geometry before committing.
---

Follow the root project `/verify` and direct-to-main contract. Working directory
is the repository root. This scoped recipe covers only the new Cloth Lab files.
It does not change the historical T-shirt FAIL or certify calibrated fit.

1. Record `git rev-parse HEAD` and `sha256sum web/cloth-lab.html`. Run
   `npm ci --prefix experiments/single_html_cloth`,
   `node experiments/single_html_cloth/build.mjs`, then
   `python scripts/build_pages.py`. The builder requires the fingerprinted
   existing MakeHuman OBJ and embeds assets/libraries/WASM in the new HTML.
2. Launch the built site at the `/pattern-agent/` prefix as documented in the
   adjacent README. HTTP 200 and `window.clothLab.ready` are readiness signals.
   Keep the process handle and stop only this task's server after verification.
3. Run `python experiments/single_html_cloth/verify_browser.py --url URL --out
   work/cloth-lab-qa`. Require every browser check to pass: actual run/pause,
   four diagnostic views, seam tracing, front/side/back and real pointer orbit,
   range/material edits, five real downloads, exact saved-state reopening with
   subresources blocked, measured SVG/DXF/PDF units/calibration and mobile
   without horizontal overflow. Preserve console, snapshot and timing evidence.
4. Run `python experiments/single_html_cloth/independent.py
   work/cloth-lab-qa/simulation.json --repo . --out
   work/cloth-lab-qa/independent.json`. Require source-bound four seam maps,
   matching notch/direction/length, gap <=2 mm, one component, two boundary
   cycles, Euler 0, no winding/degenerate/duplicate errors, zero proper
   body/cloth triangle intersections at 1 micrometre tolerance, no cloth
   vertices inside the closed body, and NumPy heatmap agreement. The six
   adversarial mutations and the existing analytic geometry controls must pass.
5. Run `python -m unittest discover -s scripts -p test_verify_artifacts.py -v`
   after building `dist`, and `git diff --check`. Keep previous failures rather
   than weakening accepted geometry thresholds. Reopen and inspect the current
   screenshots, including mobile and heatmaps. Fix overlap or clipping.
6. Record candidate base, changed-file hashes, exact commands, observations and
   PASS/FAIL/BLOCKED verdict under new `docs/verification/single-html-cloth-20261117/`.
   Never certify fabric calibration, continuous self-contact, manufacturing or
   real-device frame rate from these checks. Record file:// policy BLOCKED and
   the document-only offline test separately.
7. Fresh-fetch and reconcile remote main, commit only new files, and non-force
   push main. Existing Pages automation is publication only, never verification.
   Reopen the public URL with the same browser test and independent reopener;
   confirm `build.json` commit and HTML digest against the pushed artifact.
   Preserve publication and live browser receipts. Do not introduce CI.

Observed browser: `/usr/bin/chromium`, Python Playwright, `--no-sandbox` for the
container and `--enable-unsafe-swiftshader` for its software-rendered WebGL.
SwiftShader screenshot readback warnings are expected and must remain in logs;
application exceptions and failed runtime resource requests are failures.
