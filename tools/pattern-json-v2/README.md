# Pattern JSON v2

Golden Garment uses `patterns/fitted-tshirt/input-spec.yaml` as the design source.
The importer produces Pattern JSON v2.1.0 and verifies its schema and source
projection before writing. The source specification version is `1.1`. That
number does not declare the YAML language version.

The frozen input has SHA-256
`88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e`.
It contains four pieces, 204 named lines, 27 text entities, 1,487 polyline
vertices, 23 measurements, 25 interfaces, 11 seam records and nine connection
summaries. Coordinates remain `U`; `mm_per_unit` remains `null`.

## Import and reopen

Install the dependencies from `requirements.txt`, then run from the repository
root:

```sh
python tools/pattern-json-v2/import_golden_garment.py \
  patterns/fitted-tshirt/input-spec.yaml \
  work/golden-pattern-v2.json \
  --reference-dxf patterns/fitted-tshirt/input.dxf \
  --expected-sha256 88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e \
  --check
python -m unittest discover -s tools/pattern-json-v2 -p 'test_*.py' -v
```

The optional `--reference-dxf` records the SHA-256 of bytes actually read. Its
role is `reference-only`; the importer does not treat DXF as design authority or
claim to validate its geometry. Without that option, `reference_assets` is empty.
An independent source and geometry auditor must compare the delivered manifest
with the actual YAML and reference DXF.

A successful `--check` prints a JSON report. Invalid input exits with code 2 and
preserves any existing output. Output uses an atomic replacement. Moving or
renaming the input file does not change the output; the logical source path
always remains `patterns/fitted-tshirt/input-spec.yaml`.

## Contract fields

| Field | Contents |
| --- | --- |
| `source_document` | Complete parsed source, including unknown values and original geometry |
| `geometry` and `pieces[].geometry` | Existing consumer projections, checked against the source |
| `pieces[].roles` | All component roles, including both sleeve roles; these are not approved cut quantities |
| `edges` | 204 named line references with piece identity and RFC 6901 source paths; no additional coordinate copy |
| `interfaces[].edge_chain` | Ordered edge IDs with the source `正向` or `反向` direction |
| `seam_pairs` | All 11 seam records and their complete source records |
| `seam_relations` | The nine connection summaries, distinct from the seam records |
| `manufacturing` | Unknown or missing cut quantities, grainlines, seam lines, cut lines, allowances, notches and grading |
| `review_events` | Empty until a review event implementation exists |
| `revision.spec_patch` and `revision.geometry_patch` | `null`; this importer has not generated patches |
| `derived_artifacts` | Freshness state for geometry, mesh, physics, debugger, timeline and validation results |

`RESOLVED` on a seam side means that its interface references are specified. It
does not approve sewing parameters. Four sleeve sides remain `UNRESOLVED`, with
`interface_ids: null` and both candidate interfaces preserved. The importer
preserves the front hem's recorded `426.184448 U` gap; it does not join that gap.

Manufacturing entries carry `value: null`. `UNKNOWN` points to an unconfirmed
source record, while `MISSING` has no supplied design value. No allowance or cut
quantity is inferred from display text. Manufacturing release remains false.

## Identity and freshness

Stable IDs use the complete source names, independent of coordinates and line
array positions. Reordering lines preserves their IDs. `revision_id` is
`sha256:` followed by the SHA-256 of canonical parsed JSON: UTF-8, sorted object
keys, compact separators and finite numbers. The original byte hash is retained
separately. Formatting changes can change the byte hash while preserving the
revision. Coordinate changes produce a new revision.

`--previous previous-manifest.json` validates and reopens an existing v2.1
manifest. Existing result records keep their result and source revision. The
importer computes their status:

- `NOT_RUN` when no result or source revision exists.
- `CURRENT` when a result is bound to the current revision.
- `STALE` when a result is bound to a different revision.

`CURRENT` describes revision freshness. It does not mean that a result passed.
A new import has six `NOT_RUN` records. This command does not run a solver,
produce a mesh or certify fit.

## Migration from the v2.0 draft

The v2.1 contract retains the source, geometry and connection-summary fields.
Read all `pieces[].roles` instead of the removed singular `role` and
`role_quantity`, which had lost one sleeve role. Rebuild IDs from the new
manifest instead of reusing draft measurement, interface or relation IDs.
Piece IDs remain unchanged. The new SHA-256 IDs eliminate punctuation-based
slug collisions. The v2.0 fixed baseline revision is replaced by a content
revision; old results must be re-bound using actual evidence before use.

The importer rejects duplicate YAML keys, non-string mapping keys, wrong source
versions, non-finite numbers, broken line or interface references, duplicate
identities and inconsistent output projections. Its isolated scalar resolver
keeps `yes`, `no`, `on` and `off` as text, supports `true` and `false` booleans,
and preserves `null`. It does not change PyYAML's global `SafeLoader` behavior.
