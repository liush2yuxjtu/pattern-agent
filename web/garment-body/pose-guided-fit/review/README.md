# Independent pose-guided review

Run from repository root with Python 3, numpy, scipy, opencv-python and Node.js available:

```sh
python tools/skill_evals/grade_pose_guided_fit.py --candidate work/pose-guided-fit-20261118/baseline --out work/pose-guided-fit-20261118/review/baseline
python tools/skill_evals/grade_pose_guided_fit.py --candidate work/pose-guided-fit-20261118/iterations/round-4 --out work/pose-guided-fit-20261118/review/round-4
python work/pose-guided-fit-20261118/review/negative_controls.py work/pose-guided-fit-20261118/iterations/round-4
```

The grader independently rasterizes OBJ triangles using the explicit 3×4 photo camera matrix. It reconstructs the body using `tools/human_fit/pose_guided/runtime.py` and its `calibrate-worker.mjs`, the real `web/human-studio/body-engine.js` and `assets/human.json`, checking every OBJ vertex. This is source independent of the fitter objective, but shares the actual body engine by design. Asset SHA256: `a75b6a2d59b2fa60ea29393e380182174627ba66d0993c649c8c571a6ccecda6`.

`provenance-contract.json` enforces original image, reference mask and unchanged frozen protocol hashes/dimensions. `acceptance.json` freezes region definitions/thresholds. `region-masks/*.png` are literal source pixel ROI masks, not generated anatomy segmentations. Never alter them to make a candidate pass. Original clothing mask is from the prior fixed source fixture and is not an anatomical body mask.

Automatic 3D plausibility is deliberately NOT_RUN: individual `manual-review.json` records direct inspection of saved actual front/side/back renders. Exact body/hand collision requires a dedicated geometry test; do not call visual inspection a collision simulation. One photograph cannot prove true hidden joint depth, exact grasp contact, true girths or full lower-body pose.

Negative controls regenerate real geometry for arm/pelvis pose faults, modify state alone to test metadata fraud, and shrink geometry to test containment cheating. A rejected control made from an already failing candidate proves rejection but does not alone prove sensitivity at a passing boundary; report source candidate and detailed outcomes.

Stable dependency migration: runtime/calibration/render now use tracked `tools/human_fit/pose_guided/`. The frozen legacy mask path resolves to tracked `tools/human_fit/pose_guided/real-photo/reference-mask.png` only if absent; content SHA remains mandatory. Regional protocol/thresholds unchanged.

Explicit publication replay (no ignored workspace dependency):

```sh
python tools/skill_evals/grade_pose_guided_fit.py --artifact-root web/garment-body/pose-guided-fit --candidate web/garment-body/pose-guided-fit/model --protocol web/garment-body/pose-guided-fit/review/acceptance.json --out /tmp/pose-guided-independent-replay
python web/garment-body/pose-guided-fit/review/negative_controls.py web/garment-body/pose-guided-fit/model
```

Read `grader-hill-climb.md` and `pose-sanity-contract.json` for the explicit v2 grader addition after a real arm negative control revealed a containment blind spot. This does not rewrite the frozen regional-v1 protocol.
