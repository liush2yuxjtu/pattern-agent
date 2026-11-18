# 2D paper pattern gallery and 3D cases

Scope: `web/pattern-library/` and the homepage gallery link. Use
[github-pages.md](github-pages.md) for the existing publication gate and link
regression. Generation commands and the sample scope are under
[the gallery README](../../../../web/pattern-library/README.md).

## Claims and exact commands

- Verify the 26 preview hashes in the 2D manifest against Pages metadata.
  Reopen the six actual SVG files and 20 raster previews, check raster ink and
  margins, and match the 19 planar research exports to their 24 catalog records.
  Check all thumbnail images in a browser, combined filters, empty recovery,
  keyboard access, and a mobile permalink to the enlarged DXF preview.
- Reopen both FreeSewing Sandy states against the existing independent geometry
  audit, check native SVG and state hashes, and compare source vertex arrays,
  face indices and per-corner UVs to published OBJ. Check each of the nine
  Blender output views for garment pixels and framing inside the image.
- Reopen the published T-shirt GLB hash and the existing independent sleeve-cuff
  seam record. Keep the 3D sleeve-cuff case and the 2D sleeve-length edit as
  distinct source revisions. Physical fit remains NOT_RUN.
- Run the local editor tests. Then extract the ZIP downloaded by the browser
  into ignored work, compile the sample intent and apply the saved patch. Compare
  the results to the example output included in the ZIP.
- Run the actual site at the Pages project prefix with the commands below.
  Observe navigation from home to the 2D gallery, the three 3D cases, all nine
  render changes, the three 2D edit states,
  keyboard zoom, focus restoration, deep links, invalid-query fallback, mobile
  overflow, and SHA-256 of actual browser downloads. Record the screenshots
  and the metadata commit in the receipt.

```sh
export PYTHONDONTWRITEBYTECODE=1
(cd web/pattern-library/editor && python -m unittest discover -s tests -v)
python scripts/build_pages.py
python web/pattern-library/source/verify_gallery.py --directory dist --output work/pattern-library/verify
python scripts/verify_pages.py --output work/verify-pages
```

Run the gallery browser verifier with `--expected-commit DEPLOYED_SHA` against
`--base-url https://liush2yuxjtu.github.io/pattern-agent/` after the publication
workflow completes. The verifier uses a clean browser context and closes its
browser and loopback server. Raw evidence belongs in ignored work. Record the
candidate, verdict and selected evidence under `docs/verification/`.

## Searchable CAD and feedback catalog

Use the same static build and execute the specific catalog browser gate after
regenerating the data as described in
[the catalog README](../../../../web/pattern-library/catalog/README.md).

```sh
python web/pattern-library/source/verify_catalog.py --directory dist \
  --output work/verify-catalog --source work/corpus/nicapotato.zip \
  --fit-source work/corpus/fitdata.zip
```

The source option checks every published evidence span against its original
review and product ID. The browser exercise enters the catalog from the gallery,
filters CAD by format and publisher, opens a research preview link,
checks feedback grouped by dataset or named publisher and style, and exercises
part filtering, actual excerpts, style pagination, comment expansion, and
mobile permalinks. It compares all four CSV downloads with their build hashes. Use the same verifier against the live Pages root
with `--expected-commit` after publication. Keep CAD-byte deduplication and
publisher-only entries distinct in the receipt.

## Brian standalone SVG tool

Scope: `web/freesewing/` and `tools/freesewing-brian/`. This is a separate
Brian body-block demonstration; it does not certify the gallery, garment
physics, grading rules, or human fit.

```sh
(cd tools/freesewing-brian && npm ci && npm run build && npm test)
python3 scripts/build_pages.py
git diff --check
```

The fresh dependency install needs Node 24+. `npm test` checks all 11 required
measurements, optional high bust, 22 boundary drafts, the master slider and
SVG export. Its independent reference calls published Brian directly for
27 inputs and compares all 81 back/front/sleeve outlines and downloaded SVG
paths. `upstream-manifest.json` pins all ten original Brian package files.
The expected single-HTML SHA-256 is
`3214641c9b044ec844f2926717a882bf21c4d12d75be3c53f6b3f62f8e4ffe9f`.

Drive the exact artifact in a real browser before shipping: reset, change
chest from 100 to 110 cm, require quarter width 302.5 mm, enable high bust,
then reset and change the master slider. Check the ready status, all three
rendered pattern pieces and the SVG button. The user-facing labels use cm;
Brian receives mm, except shoulder slope in degrees.

After publication, open `/pattern-agent/freesewing/`, follow its Brian entry,
repeat the controls, then check guide links. Compare the live HTML hash and
root `build.json` file entry with the committed candidate. Keep publication
workflow success separate from actual browser verification.

On the 2026-11-18 host, local Chromium launch was BLOCKED and the connected
Grok browser was unavailable. The working fallback was the managed Chrome
Playwright/AX surface: a source-bound standalone preview before commit, then
the actual GitHub Pages URL after publication. Do not treat DOM-only JSDOM
checks as a rendered-browser result. Retain these environment limitations.
Receipts: `docs/verification/freesewing-brian-20261118/`.
