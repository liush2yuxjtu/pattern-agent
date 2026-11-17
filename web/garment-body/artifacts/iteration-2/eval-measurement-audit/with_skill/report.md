# Measurement audit

All inputs are synthetic controls. Results describe the supplied proxy mesh, never real-person dimensions. A single synthetic front is supplied; generated side/back previews are not observed evidence.

The original report summed disconnected loops and overstated evidence. Triangle-plane cuts were recomputed from body.obj. Coordinates are X left/right, Y vertical, Z front/back. Mesh units are prior-scaled centimetres under the supplied 170 cm stature assumption, without calibration.

| Section | Y plane | Selected torso cm | All loops cm (incorrect girth) | Loops |
|---|---:|---:|---:|---:|
| chest | 128 | 95.931477 | 158.718481 | 3 |
| waist | 109 | 71.948608 | 124.362106 | 3 |
| hip | 88 | 99.928621 | 141.619191 | 3 |

Each triangle edge crossing was linearly intersected. Endpoints were welded on a 1e-6 mesh-unit grid, duplicate segments removed, and degree-two adjacency graphs traversed into closed unbranched loops. No coplanar triangles occurred. The selected loop has the centroid nearest the central X=Z=0 axis. The plotted large central contour identifies the torso; small lateral contours are excluded arms. Loop closure alone does not establish anatomical validity.

Mesh contains 1548 vertices and 3072 triangles; vertical span is 170.000000 prior-scaled cm. Height 170 cm remains a prior (not independently measured).

Bust-point distance stays null: no semantic landmarks or reliable multi-view observations exist. Observed physical depth stays null; the 25.3 cm claim is withdrawn. corrected-depth.png preserves the synthetic side drawing but replaces its caption. No depth estimator or Z-buffer was run.

Uncertainty: units depend on the height assumption; all lengths change linearly with scale (1% scale change = 1% length change). Polygonal resolution, endpoint tolerance, section location, proxy design, garment ambiguity and missing calibration limit interpretation. There is no statistical basis for a confidence interval.

Verification: executed NumPy triangle intersections and rendered all selected/excluded loops with Matplotlib. Source hashes, component perimeters, selection indexes, mesh bounds and software versions are saved in corrected-measurements.json. Further VTK cross-check and visual inspection are recorded in transcript.md.

Reproduce with `python outputs/reproduce.py` from this run directory. Requires local NumPy, Matplotlib and Pillow; no paid or external service. Font: local DejaVu Sans.

No blockers for this synthetic audit. Unknown physical/anatomical quantities remain unavailable.

Actual validation results: the skill VTK cutter/closest-point component helper was executed at origins [0,128,0], [0,109,0], [0,88,0], normals [0,1,0], and matching central seeds. It agreed with the independent triangle graph implementation within 1.5e-14 cm; full results are in vtk-crosscheck.json. Visual inspection opened section-evidence.png and corrected-depth.png: three closed contours are visible per section, central torso green and both arms excluded; the old observed-depth caption is covered and replaced.

The input reported chest/waist/hip 128.7/97.1/123.4 cm. These values are not reproducible even as the actual sum of every loop (158.718481/124.362106/141.619191 cm); both the numbers and stated method were rejected. Height 170 cm equals mesh vertical extent but remains the scale prior. The original bust distance 19.6 cm has no evidence and is null.
