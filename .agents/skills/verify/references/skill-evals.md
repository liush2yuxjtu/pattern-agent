# Apparel body skill / trigger evaluation

Work from the repository root. Canonical skill is
`.agents/skills/garment-body-six-view`; Claude's path is a relative symlink.
Read root `AGENTS.md`; no CI, PR or Issue, and no force push.

## Local caller checks

```sh
python -m unittest discover -s .agents/skills/garment-body-six-view/tests -v
python -m unittest discover -s tools/skill_evals -p 'test_*.py' -v
python tools/skill_evals/upstream/scripts/quick_validate.py .agents/skills/garment-body-six-view
python tools/skill_evals/smoke_helpers.py --out work/skill-evals/smoke
python tools/skill_evals/helper_benchmark.py --out work/skill-evals/helper-benchmark.json
python tools/skill_evals/run.py prepare --out work/skill-evals/review
python tools/skill_evals/run.py doctor --out work/skill-evals/readiness
```

The public helper CLIs must export/reopen a real overlay and JSON, reject an
invalid mask, and measure a known cylinder section close to 20π cm. These are
analytical controls, not a real body or physical fit test.

Open the actual generated upstream `work/skill-evals/review/review.html` with
Playwright. Check 20 query fields, edit a label/query and export the JSON;
reopen the exported data. Save screenshot, edited export and console findings
under the current ignored work directory. Run `node tools/skill_evals/verify_review.cjs`: it starts a loopback-only HTTP server, observes HTTP 200 and closes its own server/browser.
Managed Chromium blocks file:// navigation here; localhost HTTP is the supported preview transport, with no browser policy changes. Do not upload edited labels as ground truth
until the user reviews them.

Rebuild with `PYTHONPATH=tools/skill_evals/upstream python tools/skill_evals/upstream/scripts/package_skill.py .agents/skills/garment-body-six-view skill-packages` (the upstream packager needs its module root on PYTHONPATH).

Validate the `.skill` ZIP: it must contain the canonical SKILL.md and helpers,
exclude caches, and match source bytes. A source symlink proves filesystem
wiring, not that a native agent loaded it.

## Native routing boundary

A missing `claude` executable is **BLOCKED**, exit 3, with null native results.
Do not turn CLI/auth/model/timeout failures into non-trigger successes. Only
with an authorized authenticated Claude runtime, execute the command in
`tools/skill_evals/README.md`; it preserves an outer final holdout, three repeats,
actual Skill/Read routing events, and unmodified pinned upstream code.

The currently available command protocol stops at the first routing decision;
this is not full task execution. Full image generation/body fitting is separately
NOT_RUN unless actual outputs and independent evidence are exercised.

## Candidate / evidence / cleanup

Before commit, preserve base SHA, a source-content manifest, all commands and
exit codes, observations, boundary-specific findings and one overall verdict
under `docs/verification/`. Native routing remains BLOCKED when runtime is
unavailable even when helpers pass. Never claim an unmeasured description is the
best candidate. The current receipt is
[garment-body-six-view-20261116](../../../../docs/verification/garment-body-six-view-20261116/receipt.json).

Temporary trial commands are removed by the strict adapter. Kill only processes
started for the current check; do not alter authentication, CI or branch rules.
After local `/verify`, commit directly to main and reconcile latest remote main
before a non-force push. Read back the exact pushed revision with GitHub.

## Subagent surrogate reporting

For saved subagent routing observations, invoke `tools/skill_evals/score_surrogate.py`
with `--labels`, `--observations` and `--out`; use the command in the dated
[2026-11-17 report](../../../../docs/verification/garment-body-subagent-hillclimb-20261117/README.md).
Reopen scores and compare complete case IDs and confusion counts; send a duplicate
or missing decision through the same CLI and require rejection. Run the local
`test_surrogate.py` controls through the existing unittest-discover command.
The scorer verifies arithmetic only. Check that aggregate repeated decisions
are not described as new independent queries, final holdout was not used to tune,
and no native trigger claim is made. Native overall verdict stays BLOCKED.

## Executed functional review / existing Pages publication

Use `tools/skill_evals/grade_functional_fit.py --case CASE`,
`grade_functional_audit.py --case CASE`, and
`node tools/skill_evals/grade_functional_viewer.cjs --case CASE`.
These independently reopen actual geometry, images, source evidence and browser
state. Preserve expectation failures as measured outcomes; they are not a
reason to rewrite or weaken a test. New regression expectations apply
prospectively and are distinct from earlier frozen grades.

Invoke `aggregate_functional.py ITERATION`, then
`build_functional_assets.py --workspace WORKSPACE --evidence EVIDENCE --site web/garment-body`.
Keep the official upstream files hash-pinned; static feedback/security fixes are
in the separate `build_functional_review.py` adapter. Build with
`python scripts/build_pages.py`. Serve dist with loopback HTTP and drive
`node tools/skill_evals/verify_functional_review.cjs --url URL --out OUT --expected-runs 6`. Require actual Outputs/Benchmark
navigation, grades, reload persistence, downloaded/reopened feedback, mobile and
no API or page errors. Independently open screenshots.

