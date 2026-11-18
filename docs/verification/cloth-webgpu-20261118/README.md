# FreeSewing 2.4 hardware WebGPU renderer

Artifact: `web/freesewing-webgpu.html`, SHA-256
`293e34afab07c2ad4b504f8463b8255fd1908aa9dab8866cf71e289dba6ec263`.
Build provenance and byte count: `candidate.json`. The 2.2 pinned and 2.3 free-waist
HTML files remain unchanged. This is the four-panel Sandy case, separate from
the concurrently maintained modular cloth-lab and two-panel fitting cases.

## Production policy and scope

Request a high-performance WebGPU adapter. Hardware adapters use native WebGPU
via pinned Three.js 0.181.2, TSL-generated WGSL and the procedural weave. A
software/fallback, unavailable or denied adapter selects WebGL2 compatibility.
`?renderer=webgpu` forces the diagnostic path, including slow software devices;
`?renderer=webgl` selects compatibility explicitly. Both renderers and dependencies
are in the one HTML; no runtime service, CDN, MCP or new asset download.

**Physics remains Float64 WASM on the CPU.** This is not a WebGPU cloth solver.
Gravity, all 1,856 positive particle masses, 120 iterations, closed reinforced
waist edge, actual MakeHuman contacts and cloth contacts remain. Actual hardware
GPU speedup is **NOT_RUN** on this software-only machine. Material, wearer
pressure and real fit remain **NOT_VALIDATED**; high stretch remains visible.

## Local verification

Root and scoped `/verify` recipes were used on base
`6d323edbcf3b13bbabfed18d72f4267c6eb465eb`, after non-force reconciliation.
No CI tests, PR, Issue, paid compute or settings change. Existing Pages publication
is observed only after independent local verification.

| Boundary | Verdict and evidence |
| --- | --- |
| Default production UI | PASS, **52/52**, `local/browser/browser-report.json`; actual WebGL2 compatibility on this host, p95 **94.5 ms** below unchanged 100 ms gate |
| Earlier default run | PASS 52/52, p95 79.2 ms; earlier counter-label candidate retained in logs; not substituted for the final-byte result |
| Native WebGPU functional acceptance | PASS, **15 checks**, `local/gpu/receipt.json`; actual shader modules, queue submits and cloth draw bindings observed, not just an API availability flag |
| Actual GPU heatmaps | PASS for all 32,256 color components in each of strain/stress/fold/curvature/pressure, error <2e-6; copied GPU buffer must be the same object bound by the cloth draw |
| Actual canvas images | Five distinct raw canvas PNGs, plus screenshots, not only DOM/tab changes; canvas nonblank; primary agent visually reviewed actual body/fabric and diagnostic evidence |
| Rendered human equals collider | GPU vertex/index readback equals the source collision human; 13,380 vertices/26,756 triangles, CPU Uint16 vs GPU Uint32 index values exactly equal |
| Device failure and offline | Saved single HTML reopens on native WebGPU; real GPUDevice.destroy pauses physics; WebGL2 recovery preserves positions exactly; missing/null/denied adapters and automatic software compatibility pass |
| Physics, support, source and fields | Native WebGPU pages at 120/240/360, wind 480, edited linen 650mm/60% 120, and 1440/1800 pass independent audits; zero body intersections, self-intersections and inside vertices; zero exposed posterior samples /466; zero seam gap |
| Actual free fall | Removing the real collider gives the analytic damped-gravity COM fall, no hidden pins; detailed force/pressure ledgers remain in `local/support` |
| Trajectory preservation | All 8 states, including body-removed fall, have bit-identical current/previous coordinates, UVs, inverse masses and pressure vs accepted 2.3; `local/trajectory-exact.json` |
| Unit and root regressions | Four Node controls, complete independent bad-input controls and five active WebGL draw buffers passed; root build, six artifact negative controls and homepage/root browser acceptance archived locally |
| Forced software full UI | **FAIL**, p95 **135.8 ms** >100; the other 51 checks passed. `rejected/forced-software-final/` preserves the receipt. This override is not reported as 52/52 or hardware performance |

The local native functional/physics receipts were taken immediately before the
final label-only correction to the WebGL counter scope. The actual GPU branch
and physics code are unchanged. The final-byte default 52-check receipt is bound
to the artifact above. Public acceptance repeats the actual published artifact.

