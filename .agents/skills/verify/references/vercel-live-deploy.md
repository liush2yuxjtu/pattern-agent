# Vercel live deployment surface

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

### Hosted publication checks

For the exact Vercel deployment, call the connected Vercel `get_deployment`
tool and inspect `readyState`, URL, project and aliases. READY establishes
deployment completion only.

Use `web_fetch_vercel_url` to retrieve:

1. the production alias root;
2. the fixed deployment root;
3. `/aster-pattern-1-to-1.svg` on the production alias.

Require HTTP 200 and compare the complete returned text against the uploaded
`index.html` and SVG. The recorded Aster deployment passed all three comparisons.
Keep these checks separate from browser acceptance. This connector can use an
authenticated share mechanism, so its success alone is not proof of anonymous
access; inspect protection settings and test an unauthenticated browser when
available. Never change existing protection or permissions to obtain PASS.

The Aster publication was a manual static-file upload with no Git-connected CI.
It included the archived HTML as both `index.html` and `aster-studio.html`,
the SVG, handoff files and a download header for the standalone HTML.
No other Vercel project was replaced.

Run the full [Aster browser recipe](browser-aster.md) on the exact live URL,
including export/reopen checks. Record local and hosted verdicts separately.
A manual upload has no Git metadata requirement: compare uploaded file hashes
against the named source commit instead. Append one README deployment row per
variant; preserve prior deployment IDs, URLs and other projects.

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
