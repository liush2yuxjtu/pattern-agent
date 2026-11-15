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

The next experiment generates a standalone model and standalone garment without
the prior garment generator, then compares the frozen verifier against an
independent geometric oracle and known invalid controls. Results will distinguish
cloth defects from detector errors and limits of the arm-routing claim. A clean
static mesh does not establish cloth simulation or real-world fit.

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
