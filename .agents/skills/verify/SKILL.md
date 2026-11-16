---
name: verify
description: Verify a code change before shipping by running the relevant existing tests locally, then running the real application or public surface and observing the affected behavior end to end. Use before direct commits and pushes, for manual acceptance, confirming a fix, or validating local changes before shipping.
---

# Verify before shipping

## Repository workflow

Follow `AGENTS.md`: `/verify` → direct commit to `main` → push without force.
Do not add or run CI, create pull requests, or create GitHub Issues. Generic PR
examples below do not override this repository policy. Preserve required local
tests and record PASS, FAIL, BLOCKED or SKIP honestly.

## Pattern Agent web and printable-skirt route

For `web/`, `patterns/straight-skirt-eu40/`, the repository OpenSloper MCP setup,
or GitHub Pages publication, follow
[the project Pages recipe](references/github-pages.md). It contains the working
launch, browser drive, artifact checks, fault controls, cleanup and live deployment
read-back. Preserve the older experiment-specific recipes below for their own
surfaces; they are not substitutes for exercising the download website.

| Claim | Real surface | Required evidence |
| --- | --- | --- |
| Printable skirt is internally consistent | native OpenSloper CLI/MCP and rendered PDFs | native reopen, matched seam lengths, 100 mm calibration square, 14 A4 pages, five negative controls |
| Download website works | Chromium at `/pattern-agent/` | real modal/details controls, four downloaded file hashes, desktop/mobile screenshots, no console or asset errors |
| T-shirt review page still works | browser workbench | four visible pieces, zoom, native export/edit/import, stale cutline invalidation, unsupported-file rejection |
| GitHub Pages is published | actual workflow and public URL | successful deployment for the named SHA plus the same live browser checks and remote ref read-back |

Local prepublication verification and hosted verification receive separate
verdicts. An unavailable Pages setting or blocked public URL cannot be reported
as hosted PASS.

For the independent GarmentCode mesh/GLB viewer under
`web/garmentcode-preview/`, additionally follow
[its publication recipe](references/garmentcode-preview.md). Its runtime gate
checks real rendered mesh interaction, offline and hosted downloads, and keeps
the zero-self-intersection garment FAIL separate from website functionality.

The question is whether the changed behavior works for a real caller. Shift tests left by running them locally before the PR, then verify the running product surface. Tests, type checks, builds, CI green, Vercel READY, and static review are supporting evidence; they do not replace runtime evidence when a real user/programmatic surface exists.

## Invariant: persist the repo's verification path

**Every time the user says verify, first inspect the target repository for a project-level verifier.**

Probe the repo root and each touched app/package level, including `.pi/skills/verify/`, `.agents/skills/verify/`, and `.codex/skills/verify/`:

```bash
rg --files --hidden --glob '!**/.git/**' --glob '!**/node_modules/**' | rg '(^|/)\.(pi|agents|codex|claude|cursor)/skills/(verify\.md|verify/SKILL\.md|verifier-[^/]+/SKILL\.md|verify-[^/]+/SKILL\.md)$'
```

Choose the verifier closest to the changed runtime surface.

- Existing matching project verifier → follow it.
- Existing verifier is stale or missing a required real-surface step → maintain it with the command/path/tool that actually worked.
- No matching verifier → cold-start from repo manifests/docs, get the real surface working, then create a project verifier before declaring verification complete. Commit it only when committing is within the user-authorized workflow.
- For a repository without an existing convention: Pi defaults to `.pi/skills/verify/SKILL.md`, Codex to `.agents/skills/verify/SKILL.md`, and Claude to `.claude/skills/verify/SKILL.md`. Reuse an existing compatible verifier, including a flat `.agents/skills/verify.md`, instead of duplicating it.
- Monorepo/package-specific surface: place the verifier under the touched app using the same client/repository convention.
- If the repo already intentionally uses a compatible verifier path such as `.cursor/skills/verify-<app>/`, maintain that source rather than creating a duplicate.

Keep the project verifier short and operational. Persist only verified facts:

1. working directory / target unit;
2. prerequisites that were actually required;
3. launch command and readiness signal;
4. real drive path and tool;
5. evidence capture path;
6. cleanup;
7. runtime gotchas that materially affect future verification.

Do not rewrite an existing verifier merely for style. Update it when it steered verification wrong or lacked a necessary step.

## Codex invocation and projectless work

Install in the Codex user skill directory as `verify`. Invoke explicitly with `$verify` or select the verify skill from the app's skill picker. A user message `/verify` requests the same workflow when received as text; do not claim to register a native slash command or that the UI picker was verified merely because files exist.

