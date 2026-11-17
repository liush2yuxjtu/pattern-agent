# Single HTML Cloth Lab

Public route: `https://liush2yuxjtu.github.io/pattern-agent/cloth-lab.html`.
The executable artifact is [`../../web/cloth-lab.html`](../../web/cloth-lab.html).
Read the [research and source cases](../../docs/cloth-lab-research-20261117.md).

The HTML embeds Three.js, three-mesh-bvh, the original WASM solver and a real
MakeHuman surface. It makes no runtime resource requests. `Save single HTML`
also embeds the current design parameters and exact simulated coordinates.

## Build

From the repository root, with Node 22+:

```sh
npm ci --prefix experiments/single_html_cloth
node experiments/single_html_cloth/build.mjs
python scripts/build_pages.py
```

The builder checks the existing CC0 MakeHuman source OBJ's SHA-256, converts cm
to m and embeds its surface. It refuses a changed source asset. Generated
`source/body.json` and `source/solver-bytes.json` are ignored. No MakeHuman
application code or external game code is bundled.

Readable implementation: `source/app.js`, `source/template.html`,
`source/solver.wat`; dependency versions and license notices are retained.

## Local verification

Read and follow [.agents/skills/verify/SKILL.md](.agents/skills/verify/SKILL.md).
This is a new scoped recipe; the repository's existing verification files are
not edited by this addition. Playwright and Chromium were explicitly requested.

```sh
python -m pip install -r experiments/single_html_cloth/requirements-verify.txt
mkdir -p work/cloth-lab-site
ln -sfn ../../dist work/cloth-lab-site/pattern-agent
python -m http.server 8766 --bind 127.0.0.1 --directory work/cloth-lab-site
```

From another terminal, at repository root:

```sh
python experiments/single_html_cloth/verify_browser.py \
  --url http://127.0.0.1:8766/pattern-agent/cloth-lab.html --out work/cloth-lab-qa
python experiments/single_html_cloth/independent.py work/cloth-lab-qa/simulation.json \
  --repo . --out work/cloth-lab-qa/independent.json
python -m unittest discover -s scripts -p test_verify_artifacts.py -v
git diff --check
```

The independent checker reuses the repository's NumPy/SciPy triangle oracle,
whose analytic probes include incident triangles; it does not call the runtime
BVH or the app's heatmap code. It reopens actual downloaded arrays, verifies
source correspondence, all seam directions and flat lengths, topology,
body/self intersections, solid-angle membership and deformation tensors. Six
mutated exports must be rejected. Saved JSON retains all rest coordinates.

The browser test drives run/pause, views, seam tracing, cameras, orbit, range and
material controls, exports, printing, saved-state reopening and mobile layout.
It preserves screenshots, accessibility snapshot, console/network logs, solver
timings and real downloads. Tiled PDF page dimensions tolerate Chromium's
approximately 0.11 mm media-box rounding; the separate 100 mm vector-line check
uses a tighter 0.053 mm tolerance and verifies actual pattern scale.

Managed Chromium in this environment blocks `file://`. Saved HTML is reopened
over a document-only local HTTP server, subresources are blocked, and network
access is then disabled. This limitation is retained in the report; browser
policy is not changed. The same validator accepts the public Pages URL.

## Claim boundaries

The demo is a four-panel flared skirt with pinned waist support, not a finished
waistband/closure pattern. It has two intentional openings. Shared solver
vertices implement four seam relationships; there is no stitch-pulling animation.

WASM does integration and XPBD distance constraints; JavaScript/BVH handles
actual body triangles, with additional barycentric edge/face contacts. There is
no general cloth self-contact solver. Zero self-intersections is a test of the
saved inspected state, not a guarantee for all inputs or future trajectories.

Heatmaps use the true material-to-world deformation gradient. Estimated stress
uses stated isotropic plane-stress constants and is not calibrated fabric data.
Large stretch hotspots are retained and visible; digital PASS does not mean a
cotton garment is wearable. Fabric calibration, physical print measurement,
manufacturing, wearer fit and arbitrary body motion remain unvalidated.

SVG/DXF are physical 2D pattern geometry. OBJ is a zero-thickness render/sim
surface with UVs; it is not a watertight 3D-printing solid. Hardware 60 fps is not
established by headless SwiftShader timings.
