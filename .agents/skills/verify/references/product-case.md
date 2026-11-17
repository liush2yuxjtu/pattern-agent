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
