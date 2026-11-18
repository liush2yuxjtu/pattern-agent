# Real garment reference, generated views and adjustable body case

Work from the repository root. Follow `AGENTS.md`; use the existing Pages
publisher after local verification, with no CI or permission changes.
This case is separate from the historical synthetic skill benchmarks.

## Build and exercise the actual files

The workspace is `work/product-red-pointelle-20261117`. Keep its original
reference, both native generation iterations, frozen masks and fitting history.
Do not silently regenerate images to reproduce a numerical check.

```sh
python tools/skill_evals/build_product_case_review.py --workspace work/product-red-pointelle-20261117 --site web/garment-body/product-case --include-model
python tools/skill_evals/validate_product_model.py --workspace work/product-red-pointelle-20261117
python tools/skill_evals/test_product_case_integrity.py --workspace work/product-red-pointelle-20261117 --output work/product-red-pointelle-20261117/integrity-verify
python scripts/build_pages.py
```

Use the builder's `--include-model` mode only after the final geometry producer
finishes. Its input-image/state/mesh/render provenance gates must reject stale
or tampered evidence. Preserve negative-control results under the case work
directory. Recompute neutral dimensions from the real matching MakeHuman asset,
and verify OBJ cm / GLB metres and actual posed vertices independently.

Serve `dist/` over loopback HTTP. Drive the pinned Anthropic review and four
visual stages with the repository Playwright verifier:

```sh
node tools/skill_evals/verify_product_case.cjs --url http://127.0.0.1:PORT/garment-body/product-case/eval.html --out work/product-case-browser --require-model true
node scripts/verify_human_studio_handoff.cjs --url http://127.0.0.1:PORT/human-studio/ --model-url ../garment-body/product-case/model/final-state.json --output work/product-case-handoff
```

Require all six native Image Gen files to decode and match hashes, real model
renders and OpenCV comparisons, gallery/lightbox keyboard and pointer behavior,
official Outputs/Benchmark/feedback download and persistence, mobile layout,
real JSON/OBJ/GLB/archive downloads, and no runtime or asset errors. Open the
screenshots. Follow the model link and actually change cm and joint angles;
save, reopen and compare actual geometry. Wrong-origin/broken-state probes must
leave the current editable model usable.

Read the numerical protocol before describing improvements. Camera registration,
shared pose, conditional cm search and view-specific pose are different stages.
Keep regressions and the weakest view. A generated held-out view is not an
independent real-person observation. Clothing containment is not silhouette IoU,
and neither is a measurement-accuracy score. Source model height/size, M prior,
conditional avatar values and unknown measurements remain distinct.

After publication, repeat these same browser verifiers against the exact-SHA
live site. Check `build.json`, public manifest/file hashes and archive contents.
If the local network blocks Pages, use the public-only pinned-verifier fallback
in [github-pages.md](github-pages.md). Record local and live receipts separately;
close owned servers/browsers/sessions. Native Claude routing remains BLOCKED
when its runtime is unavailable; physical cloth fit remains NOT_RUN.

## Pose-guided original-photo review

The newer case uses `tools/human_fit/pose_guided/` and
`web/garment-body/pose-guided-fit/`; preserve the original product case as history.
The downloadable reproduction ZIP contains the actual asset, cm/FK solver,
reference/targets, frozen protocols and final artifacts. Extract to a disposable
folder for its README replay. Do not regenerate the illustrative Image Gen cue
or treat its shoulder/waistband points as internal anatomical truth.

```sh
python tools/skill_evals/grade_pose_guided_fit.py --artifact-root web/garment-body/pose-guided-fit --candidate web/garment-body/pose-guided-fit/model --out work/pose-guided-independent-replay
python tools/skill_evals/build_pose_guided_review.py
python tools/skill_evals/build_single_state_review.py
python scripts/build_pages.py
node tools/skill_evals/verify_pose_guided_review.cjs --url http://127.0.0.1:PORT/garment-body/pose-guided-fit/eval.html --out work/pose-guided-focused-browser
node tools/skill_evals/verify_pose_guided_review.cjs --url http://127.0.0.1:PORT/garment-body/single-state-evals/eval.html --out work/pose-guided-existing-browser
node scripts/verify_human_studio_handoff.cjs --url http://127.0.0.1:PORT/human-studio/ --model-url ../garment-body/pose-guided-fit/model/final-state.json --output work/pose-guided-handoff
```

The builder must reject pending/stale grades and changed references, clear stale
managed candidate files, and preserve old embedded run data/feedback keys.
Inspect desktop/mobile and enlarged-overlay screenshots. Drive before/after,
alpha, true FK vs illustrative cue layers, gallery keyboard/mouse, real downloads,
and the editable Human Studio handoff. Check changed cm/angles, import and reload.
Source and unit checks are separate from photo/action acceptance: a correctly
exported model can still FAIL the requested pose. Critical regional failures,
visible-wrist/coarse-direction contradictions and 3D grasp failure cannot be
averaged into a functional pass score. Keep negative controls and rejected real
renders. See `docs/verification/pose-guided-fit-20261118/` for observed boundaries.

The pose review verifier also drives the source-bound human feedback workflow:
actual assertion evidence, baseline/candidate drafts, reload, shared URL storage,
real feedback.json download, explicit acceptance separate from automatic grade,
changed-model isolation and corrupt-cache fallback. These are executed browser
checks, not human acceptance. See `docs/verification/pose-review-feedback-20261118/`.
