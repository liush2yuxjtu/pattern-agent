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

### Quick visual review gallery

The static adapter in `visual_gallery.py` adds four provenance-labelled stages
to each case: input, Image Gen, simulation/3D render and overlay. Image Gen is
NOT_RUN in this dataset; state-only audits have explicit no-image placeholders.
Some source projections/replay overlays are review-derived and labelled as such.
Never relabel them as executor outputs or generated photos.

After rebuilding, run `node tools/skill_evals/verify_visual_gallery.cjs --url URL
--out OUT` on eval.html, iteration-1.html and iteration-3.html. Require all14case
selections, four sections, decoded previews, honest missing-data slots, original
file hashes, keyboard/pointer lightbox navigation, close/focus restoration and
mobile behavior. The selected case must survive reload together with feedback;
run the existing functional review verifier too. It selects case0 through the
actual dropdown before testing the upstream feedback flow.

Compare embedded run/grade/benchmark JSON, original run archive hashes and
feedback keys with the prior commit. Gallery additions must leave them unchanged.
Check the generated gallery JSON/asset hashes on the live exact-SHA Pages build.

## Same-body, same-target-action functional review

The paired workspace is `work/single-state-skill-evals-20261117`. Preserve its
frozen old/new skills, prompts/assertions, shared runtime, original run archives
and independent grades. Three cases test joint cm/bone/pose/camera optimization,
actual editor action preservation, and the original product photograph. Every
view of a final body must use the same complete pose and posed mesh.

```sh
python tools/skill_evals/grade_single_state_evals.py --workspace work/single-state-skill-evals-20261117
python tools/skill_evals/grade_single_state_evals.py --workspace work/single-state-skill-evals-20261117 --negative-controls
python tools/skill_evals/aggregate_single_state.py work/single-state-skill-evals-20261117/iteration-1
python tools/skill_evals/build_single_state_review.py --workspace work/single-state-skill-evals-20261117 --site web/garment-body/single-state-evals
python scripts/build_pages.py
```

Grade by reopening actual OBJ/state, source Three.js skinning, neutral rulers,
projection matrices, masks and raw depth; use private controlled targets only
after executor completion. Recheck browser state independently with the provided
`grade_single_state_editor.cjs`. The grader must reject a real alternate side
pose with forged common metadata, a1cm displaced mesh with updated hashes,
false IoU and changed frozen references. Keep subjective action review separate
from precise numerical and file-integrity claims.

Serve the real `dist/` build, not bare `web/` (the homepage needs generated
pattern artifacts). Drive:

```sh
node tools/skill_evals/verify_single_state_review.cjs --url http://127.0.0.1:PORT/garment-body/single-state-evals/eval.html --out work/single-state-skill-evals-20261117/browser-review
```

Require six cases, four visual stages, actual image bytes, lightbox keyboard and
pointer behavior, official feedback/Benchmark/persistence/download, mobile,
archive CRC and hashes, and all six same-origin Human Studio states loading as
real finite skinned meshes. Actually edit a cm value while preserving the pose.
Inspect desktop/mobile/real-photo screenshots. Final build rejects changed
post-grading output files and missing grades; `--allow-pending` is only preview.

Read pass rates as task-assertion completion. Single trials and an unblinded
coarse action judgment do not establish general skill superiority, perfect
photograph matching or real-person measurement accuracy. Shared cm/FK/LBS
infrastructure is supplied to both groups, not bundled as a skill optimizer.
Image Gen was not called in these tests; reused photos are context only.

After the direct-main push, run the same pinned public verifier on the exact
deployed SHA using `--expected-commit SHA`; also recheck the skill package's real
download. Use the existing public-only browser fallback if the local proxy
blocks Pages. Preserve receipts separately, stop owned servers/browsers, and
keep native Claude routing BLOCKED and physical fit NOT_RUN where applicable.

## Cross-retailer commerce functional runs

Use the pinned Anthropic reviewer through `build_commerce_review.py`; galleries
are inside the native Output section. Preserve paired skill snapshots, source
bytes, generation receipts, complete cm/FK state, independent region/3D grades
and their hashes. The grader uses the actual 3x4 photo camera, not camera.final
parameter aliases. Scores count assertions, never real-person accuracy.

```sh
python -m unittest discover -s tools/skill_evals -p 'test_*.py' -v
python tools/skill_evals/aggregate_commerce.py work/commerce-skill-evals-20261118/iteration-1
python tools/skill_evals/build_commerce_review.py --iteration 1
python scripts/build_pages.py
node tools/skill_evals/verify_commerce_review.cjs --url http://127.0.0.1:PORT/garment-body/commerce-evals/eval.html --out work/commerce-skill-evals-20261118/browser
```

