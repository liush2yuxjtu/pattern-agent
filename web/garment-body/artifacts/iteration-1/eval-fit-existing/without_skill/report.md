# Synthetic proxy fit evidence

The exported proxy matches both supplied binary masks exactly at the frozen 384 × 640 pixel camera. Both front and side IoU improved by more than 0.03. No target evidence beyond `inputs/target-front-mask.png` and `inputs/target-side-mask.png` was used.

| View | Stage | IoU | Dice | Mean contour distance (px) | P95 contour distance (px) |
|---|---|---:|---:|---:|---:|
| front | initial | 0.95275387 | 0.97580539 | 1.122637 | 9.000000 |
| front | final | 1.00000000 | 1.00000000 | 0.000000 | 0.000000 |
| side | initial | 0.88875370 | 0.94110069 | 3.146642 | 12.000000 |
| side | final | 1.00000000 | 1.00000000 | 0.000000 | 0.000000 |

Fitted parameters: height 170 cm (fixed prior), chest 95.723453, waist 72.635147, hip 100.057357 prior-scaled cm; depth_ratio 0.78573439. These values describe a synthetic model and are not observed real-person measurements. Circumferences were constrained to 40–160 cm and depth_ratio to 0.45–1.05. The final geometry contains 1548 finite vertices and 3072 triangular faces with a measured height of 170 cm.

The optimization initializes from central torso row widths, then minimizes equal-weight front/side (1 − IoU) using seeded differential evolution and bounded Powell refinement. It used 703 raster objective evaluations. The supplied generator and camera were preserved. The camera projects front on x, side on z, and back on −x with x/z extent −50..50 and vertical extent −4..180 cm. No translation, rescaling or mask editing was applied.

Metrics use white foreground >127, intersection/union for IoU, twice intersection/summed area for Dice. Contours are foreground minus one cross-shaped binary erosion. All distances are pooled bidirectional nearest-contour Euclidean pixel distances; P95 uses NumPy percentile. `metrics.json` includes camera details and SHA256 reference-mask hashes. `verification.json` records independent OpenCV metric calculations agreeing within 1e-6. The OBJ was independently reopened, and rerendered final masks and all three previews were pixel-identical to the delivered images. Assertions for height, positive parameters, depth bounds, triangular finite geometry and required IoU gains passed.

`front-overlay.png` and `side-overlay.png` use gray for overlap, cyan for target-only pixels and pink for candidate-only pixels. Because the final masks match, no colored mismatch remains. Initial/final binary masks are included. `front.png`, `side.png` and `back.png` render the reopened actual mesh. The back is generated model evidence only: there is no observed back reference. Front/back symmetry follows this proxy construction.

This exact pixel match does not identify unique latent parameters or prove anatomical accuracy. Rasterization has parameter plateaus, and the simplified disconnected capped-loft geometry has fixed head and limbs. Two silhouettes under this model constrain only its available parameters; they do not validate unseen surfaces, anatomical landmarks, body composition or clothing. The 170 cm scale is an assumed height prior. Parameter decimal places are reproducibility values, not measurement precision.

Run from this directory: `python reproduce.py --inputs ../inputs --out .`; then `python verify.py`. Python requires NumPy, SciPy, Pillow and OpenCV. The adjacent `generator.py` is an unchanged copy of the supplied generator. `fit-log.txt` records the actual optimizer output. `index.html` provides a local comparison gallery. No external services or image generation were used.
