# Functional benchmark

| Configuration | Assertion pass rate (mean ± SD across cases) |
| --- | --- |
| with_skill | 1.0000 ± 0.0000 |
| old_skill | 1.0000 ± 0.0000 |

- Actual OBJ/mask/browser/output executions, not plan-only or metadata routing judgments.
- Three controlled tasks, one execution per configuration/task; standard deviation is across tasks, not repeated-run reliability.
- Synthetic controls do not validate real human anatomy, cloth fit, or the full six-image generation workflow.
- Token notification metadata was unavailable. Executor wallclock scopes differed; raw timing is retained, comparative time/token metrics omitted.
- benchmark-upstream-raw.json preserves official aggregation, including fallback placeholders; only this normalized benchmark is used for interpretation.
- Untuned held-out camera transfer: new448x576 canvas, changed framing/scale/range, front-facing pose and depth; both candidates pass8/8.
- Same source seated mesh, different camera protocol. This checks transfer of geometry evidence, not new body shapes or photograph realism.
- No candidate edits are based on this result; no time/token comparison.
