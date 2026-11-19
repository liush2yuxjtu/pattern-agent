# Run a review batch

## Local preflight

Confirm a working Boat client and access to the private `clo-rust` snapshot.
Use the three-pose mesh workflow only after verifying that the source garment
has metric flat UVs, raw positions in millimetres, Y up, and +Z forward.
The helper consumes a garment-only CLO GLB with a single `Cloth_mesh` and one
primitive per named piece. Pass the poses in the intended report order.

```sh
python3 scripts/prepare_meshes.py <scratch-input> \
  --mesh-source "<project and original pose source>" \
  --pose "垂臂" <relaxed-cloth.glb> \
  --pose "斜展" <a-pose-cloth.glb> \
  --pose "平举" <horizontal-cloth.glb>
```

Inputs with different flat UVs or triangle indices are rejected. Transfer the
resulting pose GLBs and `manifest.json`. Include `line-art.png` or the declared
four `seams/` JSON files only when the requested review uses them. The raw input
GLBs, ZPRJ files, avatars and textures stay local. Keep tokens, host settings,
and private snapshot IDs out of the package and report.

## Boat execution

Use an authorized existing sandbox, or start an isolated personal sandbox with
`boat new --personal --no-env --from clo-rust` when authorized. Check
`boat exec --help` and `boat scp --help` for the installed client. Send only
the allowlisted staged input and this skill's scripts; use new input and output
directories. In the sandbox, run the snapshot's `verify-boat.sh` first and check
its exit status. Confirm that `target/release/pattern-native` in the selected
CLO_RUST directory supports `mesh-metrics`; seam review additionally uses
`clo-import`, `constraints`, and `connectivity`.

Install `scripts/requirements.txt` in a sandbox Python environment if needed.
For the optional `--carlton` drafting example, provide the three files in
`vendor/` to the CLO_RUST project's vendor directory and use
`npm ci --prefix <CLO_RUST>/vendor --ignore-scripts`. The adapter pins FreeSewing
4.10.2. Run one batch and collect the result:

```sh
python scripts/run_review.py <CLO_RUST> <staged-input> <result-dir>
```

## Result checks

Confirm that three pose inputs yield three JSON and VTK pairs and that the
garment and pose counts match the manifest. The offline HTML displays the
supplied line art when present and uses fixed ranges for strain and fold
angles. Verify file links or decoded images and the two viewport widths before
handoff. Reopen earlier results separately if doing a regression comparison.
Stop only a sandbox created for the run, after collecting its outputs.

Results describe the geometry of the input poses. Keep native CLO fit
categories, stress, pressure and dynamic drape tied to their respective source.
