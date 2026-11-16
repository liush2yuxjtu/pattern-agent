# Verify skill fork verification — 2026-11-16

Candidate base: `29a3c07fa91887e768c52f32dca37833a3114adf` plus the documentation
and Claude symlink changes in this commit. Upstream dot-pi:
`924bf755028d6b0fc6096c3fcf4d9c97f87a7693`.

Invoked the project verify workflow for this documentation-only refactor.
Inspected the current AGENTS.md, upstream meta verifier, slash contract, seed
template/script, existing project verifier and both existing surface references.
Read official Anthropic skills documentation; source and adaptations are recorded
in the skill's provenance reference.

Checks performed:
- Resolved every Markdown link in the changed skill files against the complete
  candidate Git tree: zero missing local targets.
- Checked 11 surface-index entries and direct links from the meta claim table.
- Meta SKILL.md is below the official 500-line recommendation.
- Confirmed Claude symlink resolves to the canonical .agents/skills/verify folder.
- Preserved existing github-pages.md and garmentcode-preview.md blobs unchanged.
- Compared extracted legacy/full-arm/control/motion/roundtrip recipes with the
  previous skill; commands and historical FAIL/UNKNOWN/NOT_RUN remain.
- Split Aster numeric, browser, export and deployment boundaries. Historical
  observed checks remain distinct from pending acceptance steps.
- No application, test, deployment, CI or permissions changes.

Runtime verdict: **SKIP** (documentation and skill routing only). No fresh garment,
browser or deployment PASS is claimed. Native Claude/Codex skill discovery was
not exercised in a new client session; file routing was checked structurally.
The recorded Aster real-browser BLOCKED and physical fit NOT_RUN are unchanged.

Publication procedure: read fresh main, create a commit on the inspected parent,
update main without force using an expected-SHA lease, independently read back
the committed Git tree. No PR, Issue or CI verification.
