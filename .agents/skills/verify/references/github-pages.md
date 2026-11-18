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

## Observed upstream error and concurrent publication — 2026-11-18

A missing-PDF assertion failed; an immediate independent read returned a GitHub
Unicorn 503 page. Preserve that FAIL and response. The exact same URL later
returned 404 in both API and real Chromium navigation; rerunning the complete
flow passed. Do not accept 503 or silently retry away the first failure. The
verifier now records the actual missing URL/status/content type on failure and
in the successful report.

If another authorized publication advances root build.json during verification,
preserve the revision-mismatch FAIL. Independently verify the affected app's
full HTML hash against the tested candidate before pinning the new root commit
and rerunning the download flow. A changed expected SHA alone is not proof.
Evidence: `docs/verification/cloth-handoff-20261118/live/`.

## Verified public-only fallback — 2026-11-16

Pages run `43819293093`, attempt 2, successfully deployed commit
`2a254fa7899bce5302aebbae87172ee29d837578`. The complete existing
`scripts/verify_pages.py` then passed against the public URL, including real
browser file-save, all four download hashes, mobile, and native export/import.
See the [live receipt](../../../../docs/verification/pages-20261116/live/receipt.json).

When this VM cannot reach the Pages domain, the working fallback is an authorized
Firecrawl `firecrawl_interact` session using **Bash**, not its preconnected browser
proxy. The proxy canceled downloads even with `acceptDownloads: true`; the host
has `/usr/bin/google-chrome`, Python and pip, and can reach the public site.

1. Open an interact session at the public site. Use only public URLs and public
   source. Do not transfer unpublished local pattern fixtures: automatic approval
   review rejected that transfer. The successful route transmitted no such data.
2. In a fresh `/tmp/pattern-agent-browser/`, install the observed Playwright 1.62.0
   with `python3 -m pip install --no-cache-dir --target ... playwright==1.62.0`.
   Python Playwright was absent on that host; no browser installation was needed.
3. Fetch the verifier from the **public pinned commit** over normal HTTPS. Check
   its reviewed SHA-256 before executing it. The verified source digest was
   `31d73128e61b35bc0bbc5e4a22d581196f48a6df669f9e097d5e397ef569bc42`.
4. Run the same Python verifier with `--base-url`, `--expected-commit`,
   `--browser /usr/bin/google-chrome` and an explicit `/tmp/.../evidence` output.
   The exact executed command is preserved in
   [remote-command.sh](../../../../docs/verification/pages-20261116/live/remote-command.sh).
   This uses the real published app and its generated files, not synthetic local
   fixtures, altered response headers, mocked downloads or replaced assertions.
5. Retrieve the report, actual downloads and screenshots. The interact tool caps
   stdout at 1 MiB: the observed 930285-byte evidence ZIP required two base64
   transfers of at most 700000 binary bytes per chunk. Verify the reconstructed
   archive SHA-256 and ZIP integrity before reading its evidence locally.
6. Inspect the screenshots and reopen the actual downloaded PDFs. Stop the
   interact session afterwards. The Python verifier closes its own Chrome.

Do not mark the browser-proxy cancellation as PASS. Here the subsequent standalone
Chrome run independently completed the full unchanged verifier with exit 0 and
`verdict: PASS`. Retain earlier failed publication receipts as history; the new
live receipt resolves their blocker without rewriting them.

## Current native Playwright path — 2026-11-17

The selected managed host can now reach the public Pages URL in Chromium.
Its separate APIRequestContext did not automatically inherit the environment's
HTTP(S) proxy and failed on direct IPv6. `scripts/playwright_http.py` explicitly
uses the existing proxy settings and NO_PROXY for this HTTP client, with normal
TLS verification. Do not change network/security policy or disable TLS.

The actual existing Pages browser/download verifier passed against deployed
`b90b22582072912df8ab4041bbf3d4113bab49d8` using `/usr/bin/chromium` and this
transport; the full new WASM cloth verifier also passed. See
`docs/verification/cloth-lab-20261117/live/existing-pages.json` and `receipt.json`.
The earlier Firecrawl-host workaround and earlier BLOCKED observations remain
historical evidence, not a reason to assume the current host is still blocked.