The existing Pages workflow only publishes. No CI or workflow change is needed.
After direct-main push, inspect its exact-SHA deployment then run the same
public pinned browser verifier against the real Pages URL. If this VM's proxy
blocks the domain, follow the public-only Firecrawl Bash/standalone Chrome
fallback in github-pages.md. Never send unpublished local artifacts to that host.
Require hosted build.json SHA and downloaded public asset hashes to match the
deployed source; preserve the live receipt after verification.

Functional verification is distinct from native Claude trigger tests, which
remain BLOCKED until that runtime is available. Current evidence:
[functional20261117](../../../../docs/verification/garment-body-functional-20261117/README.md).

## Current Human Studio skill contract and public download

For changes to the anatomical-model integration, run the bundled
`inspect_human_state.py` CLI on a real saved state, with the matching
`web/human-studio/assets/human.json` and `--require-match`. Recompute neutral
dimensions; reject a false measured value, wrong asset SHA and wrong units.
Structure-only checks must not claim mesh or posed-skinning validation.
The model's separate browser/OBJ/GLB verifier remains in human-studio.md.

After the upstream packager, run `python scripts/build_garment_body_skill_page.py`,
then `python scripts/build_pages.py`. The guide builder rejects stale package
entries, copies canonical resources and publishes their hashes. It adds only
navigation/favicon to the historical review; confirm embedded evaluation JSON
and feedback keys remain byte-identical.

Serve dist over loopback HTTP, then run:

```sh
node scripts/verify_garment_body_skill.cjs --url http://127.0.0.1:8765/ --output work/human-skill/browser
```

The browser follows editor → guide → actual .skill download, checks all public
hashes, mobile overflow, historical review navigation, return to the editor and
real cm/pose state changes. Independently reopen the downloaded ZIP, compare
every member with canonical source, run its actual state helper and inspect
desktop/mobile screenshots. Stop the owned loopback server after verification.

After publication, use the same script against the site root with
`--expected-commit SHA`. If needed use the established public-only Firecrawl
fallback: download the exact committed verifier and check its SHA before use.
Keep publication evidence separate from native Claude triggers and six-image
generation quality. Current integration evidence:
[human-studio-skill-20261117](../../../../docs/verification/human-studio-skill-20261117/README.md).

## Anatomical functional hill climb and independent projection checks

Keep the old functional review immutable; new model-component evidence is under
`web/garment-body/anatomical-evals/`. Frozen source and run archives, candidate
snapshots, grader controls and the post-run disclosed oracle are hash-indexed
there. Extract fixtures.zip into `work/anatomical-skill-evals-20261117/fixtures`
and run archives into matching iteration/case/config/run directories to replay.
The renderer uses NumPy/OpenCV, and source shape solving uses Node and the actual
Human Studio asset/engine. No external generator is needed for these controls.

```sh
python tools/skill_evals/grade_anatomical_runs.py --workspace work/anatomical-skill-evals-20261117 --iteration 2
python tools/skill_evals/grade_anatomical_runs.py --workspace work/anatomical-skill-evals-20261117 --iteration 3
python tools/skill_evals/aggregate_functional.py work/anatomical-skill-evals-20261117/iteration-2
python tools/skill_evals/plot_anatomical_fit.py --workspace work/anatomical-skill-evals-20261117 --out web/garment-body/anatomical-evals
python tools/skill_evals/build_anatomical_review.py --workspace work/anatomical-skill-evals-20261117 --site web/garment-body/anatomical-evals --evidence docs/verification/garment-body-anatomical-evals-20261117
```

Reopen actual OBJ topology, neutral tape measurements, model state and frozen
cameras; reproject masks and compare actual images. The shared raster replay
is distinct from `grade_anatomical_projection.py`: this imports no renderer,
uses its own OBJ parser and vectorized ray/triangle intersections for 40 depth
pixels, and recomputes all joint pixels. Negative controls must reject shifted
depth, shifted joints and a false valid mask. Visibility here means inside the
canvas, not occlusion. These are synthetic anatomical geometry controls.

The pinned official aggregator cannot sum null timing. The local adapter uses
a temporary grading-only projection, retains original null observations and
removes upstream fallback zeros before presenting resource metrics. Test this
with the existing unittest command; never modify pinned upstream to hide it.

After building Pages, serve dist locally and drive the existing
`verify_functional_review.cjs` against the new eval.html (`--expected-runs 6`)
and iteration-3.html (`--expected-runs 2`). Require formal grades, quantitative
tab, downloaded/reopened feedback, persistence, mobile and no API writes/errors.
Inspect actual screenshots and images. Feedback entered by the verifier is
test data, not human acceptance. Verify the changed skill package with the
current download recipe above, including every ZIP member/source byte.

After publication, repeat on the exact-SHA live Pages build; check the new
manifest and archived public artifact hashes. Keep core character reduction,
all-reference size, fit IoU, schema completeness and real-person accuracy as
separate claims. No native trigger or full clothed-generation score is inferred.
Current evidence:
[anatomical-evals-20261117](../../../../docs/verification/garment-body-anatomical-evals-20261117/README.md).
