# Single-file mannequin and cloth motion reproduction

The two generators were recovered byte-for-byte from saved source. Their hashes
are66f95f1f…152915 (model) and9ac6bef0…610b0a (cloth). They were not changed to
obtain a passing result. This directory contains a new actual Blender4.3.2
execution of those frozen sources, separate from the analytic block controls.

- [`assets/model.blend`](assets/model.blend): standalone complete rigged mannequin.
- [`assets/cloth.blend`](assets/cloth.blend): portable measured121-frame garment
  replay with the mannequin for context; no external geometry cache is needed.
- `one_shot_model.py` and `one_shot_cloth.py`: each generator is a single file;
  the cloth generator reads the standalone mannequin file.
- `evidence/frames.zip`: every measured NPZ frame, plus separate JSON reports.

The mannequin includes head, torso, shoulders, arms, hands, legs and feet. Motion
is A-pose → T-pose → arms raised → A-pose at24fps. The garment is a preassembled
synthetic3D mesh, not a paper-pattern sewing experiment. Body and material values
are uncalibrated. There is no human fit approval.

Actual121-frame result: **83 saved poses PASS,35 confirmed FAIL,3 UNKNOWN; overall
FAIL**. The independent v2 check finds35 self-intersection frames, peak34 pairs;
cloth/body crossings, body self-intersections and sampled cloth containment are0
throughout. The86 geometrically clean meshes include the3 unresolved route cases,
so86 clean meshes must not be reported as86 successful wearing poses.

## Reproduction commands

Use fresh `runs/` directories. Requires Blender4.3.2, Python3.12, NumPy and SciPy.

```sh
blender -b -t 2 --python-exit-code 2 --python one_shot_model.py -- --out runs/model
blender -b -t 2 --python-exit-code 2 --python one_shot_cloth.py -- --model runs/model/model.blend --out runs/cloth
blender -b -t 1 --python-exit-code 2 --python ../full_arm/verification/geometry.py -- \
  --frames runs/cloth/frames --topology runs/cloth/topology.json --out runs/legacy
python3 verify_motion.py --workers 4 --frames runs/cloth/frames --legacy-report runs/legacy/verification.json --out runs/independent.json
blender -b -t 1 --python-exit-code 2 --python inspect_caps.py -- \
  --run runs/cloth --legacy-report runs/legacy/verification.json --out runs/caps.json
python3 adjudicate.py --audit runs/independent.json --caps runs/caps.json --out runs/adjudication.json
```

The geometry commands exit2 for an observed quality FAIL. Execution completion
is separate from approval; do not weaken the checks or discard failed frames.
To inspect delivered data without solving again, unzip `evidence/frames.zip` and
use `evidence/topology.json` and `evidence/legacy-verification.json` as references.

## Independent verification and uncertainty

The v2 oracle retains incident triangles and checks topology, cloth self-overlap,
body self-overlap, cloth/body crossings and sampled cloth containment in every
saved frame. A conservative slab bounding box removes only proven exterior
samples before solid-angle queries. Three known-volume tests compare that pruning
against full winding, including rotated and disconnected closed volumes.

```sh
python3 -m unittest discover -s . -p test_containment.py -v
```

Three right-cuff alarms at118,120,121 depend on the artificial cap: the old
centre fan yields3 hits, a corner fan over the identical boundary yields1, and
the consistently oriented centre cap has signed crossing sum1. Sleeve-wall
crossings are0. These cap-dependent cases are UNKNOWN, not proven wearing faults
and not an excuse to choose the favorable cap and declare PASS. Original strict
flags are retained. See `evidence/adjudication.json` for the final saved-pose counts.

The replay was copied alone into a new empty directory, reopened, and compared
against every body/cloth vertex and triangle in all121 measured frames. Maximum
coordinate difference is1.49e-8m; all121 frames and shape keys are present, with no
external geometry dependency. Actual Blender stills are saved under `evidence/`.

Saved-pose geometry and trusted-source arm routes do not establish actual donning,
continuous-time collision freedom, calibrated mechanics, comfort or physical fit.
