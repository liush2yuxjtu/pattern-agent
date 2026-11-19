# CLO Rust Boat

Boat Linux counterpart to CLO Local. Mirror its three entry points with
`clo-dxf-fit-review`, `clo-seam-walk`, and `clo-fit-export`. The earlier
`clo-rust-boat-fit-review` remains the shared batch entry point.

The private OpenAI package includes Linux `pattern-native` executables. The
GitHub package contains the workflow source and can use an authorized
executable already on Boat with `--remote-native` or `--native`. The
[runbook](skills/clo-rust-boat-fit-review/references/boat-run.md) covers all
commands and input layouts.

The Rust runtime audits paper pattern sewing records and recomputes strain
and folds from saved poses. Native CLO fit and stress images retain their
original bytes and provenance. Fresh CLO simulation and native CLO project
changes require the live CLO workflow.

```sh
codex plugin marketplace add liush2yuxjtu/pattern-agent --ref main \
  --sparse .agents/plugins --sparse plugins/clo-rust-boat
codex plugin add clo-rust-boat@pattern-agent
```
