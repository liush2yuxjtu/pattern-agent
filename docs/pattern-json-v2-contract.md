# Golden Garment JSON contract

The Golden Garment is the fitted long-sleeve T-shirt in
`patterns/fitted-tshirt/input-spec.yaml`, application specification version 1.1.
The YAML remains authoritative. The JSON contract projects that source into
stable references for editors, geometry engines and later simulation consumers.

## Caller contract

Run the importer from any directory with the same source bytes. Filesystem paths
do not change the logical source identity. The CLI writes JSON only after source,
reference and schema validation succeed. Failed imports preserve an existing
output file.

```sh
python tools/pattern-json-v2/import_golden_garment.py \
  patterns/fitted-tshirt/input-spec.yaml \
  patterns/fitted-tshirt/pattern-json-v2.json \
  --reference-dxf patterns/fitted-tshirt/input.dxf \
  --expected-sha256 88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e \
  --check
```

The public Python entry point is `import_golden_garment(raw, source_path=SOURCE_PATH,
previous=None, *, reference_dxf=None)`. It owns parsing, projection and validation.
Consumers cannot supply a parsed document that disagrees with its byte digest.

## Source and references

`source_document` preserves the full parsed YAML. Existing geometry projections
remain available and must equal their source. `edges` contains references to the
204 named source lines, without another copy of the coordinates. An edge can be
an internal construction line. Its presence does not classify it as a sewing edge.

The 25 interfaces contain ordered edge chains. The 9 connection summaries remain
separate from the 11 seam-level records in `seam_pairs`. Four sleeve sides retain
two candidates and a null selection. `RESOLVED` means the source identifies an
interface. It does not mean a manufacturing parameter is approved.

Piece roles are lists. The same sleeve pattern supplies both left and right
sleeve roles. Role count does not approve cutting quantity. Manufacturing fields
retain null values and their source state. Missing declarations remain missing.

Raw bytes have a SHA-256 digest. A separate digest of canonical parsed JSON
identifies the revision. Whitespace changes preserve revision identity, while
source content changes produce a different revision. Named IDs depend on names,
not coordinates or array positions.

`derived_artifacts` records the source revision for each result. A result from a
different revision becomes `STALE` when imported with `--previous`. New results
remain `NOT_RUN` until a consumer provides them. Baseline patch and review fields
remain empty.

## Design decision

Two shapes were compared: extend every copied projection, or replace them with a
fully normalized graph. The chosen increment retains existing readable projections
and adds reference-only edges. This keeps the CLI useful without forcing a full
consumer migration. Validation checks every retained projection against the source.
The independent auditor reads the original YAML and DXF rather than regenerating
expected JSON with the importer.

Replacing all existing geometry projections with graph lookups would reduce file
size, but requires a separate consumer migration. Guessing missing sewing mappings
would change the garment design and is excluded from import.

## Acceptance boundary

The independent audit reuses the repository's existing raw-DXF and measurement
auditor for 231 entities, 1,487 polyline vertices, 23 measurements and 25 interfaces.
It separately checks JSON references, role preservation, seam records and result
states, then rejects corrupted copies. Geometry comparison uses the source's six
decimal places. This tolerance describes numerical representation, not cutting
precision or fit.

The source front-hem interface records a 426.184448 U gap between its segments.
Import preserves this fact. Units remain U with null `mm_per_unit`. Physical fit,
fabric calibration, production patterns and native CAD round-trip remain separate
acceptance tasks.
