# Pattern Agent

Runnable Blender garment experiments and independent geometry checks. This is a
research repository; physical garment fit has not been verified.

## Printable straight skirt and GitHub Pages

The static download site is prepared for
[GitHub Pages](https://liush2yuxjtu.github.io/pattern-agent/). It includes the
EU40 straight-skirt preview, A4 and full-size PDFs, Chinese instructions and a
complete editable source bundle. The existing T-shirt review workbench remains
at `/pattern-agent/pattern-review/`.

The [skirt source and measurement assumptions](patterns/straight-skirt-eu40/README.md)
are tracked separately from the older T-shirt experiments. Its digital geometry
checks pass; sewn-sample and human-fit verification remain NOT_RUN.

```sh
python3 scripts/build_pages.py
python3 -m pip install -r scripts/requirements-verify.txt
python3 -m unittest discover -s scripts -p test_verify_artifacts.py -v
python3 scripts/verify_artifacts.py --cli /path/to/opensloper-cli
python3 scripts/verify_pages.py --output work/verify-pages
```

For OpenSloper on Linux x86_64, run `bash scripts/install_opensloper.sh`. It checks
the pinned official release archive and installs under ignored `work/tools/`.
The project `.mcp.json` starts the installed CLI through
`scripts/opensloper-mcp.sh`. Set `OPENSLOPER_CLI` to use another installation.

`.github/workflows/pages.yml` performs publication only: build static files,
upload the Pages artifact, and deploy. Generic verification stays local. GitHub
Pages must use **Settings → Pages → Source → GitHub Actions**; this workflow does
not change account permissions, enable paid services, or bypass environment rules.
The working verification recipe and receipt are in `.agents/skills/verify/`
and `docs/verification/`.

## Current full-arm experiment

Code is in `experiments/full_arm/`. It creates a complete synthetic mannequin and
preassembled T-shirt, runs real Blender Cloth, exports measured meshes, checks
every saved frame, and creates a portable replay with independent reload checks.

The preserved 241-frame experiment has **arm-routing checks PASS in all 241
frames**, but **cloth geometry FAIL in 161 frames**. Cloth self-intersections peak
at 535 pairs; cloth/body and body self-intersections are zero. These numbers do
not establish armhole sizing, calibrated material behavior, or physical fit.

```sh
cd experiments/full_arm
python3 -m unittest discover -s verification -p test_pipeline_gate.py -v
blender -b -t 1 --python-exit-code 2 --python verification/test_geometry.py
python3 run_pipeline.py --out runs/full-arm --frames 241 --render-video
```

Prerequisites: Python 3.11+, Blender 4.3.2 with NumPy, and FFmpeg for video.
The selected full-motion baseline intentionally exits 2 for quality failure;
execution completion is separate from the physical and geometric verdict.
Use a fresh output directory to preserve evidence.

## Controlled verification experiment

The completed [one-shot control experiment](experiments/oneshot_control/README.md)
includes a standalone full-body model and T-shirt, independent geometry code,
input fixtures and results. Four positive controls pass; eight invalid cases
are rejected by the independent static gate.

**Both problems are real:** the strict v2 audit of all241 old frames confirms161
frames with garment self-crossings and a595-pair peak. Earlier v1 evidence is
historical and incomplete because v1 also excluded shared-vertex pairs.
new controls expose false approvals for a displaced body with stale paths and
64 coplanar overlaps omitted by the legacy Blender BVH. A clean static mesh does
not establish cloth simulation or physical fit. Download the two files in
[`experiments/oneshot_control/assets/`](experiments/oneshot_control/assets/).

The exact recovered single-file dynamic generators and a newly executed121-frame
reproduction are in [`experiments/oneshot_motion`](experiments/oneshot_motion/).
Its portable model/cloth files, all saved meshes and independent reload evidence
are retained separately from the analytic rectangular controls.

## Verification and history

The [one-shot pattern roundtrip](experiments/pattern_roundtrip/README.md) separates
the human/cloth into pure standalone files, unwraps4 actual2D panels and challenges
armhole fit independently. Representation checks pass, each armhole/cap has a
23.27mm transfer mismatch, and the forward solver fails atlas invariance. Real
fit remains UNKNOWN; the source patterns have no seam allowance.

Follow `AGENTS.md` and `.agents/skills/verify/SKILL.md` before committing.
Runtime recipes and observations are recorded under `docs/verification/`.
No generic GitHub Actions verification workflow is used.

The recovered original documentation is preserved in
[`docs/historical-tshirt-readme.md`](docs/historical-tshirt-readme.md). Its referenced
paper-pattern implementation and original assets are not currently restored in
this checkout. Its historical 7.6455 mm seam gap and 20 self-intersection FAIL
remain separate from the newer synthetic experiment.

Private workspace notes and connected-storage artifacts are maintained outside
this public repository.
