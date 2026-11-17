# Anatomical skill functional hill climb — 2026-11-17

Followed the pinned Anthropic skill-creator workflow: frozen original, isolated paired subagent executions, actual files and traces, programmatic grading, official aggregation/viewer, an instruction revision and an untuned transfer check. All 14 runs explicitly received their skill; this is not native Claude routing.

| Comparison | Candidate | Original |
| --- | ---: | ---: |
| First instruction candidate | 22/22 | 22/22 |
| Lean v2 | 22/22 | 21/22 |
| Untuned new camera | 8/8 | 8/8 |

The original's sole failed assertion is a missing required `neutral_measurements_cm` handoff field; its geometry is correct. Do not interpret the one-field result as a statistically established quality gain. Baseline fit IoUs in round2 (0.990687/0.994676) slightly exceed v2 (0.989441/0.993139); both exceed the frozen0.97 threshold.

Core SKILL.md: 6,522 → 3,911 Unicode characters,40.03% shorter. The tested snapshots' total Markdown reduces only3.01%; subsequent evaluation-record appendices are excluded from that comparison. No model-token, cost, latency, whole-package reduction or fit-accuracy advantage is claimed. [Independent coverage review](independent-review.md) found no concrete dropped requirement.

## What actually ran

- Six saved states: independently reconstruct12neutral dimensions, reject false units/NaN/unknownbone/falsemeasurement, preserve a truthful closest-supported target and source hashes.
- Actual MakeHuman mesh: 13,380 vertices/26,756 triangles; constrained silhouette optimization, final saved state, exact topology, fixed cameras, OpenCV overlays and six triangle renders.
- Genuine exported seated pose: actual163-bone projection, neutral vs seated height, raw floating depth and valid mask; same-mesh new-camera transfer.
- Reopen files and recompute. Raster replay shares the supplied rendering kernel. A separate OBJ parser and vectorized triangle intersections check40depthpixels; all joint pixels are projected independently. Visibility means inside canvas, not occlusion. Corruption controls demonstrate rejection.

[Local receipt](receipt.json) · [Input integrity disclosure](input-integrity.json) · [Selection](selection.json) · [Full public artifact manifest](site-manifest.json).

## Review and reproduce

[Official review](https://liush2yuxjtu.github.io/pattern-agent/garment-body/anatomical-evals/eval.html) · [First candidate](https://liush2yuxjtu.github.io/pattern-agent/garment-body/anatomical-evals/iteration-1.html) · [Untuned transfer](https://liush2yuxjtu.github.io/pattern-agent/garment-body/anatomical-evals/iteration-3.html) · [OpenCV before/after](https://liush2yuxjtu.github.io/pattern-agent/garment-body/anatomical-evals/opencv-before-after.png).

The viewer uses curated visual inputs; exact complete run archives retain source meshes, rawdepth, scripts, traces, metadata and grading. Fixture/candidate/oracle/grader-control ZIPs are also public. Source renderer/shape assets are CC0 MakeHuman. Asset fingerprint/provenance are retained.

From repository root, extract public fixtures.zip into `work/anatomical-skill-evals-20261117/fixtures` and oracle.zip into `work/anatomical-skill-evals-20261117/private-oracle`; extract each run ZIP into its named iteration/case/config/run-1 directory. Then:

```sh
python tools/skill_evals/grade_anatomical_runs.py --workspace work/anatomical-skill-evals-20261117 --iteration 2
python tools/skill_evals/grade_anatomical_runs.py --workspace work/anatomical-skill-evals-20261117 --iteration 3
python tools/skill_evals/aggregate_functional.py work/anatomical-skill-evals-20261117/iteration-2
python tools/skill_evals/plot_anatomical_fit.py --workspace work/anatomical-skill-evals-20261117 --out work/anatomical-replot
```

NumPy/OpenCV/Node are needed for geometry; Matplotlib for the plot. To rebuild all fixtures and disclose the synthetic target anew, run `python tools/skill_evals/anatomical_controls.py build` only outside a frozen evaluation. Pinned official upstream files were not modified. Its inability to sum null timing is handled by a grading-only adapter; normalized time/tokens remain null. No native Claude CLI is installed.

Local release checks:24helper tests,20tool tests; actual browser first/selected reviews31checks each, holdout23checks, skilldownload18checks; all image-run previews decode. Desktop/mobile screenshots inspected. [Review screenshot](local/review/benchmark.png) · [Mobile](local/review/mobile.png).

Full clothed image generation, photo segmentation quality, real-person measurements and physical garment fit are unmeasured. Historical cloth FAIL remains unchanged. Human review feedback has not yet been submitted. Publication receipt follows exact-SHA live verification.
