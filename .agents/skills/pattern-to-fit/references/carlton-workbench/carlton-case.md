# Carlton reference case

The verified reference is Pattern Agent commit `26a1dccb00ea092e1e2aed8c154b9f0fcc20e632`. Scope numeric values below to this example. The live workbench and report are published under <https://liush2yuxjtu.github.io/pattern-agent/carlton-workbench/>.

## Locate the implementation

- In `web/carlton-workbench/source/carlton-physics`, `pattern.mjs` reads FreeSewing front landmarks. `assembly.mjs` warps the reference panels and retargets pockets and hardware. `mounts.mjs` locates points on triangles. `physics.mjs` registers seams and checks residuals. `trim-view.mjs` follows the simulated front surfaces. `mesh.json` contains the reference tessellation and prepared constraints.
- Check that the raw CLO GLB and seam records belong to the intended project before regenerating the packed mesh.
- The original reference supplied six button meshes and six slit primitives. The return edge was folded back onto its own patch-pocket panel, while the bag opening remained free. Collar tessellation and the collar-to-stand, collar-to-front, and stand-to-neck sampling were repaired using the existing CLO pairings.

## Browser replay

Run the repository's packaged verifier against a built local server first when changing the workbench. For the deployed revision, supply the exact expected commit. Install Playwright and Chromium, or set `PLAYWRIGHT_PACKAGE` to a resolvable Playwright package and `CHROMIUM_EXECUTABLE` to a local browser. Set `CARLTON_BROWSER_EVIDENCE` to capture screenshots.

```sh
node web/carlton-workbench/verify.mjs \
  https://liush2yuxjtu.github.io/pattern-agent/carlton-workbench/ \
  "$(git rev-parse HEAD)"
```

The six-run live check covers M, chest, length, reset, vertical pocket placement, and horizontal button spacing. It checks 480 completed GPU steps for each, actual 2D outlines, fresh 3D targets, accessory counts, diagnostic images, and downloaded file bytes. The pocket edit is 6% → 9%. The horizontal button spacing edit is 43.5% → 49.5%. A separate local check raised collar height from 9.6% to 10.6% and compared the collar-stand SVG, assembled rest geometry, and settled result.

## Reopen published evidence

Use the report's `evidence.tgz` and the matching source. Run the following from `web/carlton-workbench/source`. Use the native CLO_RUST `pattern-native` binary matching the evidence producer to compare native files byte for byte. For a different binary version, compare semantic output and document the version.

```sh
review_dir=$(mktemp -d)
tar -xzf ../evidence.tgz -C "$review_dir"
cp verification/coupon.json "$review_dir/"
for pose in "$review_dir"/browser/pose-*.glb; do
  stem=$(basename "$pose" .glb)
  pattern-native mesh-metrics "$pose" "$review_dir/replayed-$stem.vtk" \
    > "$review_dir/replayed-$stem.json"
  cmp "$review_dir/replayed-$stem.vtk" "$review_dir/$stem.vtk"
  cmp "$review_dir/replayed-$stem.json" "$review_dir/$stem.json"
done
pattern-native connectivity "$review_dir/browser/assembly-connectivity.json" --strict \
  > "$review_dir/connectivity.json"
MPLBACKEND=Agg python verification/field_review.py "$review_dir" "$review_dir" \
  'Independent replay' --summary-only
```

The six native evidence cases cover M, chest, length, upper-arm circumference, vertical pocket placement, and horizontal button spacing. Each uses the captured 480-step state with 18 outer panels and 6,210 triangles. The field checker validates strain against native data, independently recomputes stress and pressure, and tests the attachment residuals and front-panel bindings.

The browser and native checks used limits of 0.65 mm for sampled pocket seams, 0.8 mm for return-edge constraints, and 4 mm for sampled collar pairings. The published native maxima were 0.35 mm, 0.24 mm, and 3.43 mm respectively. These limits are acceptance gates for this simulation fixture. The six buttonholes are visible surface marks. Physical openings, button contact and closure forces, and real garment fit remain outside this case's evidence.
