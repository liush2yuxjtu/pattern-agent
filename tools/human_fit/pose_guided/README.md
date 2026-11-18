# Pose-guided adjustable human fitting

This is the actual numerical source used for the 2026-11-18 photo fit. Python FK/LBS evaluates the same 163-bone MakeHuman asset and actual cm calibration as Human Studio. All exported views share one state/posed mesh. Image Gen landmarks are illustrative garment-surface hypotheses, not detector truth or true person measurements.

Requirements: Python 3.12.14 tested, numpy, scipy, opencv-python; Node 24+ (tested 24.22.1). No API key, paid generation or GPU is used by fitting. Repository `web/human-studio/assets/human.json` and `body-engine.js` are the fixed CC0 source asset/calibration dependencies. Original product photo, Image Gen annotation, registered targets, baseline state/camera are explicit inputs in `work/pose-guided-fit-20261118` (packaged with the downloadable evidence ZIP).

```
python tools/human_fit/pose_guided/fit.py --label replay --resume work/pose-guided-fit-20261118/iterations/round-7 --handonly --ik-length --steps 100
python tools/human_fit/pose_guided/check_hand_surface.py --candidate work/pose-guided-fit-20261118/iterations/replay
python tools/human_fit/pose_guided/export_evidence.py --candidate work/pose-guided-fit-20261118/iterations/replay
python tools/skill_evals/grade_pose_guided_fit.py --candidate work/pose-guided-fit-20261118/iterations/replay --out work/pose-guided-fit-20261118/iterations/replay/independent-grade
```

Set `POSE_FIT_WORK_ROOT` to an alternate input/output directory with the same reference/targets/baseline structure. `final-state.json` includes every bone and all actual cm controls; import it in Human Studio to continue adjusting. OBJ is centimetres; GLB is metres. GLB itself is a frozen surface export, while state+the original asset retain all adjustable controls.

`check_hand_surface.py` intersects every actual hand vertex ray with actual torso triangles. Only rays with two separated skin intersections are classified; this is a bounded skin overlap check, not cloth physics. The region grader and human review remain separate. Visible residuals and FAIL results must be retained.

The selected candidate is round14, overall FAIL pending human review. The final block freezes round7 body/camera and uses actual calibrated upper-arm/forearm surface rulers28/25cm, then fits arm/wrist rotations against stronger actual elbow/wrist cues and body clearance. It fixes the inverted left forearm of round13 and detects zero skin penetrations on1424 R and1402 L covered rays;22 L rays remain unclassified. Hidden elbow residual(~46px), right-arm/waist contours and cup-like hand action remain visible failures. This is an improvement candidate, not a perfect pose/garment-pinch recovery.
