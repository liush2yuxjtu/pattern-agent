# Modular cloth source → one WASM/WebGPU HTML

Local `/verify`: **PASS** on the exact candidate below. Hosted publication is
pending and will be recorded separately after actual public-browser verification.
This verifies the refactor, numerical preservation and actual rendering boundary;
it does not approve physical fit or manufacture.

## Exact candidate and delivery

- Parent: `b9b67e79302e02dbb967bfff148446c960217fb6`.
- HTML SHA-256: `55950b75f7f5abc4923d943a029b08492f4d8cfb03f38d031faf8fe193ee50af`;
  2,550,975 bytes, with no external runtime dependency.
- Build fingerprint: `0f2afe8f6957102a7ae925f675d0dfc8f2ddbfef350d87b420ab53631ec69fc1`.
- Source MakeHuman SHA-256:
  `a75b6a2d59b2fa60ea29393e380182174627ba66d0993c649c8c571a6ccecda6`.
- [Full source/build hashes](build.json), [candidate and changed-file hashes](candidate.json),
  [raw evidence inventory](inventory.json), [pre-refactor baseline](baseline.json).

Fourteen runtime ES modules separate simulation, rendering, diagnostics,
recording/replay, persistence, controls and startup. `app.js` assembles their
factories without circular imports. `node web/cloth-lab/build.js` compiles the
existing C solver to WASM, bundles JavaScript/Three.js, and embeds the original
MakeHuman triangles/BVH, styles, notices and all runtime code in one HTML.
WASM performs cloth physics; actual WebGPU renders it; JavaScript handles the
browser interface. This does not claim JavaScript DOM code was compiled to WASM.

The Python build entry forwards to Node. Custom `--out`/`--work-dir`, source-root
portability, recursive source hashes, stale-avatar rejection and failed-build
output preservation are exercised at their actual CLI boundaries. The adjacent
build manifest is for inspection; the HTML does not request it at runtime.

## Local acceptance

Followed the repository [verify skill](../../../.agents/skills/verify/SKILL.md)
and [cloth-lab recipe](../../../.agents/skills/verify/references/cloth-lab.md).
All browser suites ran sequentially with repository Playwright and system
Chromium. Native adapter/device/context/configure/queue events establish actual
WebGPU, independently of the app's diagnostics. No renderer or solver is mocked.

| Boundary | Result | Raw receipt |
| --- | --- | --- |
| Original complete trial, waist, pressure and pixel checks | 16/16 PASS | [fit](local/fit.json) |
| Original steps, faults, exports, cache, resources and offline controls | 15/15 PASS | [browser](local/browser.json) |
| Original physical replay, all states, transport and cap | 15/15 PASS | [replay](local/replay.json) |
| Original actual file import and atomic state handoff | 6/6 PASS | [handoff](local/handoff.json) |
| Same embedded WASM analytic core checks | 3/3 PASS | [raw kernel log](local/logs/kernel.stderr.log) |
| Actual waist and three independent fault probes | 4/4 PASS | [waist](local/waist.json) |
| Standalone Node/legacy CLI and source-root rebuild | 8/8 PASS | [build](local/build.json) |
| True WebGPU/WebGL, pixels, offline, fallback and real device loss | 14/14 PASS | [renderers](local/renderers.json) |
| Zero/subpixel/hidden viewport and hidden startup | 7/7 cases PASS | [resize](local/resize.json) |
| Adjacent existing printable/download Pages surface | PASS | [actual browser](local/existing-pages.json), [all commands](local/pages-commands.json) |

[Original-suite commands and exit statuses](local/original-suites.json),
[fit command and exit status](local/fit-command.json),
[supplemental commands/results](local/qa-summary.json), and raw stdout/stderr in
`local/logs/` bind these results to the same HTML. All original 52 check keys and
130 existing assertions remain unchanged; see
[assertion inventory](numerical/original-assertions.json). No numerical threshold
was raised to obtain PASS.

All **61 corresponding recorded states** retain exactly the pre-refactor raw
Float32 state buffers and sparse pressure state; see
[per-frame bit identity](local/all61-baseline-equivalence.json) and the actual
[old](local/baseline-recording.json.gz)/[new](local/actual-recording.json.gz) exports.
The independent float64 geometry/tensor oracle also reopens every frame:
[61 raw reports](local/frame-oracles.json). It checks full sewing, 4,770 sampled
body distances, both edge/face intersection directions, waist and coverage, and
all 1,536 triangle tensors. The renderer gate additionally compares native
Float32 bytes at frame 240 and after 1/60 steps, including signed zero.

[Initial exported physical fields](local/initial-physical-equivalence.json),
[24 mechanically equivalent functions](local/ast-equivalence.json), and
[20 blocked/pending guards](local/blocked-guards.json) supply separate supporting
checks. Actual device destruction also verifies that strict WebGPU clears ready,
keeps BLOCKED visible through read-only exports, locks controls and rejects
mutating APIs without integrating. Auto mode switches to actual WebGL while
preserving physical state, pointer input and resize behavior.

