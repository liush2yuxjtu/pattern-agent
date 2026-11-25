# Carlton accessory review

Use the actual FreeSewing draft, the source CLO sewing assignments, and the solved browser mesh. Establish the reference revision and reproduce the reported defect. Follow the repository's `/verify` workflow when a repository is involved. Use headless Playwright to avoid changing desktop focus.

## Repair

- **Patch pockets and flaps.** Trace the actual internal sewing lines on each front. Attach each sampled side or bottom stitch and each flap hinge sample to a triangle on the corresponding front, using barycentric weights. Retarget the samples in the front panel's flat coordinates using the current draft's location and dimensions. Rebuild the stitches at each solver reset and warm-start the separately placed panels. Measure the distance lost when a target projects back onto the front. Preserve the free pocket mouth. Keep the return edge on the inside of the pocket with same-piece fold constraints derived from the paper fold line.
- **Collar and stand.** Look up the verified front-neck, back-neck, collar and stand pairings in the CLO seam graph. Retain enough boundary vertices on the collar and stand to sample the edges. Pair a boundary vertex with a point on a boundary segment of its assigned counterpart. At multi-layer junctions, use reference landmarks and proximity to remove spurious cross-links. Check every named pairing separately.
- **Buttons and buttonholes.** Inventory reference hardware and slit marks and map them to their actual front panels. Transfer the deltas of the FreeSewing button points into the flat panel, accounting for mirrored orientation. Retarget onto the relevant front triangles and use their solved positions and normals to place the visible accessories. Record whether each element is a surface marker, physical opening, or functional closure.

## Verify and iterate

1. Exercise the exact affected 2D controls and the same 3D simulation in a real browser. Capture a baseline, change one relevant control at a time, and compare actual SVG paths or marker coordinates to the fresh attachment targets and solved mesh. Verify the requested step count completes through WebGPU dispatches, values stay finite, and readouts belong to the latest revision. Check front views from a comparable camera and confirm reset, export, and diagnostics when affected.
2. Reopen the final mesh with CLO_RUST. Independently compute sampled distances in millimetres for each pocket sewing run, each pocket return, and every collar pairing by interpolating each edge or triangle target and measuring the distance to the sewn vertex. Validate host panels and hardware counts. When stress, strain, or pressure is in scope, replay the repository's independent field checks on captures from the same run.
3. Iterate on the failing part and rerun the baseline and edit cases. Report the measured residuals and any unresolved visual issues. State which closure behavior, materials, and physical fitting were actually tested. For an authorized release, check the deployed revision and rerun the affected browser flow at its live URL.

Read [the Carlton case and commands](carlton-workbench/carlton-case.md) for the tested fixture, implementation entry points, and reproducible commands.
