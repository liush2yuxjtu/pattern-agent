# Aster browser surface

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

### Real-browser acceptance and the observed blocker

Prefer Playwright with actual clicks, then the approved interactive-browser
fallback if needed. The attempted live run used an isolated scratch directory:

```sh
npm init -y
npm install playwright
node verify-live.mjs
```

The driver launched the installed `/usr/bin/chromium` headlessly with Playwright,
created a 1440 x 1100 viewport with downloads enabled, and navigated to the fixed
deployment URL using `waitUntil: 'networkidle'` and a 30-second timeout.
It stopped at `page.goto: net::ERR_TUNNEL_CONNECTION_FAILED`, before any
interaction or screenshot. Its checks array was empty and verdict BLOCKED.
This is launch/navigation evidence, not a browser test pass.

Earlier managed Sites preview failed to open its relay, the workspace browser
failed to initialize, and shell HTTP retrieval was rejected by the environment
proxy. Preserve those failures. Do not bypass the environment restrictions.

When the approved live browser becomes reachable, finish these pending steps:

1. Require the intended build, a working WebGL renderer and no page, asset or
   console errors. Capture actual rendered pixels; a state flag alone is not enough.
2. Orbit and zoom with real pointer input; check front/back/reset views.
3. Release B01 and observe the gap; rejoin and observe closure. Hiding seam lines
   must not change join state.
4. Unpick/unfold and observe completion to 16 2D panels, then reassemble.
5. In Compare, select S06 and verify matching visible selection in both views.
6. Probe invalid dimensions (top ring 60 cm must be rejected for the default
   draft), then change a valid dimension and allowance and inspect both views.
7. Save a panel/seam note, export and import the review, and confirm restored
   values after reopening.
8. Download the SVG, inspect its 16 pieces, units and 100 mm calibration square;
   download the HTML and reopen it independently with the selected draft.
9. Capture desktop and 390 x 844 mobile layouts; inspect clipping and controls.
   Record the exact URL, candidate hashes, actions, observations and failures.
10. Close the browser and any test server; keep evidence and remove only
    disposable scratch state. Never delete source tests or historical failures.

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