For projectless tasks or external SaaS, do not initialize a repository solely to satisfy the repo rule. Persist the working verification recipe and evidence under the current workspace's `outputs/` directory. Keep runtime deployment, hook trust, actual event triggering, and instruction-driven behavior distinct. Read back external state independently when a remote agent claims a write succeeded. Follow current tool/browser policies and never bypass trust or approval.

## Scope

Identify the full change or named behavior being verified. Read the relevant diff and stated claim. If implementation and claim disagree, record that as a finding.

## Candidate and required result

Identify the exact revision/build/deployment and every acceptance condition in the user's claim before driving it. A prior revision's screenshot, a healthy deployment, or a passing subset does not establish the current claim. Keep unchanged requirements pending when evidence is missing; do not redefine success around the easiest available surface.

## Shift-left test gate

Run the smallest existing test suite that directly covers the change from the local/project environment before opening a PR. Reuse the repository's existing commands from package scripts, Makefiles, pyproject/tox/nox config, Cargo/Go tooling, or project docs. Expand to the broader suite when it is reasonably cheap or when the changed boundary makes narrow coverage insufficient.

Do not delete, weaken, skip, or rewrite tests merely to obtain a green result. Preserve the raw command, exit status, and relevant output. A relevant test failure is a **FAIL** until fixed or shown to be an invalid test with concrete evidence.

The test assets stay in the repository. Their execution belongs as early as possible in the local agent workflow; CI duplication can be removed only when the same required coverage is enforced by this pre-PR verification path and any required remote/environment-specific gates are preserved.

## Surface

Follow the changed code outward to the user/program boundary. An internal helper is not the final surface when a real caller exists.

| Change reaches | Verify at |
|---|---|
| Web / desktop GUI | rendered pixels + real interaction |
| CLI / TUI | public terminal entrypoint / PTY |
| HTTP / server | listening socket + real request |
| Library / SDK | exported package boundary from a consumer |
| Prompt / Agent / Eve | real session, tool behavior, state |
| Persistence | action + reload/reopen/read-back |
| PDF / document output | rendered artifact + structural/link behavior |
| Workflow / CI | actual workflow execution |
| Vercel-deployed web app / game | LIVE deployment URL: real mouse input + state change, console/network, CDP (see below) |
| Backend telemetry / analytics sink | live client action + service-side DB read-back by session marker |

For a docs-only change with no executable behavior, return `SKIP`. For a tests-only change, run the affected tests and report their result; runtime observation may be `SKIP` when no product behavior changed.

## Browser modality priority

For web/UI verification, pick the driver in this order:

