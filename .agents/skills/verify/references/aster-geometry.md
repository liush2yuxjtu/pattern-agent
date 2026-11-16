# Aster geometry surface

### Scope and candidate identity

Target: `experiments/aster_dress/source`. This is a developable Three.js study,
not a cloth simulation or a fit-approved garment. Preserve the other experiments
and their historical FAIL results.

Before a run, record the remote main SHA, artifact source commit, source-file
hashes, exact deployment ID and fixed deployment URL. Do not treat the current
production alias as a permanent identifier: it can advance independently.
For each new variant or release, append its own README deployment row; preserve
earlier URLs and other Vercel projects.

Recorded Aster artifact: commit `855549017ec7bdf92c1dccca303c9cfcfe2042e7`.
Vercel project: `aster-dress-pattern-studio`.
Deployment: `dpl_CSyNWEo8fVhkX2UEkcLuMaK94UCb`.
Fixed URL: https://aster-dress-pattern-studio-fagpddri4-nyn5255-8475s-projects.vercel.app/
Production alias: https://aster-dress-pattern-studio.vercel.app/

### Local reproducible checks

The handoff run used Node.js, npm, Three.js 0.180.0, esbuild and jsdom 26 from
the committed package lock. From the repository root:

```sh
cd experiments/aster_dress/source
npm ci --ignore-scripts
node build.mjs
node verify.mjs
node verify-dom.mjs
cmp dist/aster-studio.html ../aster-studio.html
cmp dist/aster-pattern-1-to-1.svg ../aster-pattern-1-to-1.svg
cmp dist/geometry-verification.json ../geometry-verification.json
cmp dist/dom-verification.json ../dom-verification.json
```

The archived run actually performed byte comparisons in Python; `cmp` above
is the equivalent reproduction command, not an additional claimed historical run.
For a changed candidate, regenerate intended outputs and review their differences
before comparison; do not overwrite baseline evidence merely to make a check pass.

Observed evidence:

- Four dimension/allowance configurations, 30,720 sampled 3D/2D mesh-edge
  comparisons and 96 seam-pair checks (65 paired coordinate samples per join).
- Default maximum relative edge difference: 0.0024878841%; triangle-area
  difference: 0.0024878808%. These are finite mesh-chord approximation differences,
  not a measured fabric-strain result.
- Default seam-length mismatch: 0 mm; maximum coincident-edge gap approximately
  9.36e-14 mm. Matching mathematical edges do not prove sewn closure or body fit.
- Perpendicular cut allowances checked at 6, 10, 15 and 20 mm, with 25 mm hems,
  within 0.00001 mm. No cut-contour self-intersections in the four tested drafts.
- Thirteen DOM integration checks: fallback startup, individual release versus
  overlay visibility, release-all/reassembly, unfold completion, linked selection,
  valid/invalid dimensions, allowance updates, safe review notes, review import/
  export, SVG units/panels/calibration, repeated saved-HTML reopening, shared draft
  state without notes, direct expert entry and absence of unhandled DOM errors.
  The script groups these behaviors into 13 checks.
- Rebuilding the copied source reproduced the HTML, SVG and both verification
  JSON files byte-for-byte. All 25 archive-commit file blob hashes were compared
  against the remote Git tree after push.

The DOM harness deliberately provides no WebGL context. It tests application
state and exports, not GPU rendering, real input, pixels or real browser downloads.
The checks use the project's mathematical model; they are not independent
acceptance by a garment/pattern expert.

Keep commands, exit codes, observations, source manifest and overall verdict in
a fresh directory under `docs/verification/`. Existing evidence is in
`docs/verification/aster-20261116/` and
`experiments/aster_dress/{VERIFICATION.md,geometry-verification.json,dom-verification.json}`.

### Verdict and garment limits

Overall real-application acceptance remains **BLOCKED** for the recorded build.
Geometry and DOM assertions passed within their stated scope; READY plus HTTP
content equality does not upgrade the application verdict.

Cloth mechanics, calibrated fabric behavior, physical print scale, sample sewing
and human wear fit are NOT_RUN. The conical bodice is not anatomical bust shaping.
A patternmaker must review grain, hems, closure, facings/lining/support and fit a
toile before production. Do not claim a production-ready pattern from these checks.

For documentation-only changes to this recipe, runtime verdict is SKIP. Check
the instructions and evidence for accuracy, preserve unrelated recipes, reread
remote main, commit and push directly without force, then independently read back
the changed file and commit. Do not open CI, a PR or an Issue.
