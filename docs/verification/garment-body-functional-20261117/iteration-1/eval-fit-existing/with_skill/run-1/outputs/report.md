# Constrained synthetic proxy fit

Completed actual constrained parameter optimization using only the supplied front and side binary masks as target evidence. The 170 cm height is a fixed scale prior, not an observed human dimension. This is a synthetic simplified body proxy, not anatomical measurement or anatomical accuracy. No side or back photograph was observed or invented.

| Stage | View | IoU | Dice | Mean symmetric contour px | P95 px |
|---|---|---:|---:|---:|---:|
| initial | front | 0.952754 | 0.975805 | 1.1226 | 9.0000 |
| initial | side | 0.888754 | 0.941101 | 3.1466 | 12.0000 |
| final | front | 1.000000 | 1.000000 | 0.0000 | 0.0000 |
| final | side | 1.000000 | 1.000000 | 0.0000 | 0.0000 |

All comparisons use the same 384×640 frozen orthographic camera from inputs/camera.json, full canvas, >127 foreground threshold and unchanged reference masks. The contour protocol uses external full boundary chains and concatenated bidirectional exact Euclidean pixel distances. IoU is silhouette agreement, not body-dimension accuracy. metrics.json records reference and exported mesh hashes. Green overlay marks agreement, pink reference-only and cyan model-only pixels.

Fitted controls: {"height": 170.0, "chest": 96.07174144787164, "waist": 71.94736992050557, "hip": 99.6914922451739, "depth_ratio": 0.7837551414825598}. Chest, waist and hip are generator ellipse circumference controls in prior-scaled cm; depth_ratio is dimensionless. These values are mesh parameters constrained by synthetic silhouettes, not observed anatomical truth. Global height stays exactly 170. The optimization bounds were chest 60–125, waist 50–115, hip 65–130 and depth_ratio 0.45–1.05. A seeded differential-evolution search followed by bounded Powell refinement evaluated 816 candidates. optimization-history.json records actual improving candidates and solver termination messages. The budget was bounded; no claim of unique or global optimality is made.

fitted.obj was independently reopened by an OBJ parser, validated for finite indexed triangle geometry and rendered for all final masks and previews. mesh-check.json records dimensions, edge counts and degenerate triangle count. The native generator coordinate system (X lateral, Y up, Z depth) is deliberately preserved to keep the camera frozen. It consists of six capped, disconnected lofts; overlap and intersections are possible. Previews use the generator's simple triangle shading, not a photorealistic anatomical render. The back preview is an unobserved projection of the fitted proxy, never held-out evidence.

Uncertainty: only two synthetic silhouette masks constrain the solution; surface details, concavities, asymmetry, anatomy and back appearance are not observed. The fixed head, limbs and posture come from the supplied generator. Discrete rasterization creates subpixel parameter ambiguity, and 170 cm scaling remains a prior. Final residuals can reflect raster quantization and the bounded search. No invented confidence interval, photograph or measurement is supplied.

Reproduce from this folder: `python reproduce.py --inputs ../inputs`. generator.py and verify_masks.py are local copies of the supplied generator and skill metric helper. Requires NumPy, SciPy, Pillow and OpenCV. All required deliverables use the requested names; additional target copies, initial overlays, audit and history files aid review. No external service or image generation was used.

Independent validation: `python independent_check.py` recomputed overlap and contour metrics using SciPy Euclidean distance transforms and rerasterized the independently parsed OBJ. All values agree within 1e-6 and saved final masks equal the independently rerasterized mesh masks. The review sheet was reopened and visually inspected: initial torso discrepancies are visible in both views; final overlays show agreement. The synthetic back and disconnected arm geometry are visible. No browser-interaction check was needed for this static HTML/image evidence page.
