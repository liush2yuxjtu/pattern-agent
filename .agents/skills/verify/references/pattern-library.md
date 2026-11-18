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
  render changes, and three layer visibility states on one SVG. Confirm both
  layers match the original and revised coordinates and that toggling keeps
  the SVG document, viewBox, and transform fixed on desktop and mobile. Check
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

## Brian native-input SVG tool

Scope: `web/freesewing/` and `tools/freesewing-brian/`. This does not certify
other galleries, factory grading, garment physics or human fit.

```sh
(cd tools/freesewing-brian && npm ci && npm run build && npm test)
python3 scripts/build_pages.py
git diff --check
```

The input schema and its units come from Brian 4.10.2 and `@freesewing/config`.
The SDK adapter must not convert, round, clamp or fill measurements, or couple
highBust presence to draftForHighBust. Default options must match the native
library (chestEase 0.15). Numerical inputs have no invented measurement bounds;
slider extents are display windows that expand around entered numbers.

The local gate checks all 11 required and one optional field, retained old
boundary vectors, decimals, missing inputs, outside-old-range bodies and both
high-bust settings. It compares 47 inputs and 141 parts, 13,066 coordinates
with zero tolerance, and full original native SVG bytes. It pins all ten files
of the official Brian npm archive. Missing/invalid GUI inputs must clear stale
paper and disable exports, never substitute example dimensions.

Use actual browser number-entry events: inspect the mm/degree units and
absent overall field; enter chest 1000.123456, inspect exact native JSON and
quarter width 287.5354936; clear chest and require export disabled; restore;
provide highBust and confirm the shape still uses chest until the independent
draft checkbox is enabled. Download both JSON and SVG and reopen them against
a direct Brian call. Check an input outside the old bounds and the reset.

After publication, open `/pattern-agent/freesewing/brian/` over HTTPS, repeat
the actual UI flow, and compare HTML and `input-contract.json` SHA-256 with the
committed candidate and deployed `build.json`. Publication success alone is
not browser verification. Retain the original 10% demo evidence as history.

This host's native Chromium launch and Grok browser were unavailable; the
managed Chrome HTTPS surface works. Its URL policy blocks data/file protocols.
Do not bypass that gate or claim a local browser PASS. If prepublication pixels
are blocked, record the blocker separately from the local SDK/DOM test PASS,
then use the user-authorized normal HTTPS Pages publication for runtime review.

Receipts: `docs/verification/freesewing-brian-input-contract-20261118/`;
historical receipts: `docs/verification/freesewing-brian-20261118/`.
