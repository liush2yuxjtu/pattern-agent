# Paper pattern library and 3D gallery

Scope: `web/pattern-library/` and the homepage gallery link. Use
[github-pages.md](github-pages.md) for the existing publication gate and link
regression. Generation commands and the sample scope are under
[the gallery README](../../../../web/pattern-library/README.md).

## Claims and exact commands

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
  Observe the source folder link, nine image changes, three 2D edit states,
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
filters by format, publisher, part and keyword, checks empty results and
pagination, compares all four CSV downloads with the build hashes, and opens a
filtered mobile permalink. Use the same verifier against the live Pages root
with `--expected-commit` after publication. Keep CAD-byte deduplication and
publisher-only entries distinct in the receipt.
