# Generation2: real anatomical avatar and observed evidence

The current selected avatar is an actual CC0 MakeHuman mesh,13,380 surface vertices,26,756 triangles and163 bones, with real authored morphs and four-weight skeletal skinning from Human Studio. Asset SHA256 is `a75b6a2d59b2fa60ea29393e380182174627ba66d0993c649c8c571a6ccecda6`.

Verified original product metadata identifies ASOS211010805, a boat-neck three-quarter-sleeve pointelle top; the catalog model is171cm wearingS. The current avatar uses a separately authorized170cm/M prior. Those are distinct facts. Generation2 corrects the previous long-sleeve imagery; it does not create independent real-person body observations.

## Current adjustable state and actual exports

Final target dimensions(cm): height170, bust90, waist69, hips96, shoulders37, upperArm27, thigh50, neck32, upperArmLength29, forearmLength23, thighLength40, calf36. Original authorizedM was waist72/thigh54 with the other targets unchanged. Changed waist/thigh are conditional `clothed_envelope_estimate` values from AI-generated references; unchanged values remain `prior`. None are measurements recovered from the real catalog model.

`initial-state.json` permanently preserves the originalM. `final-state.json` imports into Human Studio with exact version/asset fingerprint,12 adjustable target dimensions, calibrated morph weights and complete163-bone pose entries. Dimensions actually change vertices; rotations actually drive skinning.

- `final-neutral.obj`: selected actual neutral measurement surface, centimetres,Y up.
- `final-posed.obj`: selected actual source-skinned surface,cm.
- `final-posed.glb`: selected actual rig/skin,163 bones; real0.01 world matrix converts cm to metres.
- `final-posed-joints.json`: actual posed bone world positions.
- `final-renders/`: actual normal-color front/side/back/upper-body-closeup renders, realfront skeleton projections, masks, numerical`rawdepth.npy`/`depth.npy` and`depth-valid.png`. Geometry images are768×1024, separate from generated illustrative pose/depth images.
- `final-independent-check.json`, `final-geometry-check.json`, `final-geometry-audit.json`, `neutral-measurements.csv`: independent reconstruction and export checks.
- `render-provenance.json`: generation2 binding of final state, posedOBJ, camera and every final-render file hash. Hash integrity does not prove real-person truth.

Independent matching-asset neutral reconstruction gives maximum target residual0.000818cm. Independent NumPy versus source Three.js LBS differs by at most0.00001229cm. Actual final source-render masks equal the fitting masks exactly.115,625 front depth pixels are finite and valid. These are numerical geometry checks, not physical or human measurement accuracy bounds. No cloth/tissue/support/collision simulation is run.

## Frozen actual generation2 inputs

All front/side/back native images are1086×1448. OpenCV GrabCut was freshly run for generation2 on uniform768×1024 copies with recorded seeds and visually inspected for hair, person, clothing, gaps and detached shadows. The original v2 files remain unchanged. `references-generation-2/` stores frozen masks/segmentation previews; `fit/input-hashes.json` records image hashes, mask ndarray-byte hashes and native/evaluation resolutions; `fit/frozen-references.json` binds evaluation references.

Fresh manual annotations on the actual v2 images locate6 front/side and4 back wrist/ankle centers. Cuff occlusion and side identity make these approximate. No detector ran. `images/landmarks.json` and `fit/frozen-landmarks.json` preserve the points. `fit/*-reference-landmarks-roi.png` shows magenta manual points, exact optimization regions and yellow approximate neck/ankle camera anchors. Camera anchoring points do not become independent validation landmarks.

## Camera, shared pose and shape contributions

First, per-view orthographic scale/translation was fitted approximately from neck-base and ankle-height anchors using the original170cmM mesh, then frozen. These are nuisance registration cameras, not physical photographic calibration. `camera-calibration.json` preserves anchors, uncertainty and source/calibrated camera hashes. Front/pose/depth share a front camera. Full cameras are in`camera.json`; generic side projection explicitly uses horizontalZ/depthX.

