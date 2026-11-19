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
