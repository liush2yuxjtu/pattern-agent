---
name: clo-fit-export
description: Export four CLO3D garment fit maps per pose (试穿图、应变图、应力图、褶皱图), and report strain, fold angles and recorded stress samples.
---

# CLO fit export

Run the bundled `scripts/export_fit.py` for every export. It works on files and does not launch CLO or take desktop focus.

1. Use the garment-only CLO GLB from the target simulation. This script expects one cloth mesh, one primitive per piece, and a planar `TEXCOORD_0` carrying the original pattern coordinates. Confirm the units of the raw position and UV accessors. The defaults are millimetres. A root node scale that converts CLO's raw millimetres to metres does not change these defaults. Packed, rotated with unequal axis scales, or arbitrary texture UVs are unsuitable unless their metric mapping is known. If provenance is uncertain, verify representative 2D edges or piece areas against the CLO pattern before interpreting strain.
2. Supply `--piece-ids` in verified GLB primitive order, separated by commas. If order is unknown, omit it and report the script's stable `piece_01` identifiers. Never assign anatomy by a guessed index.
3. Capture the **CLO native Fit Map (试穿图)** and **CLO native Stress Map (应力图)** from front and back of the matching saved simulation. Confirm the active mode and inspect each capture after the overlay has rendered. The Fit Map uses CLO's categorical fit legend, including Can't Wear and Tight. Keep the pressure map and ordinary garment views separate. Use `--fit-front/back` and `--stress-front/back`; provide `--project` for the saved legends. Add `--strain-front/back` when native Strain Map captures are available. The exporter always generates a metric-GLB engineering strain map.
4. Use `--require-all-maps` for complete delivery. For an offline run with missing native screenshots, the exporter emits labeled unavailable panels and records the missing views in `fit_statistics.json`. Disclose any missing map or view when reporting. Use `--stress-samples` only for recorded CLO point measurements with columns `piece_id,location,stress_kpa`. Screenshots document location and displayed categories, while the JSON and CSV keep absent point values empty.
5. Inspect the four maps, the fit categories, and the JSON `maps` statuses. For a live source, capture the native modes in CLO and export the garment-only GLB. Keep pose, project and simulation fixed across captures. Restore the working display and respect the user's desktop focus.

Requires Python 3.10+, NumPy, and Matplotlib (see `scripts/requirements.txt`). Use an existing project environment or install into a local isolated environment as needed.

```sh
python scripts/export_fit.py garment.glb --out-dir outputs/fit-export \
  --piece-ids Front,Back,Sleeve_L,Sleeve_R,Neck_Front,Neck_Back \
  --project garment.zprj --fit-front fit_front.png --fit-back fit_back.png \
  --stress-front stress_front.png --stress-back stress_back.png --require-all-maps
```

| Map | Output |
| --- | --- |
| 试穿图 | `fit_map.png` from CLO's native Fit Map, with the project categories when available |
| 应变图 | `fit_strain.png` from metric GLB coordinates. Optional CLO native screenshots also produce `fit_strain_native.png` |
| 应力图 | `fit_stress.png` from CLO's native Stress Map, with the project display scale when available |
| 褶皱图 | `fit_fold_views.png` and `fit_fold_patterns.png` from neighboring face angles |

The exporter also writes `fit_statistics.json`, `fit_statistics.csv` and the legacy `fit_heatmaps.png` combined stress/strain view. Strain values use engineering percent (10 means 10% longer), weighted by original 2D triangle area. P50/P95/P99 are area-weighted percentiles. Stress point readings use kPa when available. The display scale does not supply point readings.

Fold angle is the unsigned angle between adjacent faces within a piece, with 0° flat. This follows the geometric quantity in [Pattern Agent's bending reference](https://github.com/liush2yuxjtu/pattern-agent/blob/main/.agents/skills/garmentcode-preview/references/simulation.md). The four-view map colors each visible face by its largest neighboring angle. The flat map shows every measurable interior edge meeting `--fold-threshold-deg` (default 15°), even when occluded in 3D. Different primitive seams, boundaries, degenerate pairs, and non-manifold edges are outside the measured set. Edge counts are not counts of physical wrinkles. Compare like meshes and threshold settings. The preview has no simulation or physical fit verdict.

Use `--help` for coordinate conversions, cropping, and overwrite options. Strain views are orthographic projections using the raw CLO axes (Y up, +Z front). Use a direct CLO export with preserved axes. By default the script excludes triangles at or below 0.1 mm² in the flat pattern, and records the count.