Second,520 actual bounded Powell evaluations fitted10 shared shoulder/elbow/hip/knee angle components to front+side manual joints, with a weak limb-region clothing-envelope term and regularization. Back wrist/ankle errors and silhouette never entered that objective. The complete fixed-M result is preserved in`fixed-M-baseline/`. `fixed-M-baseline/fit/camera-pose-contributions.json` separates source-camera neutral, calibrated-camera neutral and calibrated-camera shared-pose scores; do not interpret it as final conditional-shape scores.

Third, the actual source`fitDimensions` solver calibrated every cm-shape candidate. A torso-only33-candidate search is preserved in`shape-fit/torso-only-search/`. The selected45-candidate search used fixed cameras/shared pose and reasonable adult bounds on bust/waist/hips/shoulders/upperArm/thigh/calf, with height170 fixed. It penalized body pixels outside the2px-dilated clothed torso/hip/leg envelope, a weak exposed-forearm term and deviations fromM. Loose trousers supplied only an upper containment bound, never naked-body width equality. Back did not enter the shape objective.

The selected shape is waist69/thigh50. Objective0.02397→0.01398. Side containment loss0.02137→0.00986(−54%), but side outside pixels3578→2850(−20%): these are different metrics. Front outside pixels936→797. The selected candidate does not hit a search bound. `shape-fit/optimization.json` records all actual candidates, calibrated states, bounds, regularization and losses. `shape-fit/*-before-after.png` compares fixedM versus conditional shape at exactly the same pose/camera. Shape search stops with remaining clothed-envelope discrepancies and prior regularization; it does not force all pixels to agree.

| Full clothed-envelope IoU | Calibrated M neutral | M shared pose | Conditional shape/shared pose |
|---|---:|---:|---:|
| Front |0.78887|0.81420|0.80564|
| Side |0.58741|0.68676|0.68376|
| Back, held out of optimization |0.73849|0.74962|0.74437|

Shape containment improves while full-envelope IoU regresses versus theM shared-pose result; all regressions and mean/P95 contour distances are retained. The body should fit inside clothing; matching the whole loose garment boundary is not the objective. Final shared-pose manual errors are front wrists3.46/0.18px and ankles3.10/2.89px; side wrist5.40px and ankle3.45px. Held-out back wrists remain23.15/30.76px, ankles3.36/9.99px. Generated arm poses differ across views. Side remains the weakest full-envelope view; hair, torso projection, clothing ease and hand articulation retain visible discrepancies.

`fit/metrics.json` is the current final metric set. `fit/{front,side,back}-before-after.png` and`fit/all-before-after.png` overlay the actual mesh/rig on the actual v2 photos: initialM neutral→conditional shape/shared pose with the same calibrated cameras. Cyan=model, magenta=manual landmarks/error vectors. Mask overlaps use green=overlap,pink=reference-only,cyan=model-only.

## Independent view-specific pose adaptations

The same final dimensions/morph weights can use different arm poses to match the different generated stances. `side-state.json` and`back-state.json` retain the same body as`final-state.json`; actual OBJ/riggedGLB/cameras/color renders/overlays are under`view-specific/{side,back}/`. Each directory has`metrics.json` and`before-after.png`, comparing the shared pose to the independent view pose.

View-specific side wrist error becomes0.18px; back wrists0.22/0.08px. These are fits to those views, not held-out validation. Shape and cameras remain unchanged; shared main defaults and held-out results are preserved separately. Foot errors remain unchanged. Flexible pose adaptation does not justify changing the body shape to impersonate another stance.

## Separate original-photo check: POSE_FAIL

The original catalog photograph has a different oblique bent-arm pose, crop, garment gathering and partly hidden hands. `original-reference/` keeps the same final conditional body but a separate native1000×1276 crop camera. It includes actual OBJ/riggedGLB, normal-color front and90degree-side renders, manual annotations, frozen OpenCV mask, before/after overlays and metrics. The main default avatar, generation2 cameras/renders and side/back generated-view adapters remain unchanged.

