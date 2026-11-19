# CLO Rust Boat

Use this plugin to reproduce geometric audit and analysis on authorized
Boat Linux with access to the private `clo-rust` snapshot. It accepts already
saved pose meshes and optional seam metadata. It produces strain, fold angle,
per-piece CSV and JSON, VTK, and an offline self-contained HTML report.

The [review skill](skills/clo-rust-boat-fit-review/SKILL.md) includes a
[batch runbook](skills/clo-rust-boat-fit-review/references/boat-run.md),
mesh preparation and report scripts, and the optional pinned Carlton adapter.
Boat access and the existing Rust runtime are prerequisites. Dynamic draping,
native CLO fit categories, stress, and pressure have separate provenance.

```sh
codex plugin marketplace add liush2yuxjtu/pattern-agent --ref main
codex plugin add clo-rust-boat@pattern-agent
```
