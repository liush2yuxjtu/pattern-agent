# v4 description proposal

The proposal is 155 Unicode characters, below the 175-character baseline. It changes scope wording rather than asserting an accuracy gain.

## Evidence and saturation

Only `development-round-0.json` and `input-K.json` were read. The four prior candidates each achieved 24/24 on independent subagent metadata routing. This is a saturated development surrogate, not native Claude routing, and offers no observed accuracy improvement to optimize. v4 has not been evaluated.

## Wording decisions

- Anchor applicability in the complete apparel-photo-to-body workflow: six independent views, an adjustable body proxy, three-dimensional rendering, OpenCV contour overlays, and body dimensions with evidence/provenance and inference labels.
- Name the six outputs compactly while retaining pose point/line and relative-depth semantics.
- Explicitly cover continuation, fitting audits, and consistency repairs across sliders, mesh, and exported dimensions. The existing artifacts need not be regenerated for a follow-up task to remain in scope.
- Use general workflow terms rather than file names, product identifiers, exact query phrases, or a development-case enumeration.
- Exclude standalone product retouching, size-chart work, medical work, general vision work, and avatar editing. Pattern/CAD and garment-preview tasks require photo-derived body fitting; pattern JSON alone does not qualify. This retains mixed photo-fitting-plus-pattern workflows without broadening to standalone garment simulation.

## Limits

No holdout material, other outputs, repository files, or installed skill were read or modified. No native Claude success, end-to-end execution success, or routing improvement is claimed. Any future evaluation should be reported separately from the current wording proposal.
