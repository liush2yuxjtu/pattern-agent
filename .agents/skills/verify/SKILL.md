---
name: verify
description: Verify a code change before shipping by running the relevant existing tests locally, then running the real application or public surface and observing the affected behavior end to end. Use before every direct commit and push, manual acceptance, confirming a fix, or validating local changes before shipping.
---

# Verify before shipping

Project fork of dot-pi's meta-level verifier, pinned and adapted as described in
[provenance](references/provenance.md). Canonical source: `.agents/skills/verify/`;
Claude discovers the same directory through `.claude/skills/verify`.

Follow root `AGENTS.md`: local `/verify` → direct commit to `main` → non-force push.
No CI, PRs or Issues. Existing publication receipts are evidence, never a test gate.
Read only the applicable recipes from the [surface index](references/verification-surfaces.md).

| Claim | Real surface | Required evidence |
| --- | --- | --- |
| Aster developability and seam arithmetic | [aster-geometry](references/aster-geometry.md) — local model assertions and rebuilt artifacts | numeric results, allowances, source hashes; no fit claim |
| Aster 3D/2D controls | [browser-aster](references/browser-aster.md) — rendered WebGL and real pointer input | pixels, state transitions, edge probe, console/network |
| Aster usable review and pattern files | [aster-pattern-export](references/aster-pattern-export.md) — download, reopen, measured SVG/HTML/review | 16 pieces, units/calibration, restored review |
| Aster Vercel publication | [vercel-live-deploy](references/vercel-live-deploy.md) — exact deployment and anonymous live URL | project/build identity, content, live browser evidence |
| Printable skirt and download workbench | [github-pages](references/github-pages.md) — OpenSloper CLI/MCP, PDFs, live Pages browser | native reopen, calibration, real downloads |
| GarmentCode preview | [garmentcode-preview](references/garmentcode-preview.md) — GLB/downloaded HTML and live browser | mesh pixels, rotation, hashes; garment FAIL separate |
| Full-arm simulation | [full-arm](references/full-arm.md) — pipeline CLI and independently reopened Blender | saved frames, negative controls, renders |
| Strict static geometry controls | [oneshot-control](references/oneshot-control.md) — experiment CLI and independent oracle | 23 analytic probes and strict fault controls |
| Recovered motion | [oneshot-motion](references/oneshot-motion.md) — saved meshes and independently reopened replay | 121 full-array matches, UNKNOWN retained |
| 2D roundtrip and metric response | [pattern-roundtrip](references/pattern-roundtrip.md) — physical-size PDF, independent verifier, replay | negative controls, seam/trajectory FAIL retained |
| Anatomical pose and centimetre editor | [human-studio](references/human-studio.md) — actual skinned mesh, measured dimensions, exported OBJ/GLB | browser input, independent tape/skin math, persistence and units |
| Actual garment six-image case | [product-case](references/product-case.md) — native generation, anatomical fit and four-stage visual review | source hashes, actual overlays, editable model handoff and live downloads |
| Apparel body skill and trigger evals | [skill-evals](references/skill-evals.md) — shipped helper CLIs and actual Claude routing | helper controls, package readback, native events or BLOCKED |
| Fitted T-shirt source and visual preview | [fitted-tshirt](references/fitted-tshirt.md) — real WebGL, downloaded archive and rebuilt mesh | source hashes, real controls and fallback; physical fit NOT_RUN |
| Prototype package reference page | [prototype-package](references/prototype-package.md) — actual diagrams, JSON-backed examples and saved source downloads | original file digests, two responsive workflows, unchanged existing pages |
| Profile-bounded DXF conversion function | [dxf-service](references/dxf-service.md) — raw HTTP, file upload and actual generated GLB | repeatable output, input changes, rejection, offline/mobile controls; fit NOT_RUN |
| Style3D MCP discovery and garment integration | [style3d](references/style3d.md) — read-only CLI and actual Studio GUI | real tool schemas and measured project operations; client fixture tests separate |
| Corrected DXF sewing connections | [dxf-seams](references/dxf-seams.md) — independent source/UV/topology/intersection reopener on actual GLB | 15 sewn pairs, four intentional openings, source edits and fault controls; material/fit NOT_RUN |
| Historical T-shirt claims | [legacy-cloth](references/legacy-cloth.md) — archived evidence; unavailable legacy runtime | known FAIL and NOT_RUN limitations |

The question is whether the changed behavior works for a real caller. Shift tests left by running them locally before the commit, then verify the running product surface. Tests, type checks, builds, CI green, Vercel READY, and static review are supporting evidence; they do not replace runtime evidence when a real user/programmatic surface exists.

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

Run the smallest existing test suite that directly covers the change from the local/project environment before committing. Reuse the repository's existing commands from package scripts, Makefiles, pyproject/tox/nox config, Cargo/Go tooling, or project docs. Expand to the broader suite when it is reasonably cheap or when the changed boundary makes narrow coverage insufficient.

Do not delete, weaken, skip, or rewrite tests merely to obtain a green result. Preserve the raw command, exit status, and relevant output. A relevant test failure is a **FAIL** until fixed or shown to be an invalid test with concrete evidence.

The test assets stay in the repository. Their execution belongs as early as possible in the local agent workflow; this repository forbids CI; preserve required local coverage.

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
| Vercel-deployed web app / game | LIVE deployment URL: real mouse input + state change, console/network, CDP diagnostics |
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

For writes, verify the application result and intended affected record, then independently reopen/read back the requested change. A 2xx response with zero affected rows, unchanged data, or a permission failure is not persistence success. Compare untouched fields when the UI transforms dates, labels, or values. 

When a step fails, distinguish product failure from a launch/tooling blocker, fix what is in scope, and rerun that claim on the corrected candidate. A live operation that merely times out during observation is not proven stopped: inspect the same handle before retrying a mutating action. Preserve any discovered working launch/drive/read-back path in the existing project recipe; use `run-skill-generator` if no matching recipe exists. Do not weaken authentication or replace a real dependency with a fixture to obtain PASS.

## Evidence and verdict

Preserve raw evidence before interpreting it. Use one verdict:

- **PASS** — required local tests passed, the real surface was exercised when applicable, and the claimed behavior worked.
- **FAIL** — a required local test failed, the real surface failed/regressed, or the observed behavior materially disagreed with the claim.
- **BLOCKED** — the required test or runtime surface could not be reached because the environment/launch path failed.
- **SKIP** — no executable behavior exists to observe, or runtime observation is not applicable to a tests-only/docs-only change.

No partial pass.

Report: claim and exact candidate, project verifier/recipe used or created/maintained, local test commands/results, runtime method, each driven step with observation/evidence, one edge probe when runtime applies, findings, verdict, and cleanup status.


## Install, enrich, and run

Retain dot-pi's two entry points. The commit/push gate always runs applicable
verification. A bare `/verify` with earlier chat work installs/enriches the recipe;
a cold first `/verify` also runs once. An explicit request to run checks runs them.
For enrichment, update the matching surface file with claims, acceptance criteria,
exact commands, evidence and cleanup. Update the index and claim table if the
boundary is new; do not append run logs or dated project recipes to this meta file.
Keep dated outcomes under `docs/verification/` and link them from the recipe.
Never overwrite another surface or silently change a historical FAIL/BLOCKED.

## Failure recovery

Preserve the first broken boundary and diagnose within authorized scope. Consult
current official documentation when needed, record its URL and applicability,
then rerun the affected claim. Do not bypass trust, authentication or environmental
restrictions, change protection settings, weaken thresholds, or replace a real
surface with mocks to obtain PASS. Record a concrete recovery point if blocked.
