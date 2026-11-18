---
name: verify-cloth-self-contact
description: Verify the added single HTML against original gravity and the exact failing wind case, then real exports and offline continuation.
---

Working directory: repository root. Follow root AGENTS.md and `/verify`.
Only add this new version and dated evidence; preserve the original HTML and
its failures. No CI, PR or force push.

1. Record base HEAD and artifact/source SHA-256. Run the dependency install,
   build and `test_self_contact.mjs` from this directory's README. Actual
   proximity, swept vertex-triangle and edge-edge controls must pass. The build
   must parse the exact embedded JavaScript after HTML insertion.
2. Run `verify_dynamics.py` against the exact candidate. Capture its real WASM
   bytes and check analytic gravity, pins and elasticity. Independently reopen
   120/240/360-step states and the unchanged 360+120 strong-wind case. Require
   zero proper body/self intersections and no interior vertices, seam gap
   <=2 mm, correct source topology and independent heatmap agreement. Record
   the initial unsimulated arrangement separately; never call it a physical PASS.
3. Run `verify_browser.py` and `independent.py` as documented. Require all UI,
   real downloads, measured SVG/DXF/PDF, mobile, zero-console-error checks and
   exact offline next-step continuation. Preserve raw performance data and the
   existing <100 ms p95 default-step budget; do not loosen it to pass.
4. Run the root six artifact regression tests after `scripts/build_pages.py`,
   inspect current screenshots with view_image and run `git diff --check`.
   Fabric calibration, universal CCD/self-contact and manufacture remain outside
   the verified scope even when these discrete checks pass.
5. Persist dated source-bound receipts, failed candidates, arrays and screenshots.
   Fresh-fetch/reconcile main and commit directly with non-force push. Existing
   Pages automation publishes only. Recheck exact public HTML/build hashes and
   run the same browser and dynamics checks on the public URL. New evidence-only
   commits must name the application commit actually deployed.
