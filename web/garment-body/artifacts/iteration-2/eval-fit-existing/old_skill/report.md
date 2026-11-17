# Synthetic proxy fit evidence

Executed a constrained four-parameter fit to the two supplied binary target masks. No photographs, target parameters, or back evidence were used. This is a synthetic proxy consistency test; it does not recover a real person or establish anatomical accuracy.

The source generator is retained verbatim. Its coordinates are X lateral, Y up, Z depth. Camera is the supplied fixed orthographic 384×640 projection with horizontal extent [-50,50] cm and vertical extent [-4,180] cm. Height is fixed at the assumed 170 cm. No translation, camera adjustment, pose, head, or limb optimization was performed.

Bounds (cm under the prior): chest 60–120, waist 50–110, hip 65–130; depth_ratio 0.45–1.05. All scales remain positive. Additional bounds are broad proxy regularization, not observed anatomy. Objective is mean front/side (1−IoU); deterministic differential evolution followed by bounded Powell. The finite budget and raster plateaus mean the solution is not guaranteed unique or globally optimal.

| View | Initial IoU | Final IoU | Initial Dice | Final Dice | Initial mean/P95 px | Final mean/P95 px |
|---|---:|---:|---:|---:|---:|---:|
| front | 0.952754 | 1.000000 | 0.975805 | 1.000000 | 1.123/9.000 | 0.000/0.000 |
| side | 0.888754 | 1.000000 | 0.941101 | 1.000000 | 3.147/12.000 | 0.000/0.000 |

Final parameters: `{"height": 170.0, "chest": 95.76895901773013, "waist": 72.59665936499452, "hip": 99.89305238999965, "depth_ratio": 0.7802819757968494}`. These are mesh parameters inferred from synthetic silhouette evidence conditional on the source model and height prior. Circumference labels use the generator’s Ramanujan ellipse approximation; no anatomical measurement claim or unsupported confidence interval is made.

Final masks and all previews were rendered from vertices/faces independently reopened from fitted.obj, then all PNG masks were reopened for scoring. Initial and final metrics use identical targets, full canvas, thresholds and external-contour protocol. See validation.json for actual topology checks. The proxy consists of disconnected capped components and lacks anatomical detail.

Overlay legend: green overlap, pink target-only, cyan model-only. Front/side/back PNGs are actual mesh previews; back is a symmetry-driven model prediction with no observed back target. No held-out view exists. Neither IoU nor contour distance is a percentage of body measurement accuracy. Pixel quantization and shared generator assumptions limit identifiability; unmodeled anatomy, asymmetric depth, pose and perspective remain unconstrained.

Weakest final view by IoU: front. All target masks and camera hashes are in provenance.json. Reproduce from run directory with `python outputs/reproduce.py`; the script carries the source generator and metric helper alongside it. No external services are needed.
