---
name: verify
description: Verify restoration or changes to the archived Teagan Sites studio using byte-bound source, existing geometry checks and actual Chromium interactions.
---

# Verify the restored Teagan studio

Working directory: repository root. Unit: `experiments/teagan_sites_studio/`.
Follow root `/verify` → direct commit to main → non-force push, without CI/PRs.
Before each commit record parent/candidate file digests, commands, observations
and one verdict under `docs/verification/`. Reconcile latest remote main.

## Prerequisites and launch

Node/npm, Python 3, NumPy, Pillow, Python Playwright and `/usr/bin/chromium`.
Use already installed browser dependencies. In the app directory:

```sh
cd experiments/teagan_sites_studio/app
npm ci --cache /tmp/teagan-studio-npm-cache --no-audit --no-fund
npm run build
python3 -m http.server 8080 --directory dist
```

Readiness: `http://localhost:8080/` renders Teagan, actual body and garment in the
default 2D + plain3D views; heat and crease are off. Debugger route:
`/sleeve-debugger.html`. Stop only the server started for this check.

## Repeatable local gate

From repository root:

```sh
python3 experiments/teagan_sites_studio/tools/verify-source.py
python3 experiments/teagan_sites_studio/tools/verify-archive.py --browser \
  --out /tmp/teagan-archive-verification
```

The runner copies the archived app into a temporary directory, reuses its installed
dependencies and executes original assertions. It checks the build against every
frozen source-file hash before other suites regenerate reports. Original files are
not overwritten. Model/expert tests, 5,000 deterministic lifecycle transitions,
analytic hinge/seam controls and an independent NumPy adjacency/pairing oracle run.
The oracle's algorithm is the archived independent verifier; only paths use CLI args.

Browser scripts are the originals in `app/scripts/`. `tools/run-browser.py` redirects
only their hardcoded WORK output assignment, retaining every assertion and original
`__file__` root. They use installed Chromium and Playwright with exact local built
bytes via route.fulfill on an HTTPS test origin. Record this as LOCAL, not production.
The original ego-browser command is unavailable in this environment; use this
repository's Playwright-first route. Do not add browser plugins or weaken auth.

Require actual default pixels, four independent toggles/all 15 nonempty combinations,
body and garment, distinct angle colors, selected-edge close-up, independent cameras,
WebGL loss/recovery, 390px mobile, exports and source restoration. Lifecycle script
checks rapid inputs/save/export/undo, late callbacks/import, resource faults/retry,
isolated snapshots, 80 mixed UI steps and a final real native Worker solve. Controlled
callbacks are fault probes; they are not substitutes for the final native solve.

Read `receipt.json`, logs and both browser JSON files; count checks from those
files, inspect desktop/mobile screenshots and require zero relevant runtime errors
or warnings. In the reference v14 run the LOCAL state/views counts are 44/79; the
archived LIVE counts are 50/85 because they include six production asset hashes.
The output directory contains exact executed commands, exits and observations.
Temporary app cleanup is automatic; browser scripts close their own Chromium.

## Preservation and external writes

`SOURCE-MANIFEST.json` binds v14 original source commit
`5fd4986222886d1e4aaa5944122eaaec397c9a2a` and 93 files. An intentional later
app modification must explicitly update source provenance and record the new
candidate; do not alter the manifest merely to make an unexpected mismatch pass.
Leave raw legacy reports and negative meshes unchanged.

For Pages, create/edit only the intended pages using native tools, then read each
back and compare complete block Markdown. Store canonical URL/title and local
Markdown copies under `pages/`. Readback proves persistence, not rendered layout.
For Git, inspect staged content, reject secrets/deployment bindings, commit main,
fetch/reconcile remote and push without force. Independently fetch/read files and
verify the source-manifest digest and commit, rather than trusting push stdout.

Do not redeploy the original Site or change permissions for an archive-only task.
Existing authenticated LIVE receipts may be preserved with their exact version
and source hashes, but not relabeled as fresh executions. Screenshots named v13
are historical unchanged geometry; injected-error screenshots are fault tests.

Verdicts are PASS / FAIL / BLOCKED / SKIP. Never turn the before-ridge FAIL into
PASS. Keep the unrelated historical T-shirt 7.6455 mm seam gap / 20 intersections
as FAIL and physical fit NOT_RUN. These checks do not establish material calibration,
pressure, dynamics, professional patternmaker approval or a sewn garment fit.
