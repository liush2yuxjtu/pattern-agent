# Prototype package reference site

New independent GitHub Pages route: `/pattern-agent/prototype-package/`.

The existing root page, fitted T-shirt page, other pages, shared assets, static
builder, and publication workflow are unchanged. The existing publication-only
workflow copies this new directory along with the existing website.

`package/` contains the source-bound P0 package prepared in the accompanying
ChatGPT Page, including the original DXF, PRJ and EMF, editable S0 root, imported
geometry, two sketch-style workflows, and three reference intent cases. The
downloadable ZIP retains the previously prepared archive bytes. All examples
are NOT_RUN; no garment geometry has been edited.

The page loads real reference JSON, changes examples with pointer or keyboard,
shows the corresponding visual intent, and offers actual source downloads. It
does not implement semantic compilation, DXF patch application, or new 3D
generation. Existing prototype 3D appearance is linked separately.

From the repository root:

```sh
python scripts/build_pages.py
python web/prototype-package/package/verify_baseline.py
python scripts/verify_prototype_package.py --output work/verify-prototype-package
```

The local `/verify` recipe is
`.agents/skills/verify/references/prototype-package.md`. Publication validation
must use the deployed commit and actual public URL. No new CI workflow is added.
