---
name: verify-freesewing-cloth
description: Verify the actual upstream draft, cloth/body contacts, material and wrinkle fields, real GPU colors, downloads and offline state before direct publication.
---

Work from repository root. Use this package’s `run_check.py` wrapper for the
Python verifiers so browser concurrency matches the observed cgroup CPU quota.
Preserve its resource metadata; do not change test thresholds. Follow root AGENTS.md and `.agents/skills/verify/`.
Keep previous HTMLs, failure receipts and thresholds. Add this new version;
do not replace the earlier self-contact page. No CI or PR.

1. Record base HEAD, package lock, source and final HTML SHA-256. Run the build
   and all Node tests documented in this package's README. Require actual
   upstream Sandy dimension changes and flat/±60°/rotation/scale hinge controls,
   plus the existing proximity/swept/edge/edge and complete broad-phase controls.
   Preserve the first public performance FAIL and rejected-cache attempts. Run
   `verify_allocation_ab.py` against the actual application-commit 2.0 HTML;
   require exact current/previous/material coordinates at 120 steps. Also run
   `test_prepared_solver.mjs` after building; five coupled frames must match
   the original kernel bit for bit, and the dynamics probe must exercise the
   actual prepared export. No
   triangle-query skipping or mesh-resolution reduction is active in 2.1.
2. Serve the exact final HTML on 127.0.0.1:8771. Run `verify_browser.py` and
   `independent.py`. Require all 45 UI/download/mobile/offline checks, exact next
   step, no external requests or console errors, actual A4 calibration and
   unchanged p95 solver budget <100 ms. The reopener independently re-drafts
   pinned Sandy without importing the app adapter. Every material coordinate,
   panel, lumped mass, native SVG, tensor and signed hinge field must agree.
3. Run `verify_dynamics.py` on the same artifact: actual captured WASM analytic
   controls; 120/240/360 steps; then 120 at the actual wind slider maximum 5 m/s².
   Require zero proper body and cloth intersections, no interior vertices and
   correct sewing at each exported state, using the independent geometry oracle.
   Initial unsimulated penetration is recorded separately, never a physical PASS.
4. Run `verify_variants.py`: actual UI changes to 650 mm, circle ratio 60% and
   linen, followed by 120 physical steps and the same independent source/field/
   geometry checks. Preserve failures; do not substitute a static preview.
5. Run `verify_heatmap_gpu.py` on the real downloaded HTML. Read back the enabled
   color attribute from the actual WebGL draw and require <2e-6 error for every
   component of strain/stress/fold/curvature, 32,256 components per view. Keep
   raw arrays and screenshots. This validates display, not measured fabric laws.
6. Inspect actual desktop/mobile/fold/curvature/fabric screenshots. Ensure the
   expanded toolbar does not cover the head in the default mobile framing.
   Run root `scripts/build_pages.py`, its six artifact regressions, and
   `git diff --check`. Log real software-rendering performance without FPS claims.
7. Preserve source-bound receipts, real exports, state arrays, logs and visual
   failures under a new `docs/verification/` directory. Fresh-fetch/reconcile main,
   commit directly and non-force push. Observe existing Pages publication only.
   Verify live HTML/build identity; repeat browser, independent, GPU, dynamics
   and edited-profile checks on the real public artifact. Commit live evidence.
8. Close owned browser contexts and temporary servers; stop only the task's
   identified port-8771 server after live verification.

Numerical stress uses an assumed plane-stress material model; bending remains
an XPBD distance approximation. Dihedral/centroid-dual curvature and the 15°
face fraction are mesh-dependent geometric wrinkle indicators. Permanent-crease
behavior, material calibration, universal CCD, native waistband/closure/hem
construction, print hardware and wearer fit remain NOT_RUN.