For iteration2 add `--iteration 2 --include-holdout`, only after the candidate
freeze and actual heldout executions. Keep iteration1 and native Previous Output.
The strict builder must reject missing/stale grading before modifying the site;
`--allow-pending` is a preview only. Exercise actual galleries, Formal Grades,
Benchmark, feedback persistence/download and mobile. Reopen image bytes and
source/state/OBJ hashes. No native Claude CLI means trigger tests BLOCKED; null
timing/token observations remain null. Existing Pages workflow publishes only.
Evidence: [commerce-skill-evals-20261118](../../../../docs/verification/commerce-skill-evals-20261118/).

For commerce history, `iteration-N.html` uses its own scoped
`manifest-iteration-N.json`; the current manifest covers the whole site and
hashes historical manifests. Run the same browser verifier on both latest and
retained pages; a later six-run inventory must not invalidate a four-run page.
Run the reproducible fault-control CLIs documented in
`tools/skill_evals/COMMERCE-CONTROLS.md`; unittest imports are safe but do not
execute these costly CLI controls. Verify actual gallery→Human Studio links,
exact saved pose/mesh, cm edits and a real joint-edit/download/reimport probe.
Preserve known consumer failures and test readiness against actual debounce and
asynchronous import completion rather than reading state prematurely.


## Measurement-branch isolated skill execution

Keep `work/model-size-skill-evals-20261118` frozen executor outputs, input/skill
snapshots,7/7/5 protocol and hash-bound independent manual findings. Run the
independent grader only with unchanged audited artifacts; missing/stale manual
evidence must fail. Its scalar OBJ/weight/path implementation imports no exporter.
The five actual fault controls cover108/1000 fake values, wrong-neutral success,
missing definitions and stale TRACE. Do not rewrite old grades from new facts.

```sh
python tools/skill_evals/grade_model_size_skill.py --workspace work/model-size-skill-evals-20261118
python tools/skill_evals/aggregate_model_size_skill.py work/model-size-skill-evals-20261118/iteration-1
python tools/skill_evals/build_model_size_review.py --workspace work/model-size-skill-evals-20261118
python scripts/build_pages.py
node tools/skill_evals/verify_model_size_review.cjs --url http://127.0.0.1:PORT/garment-body/model-size-evals/eval.html --out OUT
```

Keep the original Prompt and Output visible in the official layout. Use only an
Output renderer for galleries/tables/claims: legacy `visual_gallery.inject` moves
Prompt/Output into custom details and is inappropriate for this contract. Require
gallery.closest('#outputs-body'), untouched Grades/Feedback, no custom navigation
or external intro, and Benchmark hiding all added Output content. Actually reopen
measurement/feedback downloads, run/source ZIP contents and SHA, lightbox, mobile,
and the explicitly unverified independence claim. Rendered input/reconstruction
images are review-derived, not executor or ImageGen results. N=1, no statistical
old/new win, no full photo/garment/ImageGen or native Claude claim.


## Full Image Gen workflow acceptance

For an explicit end-to-end request, use the complete six native Image Gen files,
actual original photo, current editable anatomical model, fresh fit attempts,
actual same-state renders/OpenCV overlays, and final mesh-derived measurements.
A measurement-only suite cannot stand in for this boundary. Keep the executed
skill snapshot distinct from post-execution documentation fixes. Preserve failed
pose/3D outcomes even when all operations ran. No baseline means no delta claim.

```sh
python tools/skill_evals/build_full_imagegen_review.py --workspace work/full-imagegen-skill-evals-20261118
python scripts/build_pages.py
node tools/skill_evals/verify_full_imagegen_review.cjs --url http://127.0.0.1:PORT/garment-body/full-imagegen-evals/eval.html --out OUT
```

Independent grading binds all recursive output hashes; strict builder rejects
missing/stale grades, changed native generation/ref hashes and missing views
before publishing. Check six full-resolution originals, source-versus-final
model generation lineage, model/overlay gallery and lightbox, real measurement
JSON/CSV downloads, feedback persistence/download, mobile and native Output DOM.
Large intermediate OBJ/GLB/depth arrays are preserved in compressed reproduction
archives; public gallery files and complete executor hash inventory are separate.
Single-case execution is functional acceptance, not general skill improvement.
Evidence: `docs/verification/full-imagegen-skill-evals-20261118/`.
