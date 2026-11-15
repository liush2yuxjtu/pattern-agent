# Pattern Agent

Runnable Blender garment experiments and independent geometry checks. This is a
research repository; physical garment fit has not been verified.

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
