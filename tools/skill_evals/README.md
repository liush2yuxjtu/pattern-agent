# Skill trigger evaluation (local only)

This runner follows Anthropic skill-creator's trigger-evaluation protocol. It
observes real Claude `Skill`/`Read` routing events, not a model's claim that it
would use a skill. Full task execution and physical/anatomical accuracy are
separate evaluations. No CI is added or required.

## Prepare and review

From the repository root:

```sh
python tools/skill_evals/run.py prepare --out work/skill-evals/review
python tools/skill_evals/run.py doctor --out work/skill-evals/readiness
```

Open `work/skill-evals/review/review.html`, the upstream editable review UI.
For local UI verification, `node tools/skill_evals/verify_review.cjs` serves it
on loopback HTTP, tests edits/download, and closes its own server/browser.
It requires Playwright and Chromium (`CHROMIUM_BIN` overrides the path).
Confirm or correct the 20 labels and export the reviewed set before optimization.
The source set has 10 positives and 10 nearby negatives. Four additional
GarmentCode/follow-up routing challenges are saved separately; they have not
been scored or used to select a description.

## Native hill climbing

Requires an installed, authenticated Claude Code CLI and a model ID supported
by that runtime. Existing Claude Code login can be used; a separate API key is
not required. Do not paste credentials into prompts, files or reports.
This consumes the logged-in model's quota, so run only when authorized.

```sh
python tools/skill_evals/run.py optimize \
  --eval-set .agents/skills/garment-body-six-view/evals/trigger-evals.json \
  --model '<model-id-available-in-your-runtime>' \
  --max-iterations 5 --out work/skill-evals/native-run-01
```

Use a fresh output directory for each run. The CLI preserves the source skill;
its selected candidate is written to `candidate-skill/` for inspection. After
review, apply the selected description, rerun the project `/verify`, then follow
the repository's direct-to-main workflow. Do not rename the installed skill.

The outer stratified 60/40 split reserves 8 of 20 cases for final evaluation.
Only 12 development cases enter the upstream loop, which internally separates
training from validation. Each query runs three times. Final baseline/selected
comparison sees the reserved 8 cases only after description selection.
This small set does not establish broad performance; expand it after review.

## Integrity and error handling

`upstream/` contains unmodified files from the commit recorded in
`upstream/provenance.json`, with the original Apache-2.0 license and hashes.
`strict_runtime.py` is a separately maintained adapter: it records native
routing evidence and aborts scoring on CLI/model/auth/timeout failures. The
upstream evaluator normally converts failed futures to false; this adapter
prevents a failed service call from being counted as a correct negative.

The adapter preserves the official first-routing-decision protocol. A different
first tool is a valid non-trigger decision; this does not claim the skill could
never be consulted later. CLI version, available global plugins and runtime
settings may affect routing; compare candidates in the same runtime. The
metadata-routing probe is not an execution of the complete SKILL.md workflow.

Missing native CLI returns `BLOCKED`, exit 3, and `native_trigger_results: null`.
It never creates a fake 0% or 100% trigger score. Authentication is checked only
when `doctor --probe` or `optimize` is explicitly requested.

## Local checks

```sh
python -m unittest discover -s tools/skill_evals -p 'test_*.py' -v
python -m unittest discover -s .agents/skills/garment-body-six-view/tests -v
python tools/skill_evals/upstream/scripts/quick_validate.py .agents/skills/garment-body-six-view
```

Tests of error handling use fixtures/mocks and are labeled as such. Passing them
is not evidence that native triggering or image generation ran.

## Subagent routing surrogate

When native Claude routing is unavailable, fresh-context subagents can judge a
single skill metadata card against label-hidden queries. This is a separate
surrogate experiment, not an alternative PASS for the native requirement.
Use development data to revise descriptions; create a separate holdout without
showing it to the optimizer, freeze selection, then evaluate baseline and selected
candidate independently. Save all prompts/inputs, decisions, labels and mappings.
Record same-model and instruction-only blinding limits, and avoid treating repeated
judgments as new unique queries. Stop tuning after final holdout disclosure.

`score_surrogate.py` validates exact case IDs and Boolean decisions and reproduces
confusion counts from saved observations. It always labels results as surrogate
and sets `native_trigger_results` to null. For the executed run, methodology,
command and raw evidence see [2026-11-17 benchmark](../../docs/verification/garment-body-subagent-hillclimb-20261117/README.md).

The current v4 candidate is shorter and explicitly covers workflow continuation;
no routing accuracy gain was observed. Installed trigger description v0 remains unchanged pending
native event evidence. These scores do not assess image generation or body fitting.

## Executed functional evaluation and review

The current canonical `evals/evals.json` contains actual file-based execution
cases. Historical plan-only cases are preserved as `evals/planning-evals.json`.
See [functional review tooling](FUNCTIONAL_REVIEW.md) and the
[executed two-iteration receipt](../../docs/verification/garment-body-functional-20261117/README.md).

The official pinned grader/analyzer instructions and aggregation script are
vendored unchanged. Fresh-context agents execute task/skill pairs, and separate
validators reopen real OBJ/masks/browser state. `aggregate_functional.py` invokes
the official aggregator, preserves its raw output, then removes unavailable
tokens and incomparable timing placeholders. One execution per case/config is
reported as one, and old-skill is distinct from no-skill.

The narrow v1 body-text cache guard passed19/19 vs18/19 frozen-v0 checks; the
original18 assertions passed both. This is a small synthetic functional result,
not a production reliability, native trigger or anatomy measurement score.

Build review assets (existing Pages workflow publishes `web/**`; no CI added):

```sh
python tools/skill_evals/aggregate_functional.py WORKSPACE/iteration-2
python tools/skill_evals/build_functional_assets.py --workspace WORKSPACE \
  --evidence docs/verification/garment-body-functional-20261117 --site web/garment-body
python scripts/build_pages.py
```

Public review: https://liush2yuxjtu.github.io/pattern-agent/garment-body/eval.html
Submit downloads real `feedback.json`. Browser fixture feedback is never human approval.
