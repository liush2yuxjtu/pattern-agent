# Prototype package reference page — 2026-11-17

Local verdict: **PASS** for the new `/pattern-agent/prototype-package/` reference
page and downloads. Exact base, source identity and candidate file hashes are in
[verification.json](verification.json). This is not a garment fit or DXF-edit
execution claim. Hosted verification follows the pushed, deployed commit.

The original ChatGPT Page package is preserved: source DXF/PRJ/EMF, compact S0,
complete geometry bindings, two sketch-style workflows and three reference
examples. The website actually switches the JSON-backed examples, exposes the
selected SpecPatch reference, opens the source preview and saves real downloads.
All examples remain NOT_RUN. Semantic compilation, edited DXF and regenerated
3D remain NOT_IMPLEMENTED / NOT_GENERATED. Units still require calibration.

## Local gate

The repository `/verify` skill and its `prototype-package.md`, `github-pages.md`
and `fitted-tshirt.md` recipes were applied. Commands, raw outputs and assertions
are retained in `local/`; all commands exited 0 on the final candidate:

- `python scripts/build_pages.py` — 339 public files, source identity recorded.
- `python web/prototype-package/package/verify_baseline.py` — source integrity,
  231 main entities, 3,367 bound coordinate/text fields and 8 observed paths.
- `python scripts/verify_prototype_package.py --output work/prototype-package-final-gate/prototype`
  — 8 real browser paths; 6/10 workflow nodes, pointer/keyboard tabs, modal,
  mobile 375/320, 5 saved downloads, all 40 archive digests and missing ZIP 404.
- `python scripts/verify_pages.py --output work/prototype-package-final-gate/existing`
  — 11 existing root/workbench browser and native export/import checks.
- `python scripts/verify_fitted_tshirt.py --output work/prototype-package-final-gate/fitted`
  — 13 existing T-shirt browser, WebGL, fallback and download checks.
- `python -m unittest discover -s scripts -p test_verify_artifacts.py -v`
  — 6 tests, including 5 fault-injection controls.
- `node --check web/prototype-package/app.js` and `git diff --check` — exit 0.

The actual HTTP surfaces use the `/pattern-agent/` project prefix. Screenshots
were inspected for desktop hierarchy, readable diagram labels and mobile
reflow. No console, asset HTTP or failed-request errors were observed. Browsers
and local HTTP servers close on completion.

## Preservation and findings

A concurrent remote commit was fast-forwarded before the final gate. All 271
pre-existing website files match that base byte for byte; the shared assets,
builder and publication workflow are unchanged. Their digests are retained in
`local/unchanged-website.json`. No new verification CI, PR or Issue was created.

The first browser attempt exposed a test harness reading a hidden disclosure;
it now opens the disclosure with a real click. The second exposed an actual
selector collision between tab buttons and their panel; the implementation now
selects `button[data-example]` explicitly. Both failed logs remain losslessly compressed in `local/*.log.gz`.
The full corrected browser path was rerun successfully, without weakened checks.

The existing 3D prototype is linked as an existing appearance reference. No new
3D result or manufacturing approval is implied. The historical cloth seam gap
7.6455 mm and 20 nonadjacent intersections remain FAIL; physical fit is NOT_RUN.
