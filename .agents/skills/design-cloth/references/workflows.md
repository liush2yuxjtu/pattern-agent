# Design cloth workflow

## 1. Establish the brief and current state

Identify the intended garment, design references, target body sizes, material constraints, required poses, and acceptance criteria. Inventory existing draft inputs, DXFs, CLO projects, and evidence. Resume at the first incomplete step and keep good evidence from the same revision. A limited request uses the relevant step and ends with that result.

If an intent-only brief needs a starting pattern, look for compatible designs, blocks, or parts in the [FreeSewing catalog](https://freesewing.eu/designs/). Check the draft's construction and fabric requirements against the design. For a reference-only request, return a recommended base and relevant alternatives.

## 2. Set the material and body inputs

- Carry forward the material specified by the user or design. Call `clo-fabric-selection` if material is open, a substitute is needed, or its suitability is unclear. Give it the intent, reference, draft, and any available swatch or supplier data. If stretch, drape, or support affects the draft, settle a provisional material before drafting and confirm it against the checked pattern.
- Use target body measurements for a wearer-specific draft. For an avatar-first prototype without target dimensions, call `clo-avatar-setup` to select a CLO stock or designated avatar and measure the dimensions required by the draft. Carry that measurement set into drafting and reuse the same avatar for fitting. Record estimates and proxy limitations.

## 3. Prepare the pattern and size run

Use the source that fits the request. The resulting candidate feeds the same CLO and verification steps.

| Paper pattern input or deliverable | What to do when needed |
| --- | --- |
| Modify a prototype DXF | Use the authorized native CLO pattern editor or existing project editor on a working copy. Check the exported or re-imported units, pieces, sewing outlines, allowances, notches, grain, and mating edges as applicable. |
| Adjust an existing FreeSewing JS design | Call `freesewing-new-design`. Record the base version and original and revised options or body measurements. Draft and check the resulting pattern. |
| Create a new FreeSewing JS design | Call `freesewing-new-design` with the brief and any chosen reference or block. Keep runnable source, exact input settings, and parametric checks. |
| Receive or generate a size run, such as S, M, L, XL | Map incoming files to their documented sizes and body measurements. For generation, use each size's measurement set or authorized grading rules. Keep a distinct DXF and revision record for each size. Record which sizes had pattern checks and actual avatar fitting. |

An existing checked DXF or CLO project can enter the next step directly. Keep the source revision and a separate candidate for edits.

## 4. Assemble, simulate, or review saved evidence

Use the [runtime support matrix](runtime-support.md) to choose the approved environment for this step. New native simulation and native maps use a verified CLO bridge. Rust and Boat can independently review compatible saved evidence. The independent Boat solver applies to verified DXF configurations. The inputs and checks below follow the chosen scope.

- Check the loaded avatar against the exact drafting body data or DXF size chart. Call `clo-avatar-setup` when the comparison is missing, stale, or requires adjustment. If the body target is unknown, record that limitation in the fit scope.
- Check the sewing state, including edge coverage, direction, intended ease, and closure. Call `clo-local:clo-seam-walk` when sewing or its evidence needs work. Verify the actual main, lining, and interfacing assignments and grain direction in the candidate. Record the material choice, properties and source, and the actual fabrics used. Label a CLO preset used as a proxy.
- Use `clo-local:clo-fit-review` to select the fitting workflow when that dispatcher is installed. Otherwise choose the direct specialist from the runtime matrix. Call `clo-dxf-fit-review` for native CLO simulation or collection from the matching saved simulation. Retain the settled project and evidence for each required size and pose. Collect what the final scope needs, including the material record and these five evidence groups:

| Evidence | Output |
| --- | --- |
| Fabric stress | Native stress visualization and recorded values or numeric export. |
| Fabric strain | Strain visualization and native or verified calculated data from the corresponding mesh. |
| Appearance | Worn view compared with the design line art from a comparable camera and closure state. Call `clo-line-art-review` as needed. |
| Body contact pressure | Native pressure visualization and recorded values or numeric export. |
| Fold angles | Fold-angle or wrinkle visualization and corresponding angle data. |

Reuse valid captures. `clo-fit-export` or CLO_RUST can help collect or verify supported evidence when needed. Use native recorded samples or exports for numeric stress and pressure. Pass evidence with the corresponding size, pose, project revision, avatar, and actual fabric.

## 5. Diagnose and repair only the affected item

When a fit issue has an unknown cause, isolate suspected variables in this order. Route directly to the responsible specialist if the evidence already identifies the cause.

1. **Simulation.** `clo-dxf-fit-review` checks scene, pose, arrangement, collision, closure state, and settling.
2. **Material.** `clo-fabric-selection` assesses suitability. `clo-dxf-fit-review` checks actual assignments or runs a matched fabric-only comparison.
3. **Avatar.** `clo-avatar-setup` compares the loaded body's actual dimensions with the draft target.
4. **Sewing.** `clo-local:clo-seam-walk` checks and, when approved, repairs affected seams.
5. **Accessories.** `clo-accessory-review` checks the affected part or fastening. For the Carlton browser workbench, use `clo-carlton-accessory-review` for its specialized repair and review. Keep browser and native CLO evidence tied to their respective runs.
6. **Pattern.** If the evidence points to geometry after plausible setup and construction causes are checked, return to step 3 with the affected piece, dimension, and proposed change. Directly requested pattern design changes can enter step 3.

Obtain approval for fit-derived changes. After a fix, repeat the affected checks and compare the same size, avatar, material, poses, and settings, except for the approved change. A body or material change can also reopen drafting or sewing if it affects ease or construction.

## 6. Close or continue

For full acceptance, submit the candidate and available evidence to `verify-finish`. It reports PASS, FAIL, or PENDING, includes the actual material record, and names any checks that need more evidence. After a FAIL, route approved repairs through step 5. For PENDING, call the relevant specialist for the missing evidence when available. Feed the updated package back through the same gate. Keep results scoped to the sizes and poses actually verified.
