# Constrained synthetic proxy fitting

Executed bounded SciPy optimization using only the supplied front and side binary masks. This is controlled synthetic silhouette consistency, not anatomical ground truth or a person's body measurement. The supplied source geometry, pose and camera are preserved. No back reference photograph exists; back.png is an inferred rendering of the same proxy.

## Evidence and results

| View | IoU initial → final | Dice initial → final | Mean contour px initial → final | P95 contour px initial → final |
|---|---|---|---|---|
| front | 0.952754 → 1.000000 | 0.975805 → 1.000000 | 1.123 → 0.000 | 9.000 → 0.000 |
| side | 0.888754 → 1.000000 | 0.941101 → 1.000000 | 3.147 → 0.000 | 12.000 → 0.000 |

Source masks were visually inspected before fitting. Height is frozen to the **assumed 170 cm prior**; bounds are recorded in metrics.json, with depth ratio constrained to [0.45, 1.05]. Circumference bounds are deliberately broad engineering priors, not population confidence intervals. Both views participate in fitting; neither is held out. No mask, camera, scale or source generator was modified. Native coordinates are X left/right, Y up, Z depth; these are preserved to avoid changing the existing model convention. Orthographic front views along +Z, side along +X and back along -Z; canvas is 384×640, horizontal [-50,50] cm, vertical [-4,180] cm.

The optimizer varies chest, waist, hip and depth_ratio with height=170 fixed. Search uses exact silhouette outlines of the supplied straight-centred loft construction; final masks and previews use the source generator triangle rasterizer on vertices independently reopened from fitted.obj. Metrics reopen actual saved PNGs and use the entire frozen canvas. OpenCV external contour points and exact Euclidean distance transforms produce pooled symmetric mean/P95 distances in pixels. Overlays: green overlap, pink reference-only, cyan model-only.

## Mesh and parameter interpretation

Final parameters: `{"height": 170.0, "chest": 96.29509988633787, "waist": 71.9301658975463, "hip": 100.01259696783724, "depth_ratio": 0.7875177015874257}`. Chest/waist/hip are ellipse-circumference controls in prior-scaled cm, not observed anatomy. Mesh-derived 48-edge torso-ring perimeters at native Y=128/109/88 cm are recorded under sections in metrics.json; small differences from parameter values follow polygon discretization and the ellipse formula. Source lofts include fixed head/limbs and have overlapping disconnected capped components. Reopened mesh has 1548 finite vertices and 3072 triangles; no boundary or nonmanifold edges, height 170 cm. This is a simplified synthetic proxy, not a production anatomical or physical fitting body.

## Uncertainty and limits

Two silhouettes constrain projected widths and depths under this fixed model; they do not determine arbitrary cross-section shapes, anatomical landmarks, clothing ease, tissue structure or an independently validated back surface. Side depth is inferred through the shared ellipse-ratio prior and observed synthetic side envelope. All cm values depend on assumed height; proportional changes in that prior scale all lengths. No statistical confidence interval or anatomical accuracy percentage is claimed. Pixel quantization permits multiple nearby parameters with the same raster silhouette. Remaining pixel discrepancies and each view's changes are preserved above. The weaker final view by IoU is front; any tie is equivalent. No unseen back evidence or extra observed photograph was invented.

## Reproduce and inspect

From the run directory: `python outputs/reproduce.py --inputs inputs --out outputs`. Dependencies are NumPy, SciPy, Pillow and OpenCV, with versions and SHA-256 provenance in metrics.json. It writes all requested files in outputs/, plus camera.json. Source input files remain unchanged. Inspect front.png, side.png, back.png, both overlays and initial/final masks. Numerical and mesh checks were executed; image previews are actual mesh renders. No browser, model weights, external service, or image generation was used.

## Post-export inspection performed

Opened all three actual mesh previews and both overlays after export. The previews show the existing capped, disconnected synthetic loft design; overlays are entirely overlap green where foreground exists. Independently imported the skill verification script and recomputed all four metrics for both stages and both views from saved mask files; every value matched metrics.json exactly (see independent-verification.json). Pixel-perfect final silhouettes do not imply unique parameters or human anatomical accuracy.
