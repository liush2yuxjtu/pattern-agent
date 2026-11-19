# Carlton workbench release check

Candidate base `e17b78ed74078ecbb70c1add42152aa706c1418d`. Scope covers the new `web/carlton-workbench/` route, its link on the Pattern Agent homepage, the offline report, and the evidence download. The two embedded application script blocks match the tested Carlton editor byte for byte. Publication adds navigation links and inline favicons.

## Local result

PASS. Ran the repository's Playwright-first verification against an HTTP server at the actual `/pattern-agent/carlton-workbench/` project prefix. Used macOS Chrome with local Playwright Core. See [browser.json](browser.json) for the candidate hash and readings.

```sh
python3 -m http.server 45282 --bind 127.0.0.1 --directory STAGING_ROOT
node web/carlton-workbench/verify.mjs http://127.0.0.1:45282/pattern-agent/carlton-workbench/
git diff --cached --check
```

- Loaded 62 controls and 20 SVG piece groups. Baseline, chest change, length change and reset each completed 480 Rust/WASM steps with actual WebGPU compute dispatches. The two edits changed the SVG outline, assembled coordinates, rest geometry and final solution. Reset matched baseline.
- Downloaded the SVG and the full Boat archive through browser controls. The archive hash matched the checked-in evidence. The report decoded all 22 embedded images.
- At 390 px without WebGPU, the 2D editor could still apply a 10 mm seam allowance. The first local run exposed a missing favicon request. Inline favicons resolved it and the complete run passed without browser console errors.
- The Boat archive records four exported browser mesh cases and three saved CLO poses. Material calibration and physical fitting remain NOT_RUN.

## Release verification

The published site uses the existing GitHub Pages workflow. Pass the published commit to `verify.mjs` to require the live manifest and served asset bytes to match the release. This local receipt covers the Carlton route rather than the repository's other applications.
