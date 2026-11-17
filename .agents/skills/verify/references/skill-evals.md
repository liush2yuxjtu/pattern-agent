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
