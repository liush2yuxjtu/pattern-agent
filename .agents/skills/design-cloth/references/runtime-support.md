# CLO runtime support matrix

Choose the execution location and the tool interface separately. MCP is an interface. An MCP call runs where its server is configured. Record the engine, host, tool or skill, and evidence source for every fitted size and pose.

| Runtime and interface | Pattern, seams, and avatar | New cloth simulation | Fit evidence |
| --- | --- | --- | --- |
| **Local native CLO 3D via CLO MCP** | Import DXF, build or edit the working CLO project, use native sewing, and load or measure the avatar. Route through `clo-local:clo-fit-review`, `clo-dxf-fit-review`, `clo-local:clo-seam-walk`, and `clo-avatar-setup` as needed. | Run native CLO on the approved avatar, fabric, and poses when the live bridge supports the required operations. Save the corresponding project. | Source for native appearance and fit, stress, and body-contact pressure. Collect actual numeric samples or exports where available, and export meshes for supported strain and fold calculations. |
| **CLO_RUST via MCP** | Audit normalized patterns and seam records or mappings. Measure a supported exported body mesh and, when requested, resize supported geometry and independently remeasure it. | Review or replay saved cloth results. Use a separate verified solver route for new poses. | Recompute supported strain and fold angles from matching garment meshes. Preserve or check recorded native stress and pressure maps and numeric samples. Reuse matching native imagery for appearance or line-art comparison. |
| **CLO_RUST CLI on a local machine** | Run the corresponding supported pattern, seam, or mesh audit with a compatible `pattern-native` binary and prepared inputs. | Use this route for offline computation and saved-result checks. | Outputs depend on the command and input. Record binary version and retain the matching meshes, maps, and receipts. |
| **CLO_RUST batch on Boat Linux VM** | Use `clo-boat-fit-review`, or the repository's `clo-rust-boat-fit-review` when the dispatcher is unavailable, for prepared seam, review, and fit-export batches with the supported Linux binary. | Batch saved-pose review. A separate Boat solver path is listed below. | Recompute strain and fold data and assemble same-revision native evidence supplied with the batch. Run the installed Boat review's pose and five-map checks when a complete Boat review is requested, then use `verify-finish` for the agreed garment acceptance. |
| **Independent DXF fit on Boat Linux VM** | Use the installed `clo-rust-boat-fit-review` independent DXF recipe only when the garment, seam/placement mapping, avatar collision setup, and poses match a verified configuration. The documented starting case is a fitted long-sleeve sample with upright and whole-body lean poses. | New simulation via the headless Pattern Agent WASM solver for supported cases. Current evidence covers the documented configuration. Other garments, arm motions, or avatars need their own verified setup. | Report geometric checks, strain and fold angles, and any reference stress or contact results with their provenance. Obtain native CLO maps or calibrated numeric values separately when the acceptance scope requires them. |

The documented Boat Linux routes run Rust or the independent WASM solver. A remote native CLO session is a different setup. Treat it as a native route only after confirming an authorized, working CLO installation and live bridge on that host.

## Select the route for this stage

1. Honor the user's requested environment. For a new native CLO project, new native poses, material changes, or new native fit, stress, or pressure evidence, start with the checked native bridge. Verify `clo_status` and a read-only scene query. A registered MCP server by itself does not confirm a working live scene.
2. For saved geometry, use the available Rust MCP or compatible CLI. Use Boat when requested, the files already reside there, or the authorized batch requires Linux. Check the prepared inputs and runtime version. Start or transfer work to a VM only within the user's authorization.
3. For a native run plus an independent check, collect the native artifacts first and pass the exact matching manifests, seam records, meshes, maps, and numeric samples to Rust or Boat. Confirm matching revision, size, pose, avatar, body dimensions, material, closure state, and units. Check garment mesh coordinates and pattern UVs before recomputing strain or fold angles. A batch tool's name alone does not identify the host.
4. If the chosen route cannot supply a required operation or evidence item, complete supported checks and mark the missing item PENDING for `verify-finish`. Name the required input or runtime. Change environments or add a solver run only as authorized.

For Rust avatar measurement, identify the exact Y-up mesh and closed torso sections used for circumference. An independently measured or resized mesh establishes the reported geometric dimensions of that file. A fitting run also needs a compatible collision body and pose setup.

## Reproduction references

- [CLO Local plugin](../../../../plugins/clo-local/README.md)
- [Boat batch and runtime verification](../../../../docs/verification/clo-rust-boat-mirror-20261119.md)
- [Long-sleeve avatar sizing and Boat case](../../../../docs/cases/long-sleeve-avatar-sizing/README.md)
- [Carlton native fitting case](../../../../docs/cases/carlton-joost/README.md)
