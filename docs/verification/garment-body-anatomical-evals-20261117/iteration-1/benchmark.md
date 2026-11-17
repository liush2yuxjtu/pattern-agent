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
- All tasks use synthetic projections of an actual MakeHuman surface; this does not test photo realism, real-person body accuracy, cloth fit or native Claude routing.
- Raster replay shares the supplied rendering kernel; raw depth is additionally checked by a separate OBJ parser and vectorized triangle intersections.
- Instructions and relevant references were supplied explicitly. This is functional execution, not automatic skill triggering.
- Only one execution per candidate/case per iteration; baseline repeats show sampling variation. No token or wallclock advantage is inferred from missing metadata.
- Both configurations pass22/22 frozen checks. Candidate v1 has no established pass-rate advantage. Initial front/side IoU=.913046/.916940; baseline final=.989359/.993843; v1 final=.990450/.995153. These small fit-score differences do not establish a causal skill improvement.
