# Synthetic measurement and evidence audit

All inputs are synthetic controls. No result is a measured real-person dimension. The only supplied reference view is a synthetic front; side and back previews are generated. Mode: `prior_avatar`.

## Calculated measurements

| Selected section | Y level | Torso perimeter (prior-scaled cm) | Loops intersected | Excluded arm lengths (cm) |
|---|---:|---:|---:|---|
| chest | 128 | 95.931477 | 3 | 31.393502, 31.393502 |
| waist | 109 | 71.948608 | 3 | 26.206749, 26.206749 |
| hip | 88 | 99.928621 | 3 | 20.845285, 20.845285 |

## Method and uncertainty

`reproduce.py` parses actual OBJ faces, triangulates any polygons, intersects every triangle with each supplied horizontal Y plane, merges coincident endpoints on a 1e-6 mesh-unit grid, deduplicates segments and traverses the adjacency graph. Every retained component has degree two at every vertex and closes. Each section has a unique central loop containing X=Z=0; the lateral disconnected arm loops are excluded. No OBJ group labels or input reported circumferences are used as numeric measurements. Polygonal edge lengths are summed only for the selected torso loop. The evidence image plots actual triangle geometry and all section loops.

Units are inherited from the supplied `prior-scaled cm` declaration, with assumed height 170 cm and no calibration. Mesh Y extent is checked in JSON; this does not independently validate scale. All lengths change linearly with assumed height (new length = listed length × new height / 170). Endpoint tolerance is numerical, not an estimate of anatomical accuracy. Finite mesh resolution, selected section levels, synthetic shape and unobserved depth are limitations. No statistical confidence interval is justified. The supplied levels are controls, not verified anatomical landmarks.

Height remains a prior. Bust-point distance remains null: no semantic bust landmarks or reliable multi-view evidence. Claimed observed depth 25.3 cm is removed; physical depth remains null. `corrected-depth.png` retains the illustrative side preview with a replacement caption; it is neither an estimator output nor a Z-buffer. Generated views add no independent observed dimensions.

## Audit findings and reproducibility

The original JSON incorrectly labels dimensions as observed, sums disconnected components, invents bust-point distance and claims physical depth from an illustrative screenshot. Recalculated component totals and perimeters are retained in JSON so that torso selection is reviewable. Input report values were not used in the calculation. SHA-256 hashes of every input, mesh bounds and software versions are in `corrected-measurements.json`.

Run `python outputs/reproduce.py` from this run directory (or invoke the script by absolute path). Requires local NumPy, Matplotlib and Pillow; no external service. This writes the corrected JSON and both evidence images. Renderings and final files were inspected during this run; the script records no photographic fit or real-person accuracy claim. No blockers.

Independent package helper cross-check executed with `measure_mesh.py --mesh inputs/body.obj --sections outputs/helper-sections.json --unit cm --out outputs/helper-crosscheck.json`. VTK VTK 9.3.1 selected the central component using seed [0,Y,0]. Maximum absolute difference from the standalone triangle-intersection calculation: 1.4210854715202004e-14 cm. Agreement verifies computation, not real-person accuracy.
