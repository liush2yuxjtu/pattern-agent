# Functional benchmark

| Configuration | Assertion pass rate (mean ± SD across cases) |
| --- | --- |
| with_skill | 1.0000 ± 0.0000 |
| old_skill | 0.9583 ± 0.0722 |

- Actual OBJ/mask/browser/output executions, not plan-only or metadata routing judgments.
- Three controlled tasks, one execution per configuration/task; standard deviation is across tasks, not repeated-run reliability.
- Synthetic controls do not validate real human anatomy, cloth fit, or the full six-image generation workflow.
- Token notification metadata was unavailable. Executor wallclock scopes differed; raw timing is retained, comparative time/token metrics omitted.
- benchmark-upstream-raw.json preserves official aggregation, including fallback placeholders; only this normalized benchmark is used for interpretation.
- All tasks use synthetic projections of an actual MakeHuman surface; this does not test photo realism, real-person body accuracy, cloth fit or native Claude routing.
- Raster replay shares the supplied rendering kernel; raw depth is additionally checked by a separate OBJ parser and vectorized triangle intersections.
- Instructions and relevant references were supplied explicitly. This is functional execution, not automatic skill triggering.
- Only one execution per candidate/case per iteration; baseline repeats show sampling variation. No token or wallclock advantage is inferred from missing metadata.
- Candidate v2 passes22/22; original baseline passes21/22. The baseline missing neutral_measurements_cm field fails the metrics handoff contract; its mesh, depth and joint geometry are otherwise correct.
- Core SKILL.md Unicode characters fall from6522 to3911 (40.03%). This measures core instruction length, not model token use, total package size or execution cost.
- Baseline final front/side IoU=.990687/.994676 versus v2=.989441/.993139; both exceed frozen.97 threshold. V2 does not improve fit accuracy in this draw.
- Selection criterion was recorded before iteration2: reject assertion regressions; on passing cases prefer shorter core with full domain coverage. The held-out camera transfer result is not used for tuning.
