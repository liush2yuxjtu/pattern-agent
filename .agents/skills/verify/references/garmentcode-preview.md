# GarmentCode preview publication

Surface: `/pattern-agent/garmentcode-preview/`, source in `web/garmentcode-preview/`.
This recipe verifies the website and its downloads. It does not approve physical
fit or the simulated garment's geometry release.

## Local gate

Use the repository Python environment with Playwright and Chromium. No Warp,
trimesh or GPU is required for this independent published-file check.

```sh
python3 scripts/build_pages.py
python3 -m unittest discover -s scripts -p test_verify_garmentcode_preview.py -v
python3 scripts/verify_garmentcode_preview.py --output work/verify-garmentcode-preview
python3 scripts/verify_pages.py --output work/verify-pages
git diff --check
```

The new verifier uses the existing project-prefixed ephemeral HTTP server. It
decodes the real GLB buffers using Python's standard library, checks finite
positions, index bounds and nondegenerate triangles, and verifies actual download
hashes against `build.json`. Fault controls inject NaN positions, out-of-bounds
indices and truncation into the actual model bytes.

The real browser must draw WebGL pixels and respond to pointer rotation, wheel
zoom, initial/final selection, front/back, wireframe and body visibility. It also
reopens the downloaded self-contained HTML with networking disabled, tests a
375px viewport and deliberately disables WebGL in a separate edge-case context
to require a loaded fallback image. The rendering assertions wait for the next
rendered frame after selection; a synchronous attribute read can race
`requestAnimationFrame`.

The screenshot fallback must be captured from this published preview, with its
research-status explanation intact. Preserve local raw logs and screenshots in
ignored `work/`; commit candidate source hashes and a receipt under
`docs/verification/garmentcode-preview-20261116/` before the application commit.
After commit, rebuild and rerun both page verifiers with
`--expected-commit COMMIT` before pushing.

## Publication and live verification

The unchanged existing Pages workflow publishes `web/` on pushes to `main`.
No new hosted verification/CI workflow, repository permission change or PR is
needed. Read back remote `main`, wait for the Pages run for the pushed SHA, and
then run:

```sh
python3 scripts/verify_garmentcode_preview.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/ \
  --expected-commit DEPLOYED_SHA --output work/verify-garmentcode-preview-live
python3 scripts/verify_pages.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/ \
  --expected-commit DEPLOYED_SHA --output work/verify-pages-live
```

When the VM's network blocks Pages, use the authorized public-only Firecrawl
standalone Chrome route in [the main Pages recipe](github-pages.md). Fetch these
verifiers from the public pinned commit, check their source SHA-256, and execute
the same assertions unchanged. Fetch `verify_pages.py` alongside the new verifier
because it supplies `local_site`. Do not transfer unpublished fixtures, auth or
private notes. Record a live BLOCKED verdict until the actual published site has
been driven successfully. Never infer hosted PASS from a workflow result alone.

## Separate garment verdict

The upstream CPU run completed 232 frames, body-intersection count 0,
self-intersection count 2. Its permissive upstream GUI check passes, but the
repository zero-intersection release criterion is **FAIL** and physical fit is
**NOT_RUN**. The page and downloadable record retain these distinctions.
