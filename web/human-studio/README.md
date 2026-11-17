# Human Studio

An anatomical MakeHuman adult-female model with centimetre shape controls and
an articulated 163-bone rig. This replaces the primitive loft as the interactive
model; historical evaluation fixtures remain unchanged.

## Controls

- Standing height; bust, waist, hip, neck, upper-arm, thigh and calf circumferences;
  shoulder breadth; upper-arm, forearm and thigh lengths —12 dimensions in cm.
- Local joint rotations in 0.1-degree increments. Primary body joints have friendly
  names; the full menu also includes fingers, jaw, eyes and the rest of the rig.
- Neutral, T-pose, walking, seated and arms-up presets. Mirror left/right editing,
  clickable joint markers, orbit/zoom and front/side/back views.
- Save/import JSON, actual 2×renderer PNG, posed OBJ in cm and rigged GLB in metres.

## Measurement and geometry contract

The CC0 source supplies detailed surface topology, anatomical joint landmarks,
authored morph targets and skin weights. Rendering uses 13,380 body vertices and
26,756 triangles; 19,158 source vertices include non-rendered rig landmarks.

`body-engine.js` calibrates bounded morph coefficients against actual vertex
tape paths and named landmark distances. Height uses authored height morphs,
not uniform scaling. Shoulder breadth is bilateral acromion distance, rather
than the upstream one-sided neck-to-shoulder ruler. Circumference paths are
explicitly closed. Other length definitions follow the referenced mesh
landmarks and are not interchangeable with inseam, sewing back-length or a
different anthropometric protocol.

The solver reports the largest residual. Inputs outside the joint morph
envelope show the closest supported shape and actual measured values instead
of claiming an exact match. Neutral-pose measurements remain separate from
posed bounding-box height and local joint angles. The shape and pose are
applied to real vertices and bones; renderer pixels are not generated images.

Skeletal skinning uses the four strongest normalized authored weights per
vertex. Bones and inverse bind matrices are rebuilt from the morphed joint
landmarks, then the selected pose is applied. Grounding uses the posed surface.
State includes model version and asset fingerprint; saved morph coefficients
preserve exact calibrated geometry across save/reload and JSON import.

GLB retains the current shape, pose and rig, with a 0.01 root conversion to metres
and dimension metadata in cm. Centimetre recalibration remains available in this
editor; the GLB is not a standalone Blender centimetre-control plugin.

These are dimensions of the configurable model, not recovered measurements of a
photographed person. Skinning does not simulate tissue, joint collision or cloth.

## Sources and rebuilding

Model and morph assets: MakeHuman Community, CC0-1.0. See
[asset provenance](assets/provenance.json) and [CC0 text](assets/MAKEHUMAN-CC0.txt).
No MakeHuman application logic is redistributed. Measurement vertex IDs are
factual mesh landmarks compatible with its ruler conventions; calibration and
application code are original.

Renderer, controls, skeleton clone and GLB exporter: Three.js r180, MIT.
[Renderer provenance](vendor/provenance.json) records the exact source revision.

Rebuild assets with `python scripts/build_human_studio_asset.py` from repository
root after cloning the MakeHuman repository into `work/makehuman-upstream` and
checking out the recorded commit. The builder reads body faces, joint metadata,
skin weights, macro/measurement targets and measurement landmark definitions.

Serve the existing `web/` tree with loopback HTTP; the page is an ES module app.
The project static builder copies it unchanged into the existing Pages site.
See the repository `human-studio` verification recipe for actual browser and
independent downloaded-file checks.
