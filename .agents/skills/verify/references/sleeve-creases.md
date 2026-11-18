# Sleeve crease diagnostic verification

Claim: identify the actual local sleeve ridge using mesh geometry; highlight its
location, pair a material edge across remeshing, and capture measured inspection
and optional live-solver telemetry. This is a separate surface from seaming,
cloth/body contact, calibrated mechanics and physical fit.

Canonical workflow: [verify-sleeve-creases](../../verify-sleeve-creases/SKILL.md).
Working directory: repository root. Python 3.9+, standard library only.
No new Blender, browser dependencies, paid compute, CI, PR or Issue is required.

## Local executable controls

```sh
python -m unittest discover \
  -s .agents/skills/verify-sleeve-creases/scripts -p test_inspect.py -v
python .agents/skills/verify-sleeve-creases/scripts/inspect.py \
  --input .agents/skills/verify-sleeve-creases/fixtures/after-basic.json.gz \
  --out work/sleeve-creases/after.json --trace work/sleeve-creases/after-trace.json
python .agents/skills/verify-sleeve-creases/scripts/inspect.py \
  --input .agents/skills/verify-sleeve-creases/fixtures/before-basic.json.gz \
  --out work/sleeve-creases/before.json --trace work/sleeve-creases/before-trace.json
```

The first CLI returns0, the known bad control returns2. Treat that expected2 as a
successful negative-control assertion, while preserving the control's FAIL.
Invalid or unmeasurable input returns3, never PASS. Run the actual CLI and reopen
its JSON and Chrome Trace; unit tests alone do not establish a real caller works.

Expect161 vs0 over-limit edges and179.6579125° vs31.9020692° maxima. The visible
right-sleeve ridge is117.4297762° vs6.6209252° on an exact two-endpoint source-UV
match, despite indices374:400 changing to373:399. Fixtures have source hashes.

## Actual application surface

Original authorized owner Site:
`https://pattern-atelier-three-wasm.liushiyuxjtu.chatgpt.site/sleeve-debugger.html`.
It is a private Site; preserve that audience and use the authorized platform flow.
Its separate source checkout has `src/crease-diagnostics.mjs`,
`src/sleeve-debugger.mjs`, `src/crease-overlay.mjs`, `src/diagnostic-log.mjs`.
Do not substitute the repository's older garment cases for this Teagan control.

The flow under test is: open exact deployed debugger -> select the visible ridge
-> observe matched source UV endpoints and changed angles -> rotate and toggle
colors/normals -> download actual diagnostic and timing data -> reopen those files.

With installed Playwright and Chromium, drive the actual production origin and
record page identity, actual canvas pixels, console health, source-file hashes,
edge IDs, selection state and download contents. Test390px mobile width too.
When a Browser/MCP path is unavailable, record its exact error and use the
repository's Playwright preference with the installed Chromium. Do not install a
new browser or weaken authentication to turn a blocker into PASS.

For local artifacts, Playwright `route.fulfill` may provide exact built bytes on a
test origin without a preview server. Label that result LOCAL; it is not a live
HTTP/login check. A secure test origin supports Web Crypto for artifact binding.
Live requests must retrieve actual remote bytes with normal TLS verification;
never serve local fallback content for a failed production asset.

## Live solver logging

In the original studio, expand “袖子尖折诊断”, enable “突出袖子局部折角”, then
“重新求解并记录折角变化”. Confirm SOLVING revokes the previous result, a fresh
worker bypasses the cache, and its current-generation callbacks contain actual
iteration/fold observations. Reopen the downloaded report and trace, independently
inspect its exported geometry, and confirm logging did not mutate the final mesh.
The chart is measured iteration history for this new run, never the archived
before model's simulation history. It is not stress, pressure or calibrated force.

The original default remains2D + plain3D with both strain heat and fold overlays
opt-in. Test color off restores the original pixels, unfold pauses fold coloring,
plain3D and strain heat remain separate, reset and WebGL recovery continue working,
and invalid imports retain the prior model with a visible error.

## Evidence and verdict

Use a fresh `docs/verification/sleeve-creases-YYYYMMDD/` receipt containing the
candidate base commit and file digests, raw commands/exits, independent per-edge
comparison, actual browser/download observations, source correspondence and
separate geometry/material/fit verdicts. A successful save is read back from Git.
Keep old failures and NOT_RUN; local helpers or release status alone are not PASS.
Stop only processes created by this check and preserve failed inputs.

Runtime gotcha: JSON serializes JavaScript negative zero as0. When checking a
download, normalize only numerical zeros before canonical hashing; do not round
positions or discard source/UV/topology differences to obtain equality.
