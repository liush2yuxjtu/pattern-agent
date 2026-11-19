# CLO Rust Boat 0.3.0 verification

Candidate based on `950332e22ec3b21db5bfad3209982cf582c99106`. Followed
the [CLO verification recipe](../../.agents/skills/verify/references/clo-fit-export.md)
and the [Boat runbook](../../plugins/clo-rust-boat/skills/clo-rust-boat-fit-review/references/boat-run.md).

| Scope | Verdict | Observed result |
| --- | --- | --- |
| Git package install | PASS | Isolated Codex marketplace install reports 0.3.0. App-server `skills/list` exposes four enabled namespaced skills, including the three mirrors of CLO Local. |
| Private package | PASS | Five validated skills including the retained report skill. The private release inventory lists both ELF binaries and the SHA-256 manifest. The ZIP contains both builds and dependency notices. GitHub ships the workflow source with explicit existing-binary options. |
| Boat Linux `seam-walk` | PASS | On a fresh authorized x86-64 snapshot fork, upload, execution and return succeeded with the bundled binary. The outer shell audit reopened with the same 66 groups, 132 valid endpoints and 1,983 constraint samples. Strict connectivity matched 169 original whole-garment groups. |
| Boat Linux `review` | PASS | The same binary and transport returned three analytic flat/bent poses. Rust maps were present and the absent CLO fit and stress PNGs were recorded as missing. |
| Boat Linux `fit-export` | PASS | Carlton's three saved poses each produced all four map categories and 28 piece rows. JSON/VTK agreed at 84,832 triangles per pose. All 12 native PNGs were byte-identical to the input and the 19 embedded figures decoded. The Boat-side independent receipt and the local input digests agreed. |
| Full fit-result archive transfer | BLOCKED | The upload succeeded. After an intermittent API timeout, the staged upload was recovered and executed on the same VM. The 30 MB return transfer was stopped after reading back results independently on Boat. The two smaller mode bundles completed the return transfer. |
| Native architecture and controls | PASS | The archived AArch64 binary executed `audit` on local Alpine Linux. Missing source maps were rejected in strict mode with no results directory. Headless Chrome rendered the matching local report at 1,320 and 390 px offline, with all 19 figures visible. |

The bundled Linux builds were made with Rust 1.100.0 using
`cargo build --offline --locked --release --target x86_64-unknown-linux-musl --target aarch64-unknown-linux-musl`.
SHA-256 of the x86-64 binary used for every Boat run:
`8b9e63bcf319f2496908d75dc628c0b2c7c25a751ec816110df58b7679a9b2ff`.
AArch64:
`c3eb1f368467d56163098fba59415e19be2e5c82c5371ca6d061750d4a4dd589`.

Raster fit and stress data came from saved native CLO captures. Rust
recomputed geometric strain and fold angle. No new draping or native CLO
project edits were part of this verification.
