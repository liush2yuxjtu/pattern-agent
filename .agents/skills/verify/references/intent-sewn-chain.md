# Intent review: ordered sewing skill chain

Working directory: repository root. Source: `experiments/intent-edit-review/sewn/`.
Apply the explicitly requested skills in order: `sew-pattern-to-3d`, then
`verify-seaming`, then the root `verify` workflow. Read their canonical SKILL.md.

```sh
python experiments/intent-edit-review/sewn/run_chain.py --output work/my-fresh-sewn-run --units-assumption mm
python experiments/intent-edit-review/sewn/publish_review.py --run work/my-fresh-sewn-run --output work/my-fresh-sewn-review
python experiments/intent-edit-review/sewn/verify_preview.py --directory work/my-fresh-sewn-review --output work/my-fresh-sewn-browser
python experiments/intent-edit-review/sewn/publish_review.py --run work/my-fresh-sewn-run --verification work/my-fresh-sewn-browser/report.json --output work/my-fresh-sewn-final
```

Every output directory must be new/empty. Generation uses existing `convert_dxf`
and `bundle`; no converter, contract or threshold changes. Stage two launches the
independent CLI on the actual saved GLB and its own original DXF. Stage three
downloads the actual GLB/ZIP through the browser, checks exact bytes, and runs the
independent CLI again on each downloaded GLB. Exits 0/2/3 of the generation runner
mean PASS/FAIL/BLOCKED. Current five-case run exits3: baseline and cuff PASS;
sleeve/body/neck PROFILE_REQUIRED, not stale fallback models.

Prerequisites actually used: service Python 3.12, NumPy/SciPy/FastAPI, Pillow,
Playwright and `/usr/bin/chromium`. The unit argument is an explicit numerical
millimetre assumption; original DXF unit absence and YAML U remain uncalibrated.
Original seam lines remain FAIL; only the separately corrected outer shell can
pass. Preserve 8mm matching and correction bounds, <=0.05mm processed residual,
<=2mm gap/3D length error, all15 source-bound pairs, four openings and zero strict
intersections. Do not grant material/fit/production approval.

Run applicable existing service tests locally; never add CI. The browser driver
checks actual canvas pixels, different model renders, mouse/wheel/keyboard/reset,
wireframe, real CDP touch input in mobile contexts, 375/320 layouts, all15 visible
measurements, exact ZIP/GLB saves, disabled-network self-contained preview and
no-WebGL explicit error with remaining model download. Review actual model,
catalog, mobile and offline screenshots using view_image. It closes owned
browsers and its HTTP server. Source/raw outputs and scripts remain runnable.

Publishing only adds `web/intent-edit-review/sewn/**`; do not modify original
comparison/docs pages. Validate root Pages build and both public model bytes.
For a public-only live browser, use the same verifier `--base-url` after checking
the public pinned script/source hashes; provide its exact static artifact files
and independent reopener dependencies from public source. Preserve any TLS/file
policy blocker and use normal verified HTTPS, never disable trust or policy.

Artifact-generation total remains BLOCKED while required cases lack profiles;
a PASS for accurate preview delivery cannot replace that total. Record each
boundary separately and retain all rejected decisions, original source files,
derived-line JSON/SVG, downloaded-file reports and historical FAILs. Evidence:
`docs/verification/intent-sewn-chain-20261118/`.
