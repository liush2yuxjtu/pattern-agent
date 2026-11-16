# GitHub Pages and printable skirt verification

Working directory: repository root. Scope: `web/`, `patterns/straight-skirt-eu40/`,
the static builder, OpenSloper launch scripts and `.github/workflows/pages.yml`.
This recipe does not certify the unrelated Blender experiments or human fit.

## Prerequisites and local gate

Python 3.11+, PyMuPDF, Playwright, and Chromium. The observed working browser is
`/usr/bin/chromium`; use `--browser` on another host. Install verification packages
in a project virtual environment using `scripts/requirements-verify.txt`.

```sh
bash scripts/install_opensloper.sh
python3 scripts/build_pages.py
python3 -m unittest discover -s scripts -p test_verify_artifacts.py -v
python3 scripts/verify_artifacts.py --cli work/tools/opensloper-0.2.0-linux-x86_64/opensloper-cli
python3 scripts/verify_mcp.py
python3 scripts/verify_pages.py --output work/verify-pages
git diff --check
```

The browser verifier starts a local HTTP server at an ephemeral port, serving the
actual `/pattern-agent/` project prefix. Readiness is a successful HTTP response,
the Chinese page title and a loaded preview image. It closes the browser and
shuts down its HTTP server on exit. Do not replace real browser clicks with DOM
`element.click()` calls or static HTML inspection.

Acceptance: six artifact tests including five fault injections; a real 100 mm PDF
square and 14 A4 pages; three connected native outlines; retained dart fabric;
native CLI and project MCP reopens with no problems; matched side seams and a
750 mm sewn waist. Browser: desktop rendering, modal open/close, details toggle,
four real downloads compared byte-for-byte with `build.json` hashes, 375 px mobile
without overflow, and the existing T-shirt workbench zoom/export/import. Its
OpenSloper import must hide stale cutting lines, leave the draft unapproved and
refuse unsupported parametric files. A missing PDF URL must return 404.

Before every commit, record `git rev-parse HEAD` plus the changed source hashes,
commands, exit statuses and observations. After creating the commit, rebuild and
rerun the local gate with `--expected-commit $(git rev-parse HEAD)` on the browser
verifier before pushing. Keep raw logs and screenshots under ignored `work/`,
and copy the receipt and selected screenshots to `docs/verification/` for review.

## Actual hosted publication

Publication needs GitHub Pages enabled with source **GitHub Actions**. The workflow
only publishes; it does not enable Pages or elevate repository permissions.
`actions/configure-pages@v5` cannot enable a site using the workflow GITHUB_TOKEN.
Do not store a personal access token or invent a successful deployment.

1. Push the verified commit directly to `main`, without force, after reconciling
   a fresh remote HEAD. Record the pushed commit SHA.
2. Observe the actual Pages workflow run for that SHA, its deployment job and
   final result. Connected GitHub `fetch` can read
   `https://api.github.com/repos/liush2yuxjtu/pattern-agent/actions/runs` and its
   run/job subresources when the VM's `gh` credentials are unavailable.
3. Verify the live URL, not a local build:

   ```sh
   python3 scripts/verify_pages.py \
     --base-url https://liush2yuxjtu.github.io/pattern-agent/ \
     --expected-commit DEPLOYED_SHA --output work/verify-pages-live
   ```

4. Require the browser's `build.json` commit to match the workflow's deployed SHA.
   Retest real downloads and interactions; preserve screenshots, network/console
   findings, receipt and timestamps. A successful workflow is not a browser PASS.
5. Independently read the remote branch and committed files after push. Evidence
   commits that only change docs do not trigger a new deployment; name the exact
   previously deployed SHA rather than claiming the docs commit was deployed.

The observed Cloud VM blocks `liush2yuxjtu.github.io` and its `gh auth status`
does not authenticate, while authenticated Git clone/push and the connected GitHub
provider work. Do not change proxy/network policy or treat this as product failure.
Use an authorized connected browser if available, or run live verification on an
allowed host. Record hosted verification as BLOCKED until it really runs. Local
prepublication PASS is a separate claim and never a hosted-deployment PASS.

## Runtime gotcha recovered on 2026-11-16

At base `6fb5c7e800bf75e9ca84dbf58bc58d3d891bd3d1`, the T-shirt HTML ended midway
through `fromOpenSloper`; the unclosed script left zero SVG piece groups with no
page exception. Checking only the title or console would falsely pass it. Assert
four rendered pieces and actually export, modify and reimport a file. Also keep
the favicon in the served site so an otherwise working page does not hide a 404.

Physical printed dimensions, fabric calibration, a sewn sample and human fit are
NOT_RUN. Never promote numerical geometry checks to manufacturing approval.
