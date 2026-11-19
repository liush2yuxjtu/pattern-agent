# CLO Local and CLO Rust Boat 0.1.0

Candidate base: `738445ddaf6e43a57e3281cac243c8c61d78d644`.
Tested trees: `plugins/clo-local` at `a38c9152451297eb843c77fb7240c7007cc2f422`
and `plugins/clo-rust-boat` at `4eb312daa635c03a093b7ca56f678baecf7f9744`.

| Claim | Verdict | Observed |
| --- | --- | --- |
| Both plugins are installable from the Pattern Agent marketplace checkout and are valid private OpenAI packages | PASS | In an isolated Codex profile, both `codex plugin add` calls installed 0.1.0. App-server `skills/list` returned all four enabled namespaced skills. The two ZIPs reproduced the installed file bytes. Both private account releases were read back with their full file lists. |
| CLO Local saved-case export and batch checks | PASS | Installed `export_fit.py` reported all four maps complete for each of the three Carlton poses. JSON, CSV and PNG readback confirmed 28 pieces per pose. `compare_poses.py` gave 84 rows. Both existing fold geometry tests passed. The installed seam CLI planned two groups on its example and rejected an old Carlton plan with a measured 78.262558 mm gap. An invalid piece-ID count was rejected before a report was written. |
| Rust mesh analysis and offline report | PASS | A release build of the existing Rust source ran the installed scripts locally. Three 100 mm synthetic panels matched independent flat and bent analytic checks. Carlton produced 28 pieces and 84,832 triangles per pose. JSON, VTK and CSV agreed. The report's seven figures decoded at 1,320 and 390 px in headless Chromium with no horizontal overflow or external document requests. Modified UVs and a tampered payload digest both stopped before any result was created. |
| Fresh native CLO writes and Boat Linux replay | BLOCKED | Local CLO was open, but the MCP bridge was unreachable. The existing Boat instance reported stopped. The current run used saved CLO evidence and a local native Rust build. It neither restored Boat compute nor edited a CLO project. |

## Replay

Use the [CLO recipe](../../.agents/skills/verify/references/clo-fit-export.md)
and both installed packages. Start with these public entry points:

```sh
codex plugin marketplace add "$PWD" --json
codex plugin add clo-local@pattern-agent --json
codex plugin add clo-rust-boat@pattern-agent --json
python -m unittest discover -s .agents/skills/clo-fit-export/scripts -p test_fold_preview.py -v
cargo build --offline --locked --release
```

Run the Cargo command in an already available `clo-rust` checkout with its
dependencies cached. Use the actual CLO project, matching per-pose GLBs and
native front/back captures for all pose export inputs. The stress images are
available in this case, while numeric stress samples are absent. Use
`prepare_meshes.py` and `run_review.py` from the installed Rust skill to
reproduce the local geometry results.

The checkout retains `clo-fit` for existing users. The two bundles contain
workflow files, reference scripts and examples. Runtime credentials, the
private Rust engine and Carlton project inputs stayed outside the bundles.
