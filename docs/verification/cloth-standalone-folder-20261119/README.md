# Standalone folder delivery

Local `/verify`: **PASS**. Hosted publication and its independent browser checks
are pending. This change adds a new folder to the existing
`liush2yuxjtu/pattern-agent` repository; it creates no repository or CI workflow.

## Artifact and source

`web/cloth-lab-standalone/` contains a complete `index.html`, its build manifest,
a Node build entry, README and license. It is an actual application, not an HTTP
or JavaScript redirect. Its URL is `/pattern-agent/cloth-lab-standalone/`.

The new entry delegates to the existing canonical builder and defaults its output
to this new folder. Fourteen JavaScript modules, the unchanged C solver and original
MakeHuman/vendor assets remain maintained in their existing source directories.
The generated HTML **and manifest** are byte-identical to the canonical build:

- HTML: 2,550,975 bytes, SHA-256
  `55950b75f7f5abc4923d943a029b08492f4d8cfb03f38d031faf8fe193ee50af`.
- Build fingerprint:
  `0f2afe8f6957102a7ae925f675d0dfc8f2ddbfef350d87b420ab53631ec69fc1`.
- WASM: `6733d451ddba0b16f640c17198b80e59b432821a8eb77e1b95da1d42dabadeb2`.
- Body: `a75b6a2d59b2fa60ea29393e380182174627ba66d0993c649c8c571a6ccecda6`.

WASM runs physics, WebGPU/WebGL renders, and embedded JavaScript handles browser
controls and files. Runtime needs no CDN, model download, backend or MCP.
WebGPU requires a supported browser and a secure context; fallback is explicit.

## Local boundary checks

Followed [the project verifier](../../../.agents/skills/verify/SKILL.md) and its
[cloth recipe](../../../.agents/skills/verify/references/cloth-lab.md).
[Exact candidate hashes and verdict](local-verdict.json),
[remote reconciliation](source-sync.json) and [raw evidence inventory](inventory.json)
are retained beside the receipts.

| Boundary | Observation | Evidence |
| --- | --- | --- |
| Default wrapper build | Complete HTML and manifest written to the new folder, equal to canonical bytes | [commands](local/first-run-commands.json) |
| Custom output and work directory | Spaces and a different working directory produce the same bytes | [commands](local/first-run-commands.json) |
| Help without compilers | Describes the new default path and succeeds with absent compiler paths | [help](local/logs/help-without-compilers.stdout.log) |
| Actual build failures | Unknown option and missing compiler return failure while preserving both old outputs | [commands](local/first-run-commands.json) |
| All source inputs | Original 14 modules, WASM C, MakeHuman and renderer sources retain manifest hashes | [verdict](local-verdict.json) |
| Actual new-path WebGPU | Original 15 browser checks pass, including physics/tensors/faults/downloads/offline/mobile | [browser](local/browser.json) |
| Actual JSON handoff | Original six file/import/atomic-state assertions pass on this path | [handoff](local/handoff.json) |
| Complete existing site gate | Build, six artifact tests, native CLI/MCP reopen, actual browser interactions/downloads pass serially | [commands](local/site-commands.json), [browser](local/site-browser.json) |

The new path was driven by actual Playwright clicks. Native adapter/device/context
and queue events confirm WebGPU rather than a mislabeled WebGL renderer. This host
uses Dawn/SwiftShader software rendering. Console/page/network errors are empty;
full performance/resource observations remain in the browser receipt.
The actual [first-ready view](local/step-000.png), [back](local/back.png) and
[mobile capture](local/mobile.png) are retained; the back was visually reviewed.

This is a distribution/path change. The earlier complete numerical and renderer
evidence remains separately archived in
[the modular verification record](../cloth-modular-webgpu-20261118/README.md),
bound to the exact same HTML bytes. It includes all 52 original checks, all 61
recorded-frame independent geometry/tensor/pressure checks and both renderer
backends. These historical results are not substituted for the new route's actual
browser checks; the new public route will receive the full flow after deployment.

## Preserved failure and recovery

A duplicated site build was accidentally started while the first site gate's
artifact tests copied shared `dist/`. Three fixture copies encountered missing
files during the concurrent rebuild. The original commands keep their **FAIL**:
[first run](local/first-run-commands.json),
[site commands](failures/parallel-site-commands.json),
[actual copy errors](failures/parallel-copy-errors.log).
No product source, test assertion or tolerance changed. The complete site gate
was rerun alone and all commands passed; its serial receipts are above. The
project recipe now records this shared-output boundary.

No tests were weakened or CI added. All browser/server processes were closed.
The existing Pages workflow will publish this new `web/` directory.
Physical fit, measured material calibration, cloth self-collision, CCD and finished
construction remain outside this numerical example; historical T-shirt FAIL is
unchanged.
