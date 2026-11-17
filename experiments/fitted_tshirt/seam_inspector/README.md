# Accepted sewing inspector reference

This is a frozen verification reference for the corrected static single-sheet
outer shell. It contains the actual accepted cloud GLB, portable interactive HTML
and independent report, with original byte digests in `manifest.json`. It has no
Site identity configuration, credentials or user session. Original input is the
already committed `services/dxf-preview/public/sample.dxf`.

From repository root:

```sh
python scripts/verify_seam_inspector.py --html experiments/fitted_tshirt/seam_inspector/inspector.html --glb experiments/fitted_tshirt/seam_inspector/accepted-model.glb --dxf services/dxf-preview/public/sample.dxf --units mm --output work/seam-inspector
```

The verifier independently reopens the source/GLB, binds every displayed position,
triangle, seam, original/derived flat curve and report value, then drives the real
browser interactions. It does not trust stored PASS strings. See the repository
verify skill's `dxf-seams`, `seam-inspector`, `seam-sites` and `seam-pages` recipes.

This fixture is not a production cutting pattern or calibrated cloth simulation.
The unmodified original pattern still has the documented FAIL under the sewing
contract; derived lines move points by at most 4.41mm. Hidden inner neck layer,
allowance stacks, material mechanics and actual fit remain unverified.
