# CLO fit export verification

Run these from the repository root with the CLO fit export requirements installed:

```sh
python -B -m unittest discover -s .agents/skills/clo-fit-export/scripts -p 'test_fold_preview.py' -v
python -B .agents/skills/clo-fit-export/scripts/export_fit.py /path/to/garment.glb \
  --out-dir /path/to/new-output --project /path/to/garment.zprj \
  --stress-front /path/to/front.png --stress-back /path/to/back.png
```

Use a garment-only CLO GLB with metric pattern UVs. Add confirmed primitive IDs and crop arguments as needed. Independently reopen JSON and CSV, check agreement of counts and units, compare the strain fields against any established reference, and visually inspect the stress/strain map and both fold maps. With no stress samples, numeric stress fields must remain missing. At the CLI, probe a bad input such as a wrong piece-ID count, and check that it is rejected before any outputs are written.

The gate covers the offline exporter. It does not grade simulation, the material, or physical fit.
[2026-11-18 receipt](../../../../docs/verification/clo-fit-export-20261118/README.md).

## CLO Fit Review plugin

For changes under `plugins/clo-fit`, register the repository as a local marketplace in an isolated Codex profile and run `codex plugin add clo-fit@pattern-agent --json`. Run the exporter checks above from the installed cache. Run its sibling `compare_poses.py` with a multi-pose manifest and compare the resulting CSV with the source report. For the bundled example, check the DXF digest and open every relative image in the Page snapshot. [Plugin verification receipt](../../../../docs/verification/clo-fit-plugin-20261118.md).

For line-art workflow changes, use the installed skill and its report guide on a saved case with an original design illustration and a traceable ordinary-material screenshot. Inspect the paired view and original image links. Record the project version, pose, display mode and whether closure was confirmed. Keep the four fit maps and the original report usable if the illustration is unavailable. Verify the enabled, namespaced plugin skills and their installed paths through Codex app-server `skills/list`. Run a wrong-mesh control with a known altered pose manifest and confirm that the installed comparison rejects it before writing a CSV. [Carlton line-art verification](../../../../docs/verification/clo-fit-line-art-20261119.md).

For standalone HTML, run the installed `inline_report_images.py` on a real report draft. Copy the result to an otherwise empty directory and open it offline in Chromium at desktop and mobile sizes. Check that the paired line drawing and material photo are side by side, every inline figure decodes with a visible box, the SVG paper patterns render, and the report makes no external requests. Probe an absent or external image and confirm the helper exits before writing. [Carlton HTML verification](../../../../docs/verification/clo-fit-html-20261119.md).

For `clo-seam-walk`, run the installed reference script with the packaged
example catalog and plan. Confirm exactly two groups are planned and coverage
is complete. Run the same CLI on a plan with matching lengths that omits a
required hem span and require a nonzero exit with the measured gap. From a
safely backed-up CLO session, run `run_clo` in one bridge call on a test project.
Confirm group increments and membership on both pieces, save and reopen the
test project, and verify that replay is blocked by the expected starting count.
Restore the saved working checkpoint. Record the package version, real
readback and separate visual verification scope.
[Batch seam verification](../../../../docs/verification/clo-seam-walk-20261119.md).

## CLO Local and CLO Rust Boat

Register this checkout in an isolated Codex profile, install
`clo-local@pattern-agent` and `clo-rust-boat@pattern-agent`, and confirm the
enabled namespaced skills via app-server `skills/list`. Check the portable
archives against the installed files and verify the root manifest in each.

For CLO Local, run the installed exporter on saved CLO inputs with
`--require-all-maps` and front/back pairs for fit and stress. Include the two
native strain images if available. Compare the JSON map status and CSV piece
counts, and apply the seam and pose controls above. Report native bridge
availability separately from replay with saved inputs.

For CLO Rust Boat, follow the installed skill's
[runbook](../../../../plugins/clo-rust-boat/skills/clo-rust-boat-fit-review/references/boat-run.md).
Use the installed preparation and review scripts on a flat baseline and bent
poses. Compare JSON with VTK and CSV, read the offline page in a browser, and
confirm that altered UVs or a mismatched digest cause rejection. A native
local build can check the analysis and report path when the authorized Boat
sandbox is unavailable. Record the actual runtime and scope.
[Two-plugin verification](../../../../docs/verification/clo-plugin-pair-20261119.md).

## Boat batch entry points

Run the installed `run_boat.py` on an authorized running sandbox with
`seam-walk`, `review` and `fit-export`. Check the returned architecture
and executable digest. Compare the reopened seam audit, constraints and
strict connectivity against the input. For a full fit-export batch, match
the four map categories for every pose and verify the native PNGs against
their sources byte-for-byte. Probe a missing native capture with the
strict and permissive modes. Keep active Boat verification separate from
local Linux checks of bundled binaries.
[Boat runtime and mirrored entry points](../../../../docs/verification/clo-rust-boat-mirror-20261119.md).
