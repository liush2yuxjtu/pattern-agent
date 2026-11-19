# FreeSewing 2.5 responsiveness verification

This local acceptance applies to the exact built HTML in [candidate.json](candidate.json).
The previous public HTML was served on the same loopback host for the comparison.
Fresh Chromium sessions used the same 1440×1000 viewport and local CPU quota.
The measured renderer was WebGL2 with software rendering. The native SVG
reopen preserves the file and compares all non-transform bytes exactly. In this
run the maximum difference in a transform operand was 4.5e-13.

| Check | Result |
| --- | --- |
| First drape ready | 13.52 s → 2.90 s |
| Playback long tasks, p95 | 943 ms → 197 ms |
| Playback sample | 60 steps in 9.52 s before, 25 in 6.81 s after. The UI runs until a common step target, then receives an actual Pause click. Scheduling and click overshoot differ, so this is not a controlled steady-state FPS test. |
| Default UI | PASS 52/52, solver p95 90.2 ms against the unchanged 100 ms limit |
| Default checkpoint | Exact after a fresh 120-step simulation, including position, prior position, mass and pressure ledger |
| Physics | Eight exported states agree exactly with the previous build. Independent body collision, self-contact, coverage, seams, long-duration support and free-fall checks pass. |
| Native WebGPU | 15/15 checks on a software adapter, with actual draw-buffer validation and device-loss recovery. |
| Hardware performance | NOT_RUN. The solver continues to use CPU WASM and JavaScript. |

The performance gate tests responsiveness, not real-time simulation speed.
Custom pattern changes still compute a fresh 120-step drape. Software rendering uses a
smaller drawing buffer, and its shadows refresh when playback pauses.
Material and wearer-pressure calibration remain outside the verification.

Compare [before](performance-before.png) and [after](performance-after.png).
The [rear view](back.png), [pressure map](pressure.png) and [mobile view](mobile.png)
are actual browser captures. [Earlier failing runs](rejected) are retained.

Reproduction commands and the acceptance criteria are in the [scoped verifier](../../../experiments/freesewing_cloth_lab/.agents/skills/verify/SKILL.md).
