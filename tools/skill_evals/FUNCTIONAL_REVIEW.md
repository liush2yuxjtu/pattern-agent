# Static functional review adapter

`build_functional_review.py` imports the pinned Anthropic
`upstream/eval-viewer/generate_review.py` and calls its run discovery,
previous-workspace loader and official `generate_html` template. Upstream bytes
are unchanged. The generated standalone document is adapted to:

- put with/new-skill before without/old-skill runs, retaining honest config labels;
- escape `<` in embedded JSON so HTML output containing `</script>` remains text;
- preserve unknown token observations as null and omit incomplete token summaries,
  including zero placeholders; report actual per-eval repetitions;
- persist feedback in localStorage keyed to the exact review build and always
  download `feedback.json` on Submit, without a nonexistent server API;
- use system font fallbacks; omit unused spreadsheet CDN code for non-XLSX runs.

```sh
python tools/skill_evals/build_functional_review.py \
  --workspace PATH/iteration-2 --benchmark PATH/iteration-2/benchmark.json \
  --previous-workspace PATH/iteration-1 --out web/garment-body/eval.html
node tools/skill_evals/verify_functional_review.cjs \
  --url http://127.0.0.1:PORT/garment-body/eval.html \
  --out work/functional-review-browser --expected-runs 6
```

The browser verifier drives Outputs/Benchmark navigation, formal grades,
feedback edit/reload, a real Submit download/reopen, desktop/mobile screenshots
and absence of POST/API requests and page JavaScript errors. It launches and
closes its own Chromium; the caller owns the HTTP server. `CHROMIUM_BIN` can
override `/usr/bin/chromium`. Fixture feedback is not human approval.

Self-test performed on a two-run with_skill/old_skill fixture with hostile
HTML script text, unknown token counts and an intentionally wrong repetitions
metadata field. The real browser passed17 checks; the hostile code did not run,
literal HTML rendered as source, token row was absent and repetitions corrected
to1. Evidence is under ignored `work/functional-review-adapter-selftest/`.
