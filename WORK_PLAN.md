# Pattern Agent validation run

## Task

Continue the prior Garment Lab prototype using the user's reference knit T-shirt. Finished garment flat measurements are 540 mm chest width, 650 mm shoulder-neck-to-hem length, 500 mm outer-shoulder span, and 250 mm shoulder-to-cuff sleeve length. These were user-reported, not independently measured. Photos, body dimensions, and fabric test results are unavailable. No human fit claim is allowed.

## Task list

- [x] Read the Principles section of poteto-mode.
- [x] Phase A: Frame.
- [x] Phase B: Design the workflow.
- [x] Phase C: Run the loop.
- [x] Phase D: Keep the audit trail.
- [x] Phase E: Verify and hand back.

## Falsifiable completion predicate

A reproducible, free Linux workflow reads one provenance-bearing specification, derives closed planar T-shirt panels in millimeters, verifies seam-pair lengths and structural openings, executes Blender's actual Cloth modifier on a mesh derived from those panels, saves the .blend and numerical frame evidence, exports full-scale and A4 1:1 PDFs with measurable calibration and complete tile coverage, and reports physical fitting and photo-match as NOT_RUN. Research must ground needs and substitutes in public evidence and must not label browsing as interviews. All user-facing outputs will be saved durably and linked in the existing project Page.

## Risk and execution order

The unknown to resolve first is whether an auditable panel-to-simulation link can be implemented with the installed Blender 4.3.2. Simulation may use a synthetic mannequin with explicitly uncalibrated fabric. Record it as a structural and runtime check only. Four real measurements are insufficient to uniquely reconstruct a garment, so armhole, neckline, sleeve shape and material assumptions remain visible. No extra Boat run is needed for this artifact-level validation because its infrastructure was already verified and this Linux host contains Blender.

## Parallel boundaries

Parent owns integration, PDF output, independent checks, deliverable packaging and Page update. Geometry worker owns garment model and seam checks. Blender worker owns simulation and its runtime evidence. Research worker owns public needs and competitors. Each worker writes separate files and temporary directories. Parent checks final artifacts independently.

## Architecture rubric

Choose between independent generated geometry per output and a shared canonical millimeter panel document. Grade traceability to inputs, sewing-seam correctness, reproducible simulation, physical print fidelity and scope honesty. Prefer one canonical panel document to prevent separate printable and simulated garments.


## Final decision

P1_NO_GO. The complete software workflow was executed and independently reproduced. Canonical scale, printable vector scale, oriented logical seam topology, source linkage and portable saved simulation cache pass. Actual Cloth seam closure and self-intersection gates fail (7.6455 mm maximum gap; 20 intersecting nonadjacent face pairs). Physical print, sample sewing, fit, material calibration, photograph matching and live user-task success remain NOT_RUN. The deliverable preserves the negative result and the full reproduction path.