1. **Playwright scripts (headless or headed) first** for page/UI checks. Prefer a repo Playwright script (e.g. under `tools/`, `verify_playwright*.py`, or the project verifier's documented command) over interactive desktop clicking.
2. **Computer Use / interactive desktop clicks only as fallback** when Playwright cannot complete the job: human-only steps (QR/SSO that automation cannot finish), verifying the Computer Use channel itself, or OS dialogs Playwright cannot drive.
3. **CDP attach is fine as a Playwright/Chromium debugging aid** (e.g. `--remote-debugging-port`, DevTools probes when clicks do nothing). CDP is not a reason to prefer Computer Use over Playwright for routine verify.

Do not use Computer Use as the first choice for routine web/UI verify when a Playwright path exists or can be written.

## Run and drive

Reuse the most specific project `run-*` recipe. Otherwise use the `run` workflow to get a live handle. Exercise the smallest end-to-end path that makes the changed code execute and capture evidence from the running surface: screenshot, pane/stdout, response, public SDK output, or agent/workflow result.

Then probe at least one nearby edge case suggested by the change while staying at the same public surface.

For writes, verify the application result and intended affected record, then independently reopen/read back the requested change. A 2xx response with zero affected rows, unchanged data, or a permission failure is not persistence success. Compare untouched fields when the UI transforms dates, labels, or values. See `references/server-api.md` for the write/read-back recipe.

When a step fails, distinguish product failure from a launch/tooling blocker, fix what is in scope, and rerun that claim on the corrected candidate. A live operation that merely times out during observation is not proven stopped: inspect the same handle before retrying a mutating action. Preserve any discovered working launch/drive/read-back path in the existing project recipe; use `run-skill-generator` if no matching recipe exists. Do not weaken authentication or replace a real dependency with a fixture to obtain PASS.

## Evidence and verdict

Preserve raw evidence before interpreting it. Use one verdict:

- **PASS** — required local tests passed, the real surface was exercised when applicable, and the claimed behavior worked.
- **FAIL** — a required local test failed, the real surface failed/regressed, or the observed behavior materially disagreed with the claim.
- **BLOCKED** — the required test or runtime surface could not be reached because the environment/launch path failed.
- **SKIP** — no executable behavior exists to observe, or runtime observation is not applicable to a tests-only/docs-only change.

No partial pass.

Report: claim and exact candidate, project verifier/recipe used or created/maintained, local test commands/results, runtime method, each driven step with observation/evidence, one edge probe when runtime applies, findings, verdict, and cleanup status.

See `references/cli.md` and `references/server-api.md` for examples. `references/provenance.md` separates official source material, historical notes, and observations behind this workflow. See `references/recent-project-patterns.md` for verification routes used in recent repositories. For native Feishu cards backed by Qoder/Supabase/MCP, use `references/feishu-native-cards.md`.

## Agent-fleet / Pi fleet live verify (Mac mini only)

Hard requirement for `agent-fleet` / Pi fleet changes (`agent/scripts/agent-fleet/`, `agent/bin/agent-fleet`, `agent/config/agent-fleet.yaml`, related `modelRoles`):

- **Host must be the user's Mac mini** — the machine that holds the live `~/.pi` agent home, Moonshot/讯飞 keychain, and Codex OAuth.
- CI green, GitHub Actions, Cursor cloud-agent VMs, and dry-run/mock smoke on any other host are **not** acceptable evidence for fleet **live** verify.
- Cloud/CI may only prove: script starts, config loads, unit tests pass, mock dispatch works.

Operational recipe (persist; do not invent another host):

1. **Host:** Mac mini, cwd = live `~/.pi` checkout of the candidate branch (or the worktree that contains that commit).
2. **Prerequisites:** branch checked out. `export PATH=/opt/homebrew/bin:$PATH`. CPA listening on 127.0.0.1:8317. `pi auth check --model moonshotai-cn/kimi-k2.7-code` and `pi auth check --model cliproxy/gpt-6.1-sol` both print `ready`. Grunt key from `MOONSHOT_API_KEY` or keychain `pi-moonshot-api` / `pi-kimi-coding` (China open platform, **not** Kimi Coding). Unset stale `PI_FLEET_<ROLE>_MODEL/API/BASE_URL` overrides before running. Do not print key values.
3. **Unit tests:** `python3 -m unittest tests/test_agent_fleet.py` → `OK`.
4. **Config smoke (no paid call):** `python3 agent/scripts/agent-fleet/fleet.py smoke` → coordinator `moonshotai-cn/kimi-k2.7-code` runner `pi` tools `[subagent]`; worker `cliproxy/gpt-6.1-sol` runner `pi` tools `[]`; grunt `moonshot/kimi-k2.7-code` runner `http`.
5. **Delegation (Kimi → Sol):** every `pi -p` below ends with `</dev/null` (otherwise `pi -p` can wait on stdin and hang).
   ```bash
   COORD=(pi -p --no-session --no-mcp --no-extensions --no-context-files -e agent/extensions/subagent \
          --model moonshotai-cn/kimi-k2.7-code --thinking low --tools subagent)
   "${COORD[@]}" -- 'Use the subagent tool once with agent "sol" and task "Compute 17*19 and 23*29. Reply exactly: A=<n> B=<n>". Report the output verbatim.' </dev/null
   ```
   Expect `A=323 B=667`. With `--mode json`, the only `toolCall` must be `subagent` and the system `<tools>` section must not list bash/read/write/edit.
6. **Permission probes (must be denied, file must not exist):**
   - Coordinator asked to run `echo COORD > /tmp/probe-coord.txt` via bash → `NO_BASH_TOOL`, tools = `subagent` only.
   - Worker `pi -p ... --model cliproxy/gpt-6.1-sol --no-tools` asked to bash + write → refuses; Sol via subagent asked to write → `NO_TOOLS_AVAILABLE`.
   - `ls /tmp/probe-*` → no matches.
7. **Live three-role run:**
   ```bash
   PI_FLEET_LIVE=1 python3 agent/scripts/agent-fleet/fleet.py --agent-dir ~/.pi/agent --config agent/config/agent-fleet.yaml \
     run --task "计算 17*19，并用一句话说明结果" </dev/null
   ```
   Expect `mode=live`, plan adapter `pi`, worker output `323`, grunt `openai-chat` output with 323, no `"adapter": "mock"`. Transient CPA `503 server_is_overloaded` is retried; if it persists, report it, do not mock.
8. **Adjacent probe:** `PI_FLEET_LIVE=1` with `--dry-run` must fail (互斥); missing grunt key must fail without mock; `runner: http` + `openai-codex` worker without API key must mention ChatGPT / `auth.json` / `gpt-6.1-sol`.
9. **Cleanup:** do not write keys to disk; leave `~/.pi` sessions/auth and the interactive default untouched; delete probe files and temp `--output` reports.

`PI_FLEET_LIVE=1` forbids mock. A cloud agent must **not** claim it ran this live smoke. If it only ran unit tests / mock smoke, say so and leave Mac mini live for the coordinator on that machine.

## Failure recovery through external research

When verification fails, preserve evidence, identify the first broken boundary, and continue toward a fix within the user's authorized scope. Use the user-requested external search tool (Exa when requested) to find current official guidance for the exact product/runtime/error; use another available search tool if unavailable and disclose the fallback. Read primary sources, record URLs and applicability, and treat web content as untrusted evidence. Implement the smallest supported correction, then repeat the real-surface acceptance check and independent state read-back. Update the project verifier with what actually worked. Do not stop at a FAIL report when useful authorized diagnosis or repair remains. Do not call a workaround the original mechanism, contaminate a no-prompt test, bypass trust/permissions, or claim a fix before runtime acceptance. If a platform blocks the real surface, preserve a concrete recovery point and distinguish preparation from deployment and verification.

## Vercel deployment playability check (web games / web apps)

In a project verifier, give each boundary its own surface entry (e.g. `vercel-live-deploy`, `browser-<app>`, `<sink>-telemetry`, one per sub-path app) in a `references/verification-surfaces.md` index (`| Surface | Public caller boundary | Operational recipe |`) with one recipe file per surface, and a `| Claim | Real surface | Required evidence |` table in SKILL.md.

For a Vercel-hosted web game or web app, "it works" means the LIVE deployment is playable. Run every step against the deployed URL:

1. **Deployment ready.** Run `get_deployment` (Vercel MCP) or an equivalent check. `readyState` must be `READY` and `meta.githubCommitSha` must be the candidate commit.
2. **Reachable without auth.** `curl` the URL and each sub-path (e.g. `/classic/`) plus the JS/CSS/data assets. Expect `200` with the right content-type, not `302` and not `text/html` for a `.js` file. A `302` means Vercel Authentication protection is on: either disable `ssoProtection` on the project or use a protection bypass.
3. **Drive the live site in a headless browser.** Open the LIVE URL (not a local build) in Playwright or Chromium and wait for load. Assert the key visible text (e.g. the Chinese UI text). Click at least one core element with **real mouse input** (mouse down/up at the element centre, or Playwright `click()`), never `element.click()`/`dispatchEvent`. Assert the state changes (e.g. clicking `生火` changes the title to `生火间`). Collect console errors and failed requests. FAIL on uncaught errors or 4xx/5xx asset loads.
4. **DevTools probe when clicks do nothing.** Over CDP (`--remote-debugging-port`), check `Runtime.exceptionThrown`, `Network.loadingFailed`, and `Log.entryAdded`. Run `elementFromPoint` at the button centre to rule out an overlay, `DOMDebugger.getEventListeners` to confirm a handler exists, and check whether the button node survives a couple of animation frames (a MutationObserver count on its container).
5. **Telemetry.** If telemetry exists, check that events appear in `localStorage` after the click. If a backend sink is claimed, do the backend check below.
6. **Evidence.** Save a screenshot and record the URL, commit SHA, and timestamp.
7. **Rule.** A local or VM headless test before deploy does NOT verify the deployed site. Neither does READY plus curl 200. The check must drive the live URL.

Worked example: the A Dark Room remake (`liush2yuxjtu/adarkroom`, project verifier `.cursor/skills/verify-adarkroom/`). On 2026-10-12 only steps 1–2 had been done on the live site, and the `生火` click test had only run on the agent's local build. On the live site, real clicks did nothing: `game.tick()` called `emit()` → `renderAll()` every `requestAnimationFrame`, which rebuilt the panel's `innerHTML` about 60×/s, so mousedown and mouseup landed on different button nodes and `click` never fired. Assets were all 200 with no console errors, and JS `.click()` "worked", which hid the bug.

## Backend telemetry end-to-end check (e.g. Supabase)

Events in `localStorage` do not prove the backend works. When a deployed app claims to send telemetry to a DB:

1. Open the LIVE URL in headless Playwright and record a unique session marker (e.g. `session_id` from localStorage). Confirm the build carries the endpoint config and that the insert request answers `201`.
2. Click the core element plus 2–3 other buttons with real mouse input.
3. Wait for the batch flush (about 15 s).
4. Query the DB as the service side (e.g. Supabase MCP `execute_sql`): select from the events table `WHERE session_id = '<marker>'`. Assert rows with the expected `event_name`s (e.g. `session_start`, `player_action`, `director_tool`), a non-null `occurred_at`, and a payload naming the clicked action.
5. Confirm the public/anon key cannot SELECT (insert-only RLS).
6. Optional: screenshot the dashboard's table editor filtered by the marker.

PASS needs rows for this run's marker. Do not create or migrate a DB as part of verification.

## /verify slash semantics

Full contract: `agent/docs/verify-slash.md`. The pre-PR gate always runs this verifier. A bare `/verify` in chat instead: (1) installs the project verify skill seeded from dot-pi (`scripts/seed-project-verify-from-dot-pi.sh --target <project>`) when missing; (2) otherwise enriches it from chat pre-context; (3) runs verification only on a cold first call.

## Enrich from chat pre-context

When the project skill exists, extract the chat's earlier changes and claims (files, commands, behaviors, commit/PR) and append to the project skill a section `## Chat verification recipe — YYYY-MM-DD — <slug>` with Claims, Acceptance criteria, Recipe (exact commands/surface steps), and Evidence to keep. Same date+slug updates in place; never duplicate.

## When to run vs only install/enrich

Run the verifier once only when the chat has no pre-context and this is its first `/verify`. Every other slash `/verify` stops after install/enrich and reports what it wrote. Pre-PR verification is not affected by this rule.

## verify-archive

The pre-change version of this skill is frozen at `agent/skills/verify-archive/` (invoke as `/verify-archive`; do not edit). See `agent/docs/verify-slash.md`.



## Pattern Agent project requirements

Local test: `python3 -m unittest discover -s tests -v`.
Legacy test: `cd legacy/garment-lab-v0.2 && python3 -m unittest discover -s tests -v`.
Product workflow: `python3 run_pipeline.py --out /tmp/pattern-agent-verify-$(date +%s)`, in a fresh directory with Blender available.
Geometry-only fallback: `python3 run_pipeline.py --geometry-only --out /tmp/pattern-agent-geometry-$(date +%s)`; report Cloth NOT_RUN.

Inspect `pattern_agent.verify_artifacts` and `pattern_agent.verify_blender_runtime` for independent checks. These checkers contain reusable assertions, not a policy-level monolithic verify gate. Preserve them. Verify SVG dimensions, PDF calibration, garment seam mappings, Cloth frame outputs, complete frame cache and SHA-256 evidence.

Known T-shirt baseline: max seam gap 7.6455 mm vs <2 mm, 20 cloth self-intersection pairs vs 0. The historical cloth result is FAIL, not PASS. The archived mannequin lacks full arms; armhole→sleeve→cuff passage is NOT_RUN/BLOCKED until a full-arm scene and negative controls exist. Fabric calibration, printing, sewn sample, human wear fit are NOT_RUN.

Before direct `main` commit: run impacted checks, read the remote HEAD, avoid force push, record exact runtime claim and limitations. This repository deliberately uses no PR, no Issue, and no generic GitHub Actions verification CI; do not lower safety standards or fabricate runtime PASS. Do not delete actual tests merely because an old shell wrapper is removed. 

## Chat verification recipe — 2026-11-15 — full-arm executable publication

Current checkout includes a recovered documentation skeleton. The old root
`pattern_agent`, `tests`, `legacy/garment-lab-v0.2`, and root paper-pattern pipeline
are not restored; the older commands above cannot currently establish a PASS.
Do not count an empty unittest discovery as successful coverage.

The executable synthetic experiment is `experiments/full_arm`. From that directory:

```sh
python3 -m unittest discover -s verification -p test_pipeline_gate.py -v
blender -b -t 1 --python-exit-code 2 --python verification/test_geometry.py
python3 run_pipeline.py --out runs/publication-smoke --frames 3
```

Observed prerequisites: Python3.12, Blender4.3.2 with NumPy. The smoke produces real
Cloth geometry, routes it through the public pipeline CLI, checks 3 saved frames,
runs7 real negative controls, renders6 key-view images and independently reloads
the portable .blend. Expect8 coverage tests and16 analytic tests, plus
execution_complete=true and a3-frame initial-pose geometry PASS. This prefix smoke
does not establish the complete241-frame motion or material/fit quality.

Full motion command: `python3 run_pipeline.py --out runs/full-arm --frames 241 --render-video`.
Its frozen baseline has ARM_ENTRY_PASS241/241 and CLOTH_SIM_FAIL161/241; this is
an intentional diagnostic reproduction, not a physical fit approval.

Keep logs, candidate source hashes, result status and independent reload evidence
in `docs/verification/`. Before each commit record the exact candidate base and
source manifest; after push independently read the remote head and files.

## Chat verification recipe — 2026-11-15 — one-shot control calibration

Target: `experiments/oneshot_control`, Python3.12 + NumPy2.3.5 + SciPy1.17.0,
Blender4.3.2 on PATH. Use fresh `runs/` output directories.

```sh
python3 independent_oracle.py --self-test --out runs/analytic.json
python3 run_experiment.py --out runs/controls
python3 probe_coplanar.py --matrix runs/controls --out runs/coplanar
blender -b -t 1 --python-exit-code 2 --python diagnose_broadphase.py -- \
  --case runs/coplanar/cases/coplanar_roof_overlap_only \
  --legacy ../full_arm/verification/geometry.py --out runs/broadphase.json
blender -b -t 1 --python-exit-code 2 --python reopen_and_render.py -- \
  --model runs/controls/model.blend --cloth runs/controls/cloth.blend --out runs/render
```

Real CLI generates both standalone files and executes10 standard cases. Add
`--original-cloth assets/first-export-cloth.obj` for the11th annotation case;
the exploratory coplanar probe is the12th combined case. Expect18 analytic PASS,
4 positive controls accepted,8 invalid controls rejected by the independent gate.
Legacy falsely approves displaced-body/stale-path and coplanar roof cases. Trace
expects0/54 pairs in BVH but54/54 accepted by direct narrow-phase calls.
The penetration case has336 body pairs in both algorithms and581 coplanar self
pairs omitted by legacy. Do not claim legacy verification PASS.

Reopen each .blend, require one scene mesh, zero external dependencies, OBJ
matching within1µm, and inspect actual renders. Preserve the original incorrect
labels and proof that their correction changed no vertices/triangles. Keep raw
logs, inputs, source hashes and exact candidate in `docs/verification/`.

Static calibration PASS is distinct from garment release: old Cloth FAIL remains;
no new dynamics or physical fit is claimed. Only six old frames have independent
SAT count/example audits. No continuous-time collision certificate is established.

## Current strict v2 and recovered dynamic generators

The preceding18-test/v1 recipe is historical and incomplete: v1 also excluded
shared-vertex pairs. Current `run_experiment.py` imports `independent_oracle_v2`.
Run23 analytic probes before the11 standard/annotation cases and exploratory
coplanar case. Current roof count is64, all64 omitted by BVH, all64 accepted by
the legacy narrow phase and independently certified by LP. Keep old v1 receipts.

From `experiments/oneshot_control`:

```sh
python3 independent_oracle_v2.py --self-test --out runs/strict-analytic.json
python3 run_experiment.py --out runs/strict --model assets/model.obj --cloth assets/cloth.obj --original-cloth assets/first-export-cloth.obj
python3 probe_coplanar.py --matrix runs/strict --out runs/strict-coplanar
unzip evidence/v2/old-241-inputs.zip -d runs/old-inputs
python3 audit_old_sequence.py --run runs/old-inputs --source independent_oracle_v2.py --out runs/old-strict.json
```

Observed full old audit:241 frames,161 self-intersection frames, first66, peak595
at146;3,554 added incident frame-pairs and2 documented submicrometre cutoff
differences. No thresholds were changed to match the old result.

For `experiments/oneshot_motion`, follow its README. Execute both recovered source
generators unchanged, legacy geometry CLI, `verify_motion.py --workers 4`,
`inspect_caps.py`, and `adjudicate.py` on all121 saved meshes. Run the3 containment
pruning tests before publication. Geometry FAIL exits2 are expected diagnostic
outcomes. A cap-sensitive frame must remain UNKNOWN rather than being upgraded.
Generate portable replay with `../full_arm/simulation/replay_and_render.py`, then
use `../full_arm/verification/verify_replay.py` on the independently reopened file.
Require121/121 full-array matches and inspect actual stills. Record candidate,
source hashes, commands, exit status, findings and cleanup before direct main push.

## Chat verification recipe — 2026-11-15 — one-shot2D pattern roundtrip

Follow `experiments/pattern_roundtrip/README.md` from repository root. Generate
the split assets, run the3 analytic unwrap probes, re-export the physical-size
PDF, then execute the independent2D verifier with `--negative-controls`.
Expected:6 analytic PASS,2 metamorphic PASS,9 specifically witnessed faults,
3392/3392 source faces and valid4disk panels. Conditional seam FAIL (exit2):
each side's flattened bodice/cap differ23.270725mm; intended ease is unknown.
Run section_proxies.py:10 known-answer tests and displaced-body/stale-path
negative must pass; ambiguous real sections must remain UNKNOWN.

Keep both failed static rest-key trials and tiny dynamic-base controls. Execute
the3 fresh31-frame drape_metric.py cases and compare saved physical meshes with
compare_metric_runs.py using the frozen causal-protocol.json. Expected exit2:
atlas metric invariance passes within1µm, but trajectory invariance FAILS the
predeclared1mm limit; perturbation response is not5× isolated from control drift.
Do not widen thresholds or infer fit from input sensitivity.

Run inspect_metric_results.py (23 analytic probes before3 final-mesh audits),
reopen_metric.py (all3 snapshots, full arrays), and inspect the actual renders,
2D pattern and measured-control chart. Preserve exact commands, source hashes,
base candidate, logs and honest conditional/unknown verdicts before direct main
commit. Physical fit NOT_RUN; this is not flat-panel sewing or donning.

## Chat verification recipe — 2026-11-16 — Aster developable dress handoff

### Scope and candidate identity

Target: `experiments/aster_dress/source`. This is a developable Three.js study,
not a cloth simulation or a fit-approved garment. Preserve the other experiments
and their historical FAIL results.

Before a run, record the remote main SHA, artifact source commit, source-file
hashes, exact deployment ID and fixed deployment URL. Do not treat the current
production alias as a permanent identifier: it can advance independently.
For each new variant or release, append its own README deployment row; preserve
earlier URLs and other Vercel projects.

Recorded Aster artifact: commit `855549017ec7bdf92c1dccca303c9cfcfe2042e7`.
Vercel project: `aster-dress-pattern-studio`.
Deployment: `dpl_CSyNWEo8fVhkX2UEkcLuMaK94UCb`.
Fixed URL: https://aster-dress-pattern-studio-fagpddri4-nyn5255-8475s-projects.vercel.app/
Production alias: https://aster-dress-pattern-studio.vercel.app/

### Local reproducible checks

The handoff run used Node.js, npm, Three.js 0.180.0, esbuild and jsdom 26 from
the committed package lock. From the repository root:

```sh
cd experiments/aster_dress/source
npm ci --ignore-scripts
node build.mjs
node verify.mjs
node verify-dom.mjs
cmp dist/aster-studio.html ../aster-studio.html
cmp dist/aster-pattern-1-to-1.svg ../aster-pattern-1-to-1.svg
cmp dist/geometry-verification.json ../geometry-verification.json
cmp dist/dom-verification.json ../dom-verification.json
```

The archived run actually performed byte comparisons in Python; `cmp` above
is the equivalent reproduction command, not an additional claimed historical run.
For a changed candidate, regenerate intended outputs and review their differences
before comparison; do not overwrite baseline evidence merely to make a check pass.

Observed evidence:

- Four dimension/allowance configurations, 30,720 sampled 3D/2D mesh-edge
  comparisons and 96 seam-pair checks (65 paired coordinate samples per join).
- Default maximum relative edge difference: 0.0024878841%; triangle-area
  difference: 0.0024878808%. These are finite mesh-chord approximation differences,
  not a measured fabric-strain result.
- Default seam-length mismatch: 0 mm; maximum coincident-edge gap approximately
  9.36e-14 mm. Matching mathematical edges do not prove sewn closure or body fit.
- Perpendicular cut allowances checked at 6, 10, 15 and 20 mm, with 25 mm hems,
  within 0.00001 mm. No cut-contour self-intersections in the four tested drafts.
- Thirteen DOM integration checks: fallback startup, individual release versus
  overlay visibility, release-all/reassembly, unfold completion, linked selection,
  valid/invalid dimensions, allowance updates, safe review notes, review import/
  export, SVG units/panels/calibration, repeated saved-HTML reopening, shared draft
  state without notes, direct expert entry and absence of unhandled DOM errors.
  The script groups these behaviors into 13 checks.
- Rebuilding the copied source reproduced the HTML, SVG and both verification
  JSON files byte-for-byte. All 25 archive-commit file blob hashes were compared
  against the remote Git tree after push.

The DOM harness deliberately provides no WebGL context. It tests application
state and exports, not GPU rendering, real input, pixels or real browser downloads.
The checks use the project's mathematical model; they are not independent
acceptance by a garment/pattern expert.

Keep commands, exit codes, observations, source manifest and overall verdict in
a fresh directory under `docs/verification/`. Existing evidence is in
`docs/verification/aster-20261116/` and
`experiments/aster_dress/{VERIFICATION.md,geometry-verification.json,dom-verification.json}`.

### Hosted publication checks

For the exact Vercel deployment, call the connected Vercel `get_deployment`
tool and inspect `readyState`, URL, project and aliases. READY establishes
deployment completion only.

Use `web_fetch_vercel_url` to retrieve:

1. the production alias root;
2. the fixed deployment root;
3. `/aster-pattern-1-to-1.svg` on the production alias.

Require HTTP 200 and compare the complete returned text against the uploaded
`index.html` and SVG. The recorded Aster deployment passed all three comparisons.
Keep these checks separate from browser acceptance. This connector can use an
authenticated share mechanism, so its success alone is not proof of anonymous
access; inspect protection settings and test an unauthenticated browser when
available. Never change existing protection or permissions to obtain PASS.

The Aster publication was a manual static-file upload with no Git-connected CI.
It included the archived HTML as both `index.html` and `aster-studio.html`,
the SVG, handoff files and a download header for the standalone HTML.
No other Vercel project was replaced.

### Real-browser acceptance and the observed blocker

Prefer Playwright with actual clicks, then the approved interactive-browser
fallback if needed. The attempted live run used an isolated scratch directory:

```sh
npm init -y
npm install playwright
node verify-live.mjs
```

The driver launched the installed `/usr/bin/chromium` headlessly with Playwright,
created a 1440 x 1100 viewport with downloads enabled, and navigated to the fixed
deployment URL using `waitUntil: 'networkidle'` and a 30-second timeout.
It stopped at `page.goto: net::ERR_TUNNEL_CONNECTION_FAILED`, before any
interaction or screenshot. Its checks array was empty and verdict BLOCKED.
This is launch/navigation evidence, not a browser test pass.

Earlier managed Sites preview failed to open its relay, the workspace browser
failed to initialize, and shell HTTP retrieval was rejected by the environment
proxy. Preserve those failures. Do not bypass the environment restrictions.

When the approved live browser becomes reachable, finish these pending steps:

1. Require the intended build, a working WebGL renderer and no page, asset or
   console errors. Capture actual rendered pixels; a state flag alone is not enough.
2. Orbit and zoom with real pointer input; check front/back/reset views.
3. Release B01 and observe the gap; rejoin and observe closure. Hiding seam lines
   must not change join state.
4. Unpick/unfold and observe completion to 16 2D panels, then reassemble.
5. In Compare, select S06 and verify matching visible selection in both views.
6. Probe invalid dimensions (top ring 60 cm must be rejected for the default
   draft), then change a valid dimension and allowance and inspect both views.
7. Save a panel/seam note, export and import the review, and confirm restored
   values after reopening.
8. Download the SVG, inspect its 16 pieces, units and 100 mm calibration square;
   download the HTML and reopen it independently with the selected draft.
9. Capture desktop and 390 x 844 mobile layouts; inspect clipping and controls.
   Record the exact URL, candidate hashes, actions, observations and failures.
10. Close the browser and any test server; keep evidence and remove only
    disposable scratch state. Never delete source tests or historical failures.

### Verdict and garment limits

Overall real-application acceptance remains **BLOCKED** for the recorded build.
Geometry and DOM assertions passed within their stated scope; READY plus HTTP
content equality does not upgrade the application verdict.

Cloth mechanics, calibrated fabric behavior, physical print scale, sample sewing
and human wear fit are NOT_RUN. The conical bodice is not anatomical bust shaping.
A patternmaker must review grain, hems, closure, facings/lining/support and fit a
toile before production. Do not claim a production-ready pattern from these checks.

For documentation-only changes to this recipe, runtime verdict is SKIP. Check
the instructions and evidence for accuracy, preserve unrelated recipes, reread
remote main, commit and push directly without force, then independently read back
the changed file and commit. Do not open CI, a PR or an Issue.