The initial bent-arm and head solve greatly reduced2D wrist/eye/nose errors. Actual colored mesh inspection then exposed a serious failure: one hand folded vertically and another hid behind/inside the abdomen. Low2D errors were therefore rejected as evidence of a recovered action. `iteration-2/` preserves this low2D-error candidate. `iteration-3-depth-dominant/` brings the hands forward but displaces elbows57/142px and raises both arms; `iteration-4-elbow-dominant/` improves elbows but retains hand-body intrusion and exaggerated wrists. Both were rejected by independent actual front/side review.

`iteration-5-forward-IK/` is the latest failed diagnostic and is mirrored at the top of`original-reference/`; it is not an accepted matched pose. Actual shoulder/elbow twist, wrist orientation and mild finger flexion produce forward-visible hands pointing inward. Wrist errors are1.26/3.92px, elbow errors1.78/4.77px, eyes6.31/13.75px and nose12.79px. However, side rendering shows the hands outstretched far ahead of the abdomen, rather than gripping a nearby hem. Minimum actual hand-surface clearance in the front-axis torso check is21.16/25.30cm. Full visibility alone is insufficient; fingers still do not establish a convincing cloth grasp.

`ik-depth-feasibility.json` records actual source bone-head segment lengths26.8513cm(shoulder→elbow) and23.2162cm(elbow→wrist), the fixed shoulder world positions, inverse-projected2D elbow/wrist coordinates, algebraic depth formulas and all four sign branches per arm. These actual bone-head distances are distinct from ruler target dimensions29/23cm. With the frozen camera and approximate original annotations, the forward branches give wristZ≈36.09/47.93cm; rear branches move the hands into/behind the torso. `torso-front-depth-cm.npy` is an actual torso-triangle Z-buffer used for depth tests, with semantics and fallback recorded in the feasibility report. `hand-depth-check.json` is not collision or physical-contact certification.

`candidate-status.json` and`metrics.json` explicitly record **POSE_FAIL / UNRESOLVED / DEPTH_AMBIGUOUS**, with no accepted matched candidate. Independent review agreed to stop after the bounded attempts: neither the low2D rear solution, depth-dominant compromise nor forward solution reproduces a plausible near-abdomen hem grip. This is failure of the current fixed camera/shape/approximate-landmark hypothesis, not proof that the real person cannot make the pose. Exact camera, true limb proportions and hidden hand depths are not identifiable from this single crop. Changing the already-frozen default body to chase this photo would conflate separate evidence. Additional real views or reliable original-body/camera evidence would be needed to resolve it.

`geometry-check.json` only passes numerical export consistency and identical body shape; it explicitly carries`pose_verdict:POSE_FAIL`. The diagnostic is never combined with generated-view metrics and is not an observed-fit PASS. The originalM version remains under`fixed-M-baseline/original-reference/`. All failed candidates and actual side renders are retained so that the negative result can be inspected directly.

## Preserved history and reproduction

`generation-1/` preserves all generation1 inputs, selected fit, exports and its earlier`iteration-1/` camera/held-out failure. `fixed-M-baseline/` preserves generation2 fixedM outputs before cm-shape fitting. The current top-level`images/` and final outputs are generation2.

Key actual entry points: `build-model.mjs`(original anatomical prior),`calibrate-camera.py`,`fit-generated.py`(shared pose),`fit-shape.py`/`shape-candidates.mjs`(actual cm solver),`export-pose.mjs`(source-compatible skin/GLB),`fit-view-specific.py`,`check-original-reference.py`/`refine-original-pose.py`/`refine-original-hands.py`/`finalize-original-pose-failure.py`,`finalize-evidence.py`,`verify-candidate.py`,`audit-model.py`. The generic renderer is`work/anatomical-skill-evals-20261117/fixtures/render_mesh.py`. Saved calibration/reference hashes, intermediate states, candidate histories and final bindings allow reproduction. Do not overwrite frozen references or interpret exported numerical precision as real-person accuracy.
