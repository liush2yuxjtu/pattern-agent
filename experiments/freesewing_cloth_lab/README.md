# FreeSewing → single-file cloth and wrinkle laboratory

New artifact: `web/freesewing-cloth-lab.html`. Earlier HTML files and their
historical failures are preserved. No runtime CDN, MCP or server dependency.

The browser really instantiates `@freesewing/sandy@4.10.2`, using the pinned
FreeSewing core/plugins. Its actual Bézier waist/hem curves supply both the 2D
printable outlines and every triangle's material coordinates. A native Sandy
half-panel is mirrored across its cut-on-fold line into a full panel; four full
panels form the simulated skirt. Changing length/circle ratio re-drafts Sandy.
The native source SVG also contains a waistband; that waistband is NOT simulated.
The waist circumference is the MakeHuman support-ring length including collision
offset. The other measurements are fixed for this supported straight-waistband
profile; this is not an automatic personal body-measurement service.

WASM integrates damped gravity and solves XPBD distance constraints. Bending
uses rest-distance approximations, not a calibrated shell law. Rest lengths and
lumped particle masses come from the actual material-coordinate triangles.
The existing body contact queries the actual 13,380-vertex MakeHuman CC0 mesh;
discrete vertex/triangle and edge/edge cloth contacts are retained.

Strain/stress diagnostics reconstruct F = Ds Dm⁻¹ and Green strain. Stress is an
assumed isotropic plane-stress material estimate (maximum tensile principal second Piola–Kirchhoff stress S). It is not contact pressure or a calibrated Cauchy-stress result.
100% stretch means rest length (0% engineering extension).

New fold fields cover every interior edge, including sewn panel boundaries:

- signed dihedral θ = atan2(ê·(n₁×n₂), n₁·n₂); flat = 0°;
- current dual spacing d = (h₁ + h₂)/3, with h measured perpendicular to the edge;
- discrete spatial curvature estimate κ = θ/d, in m⁻¹;
- each face displays the strongest adjacent |θ| or |κ|;
- the fraction of faces with |θ| ≥15° is a mesh-dependent geometric wrinkle
  proxy. It is not an area percentage or a permanent-crease predictor.

Signed per-edge/per-face values, adjacency, current/previous coordinates, UVs,
upstream drafting settings and sewing relationships are exported in JSON.
SVG/DXF/A4 use millimetres; OBJ uses metres. Saved HTML retains exact state and
next-step continuation. Body geometry, WASM, libraries and licenses are embedded.

## Build and run

Node 24 was used. FreeSewing 4.10.2 additionally needs its `config` and
`plugin-transform` packages explicitly installed because upstream packages
reference them without complete npm dependency declarations. They are pinned
in this package and lockfile. Build tools run only during development and bundling; the delivered HTML does not load them.

```sh
npm ci --ignore-scripts --prefix experiments/freesewing_cloth_lab
node experiments/freesewing_cloth_lab/test_pattern_fold.mjs
node experiments/freesewing_cloth_lab/test_self_contact.mjs
node experiments/freesewing_cloth_lab/build.mjs
python -m http.server 8771 --bind 127.0.0.1 --directory web
```

Open <http://127.0.0.1:8771/freesewing-cloth-lab.html>.

## Verify the actual artifact

Use the root `/verify` workflow and this package's scoped verifier. Python needs
NumPy, SciPy, PyMuPDF and Playwright; system Chromium is used. The project geometry
oracle supplies independent triangle intersections and solid-angle membership.

```sh
python experiments/freesewing_cloth_lab/verify_browser.py \
  --url http://127.0.0.1:8771/freesewing-cloth-lab.html --out work/fs-browser
python experiments/freesewing_cloth_lab/independent.py \
  work/fs-browser/simulation.json --repo . --out work/fs-browser/independent.json
python experiments/freesewing_cloth_lab/verify_heatmap_gpu.py \
  --html work/fs-browser/downloaded.html --output work/fs-heatmap
python experiments/freesewing_cloth_lab/verify_dynamics.py \
  --url http://127.0.0.1:8771/freesewing-cloth-lab.html --output work/fs-dynamics
python experiments/freesewing_cloth_lab/verify_variants.py \
  --url http://127.0.0.1:8771/freesewing-cloth-lab.html --output work/fs-variant
```

The independent reopener imports no application drafter or solver. A separate
Node consumer runs the upstream Sandy design; Python uses de Casteljau evaluation
to reconstruct all material coordinates and panels, checks lumped masses, then
recomputes tensors, oriented hinges, dual spacing and per-face fields. It also
compares the real native SVG download byte for byte to the independent re-draft.
Original fault controls remain; forged upstream curves/fold/curvature are added.

The GPU test reads the enabled color attribute on the actual garment draw,
restores the previous buffer binding and compares all RGB components against
independently validated fields. It covers strain, stress, fold and curvature.
The dynamics test checks actual WASM gravity/pins/elasticity and 120/240/360 steps
plus 120 more at the real 5 m/s² wind slider maximum. A separate real-input
variant changes length to 650 mm, circle ratio to 60% and material to linen.

No fit/manufacturing/calibration/real-time claim follows from numeric PASS.
Large deformation remains visible. Universal continuous collision detection,
arbitrary designs/parameters, physical print hardware, waistband/closure/hem
construction and real-fabric wrinkle or crease behavior remain unvalidated.

Libraries are bundled at build time. This is not a zero-third-party-code claim:
FreeSewing, Three.js, three-mesh-bvh and their runtime dependencies are third-party
open-source code with embedded license notices. No third-party service or MCP
is required to run the delivered HTML.
