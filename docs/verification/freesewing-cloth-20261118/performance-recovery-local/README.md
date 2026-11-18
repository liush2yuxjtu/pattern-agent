# Performance recovery 2.1: local PASS

Candidate base `d8bf6518485b12a7d8f3c0ac72f13dace7c79d81`, HTML `a2caea0725050369387d639e1a8510bcb9e8674740c00bfd428e886d353e1dfc`,
1,645,085 bytes. Application 2.0 was published from
`94d41253442400afb6d8a0bcee4c8a45f5d7e62b`; its first public browser result
was FAIL solely because p95 was 134.8 ms, above the unchanged 100 ms gate.
That raw failure and actual files are retained in the parent failure directory.

The final solver retains all body queries, 64×28 cells, 1,856 vertices, 3,584
triangles, 14,336 constraints, 120 iterations and original margins. It reuses
history/mask/vector buffers, avoids temporary barycentric arrays/callbacks,
and reuses self-contact shapecast callbacks. WASM prepares identical constant
addresses/masses/compliances/denominators once per draft. The original iterative
operation order is retained. A coupled five-frame Node test and the actual
prepared public-kernel API probe pass. Actual baseline/candidate A/B positions,
previous positions and material coordinates are identical at 120 steps.

More strongly, all three arrays are bit-identical to the actual 2.0 accepted
states at 120, 240, 360 and wind step 480. Every one of these final states has
zero body intersections, zero cloth self-intersections and no interior cloth
vertices. The 650 mm / 60% circle / linen profile passes after 120 steps too.
No geometry tolerance, shader quality, mesh resolution or test threshold was
weakened. The strict independent oracle and all nine adversarial controls pass.

Two query-cache attempts are preserved and are NOT active in the final solver.
The first created seven wind self-intersections; the stricter nearest-plane
certificate preserved coordinates but consumed its performance savings. The
last prototype source/test ZIP is retained; the first prototype's saved arrays
permit independent geometry re-audit, not a complete source reconstruction.

All 45 final Playwright checks pass, now including saved view
consistency in addition to exact offline next-step continuation. All four actual
WebGL color buffers agree with independently validated fields within 2e-6.
Actual native FreeSewing SVG is byte-identical to an independent upstream re-draft.
The new WAT binary is 1,619 bytes; both its original and prepared APIs were tested.

This host exposes 5 CPUs with a 4-core cgroup quota. `run_check.py` confines only
its own process and children to that allocation. It grants no additional CPU,
changes no global setting and logs the exact environment. The actual renderer
is ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver). Final default solver median/p95:
74.1/91.2
ms. The existing <100 ms gate passes. CPU render submission p95:
114.800 ms; actual submitted frames:
15. `frame_ms_p95` is a rAF callback interval,
not GPU frame time; idle rendering is now on demand. No hardware FPS or real-time
performance claim is made. High strain/stress remains visible and uncalibrated.

Root `/verify` and the scoped verifier were followed before committing this
fix. Node tests, the full source/field/geometry matrix, actual downloads,
GPU readback, A/B, root build and six root regressions passed. Old HTMLs and
receipts remain unchanged. Source digests, commands, raw arrays/downloads and
screenshots are retained here. The existing Pages job publishes only; the final
public artifact will be checked independently under the parent `live/` directory.
