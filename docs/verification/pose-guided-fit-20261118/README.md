# Original-photo pose fitting and failure-sensitive review

This run addresses the user's screenshot of the old single-state review: a large
cyan torso/hip offset was hidden behind opaque overlap colouring and a historical
20/20 functional score. That score is preserved, not relabelled as visual success.
This is a single-case fitting/critic iteration, not a native Claude trigger test
or a statistically controlled skill benchmark.

## Evidence and frozen interpretation

- Unchanged original: `web/garment-body/pose-guided-fit/reference/original-product.jpg`,
  SHA256 `6fd6310bc225b6ba4e80f5b49a57ef75f737c08e5fbd983a95694afb402e1e53`.
- Actual preceding-turn Image Gen pose output is reused, not regenerated or called
  detector truth. OpenCV maps its annotations to the raw photo using a global
  similarity, not a body warp: 123 inliers, mean 1.378 px, p95 3.125 px.
  Registration accuracy is not joint/anatomy accuracy. Collar and waistband
  markers are surface cues, not internal neck/hip joints.
- The baseline and candidates use the actual MakeHuman asset and centimetre
  calibration, with one full bone-pose state shared across front/side/back.
  Generic M170 scale is a prior; these are not measured dimensions of the person.
- Regional acceptance was frozen before candidate review. Any critical region
  failure vetoes 2D PASS. Baseline right waist/hip: 52.37% outside, exterior
  contour p95 213.56 px, scanline centre error up to 223.5 px.
- A separately versioned action supplement was added after a real negative control
  exposed a blind spot: a reversed forearm could improve containment. Visible
  wrist residual and coarse arm direction are now explicit gates. The original
  regional thresholds were not relaxed or retroactively called the supplement.
- The critic rebuilds FK/LBS from source, projects OBJ itself, and rerenders actual
  front/side/back pixels; file existence or self-reported metrics do not suffice.
  Hash-bound manual 3D review remains separate from 2D scoring and software checks.

## Why iterations were rejected

The preserved round-2 example improved photo alignment while introducing a
whole-body forward lean and a hand disappearing into the torso. Round 9 matched
2D wrists while separating hands in depth. Round 13 removed detected right-hand
penetration but reversed the image-left forearm (elbow below wrist), so avoiding
collision could not count as matching the original action. These are actual
rendered outputs, not synthetic illustrations of hypothetical failures.

## Verification method

Followed `.agents/skills/verify/SKILL.md` and its product-case / Human Studio /
skill-eval recipes. Relevant checks are local, using real Playwright/WebGL
consumers; the existing Pages workflow is publication only, not a test gate.
The fixed Anthropic creator and grader guidance under
`tools/skill_evals/upstream/` informs the output inspection, eval critique,
negative controls and human review. Native Claude routing remains BLOCKED;
physical cloth fit remains NOT_RUN.

The historical T-shirt cloth FAIL (7.6455 mm seam gap, 20 nonadjacent face
intersections) is unrelated and unchanged.

## Selected candidate and observed results

Candidate: round14, stable published `model/final-state.json` and `posed.obj`.
Verified working tree based on remote main `54c8d8280f5c732be109722bbe2d11037619c6bb`;
source digests are in `candidate-files.json`. Four specialists handled annotation,
actual fitting, independent criticism and review UI; missing timing/token data
were not invented.

**Overall original-photo/action match: FAIL.** Software integration and shared
model replay PASS. This is a visibly improved, editable candidate, not completed
recovery of the photographed gesture or the person's dimensions.

| Check | Observation |
| --- | --- |
| Right waist/hip exterior contour p95 | 213.56 → 35.56 px |
| Maximum waist/hip scanline centre error | 223.5 → 35 px |
| Source cm/FK/LBS reconstruction | maximum posed vertex difference about 5.0e-9 cm |
| Actual front/side/back/photo replay | pixel channel difference 0, independent silhouette IoU 1 |
| Right hand torso rays | 1424 classified, no detected inside points; minimum anterior clearance 1.438 cm |
| Left hand torso rays | 1402 classified, no detected inside points; 22 unclassified; minimum clearance 3.182 cm |
| Left elbow cue residual | 46.25 px; hidden/generated cue, not measured anatomy |
| Visible original image-right wrist | 39.48 px, exceeds supplement's 35 px limit |
| Regional and manual action review | FAIL: left shoulder, both arms, right waist/hip; cupped palms do not restore original grip |

