# Pattern JSON v2

## Purpose

Pattern JSON v2 is the machine-facing projection of the Golden Garment YAML 1.1 contract.

**YAML 1.1 is the readable source of truth. Pattern JSON v2 is a deterministic derived contract.**

It does not replace the YAML file and it does not silently repair missing production data.

## Golden Garment input

Input: \`patterns/fitted-tshirt/input-spec.yaml\`

- YAML version: \`1.1\`
- source SHA-256: \`88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e\`
- pieces: 4
- measurements: 23
- named interfaces: 25
- coordinate unit: \`U\`
- \`mm_per_unit\`: \`null\`

## Deterministic rules

1. Preserve the source SHA-256.
2. Preserve \`U\`; never infer millimeters.
3. Preserve \`null\`; never replace unknown values with zero or defaults.
4. Generate stable \`piece_id\`, \`interface_id\`, \`measurement_id\`, and \`relation_id\`.
5. Keep the complete source document inside \`source_document\` for auditability.
6. Keep DXF as a reference binding, not as the semantic authority.
7. Mark production release as \`false\` until the required production inputs are approved.
8. A new revision invalidates downstream geometry, mesh, physics, debugger, timeline, and validation results.

## Run

Requires Python 3 and PyYAML.

    python3 tools/pattern-json-v2/import_golden_garment.py \
      patterns/fitted-tshirt/input-spec.yaml \
      patterns/fitted-tshirt/pattern-json-v2.json \
      --check \
      --expected-sha256 88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e

Then:

    python3 tools/pattern-json-v2/test_import_golden_garment.py

## Does not prove

This importer does not prove human fit, material physics, sleeve-cap front/back mapping, approved seam allowance, approved cut quantity, production DXF, CAD native round-trip, or manufacturing release.

## YAML 1.1 safety

YAML 1.1 has a wider implicit scalar type system than YAML 1.2. In particular, values such as yes/no/on/off can be boolean scalars under YAML 1.1. The importer disables only the implicit boolean resolver and keeps explicit boolean tags supported, so presentation strings are not silently changed during import.