## Performance measurement and interpretation

CPU quota four cores, test child affinity matched to that quota. Test-only
software WebGPU uses SwiftShader/Vulkan with its surface enabled. Readers need
no browser flags. The Browser plugin/ego executable was unavailable; the user's
explicitly requested Playwright and system Chromium were used.

The isolated, uninstrumented fixed-state comparison waits for the **same
723×1262 drawing buffer** in both renderers, warms five frames, then measures 30
CPU-submit-plus-GPU-fence completed-frame latencies. WebGPU software p50/p95:
478.9/649.705 ms; WebGL2 p50/p95: 1.2/2.175 ms. See `local/gpu/timing.json` and
both real timing canvas images. These are software-driver observations, not
GPU-only times, FPS, real-device results or a promised hardware speedup. They
support preferring compatibility for software adapters. The first comparison
failed to wait for layout/buffer size; that invalid comparison is retained and
is not used as the accepted timing evidence.

Both counters now include submitted shadow passes (GPU also includes output
presentation). `sceneTriangles` counts scene geometry once, preserving the
original <50,000 scene budget. The original <100 ms solver p95 gate remains;
no mesh, contact queries, solver rounds or tolerances were reduced.

## Fixes and preserved failures

- WebGPU uploads widen Uint16 indices in place. A numerically identical render
  clone protects the immutable body collider. GPU buffer readback proves the
  clone describes the same asset.
- Collision math is isolated from renderer math; collision geometries use the
  same BufferAttribute implementation. Face normals are precomputed in exactly
  the original Float64 operation order. Frozen broad-phase bounds are cached
  without removing or reordering candidates. The full old trajectory is exact.
- A single node material switches weave and diagnostics with a uniform. Four
  seam lines are retained across re-drafts. The first actual GPU frame is fenced
  before readiness, and drawing uses queue backpressure.
- Separate compileAsync shadow precompilation invalidated live ShadowMap /
  ShadowDepthTexture resources in this pinned build. It was removed. Actual
  heatmap, re-draft and mobile tests now report zero GPU validation errors.
- A mobile transient zero-width viewport created invalid textures. Resize now
  ignores nonpositive dimensions; a nonblank mobile-canvas check was added.
- The first test launch lacked the supported Vulkan configuration and lost the
  device. Another launch disabled Vulkan surface presentation: raw GPU pixels
  existed but screenshots were blank. Minimal red-canvas probes identified the
  environment cause; correct surface-enabled rendering is required for PASS.
- Early full software UI runs failed performance and/or GPU console checks;
  their receipts, console output, saved executable HTMLs and images are retained
  under `rejected/`. No failed check was renamed a pass.
- A Float64 SIMD kernel prototype passed bit-exact coupons but did not improve
  measured performance. It was rejected; its WAT/HTML and timings are preserved.
  The shipped WASM is the unchanged 1,783-byte scalar kernel.

Independent video visual review, a complete per-frame timeline in this specific
lab, universal CCD, calibrated fabric/pressure, full native waistband construction
and manufacturing acceptance remain NOT_RUN / NOT_VALIDATED. This is a bounded
renderer/cloth demonstration, not a completed CLO replacement.

## Reproduction

Use `experiments/freesewing_cloth_lab/README.md` and its scoped verifier. Typical
commands from repository root:

```sh
node experiments/freesewing_cloth_lab/build.mjs
python experiments/freesewing_cloth_lab/run_check.py browser --url URL --out OUT
CLOTH_WEBGPU=1 python experiments/freesewing_cloth_lab/run_check.py webgpu --url BASE_URL --output OUT
CLOTH_WEBGPU=1 python experiments/freesewing_cloth_lab/run_check.py webgpu --url BASE_URL --output OUT --timing-only
CLOTH_WEBGPU=1 python experiments/freesewing_cloth_lab/run_check.py dynamics --url 'BASE_URL?renderer=webgpu' --output OUT
CLOTH_WEBGPU=1 python experiments/freesewing_cloth_lab/run_check.py support --url 'BASE_URL?renderer=webgpu' --output OUT
```

Run timing without other tests. Keep forced software performance failures.
Observe existing publication, check the exact public hash/build identity, and
repeat actual public UI, native GPU, edited-profile and dynamic/support probes.