The model retains M170/90/71/96 cm priors; calibrated surface upper-arm/forearm
rulers are 28/25 cm, while actual neutral bone-head distances are about
25.843/25.220 cm. Maximum neutral ruler-target residual is 0.000041 cm.
Mesh calibration is not evidence that these dimensions match the real person.

## Executed verification

```sh
python tools/skill_evals/smoke_helpers.py --out work/pose-guided-fit-20261118/skill-smoke
PYTHONPATH=tools/skill_evals/upstream python tools/skill_evals/upstream/scripts/package_skill.py .agents/skills/garment-body-six-view skill-packages
python scripts/build_garment_body_skill_page.py
python tools/skill_evals/build_pose_guided_review.py
python tools/skill_evals/build_single_state_review.py
python tools/skill_evals/grade_pose_guided_fit.py --artifact-root web/garment-body/pose-guided-fit --candidate web/garment-body/pose-guided-fit/model --out docs/verification/pose-guided-fit-20261118/publication-replay
python docs/verification/pose-guided-fit-20261118/check_export_units.py web/garment-body/pose-guided-fit/model docs/verification/pose-guided-fit-20261118/export-units.json
python scripts/build_pages.py
python -m http.server 8941 --bind 127.0.0.1 --directory dist
node tools/skill_evals/verify_pose_guided_review.cjs --url http://127.0.0.1:8941/garment-body/single-state-evals/eval.html --out docs/verification/pose-guided-fit-20261118/browser-original-url
node tools/skill_evals/verify_pose_guided_review.cjs --url http://127.0.0.1:8941/garment-body/pose-guided-fit/eval.html --out docs/verification/pose-guided-fit-20261118/browser-focused-url
node scripts/verify_human_studio_handoff.cjs --url http://127.0.0.1:8941/human-studio/ --model-url ../garment-body/pose-guided-fit/model/final-state.json --output docs/verification/pose-guided-fit-20261118/model-handoff
```

- Helper smoke, official package validation/readback, strict builders and local
  browser consumers PASS. Actual fitting remains FAIL as above.
- Opened desktop, mobile and overlay screenshots. Drove alpha, before/after,
  source vs true FK layers, zoom, galleries, actual OBJ download and model import.
  Historical run/grade data and feedback storage keys remain byte-for-byte intact.
- The dedicated handoff test changed centimetres and joint angles, exported JSON,
  restored it and reopened the same geometry; invalid/cross-origin imports were
  rejected without replacing the editable state.
- Independent GLB binary parsing verifies metre positions against cm OBJ for all
  13,380 vertices in both posed and neutral exports. GLB is a frozen surface;
  JSON + original runtime/asset retain editable morphs and bones.
- Six real negative controls were rejected. A preserved local arm corruption
  still passes containment in that region but fails v2 wrist/direction gates;
  this demonstrates a specific grader improvement rather than counting a source
  that already failed elsewhere as proof of sensitivity.
- A real stale-candidate sentinel was removed by the builder. Pending/stale
  grading and changed-source gates remain strict. Two packaging defects found in
  verification were fixed: missing view-check dependency and stale temporary
  solver files surviving a build.
- The reproduction ZIP was extracted and executed independently: dimensions and
  all 163 bone angles equal the source, posed OBJ byte-for-byte equal. Its
  checker/export/grader commands run with source/view PASS and action/grasp/overall
  FAIL. Later README-only prerequisite corrections left core files unchanged.
  Final ZIP SHA256: `d756054a437f20f0bc2f14c41d1bb6c4537b370fc5ab3b17d11591875a33e3ad`.
  Tested environment: Python 3.12.14, Node 24.22.1.

Local browser evidence is distinct from live publication. A preflight public
Pages HTTP request from this environment returned 403; no live interactive PASS
is inferred from local tests or a publication workflow receipt. Owned local
servers and browsers are closed after verification.
