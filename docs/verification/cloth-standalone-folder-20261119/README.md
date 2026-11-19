# Standalone folder delivery

Local and new public-route `/verify`: **PASS**. Publication and the complete
independent public-browser flow are retained in `live/`. This change adds a new folder to the existing
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


## Actual new public route

Source commit `bc8d43fa762f7913f248e54fe2a8af00d97f94b4` was pushed directly to
the existing repository. Its existing Pages publication
[44450952292](https://github.com/liush2yuxjtu/pattern-agent/actions/runs/44450952292)
finished successfully: [run](live/publication-run.json), [job](live/publication-jobs.json).
The publication workflow was only observed; verification stayed local.
A concurrent unrelated publication advanced the root deployment to
`bc355ab5942dbce81704761bf21a2e225c9ce8da`. One restart was blocked by the old
root-commit assertion before executing replay. The [independent proof](live/repin-proof.json)
confirms this source commit is its ancestor, all relevant sources/verifiers and
the full runtime HTML are unchanged, and the [new publication](live/repin-publication.json)
succeeded. Remaining commands pin their actual root commit; the
[blocked attempt](live/failures/repin-first-attempt-commands.json) and
[trace](live/failures/repin-first-attempt.stderr.log) are preserved.
[Public HTTP readback](live/http-identity.json) requires the complete new-path HTML,
its manifest and the root deployment commit to match.

The actual [new URL](https://liush2yuxjtu.github.io/pattern-agent/cloth-lab-standalone/?v=bc8d43fa762f7913f248e54fe2a8af00d97f94b4)
passes all **52 unchanged** original checks:
[fit16](live/fit.json), [browser15](live/browser.json),
[replay15](live/replay.json), [handoff6](live/handoff.json).
Every one of the **61** recorded physical states is independently reopened:
[all-frame reports](live/frame-oracles.json). Corresponding raw Float32 buffers,
pressure states, frame/time/parameters and event kinds remain exact against the
pre-refactor export: [comparison](live/physical-equivalence.json),
[actual recording](live/actual-recording.json.gz).
The adjacent [public site/download flow](live/site-browser.json) also passes.
All [commands/exit statuses](live/commands.json),
[raw inventory](live/inventory.json) and [final verdict](live/verify.json) are retained.

A first public replay run failed the unchanged playback bound: a 0.5-second clip
at 0.5x took 1.1951 seconds rather than 1 second, beyond the 0.15 second tolerance.
Its [first commands](live/failures/first-public-commands.json),
[timing samples](live/failures/first-playback-timings.json) and
[trace](live/failures/first-replay.stderr.log) remain FAIL. Product code and the
timing assertion were unchanged. A fresh native-WebGPU
[eight-run timing probe](live/timing-probe.json) passes all four speeds twice,
including exact selected-state restoration and zero integration, then the complete
fresh replay suite passes. The cause of the single overrun is not established;
the observed software-rendering timings remain visible rather than hidden.
The portable probe is persisted as `tools/cloth_lab/probe_replay_timing.py` and
its own [eight actual runs](live/portable-timing-probe.json) pass. An initial
input guard assumed a 60-step float32 clock differed from exactly 0.5 seconds
by less than 1 microsecond. The actual valid clip spans 0.49999237060546875 seconds
with per-step error 1.2716e-7 seconds, within the original 3e-7 bound. The
[guard failure](live/failures/portable-clock-guard.stderr.log) is retained; the
portable tool now checks all 61 consecutive frames and the original per-step
clock bound. The unchanged 0.15 second playback bound is still enforced.

Actual public [untouched first view](live/step-000.png),
[front](live/first-ready-front.png), [back](live/first-ready-back.png),
[side](live/first-ready-side.png), [pressure](live/first-ready-pressure.png),
[stress](live/stress.png), [strain](live/strain.png),
[mobile](live/mobile.png) and [offline replay](live/offline-timeline.png) images
are retained. Default frame 240 has zero sewn gap, zero sampled body penetration,
zero exposed target skin pixels, and about 17.54% maximum strain. The original 20%
warning remains unchanged. Native events confirm actual software WebGPU online,
with no page/console/HTTP errors. Performance samples, real adapter/resource counts
and [performance screenshot](live/performance.png) remain separate from hardware claims.

Original-suite offline windows use `about:blank` and actually select WebGL2 there,
as their screenshots state. Secure-origin actual offline WebGPU was separately
validated on the byte-identical HTML in the modular renderer14 record; no fallback
image is presented as native WebGPU evidence. The actual
[downloaded standalone](live/actual-downloaded.html.gz),
[first-ready state](live/first-ready.json.gz) and [millimetre SVG](live/pattern.svg)
are available for reopen. Later documentation commits are not newly deployed code.
