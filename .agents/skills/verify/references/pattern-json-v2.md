# Golden Garment YAML and JSON contract

Working directory: repository root. Runtime boundary: the importer CLI and saved
JSON reopened by a consumer. No web UI changes are claimed by this boundary.

Use the exact source files in `patterns/fitted-tshirt/`. Install the dependencies
listed in `tools/pattern-json-v2/requirements.txt` if they are absent. Keep the
original YAML and DXF unchanged.

```sh
python -m unittest discover -s tools/pattern-json-v2 -p 'test_*.py' -v
python tools/pattern-json-v2/import_golden_garment.py \
  patterns/fitted-tshirt/input-spec.yaml \
  patterns/fitted-tshirt/pattern-json-v2.json \
  --reference-dxf patterns/fitted-tshirt/input.dxf \
  --expected-sha256 88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e \
  --check
python scripts/audit_pattern_json_v2.py \
  patterns/fitted-tshirt/pattern-json-v2.json \
  --report work/verify-pattern-json-v2/independent-audit.json
git diff --check
```

Observe the real CLI, then reopen the saved JSON. Repeating the same input bytes
from a different working directory must preserve output bytes. The audit must
reopen the original DXF and YAML, recompute dimensions and interfaces, check source
paths and all references, and reject every corrupted-copy control. It must not
import the converter to produce expected values.

Drive the CLI with an incorrect `--expected-sha256` and verify that an existing
output is unchanged. Import a changed source with `--previous` containing a
revision-bound control result. Its result must become `STALE`; a no-op repeat
must preserve state. Test fixtures do not establish a physical simulation result.

Record candidate file digests, raw commands, exit codes, observations and one
verdict under `docs/verification/`. The baseline file must contain 4 pieces,
204 named source lines, 23 measurements, 25 interfaces, 9 connection summaries
and 11 seam-level records. Both sleeve roles and four unresolved sleeve mappings
must remain present. The source's 426.184448 U front-hem gap remains unchanged.

Unknown material and manufacturing values remain null. Units remain U with null
`mm_per_unit`. The JSON state machine only checks revision binding; it does not
certify solver outputs. Keep the legacy garment physics FAIL and physical fit
NOT_RUN separate from a contract PASS. Temporary files use test-owned directories;
the CLI and auditor start no servers or browsers.
