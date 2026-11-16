## Chat verification recipe — 2026-11-15 — one-shot2D pattern roundtrip

Follow `experiments/pattern_roundtrip/README.md` from repository root. Generate
the split assets, run the3 analytic unwrap probes, re-export the physical-size
PDF, then execute the independent2D verifier with `--negative-controls`.
Expected:6 analytic PASS,2 metamorphic PASS,9 specifically witnessed faults,
3392/3392 source faces and valid4disk panels. Conditional seam FAIL (exit2):
each side's flattened bodice/cap differ23.270725mm; intended ease is unknown.
Run section_proxies.py:10 known-answer tests and displaced-body/stale-path
negative must pass; ambiguous real sections must remain UNKNOWN.

Keep both failed static rest-key trials and tiny dynamic-base controls. Execute
the3 fresh31-frame drape_metric.py cases and compare saved physical meshes with
compare_metric_runs.py using the frozen causal-protocol.json. Expected exit2:
atlas metric invariance passes within1µm, but trajectory invariance FAILS the
predeclared1mm limit; perturbation response is not5× isolated from control drift.
Do not widen thresholds or infer fit from input sensitivity.

Run inspect_metric_results.py (23 analytic probes before3 final-mesh audits),
reopen_metric.py (all3 snapshots, full arrays), and inspect the actual renders,
2D pattern and measured-control chart. Preserve exact commands, source hashes,
base candidate, logs and honest conditional/unknown verdicts before direct main
commit. Physical fit NOT_RUN; this is not flat-panel sewing or donning.
