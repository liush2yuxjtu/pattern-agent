# Golden Garment v2.1 contract verification

PASS for the exact YAML 1.1 to Pattern JSON v2.1 contract. Physical fit remains
NOT_RUN, and the repository's historical cloth FAIL is unchanged.

The importer preserves 4 pieces, 204 named source lines, 27 text entities, 1,487
polyline vertices, 23 measurements, 25 interfaces, 9 connection summaries and 11
seam-level records. Both sleeve roles and all four unresolved sleeve mappings
remain present. Units remain U with null `mm_per_unit`; production release is false.

The actual CLI produced
[`pattern-json-v2.json`](../../../patterns/fitted-tshirt/pattern-json-v2.json).
Its SHA-256 is
`26682c9b913b4ff897b4e55c989dbc1bf1a8231fca5a61ee07954006b8fd438f`.
The content revision is
`sha256:8b2723eb0d4f9fa8fca9c3c696db9db814ab180a7b62aaaaf03dc76aa63397c1`.

- [Candidate files and commands](candidate-files.json) bind the tested code and data.
- [25 local tests](unit-tests.log) cover the public API and CLI.
- [Independent audit](independent-audit.json) reopens the original YAML and raw DXF,
  recomputes dimensions and interfaces, and rejects all 12 corrupt-copy controls.
- [Independent recheck](review-recheck.json) reruns the public CLI, disk reopening,
  old failure fixtures, source protection, cross-directory equality and actual
  six-category CURRENT to STALE transitions.
- [Initial baseline failures](baseline-fault-controls.json),
  [source-overwrite reproduction](source-clobber-reproduction.json) and
  [first review findings](independent-review-findings.json) preserve the failures
  that led to the fixes. No prior failed receipt was converted into a pass.

Revision-control fixtures contain explicit synthetic results. They test freshness
binding only. The delivered baseline has six NOT_RUN records and empty patch and
review fields. No LLM request, mesh generation, solver run, CAD round-trip or
garment fit is established by this verification.

The existing verifier now routes this boundary through
[the contract recipe](../../../.agents/skills/verify/references/pattern-json-v2.md).
