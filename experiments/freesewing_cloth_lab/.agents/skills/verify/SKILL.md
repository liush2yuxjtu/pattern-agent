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
   `test_prepared_solver.mjs`: five coupled frames must match the original
   kernel bit for bit, including split iterations and the equal-mass division
   reuse. `test_waist_ring.mjs` must preserve arbitrary rigid motion, mass center,
   internal net impulse/torque and reject zero inverse masses. The historical
   2.0 trajectory A/B is SKIP for 2.3: all particles are now dynamic, placement,
   waist closure and drag differ intentionally; retain its prior evidence.
   No mesh-resolution reduction or contact-query omission is allowed.
2. Serve the exact final HTML (`web/freesewing-webgpu.html`) on 127.0.0.1:8771. Run `verify_browser.py` and
   `independent.py`. Require all 52 UI/download/mobile/offline checks, exact next
   step, no external requests or console errors, actual A4 calibration and
   unchanged p95 solver budget <100 ms. The reopener independently re-drafts
   pinned Sandy without importing the app adapter. Every material coordinate,
   panel, lumped mass, native SVG, tensor and signed hinge field must agree.
3. Run `verify_dynamics.py` on the same artifact: actual captured WASM analytic
   controls; 120/240/360 steps; then 120 at the actual wind slider maximum 5 m/s².
   Require zero proper body and cloth intersections, no interior vertices and
   correct sewing at each exported state, using the independent geometry oracle.
   Initial unsimulated penetration is recorded separately, never a physical PASS.
   Require zero exposed posterior samples at every accepted state: the independent
   XY barycentric ray test covers 153 body vertices and 313 body-face centroids.
   Its raw arrangement and deleted-cloth controls must fail. Pressure must agree
   with independently UV-lumped area/mass and m*normalProjection/dt²/area; forged
   pressure must fail. This validates reaction arithmetic, not wearer-pressure calibration.
4. Run `verify_variants.py`: actual UI changes to 650 mm, circle ratio 60% and
   linen, followed by 120 physical steps and the same independent source/field/
   geometry checks. Preserve failures; do not substitute a static preview.
5. Run `verify_heatmap_gpu.py` on the real downloaded HTML. Read back the enabled
   color attribute from the actual WebGL draw and require <2e-6 error for every
   component of strain/stress/fold/curvature/pressure, 32,256 components per view. Keep
   raw arrays and screenshots. This validates display, not measured fabric laws.
6. Inspect actual desktop/mobile/fold/curvature/pressure/fabric screenshots.
   Camera presets must synchronously render the requested view; inspect a real
   rear fabric image. Normal boot, UI reset and design edits must auto-relax
   120 steps before display, while API reset remains an explicit raw diagnostic. Ensure the
   expanded toolbar does not cover the head in the default mobile framing.
   Run root `scripts/build_pages.py`, its six artifact regressions, and
   `git diff --check`. Log real software-rendering performance without FPS claims.
7. Run `run_check.py support --url URL --output DIR`. At 1440 and 1800
   steps require zero fixed particles, independent geometry/source/field PASS,
   contact/friction vertical force / weight in [0.9,1.1], COM speed <=0.012 m/s
   and COM drift <10 mm over the additional three seconds. Independently
   recompute every force and Coulomb bound from exported raw arrays. Reset,
   remove the actual body collider and run 12 steps: require mass-COM fall to
   match g=-9.81, drag=0.98 and dt=1/120 within 1e-10 m, >30 mm fall, zero
   normal/friction forces and forged-pin rejection. Preserve failures. The waist
   is an explicit reinforced shape-matching edge approximation, never anchors.
8. Archive the byte-exact upstream native SVG as gzip: its generated CDATA has
   trailing whitespace, so do not trim the output or allow a failed whitespace
   gate to fall through into a commit. Use strict shell failure handling.
   Preserve source-bound receipts, real exports, state arrays, logs and visual
   failures under a new `docs/verification/` directory. Fresh-fetch/reconcile main,
   commit directly and non-force push. Observe existing Pages publication only.
   Verify live HTML/build identity; repeat browser, independent, GPU, dynamics
   and edited-profile checks on the real public artifact. Commit live evidence.
9. Close owned browser contexts and temporary servers; stop only the task's
   identified port-8771 server after live verification.

Numerical stress uses an assumed plane-stress material model; bending remains
an XPBD distance approximation. Dihedral/centroid-dual curvature and the 15°
face fraction are mesh-dependent geometric wrinkle indicators. Permanent-crease
behavior, material calibration, universal CCD, native waistband/closure/hem
construction, print hardware and wearer fit remain NOT_RUN.


For 2.4 run `CLOTH_WEBGPU=1 run_check.py webgpu --url BASE_URL --output DIR`.
Require all native draw/buffer, distinct-canvas, body/collider, offline, loss and
adapter fallback checks. BASE_URL must omit renderer selection; the test forces
WebGPU internally and separately checks automatic software compatibility.
Run the same command with `--timing-only` in isolation for a fenced comparison.
Use `CLOTH_WEBGPU=1` and `?renderer=webgpu` on dynamics/variant/support to exercise
actual native WebGPU. Default browser QA must pass all 52 and p95 <100 ms.
The optional forced-software full UI diagnostic retains that same threshold:
if it fails, archive FAIL, never call it 52/52, and distinguish the unsupported
software override from the production automatic compatibility path. Actual
hardware acceleration remains NOT_RUN on this software-only host.

No precompile shadow pass is used: it invalidated live shadow textures in the
pinned Three.js build. The first real render is fenced before readiness. Keep
native GPU validation errors at zero and reject blank mobile/canvas images.
GPU uploaded body data must equal the collision asset despite different index
representations. The immutable normal cache and math isolation must preserve
positions, previous positions, UV, mass and pressure at every archived state.


For 2.5 use `web/freesewing-responsive.html`. Run `node test_body_query.mjs`
after the build. Run `run_check.py responsiveness` with the preserved 2.4 HTML
and the exact 2.5 candidate. Require twice-as-fast readiness, playback long-task
p95 at most half the baseline, a real run and pause, coverage, no browser errors,
and a matching fresh 120-step replay. Preserve the previous physics budgets
and checks, including the longer contact-support simulations.
