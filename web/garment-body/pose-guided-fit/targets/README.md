# Registered illustrative pose cues — 2026-11-18

These are **digitized illustrative cues**, not pose-detector output, ground truth, measured body dimensions, or proof of 3D pose accuracy. The input illustration explicitly says “Pose visualization — illustrative”. Human-selected marker identities are refined from colored pixels by OpenCV; each point retains its native coordinate, raw coordinate, seed, disk extraction radius, semantic, confidence, and uncertainty.

## Reproduce

From repository root:

```sh
python work/pose-guided-fit-20261118/targets/extract_pose_targets.py
```

Python 3.12.14, OpenCV 5.0.0, NumPy 2.3.5. Source SHA-256 hashes are in `registration.json`. The script reads `reference/original-product.jpg` and `reference/imagegen-pose.png`; it does not modify either input. Rendering the annotation onto a separate output image is the only modification to original-photo pixels.

## Registration evidence

SIFT with 7,000 feature budget; exclude dilated neon lines/markers and bottom caption; Lowe ratio 0.72; partial-affine RANSAC at 4 raw pixels. Native illustration is 1110×1417; unchanged original is 1000×1276.

- 522 illustration features, 790 original features.
- 155 ratio matches, 123 RANSAC inliers.
- Inlier mean error 1.378 px; median 1.211 px; p95 3.125 px; maximum 4.815 px after consensus refit.
- Inlier illustration coverage: x 93.5–831.4, y 5.1–1164.9.
- Native→raw matrix: `[[0.901880359, -0.000914902, -0.530189945], [0.000914902, 0.901880359, -1.009450119]]`.

The transform is one global similarity (scale/rotation/translation), **not a body warp**. It maps annotations only. The generated underlying image has small local changes; feature-registration residual is not marker/joint accuracy. `registration.json` contains every matched coordinate, inlier decision, and residual for independent inspection.

## Outputs and interpretation

- `pose-targets.json`: 22 individually digitized points and 10 illustrative links, mapped onto raw original coordinates. Names `image_left`/`image_right` mean viewer sides; in this approximately frontal image these correspond to subject right/left respectively.
- `raw-target-overlay.png`: mapped annotations on original photo; inspected visually against source.
- `native-marker-review.png`: extraction centers and names on native illustration.
- `registration-feature-matches.jpg`: actual feature correspondences retained by RANSAC, for quick registration verification.
- `registration.json`: transform, statistics, match evidence, input hashes, software.

The most important semantic corrections are:

1. **neckline_center** is the front garment neckline/upper chest, not the cervical bone head. Map to a front torso surface proxy.
2. **torso_midline** lies on the front garment surface below the sternum. Use as a soft front-surface midline cue; do not pin an internal spine joint directly to it.
3. **waist_image_left/right** are waistband/iliac-surface illustration markers. They are **not femoral hip joints**. Pair with waistband center and visible waist silhouette to constrain pelvis placement and torso lean. Body shape under a garment remains uncertain.
4. Shoulder/elbow markers lie under fabric and are inferred; use lower weights. Ear markers are occluded and particularly uncertain.
5. Hand nodes are only palm/contour direction helpers. The generated drawing does not establish validated MCP/finger topology. Do not fabricate exact finger articulation or use these as a 21-joint detector result.

Eyes/nose/wrists are more visually observable, but even those are illustration cues. Successful matching requires review of actual original-vs-render overlay across head, shoulder line, torso, waist, hands, and garment/body semantics; low cue residual alone is insufficient. A single photo cannot identify true depth or centimeter dimensions uniquely. M-size dimensions are a prior/assumption unless independently measured.
