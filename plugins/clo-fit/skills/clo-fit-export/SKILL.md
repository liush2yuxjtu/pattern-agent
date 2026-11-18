---
name: clo-fit-export
description: Export CLO3D stress/strain (应力应变) statistics and heatmaps, and preview wrinkles by neighboring triangle fold angles (折角、褶皱). Use for repeatable garment fit reports from a saved CLO GLB and optional stress evidence.
---

# CLO fit export

Run the bundled `scripts/export_fit.py` for every export. It works on files and does not launch CLO or take desktop focus.

1. Use the garment-only CLO GLB from the target simulation. This script expects one cloth mesh, one primitive per piece, and a planar `TEXCOORD_0` carrying the original pattern coordinates. Confirm the units of the raw position and UV accessors. The defaults are millimetres. A root node scale that converts CLO's raw millimetres to metres does not change these defaults. Packed, rotated with unequal axis scales, or arbitrary texture UVs are unsuitable unless their metric mapping is known. If provenance is uncertain, verify representative 2D edges or piece areas against the CLO pattern before interpreting strain.
2. Supply `--piece-ids` in verified GLB primitive order, separated by commas. If order is unknown, omit it and report the script's stable `piece_01` identifiers. Never assign anatomy by a guessed index.
3. Optionally pass the saved front/back stress screenshots and `.zprj` from the same simulation. The project provides the original stress color scale. Screenshots provide visual evidence only. Supply `--stress-samples` only for recorded numeric CLO measurements, with columns `piece_id,location,stress_kpa`. These are sample statistics, without area weighting or claims about unsampled areas. Leave unavailable measurements missing.
4. Run once and use the resulting JSON for agent consumption, CSV for a sortable table, and PNGs for the report. Check the images and JSON source/availability fields before reporting. When only a live scene is available and the user permits CLO access, use the CLO3D MCP `scene_export` for a garment-only GLB and the native stress map plus `snapshot` for visuals. Respect any request to keep the desktop undisturbed.

Requires Python 3.10+, NumPy, and Matplotlib (see `scripts/requirements.txt`). Use an existing project environment or install into a local isolated environment as needed.

```sh
python scripts/export_fit.py garment.glb --out-dir outputs/fit-export \
  --piece-ids Front,Back,Sleeve_L,Sleeve_R,Neck_Front,Neck_Back \
  --project garment.zprj --stress-front stress_front.png --stress-back stress_back.png
```

Outputs: `fit_statistics.json`, `fit_statistics.csv`, `fit_heatmaps.png`, `fit_fold_views.png` and `fit_fold_patterns.png`. Strain values are engineering strain in percent (10 means 10% longer), weighted by original 2D triangle area. P50/P95/P99 are area-weighted percentiles. The default 10% area threshold is for comparison and is configurable. Stress values, when present, are in kPa. A CLO color scale is a display range. Do not use colors to infer numeric stress or interpret this static spatial report as a material stress–strain curve.

Fold angle is the unsigned angle between adjacent faces within a piece, with 0° flat. This follows the geometric quantity in [Pattern Agent's bending reference](https://github.com/liush2yuxjtu/pattern-agent/blob/main/.agents/skills/garmentcode-preview/references/simulation.md). The four-view map colors each visible face by its largest neighboring angle. The flat map shows every measurable interior edge meeting `--fold-threshold-deg` (default 15°), even when occluded in 3D. Different primitive seams, boundaries, degenerate pairs, and non-manifold edges are outside the measured set. Edge counts are not counts of physical wrinkles. Compare like meshes and threshold settings. The preview has no simulation or physical fit verdict.

Use `--help` for coordinate conversions, cropping, and overwrite options. Strain views are orthographic projections using the raw CLO axes (Y up, +Z front). Use a direct CLO export with preserved axes. By default the script excludes triangles at or below 0.1 mm² in the flat pattern, and records the count.
