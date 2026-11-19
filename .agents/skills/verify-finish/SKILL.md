---
name: verify-finish
description: Decide whether a garment passes final verification after CLO fitting. Check accessories, avatar-to-pattern sizing, seam construction, material selection and assignments, simulation stability, and the visual and numeric fit evidence required for each accepted size and pose. Report evidence, actionable changes, and criteria for retesting.
---

# Verify finish

Use as the final evidence gate for the native CLO design-to-fit workflow, or explicitly to review a completed evidence package. Honor the user's skill-use approval rule. Keep this stage read-only. Return findings to the driving skill or user for approved changes.

## Establish the evidence baseline

Record the candidate pattern and project revision, accepted size or sizes, fit goal, intended avatar and body-size source, intended fabric and actual fabric assignments, closure state, required poses, and acceptance criteria. Check that measurements, seam evidence, and captures apply to that revision. For each size and pose, verify that the fit captures and numeric exports match the same simulation state. A line-art reference has its own source and revision, matched to the simulation view and closure state. Use garment-specific thresholds from the brief, source design, or agreed baseline. When a threshold is essential and unavailable, report it as pending.

## Ask for item-level evidence on demand

Start with the evidence already available for the candidate. A gate with sufficient matching evidence needs no specialist rerun. For a missing, stale, or disputed check, return an evidence request to `design-cloth` naming the item, pose or feature, requested evidence, and owner below. When used directly, use the same ownership and approval rules. The specialist performs the check. This skill reviews its result and issues the final verdict.

| Item | Specialist to request |
| --- | --- |
| Accessories and closures | `clo-accessory-review`. Use `clo-carlton-accessory-review` as the workbench evidence source for Carlton cases. |
| Avatar-to-pattern body-size match | `clo-avatar-setup`. |
| Sewing | `clo-local:clo-seam-walk`. |
| Fabric choice and assignments | `clo-fabric-selection` for material suitability and limitations. Request the actual per-piece assignments and available property values from `clo-dxf-fit-review` for the same CLO simulation. |
| Native simulation stability | `clo-dxf-fit-review` through `clo-local:clo-fit-review`. Request only the affected poses or closure state when an existing run is reusable. |
| Fit images, line-art comparison, and values | `clo-dxf-fit-review` for native captures and measured stress and pressure, `clo-local:clo-fit-export` for matching fit visuals and supported strain or fold exports, and `clo-line-art-review` for appearance versus design. Use CLO_RUST when requested or needed to independently review supported saved evidence. Reuse the matching saved simulation where possible. |

Pass the candidate revision and relevant acceptance criteria with every request. Collect two items from a single native run when possible. Do not repeat the drafting or fitting workflow solely because one independent check is missing.

## Check the gates

| Gate | Evidence needed to pass |
| --- | --- |
| Accessories | Verify applicable pockets, flaps, collars, fasteners, and other specified parts against the design. Inspect position, attachment, and alignment. Exercise any required opening or fastening function. A hardware marker can substantiate position and tracking. Evaluate an actual opening or fastening using evidence of that function. |
| Body-size match | Compare the loaded avatar's actual dimensions with the body measurements used for the checked FreeSewing draft or the source DXF size chart. Check definitions and units, record target, actual, and difference, and apply the agreed limits to fit-relevant dimensions. Calculate ease separately from finished pattern dimensions. An exploratory fit with missing target measurements cannot establish a size-match pass for the intended wearer. |
| Seams | Use revision-matched seam evidence to check paired edges, direction, coverage, alignment, and length allowance for intended ease or gathers. Check the actual sewing and closure state used in the fit project. |
| Fabric | Compare the actual materials and directions used in the simulation with the selected material specification and garment intent. Verify the relevant shell, lining, interfacing, or trim assignments and the provenance of fit-relevant properties. A documented proxy can pass only within an agreed virtual or exploratory scope. Missing target-material calibration remains pending when acceptance requires the real fabric. |
| Stable simulation | Verify that the garment settles in the intended worn and closure state in all required poses. Inspect relevant views for consequential penetration, seam separation, unintended twisting or pulling, and fit or mobility defects. Use the pose and solver evidence together. |
| Fit visualizations and data | Review the five evidence groups defined below for each required size and pose. Validate actual content, units, coverage, and provenance. Missing required artifacts remain pending. |

A Carlton browser run can substantiate its tested accessory behavior. Use native CLO evidence for native fit and pressure, and direct evidence for physical closure or wear claims.

## Require matching visual and numeric fit evidence

| Evidence group | Visual output | Numeric export or comparison |
| --- | --- | --- |
| Fabric stress | Native CLO Stress Map. | Native stress samples or export with units, sample locations or coverage, and pose. |
| Fabric strain | Native or verified calculated strain visualization. | Native values or strain calculated from the verified garment mesh and matching original pattern geometry. Record units and method. |
| Appearance versus line art | Native worn view beside the source design drawing, with comparable viewpoint and closure state. | Record the visual differences in silhouette, length, and feature placement. If the required design reference is unavailable, retain the worn view and mark the comparison pending. |
| Body contact pressure | Native CLO Pressure Map. | Native pressure samples or export with units, locations or coverage, and pose. |
| Fold angles | Fold-angle or wrinkle visualization. | Same-mesh fold-angle data in degrees with region or piece identifiers and the calculation convention. |

Inspect original artifacts and record paths. Quantities for native stress or contact pressure require recorded measurements or native exports. CLO_RUST can review those recorded samples and compute supported strain or fold-angle geometry from saved data. Use those results only for the revisions and poses they support. A single size's fit does not provide evidence for the other sizes in a DXF batch.

## Report the material every time

Include a material record with the intended fabric and the reason it was selected, the actual CLO fabric or preset assigned by piece or layer, grain direction where relevant, and the parameter provenance. Distinguish measured swatches, supplier specifications, CLO presets, and estimates. Include relevant available values and units for properties such as weight, thickness, directional stretch, bending, or shear and mark missing values. State whether the material evidence supports the requested fit scope and identify any result that depends on a proxy.

## Decide and hand off

- **PASS** only when all applicable gates have passing evidence for every required pose. Mark an individual check **N/A** only when the garment and agreed scope make it inapplicable, and give the reason. An accessory-only verification is limited to its accessory scope.
- **FAIL** when reliable evidence shows a required criterion is unmet. Record any additional pending checks alongside the failure.
- **PENDING** when no failure is established but evidence, a required pose, a size target, or an essential criterion is missing or cannot be tied to the candidate revision.

Report one overall result and a short table with each gate, status, and evidence. For each failure, state the affected piece or body area and pose, link the relevant image or measured value, propose a specific change, name the owning specialist, and specify the retest pose and pass criterion. For each pending item, name the missing evidence and which specialist can collect it. Return the candidate for re-verification after approved changes, with affected evidence refreshed and unchanged evidence reused only where it still applies.
