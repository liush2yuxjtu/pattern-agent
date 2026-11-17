# Independent spec edit and DXF patch benchmark

Working directory: repository root. Source: `experiments/intent-edit-benchmark/`.
Input pair: `patterns/fitted-tshirt/input-spec.yaml` and `input.dxf`, pinned by
the independent auditor to the published baseline digests.

Prerequisites actually used: Python 3.12, PyYAML 6.0.3, ezdxf 1.4.4.
Matplotlib and Noto Serif CJK are optional for regenerating the review figure.

```sh
python -m unittest discover -s experiments/intent-edit-benchmark -p 'test_*.py' -v
intent_bench_dir=$(mktemp -d /tmp/intent-edit-benchmark.XXXXXX)
python experiments/intent-edit-benchmark/run_benchmark.py --output "$intent_bench_dir/results"
python experiments/intent-edit-benchmark/audit_benchmark.py --results "$intent_bench_dir/results" --output "$intent_bench_dir/audit"
git diff --check
```

The CLI requires an empty output directory to prevent stale outputs in rejected
cases. Four implemented natural-language intents produce new Chinese YAML,
semantic diff, guarded DXF coordinate patch and actual DXF. Three incomplete or
invalid requests must produce decisions without success artifacts. The intent
file entrypoint matches this closed catalog; it is not an unrestricted parser.

The independent auditor imports neither generator nor case modules. It reopens
raw CAD, recomputes dimensions/interfaces, verifies targets and preserved areas,
replays and reverses patches, compares contour defects with baseline and probes
bad hashes/old values/corrupt output. Missing positive or negative cases fail.
Public CLI tests also require deterministic artifacts and real patch replay.

The original ENTITIES-only DXF has no HEADER or physical-unit declaration.
ezdxf's in-memory unit default is not calibration. Use YAML U; production remains
BLOCKED and fit NOT_RUN. Existing small contour gaps are recorded, not repaired
or represented as fully closed production patterns. No website or CI change.

Evidence: `docs/verification/intent-edit-benchmark-20261117/`; delivered files and
review figure: `experiments/intent-edit-benchmark/results/`. Temporary test and
profile directories clean up on exit; no browser, HTTP service or paid job.
