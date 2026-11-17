# Source-bound sewing inspector

Working directory: Pattern Agent root. This surface accepts the **local HTML
artifact and its interactions**, after independently binding it to the source
DXF and exact GLB. Geometry approval still requires [dxf-seams](dxf-seams.md).
This is not an authenticated Sites check or a material/fit release.

## Inputs and local commands

The portable reference under `experiments/fitted_tshirt/seam_inspector/` contains
the actual accepted cloud GLB, standalone inspector, raw report and SHA manifest.
It uses only the already committed T-shirt source; no Site identity configuration,
tokens or account session is included. Prerequisites: Python 3.12, the pinned
DXF service NumPy/SciPy dependencies, Playwright and existing `/usr/bin/chromium`.
No server, new browser download, Blender or Site credentials are needed.

```sh
SEAM_INSPECTOR_CONTROL_EVIDENCE=work/seam-inspector-controls.json python -m unittest discover -s scripts -p test_seam_inspector_binding.py -v
python scripts/verify_seam_inspector.py --html experiments/fitted_tshirt/seam_inspector/inspector.html --glb experiments/fitted_tshirt/seam_inspector/accepted-model.glb --dxf services/dxf-preview/public/sample.dxf --units mm --output work/seam-inspector
```

For current Site build output, replace `--html ...` with
`--artifact-dir /absolute/selected-site/dist`. Supply the actual downloaded GLB
and its original DXF, not a locally regenerated file assumed byte-identical.
Use `--browser` to select an existing allowed executable. Exit codes: 0 PASS,
2 FAIL, 3 BLOCKED. Read the complete `--help`; there is no live-URL mode.

## Acceptance

The command reopens the actual GLB with the independent geometry oracle. Require
PASS before comparing the HTML. Check input/output digests; every unrounded 3D
position and triangle index; all five source charts and their original/derived
2D curves; all 15 semantic pairs and global seam IDs; every displayed measurement
against the newly computed report; and four cycles against actual mesh boundary
edges. Reject duplicate HTML data blocks, changed labels, fake measurements,
detached flat coordinates, substituted geometry, hidden openings and invented
material approval. A displayed PASS label is not the oracle.

The diagram rounds flat coordinates to 0.01mm for presentation. Comparisons of
acceptance measurements use unrounded report values. Sparse plotted dots are
readability markers, not the number of vertices tested. 3D normals are recomputed
for shading; displayed positions and triangle indices must remain the actual
exported geometry.

Readiness: title and meaningful native content, no iframe bootstrap, actual full
mesh, all declared seam buttons, exact model hash. Drive all 15 buttons and verify
**visible** counts/gaps/errors as well as datasets. Then actually click a 2D edge
and a projected 3D seam; rotate by mouse, keyboard and real touch; switch front
and back; toggle original lines; reload to verify selection persistence. Download
the report/HTML and compare bytes. Inject one 503 only for the offline download,
record that expected console error separately, and prove retry. Cover 320px,
network-disabled downloaded HTML, its embedded-report download and no-WebGL mode.

## Evidence and limits

Keep `receipt.json`, `binding.json`, `independent-reopen.json`, `browser.json`,
raw logs, downloads and desktop/mobile/touch PNGs in the chosen output directory.
The driver fulfills requests using actual local static files at a test origin;
it does not make requests to production and never simulates sewing measurements.
Do not report these local checks as hosted acceptance.

The managed browser blocked direct `file://` navigation. Do not change policy:
run the exact downloaded single HTML with networking disabled and describe that
scope. Existing browser/network restrictions still apply; unavailable permitted
runtime is BLOCKED, not PASS. The runner closes the browsers it creates; no
preview server is started. Preserve the separate Sites/Pages gates below.

References: [seam-sites](seam-sites.md), [seam-pages](seam-pages.md), and dated
evidence under `docs/verification/seam-surfaces-20261117/`.