Release WASM is 20,919 bytes, SHA-256
`6733d451ddba0b16f640c17198b80e59b432821a8eb77e1b95da1d42dabadeb2`.
The previous 89,828-byte binary embedded absolute DWARF source paths, which broke
identical rebuilds in another checkout. Only nine custom metadata sections are
removed by `-Wl,--strip-debug`; every noncustom executable/type/data/memory/export
section is byte-identical. The C source, ABI, 16 MiB memory and body are unchanged.
[Independent section parser](numerical/wasm-section-identity.json),
[intentional code-byte corruption rejection](numerical/wasm-corruption-rejection.json),
and [actual whole-memory kernel comparisons](numerical/kernel-whole-memory-equivalence.json)
separately establish this boundary. The raw WASM file digest intentionally changes.

## Actual visible result and performance

The untouched [first-ready WebGPU image](local/webgpu-first-ready-untouched.png)
is captured before any camera/mode redraw. Actual
[front](local/first-ready-front.png), [back](local/first-ready-back.png),
[side](local/first-ready-side.png), [pressure](local/first-ready-pressure.png),
[strain](local/webgpu-strain.png) and [stress](local/webgpu-stress.png) images were
visually reviewed. The complete opaque gray avatar uses original topology and
normal depth testing. The brown skirt independently covers the hip raster;
first-ready front/back/side samples contain zero exposed skin pixels.
There is no body masking or replacement collision primitive.

At the real initial frame 240, default strain remains about 17.54%, principal
Cauchy stress 43.92 kPa, peak synthetic contact pressure 59.94 Pa, and total normal
reaction 3.6884 N. Waist skin clearance is about 7 mm; sewn gap, sampled penetration
and both intersection counts are zero. Complete numeric results are in the fit
receipt and [actual first-ready export](local/first-ready.json.gz).

The [offline rendering](local/webgpu-offline-reopened.png) and
[offline replay](local/offline-timeline.png) reopen the real saved HTML, make zero
requests, restore selected physical/contact state and continue the next WASM step
exactly. Actual downloaded files are retained as
[standalone HTML](local/actual-downloaded.html.gz),
[recorded HTML](local/downloaded-replay.html.gz),
[millimetre SVG](local/cloth-patterns.svg) and [metre OBJ](local/cloth-body-scene.obj.gz).
WebGPU offline checks use an empty secure localhost document before disabling
networking; no old app instance survives. Literal `file://` WebGPU is not claimed.

This host uses real Dawn **SwiftShader software WebGPU**, not a hardware GPU.
The local timed sample logs median 83.4 ms and p95 116.7 ms across 59 frames;
the fixed WASM step near that sample is 14.83 ms. These are observations, not an
FPS acceptance target. Ten resets retain six geometries, three textures and
16 MiB WASM memory. The replay receipt records capture/seek/play timings and the
actual 1,201-state cap; total raw state/contact bound remains 98,145,720 bytes.
All performance arrays, dropped wall time, adapter and actual backend details are
retained in the browser/replay receipts, including software-only no-MSAA mode.

## Failures retained and corrected

- Native readback/queue completion initially passed while screenshots were blank
  with `--disable-vulkan-surface`. The [six-control presentation matrix](failures/native-presentation-matrix.json)
  isolated that launch flag; removing it restored actual pixels with ordinary
  security/TLS settings. The [blank native image](failures/native-first-blank.png)
  remains evidence.
- [Stale initial uniforms](failures/first-black.png) required world-matrix update,
  compile, a later real rAF draw and actual presentation before ready. Software
  transparent MSAA produced [white fringes](failures/first-halo.png); only the
  observed software adapter disables MSAA. Hardware behavior/performance is NOT_RUN.
- Candidate `386a0ebb…` passed supplemental tests but then failed the complete fit
  suite with a real zero-width GPU texture:
  [first FAIL](failures/first-fit-386.json), [original log](failures/first-fit-386.log),
  [failure image](failures/first-fit-386.png). At pixel ratio 0.8, clamping CSS width
  to one still floors to zero backing pixels. All
  [six original resize faults](failures/resize-original-summary.json) reproduce it.
  The fix tests actual backing dimensions, retains the last valid canvas and
  pauses submission while unrenderable. Seven fresh cases pass without GPU errors,
  extra physics or invalid textures. Complete fit16 then passes on `55950b75…`,
  including two naturally occurring transient skipped draws. See
  [restored view](local/zero-width-restored.png) and
  [hidden-start reveal](local/boot-hidden-revealed.png).
- Cross-checkout [DWARF build mismatch](failures/debug-path-build.json) led to the
  measured metadata-only release strip above.
- The first staged whitespace check reported 13 upstream space-before-tab lines
  in the verbatim pinned Three.js source. A file-specific `.gitattributes` rule
  exempts only that indentation category; upstream bytes/provenance remain exact,
  other whitespace checks remain enabled, and the staged check then passes.
- A first comparison of outer exports selected different recorded frames (570
  versus 600), so that comparison correctly failed. The
  [observation](failures/unaligned-selection-comparison.json) is retained; the final
  comparison uses all corresponding actual raw recorded frames, without changing
  either input or treating different selected states as equivalent.

All browsers, HTTP servers and temporary build fixtures were closed. Build-only
`node_modules` was moved outside `web/` before the static publisher copied files.
No CI verification, PR, Issue, external service, policy change or paid compute was
introduced. The existing Pages workflow is used only for publication.

Synthetic material/contact parameters, fixed waist arrangement, discrete collision
sampling and distance-based bending remain the previous model. Cloth self-collision,
CCD, measured friction, finished waistband/zipper, material calibration, physical fit
and production approval are NOT_RUN. The historical T-shirt FAIL (7.6455 mm seam
gap and 20 nonadjacent intersections) remains unchanged.
