# FreeSewing 2.3: all-free waist with gravity

Candidate: `web/freesewing-free-waist.html`, SHA-256
`c74e6c5d9330668648facbf3e90dfa241482523fa64f71daa7d2b0f7a05505ed`.
Base after reconciliation: `36a964a5c919b6ee6339752dd242dd4d76437d73`.
The old pinned `web/freesewing-cloth-lab.html` remains byte-identical (see
candidate.json). This is the four-panel FreeSewing Sandy case, distinct from
the existing two-panel `pattern-wear-fit.html` case.

## Behavior and model

All 1,856 garment particles have finite positive mass. Gravity remains
-9.81 m/s² at dt=1/120 s. A closed reinforced waist edge uses mass-weighted
shape matching: its position/rotation remain free, with no world/body anchors.
The native Sandy waist rest length is 675.848 mm. Initial waist height is 1.09 m,
with 60% circle ratio. Contact uses the actual MakeHuman mesh, accumulated
Coulomb friction μ=0.6 and 120 coupled cloth iterations. Body and discrete cloth
self-contact checks remain enabled. Velocity drag is explicitly 0.98 per step.
This is a stiff belt-edge approximation; the full native waistband, closure and
hem construction remain unmodeled. Material and wearer-pressure calibration
remain **NOT_VALIDATED**. A high strain is a fit warning, not a manufacturing PASS.

## Local `/verify` verdict: PASS for the stated digital tests

Working directory: repository root. Commands are the package scoped verifier's
`run_check.py browser`, `independent`, `dynamics`, `variant`, `gpu`, `support`;
all outputs are under `local/`. Invocation logs retain arguments and environment.
The build and four Node controls (`test_pattern_fold`, `test_self_contact`,
`test_prepared_solver`, `test_waist_ring`) passed. Root build and six artifact
negative-control regressions passed. Navigation and root browser receipts are
archived after completion.

- Playwright: **50/50** desktop/mobile, real controls, downloads, printing and
  offline checks. Saved state/support/pressure and the next step are exact.
- Actual single-file WASM analytic gravity, pinned generic coupon, elastic
  coupon and prepared kernel controls pass. The garment itself has **zero pins**.
- Independent upstream FreeSewing re-draft, UV/lumped mass, tensors, signed
  fold/curvature, seam identities and forged input controls pass.
- At 120/240/360 steps, wind 480, edited 650 mm/60%/linen 120, and 1440/1800:
  zero proper body intersections, zero cloth self-intersections, zero interior
  garment vertices, zero exposed posterior samples (153 vertices +313 face
  centroids), zero seam gap. These are discrete states, not universal CCD.
- All five heatmaps (stress/strain/fold/curvature/pressure) match actual WebGL
  color-buffer readback: 32,256 components per view, threshold <2e-6.
- At 12/15 simulated seconds, upward contact/friction / weight is
  0.9999705 / 1.0003351; COM speeds 0.00007325 / 0.00003638 m/s
  (unchanged limit 0.012 m/s). Additional three-second COM drift is 0.0334 mm
  (limit 10 mm). At 15 s: weight 1.5209995 N, upward normal 0.6254168 N,
  upward friction 0.8960923 N. Independent force ledger residual 5.4e-13 N.
- Remove the actual collider and run 12 steps: COM falls 49.4287567 mm,
  matching the analytic damped-gravity recurrence within 1.8e-14 m; normal and
  friction force are zero. Forged zero inverse mass is rejected.
- Canonical UI performance p50 77.7 ms, p95 **87.0 ms**, unchanged gate <100 ms.
  Chromium/SwiftShader, four-core cgroup quota with child-process affinity.
  The canonical 360-step timing completed before parallel functional probes
  and our fetch-triggered Git maintenance. Subsequent functional jobs overlapped;
  their timings are not substituted for the canonical benchmark. Our own
  background pack process was temporarily paused and is resumed at cleanup.
  No hardware FPS claim follows.

360-step peak principal stretch is 193.7% (100% = rest length), so real cotton
fit acceptance remains NOT_VALIDATED. Stress is an assumed plane-stress tensile
second Piola–Kirchhoff estimate; pressure is a positive contact-projection
reaction estimate, not measured wearer comfort pressure. Wrinkle fields are
mesh-dependent geometric proxies, not permanent-crease prediction.

## Failures retained and recovery

`rejected/` preserves prototype source, runnable bundled HTMLs (gzip), probe
scripts/logs and representative raw states/screenshots. Simply removing pins
slipped roughly 10 cm and exposed the posterior. Local/global length constraints
still slipped or distorted the waist. End-only friction produced excessive
first-row stretch. Softening bending produced self-intersections and was rejected.
Friction is now accumulated inside each cloth iteration; original bending and
all full contact passes remain. Identical-position body-query memoization never
skips a changed query. Equal-mass WASM correction reuse and self-contact bound
ordering retain arithmetic/candidate coverage; original-kernel bit-exact and
complete broad-phase controls pass. Binaryen -O3 was tried externally and gave
no speed improvement; it is not a project dependency or shipped solver step.

Initial UI trials had 49/50 checks, failing p95 at 115.8 and 152.6 ms; their
receipts remain. The drag=0.992 candidate passed geometry but failed the
unchanged 12-second COM speed limit (0.01834 m/s), although it passed at 15 s.
The first support runner also hit a NumPy-bool JSON serialization error after
capturing states; the runner now converts that assertion result to Python bool.
The final model uses explicit dissipative drag 0.98 and passes the same limits.
Historical 2.0-vs-2.2 trajectory A/B is **SKIP** for 2.3 because boundary
conditions, placement and drag intentionally differ; its prior evidence is kept.
This does not waive any 2.3 geometry, coverage, force or performance gate.

## Publication

Application and live-evidence commits are recorded in `live/` after actual
GitHub Pages readback. No CI tests, PRs, Issues, paid services or new settings.
Only the existing static publication workflow is observed. Local evidence is
not labeled public verification until the live artifact is independently tested.

The pre-commit whitespace gate caught the small native SVG CDATA trailing
space: it had escaped a size-based archive rule. All original SVG bytes are
now gzip archived, without trimming or changing the upstream export. The strict
gate was rerun before committing; no failed check fell through into a commit.


## Public acceptance

Application commit `255581100bab299eea9e73bbb07bdabfa1e6c374` was published by
[the existing Pages workflow](https://github.com/liush2yuxjtu/pattern-agent/actions/runs/44275114881).
Actual anonymous readback matches the candidate's exact SHA-256 and 1,654,054
bytes. All public browser (50), independent, dynamics, edited-profile, support,
five GPU map, homepage entry (6) and root browser checks pass. Canonical public
p95 is 91.1 ms, below the unchanged 100 ms gate. Eight exported local/public
states have bit-identical positions, previous positions, UVs, inverse masses and
pressure arrays (including body-removed free fall). Receipts, raw state arrays,
snapshots, screenshots, console/network and performance logs are under `live/`.

Visual review here was by the primary agent using actual screenshots; independent
video review and a full per-frame timeline/debugger in this specific lab remain
NOT_RUN. The existing project-wide timeline surfaces are separate. This page is
a bounded cloth demonstration, not a completed unified manufacturing artifact.
The final evidence change also extends the prepared-kernel control to both the
original unequal-mass profile and a mixed profile with equal nonzero masses;
both five-frame runs are bit-exact against the original solver. Its initial
report-only scope error (`edges` outside the new loop) was corrected before
acceptance; no solver or delivered HTML changed for this test extension.
