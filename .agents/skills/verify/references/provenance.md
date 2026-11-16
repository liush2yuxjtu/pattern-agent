# Upstream and adaptation

Fork source: [dot-pi meta verify](https://github.com/liush2yuxjtu/dot-pi/blob/924bf755028d6b0fc6096c3fcf4d9c97f87a7693/agent/skills/verify/SKILL.md),
commit `924bf755028d6b0fc6096c3fcf4d9c97f87a7693`.
Also inspected its `agent/docs/verify-slash.md`, project seed template and seeder.
The seeder alone is a thin pointer; this project retains the operational meta
workflow locally so access to private dot-pi is not required to use it.

Inherited: verifier discovery, exact candidate and acceptance conditions, local
test gate, real caller boundary, browser modality, independent write/read-back,
edge probe, evidence, cleanup and PASS/FAIL/BLOCKED/SKIP contract.

Adaptations: direct-main/no-CI policy replaces upstream PR language; project
recipes move to one file per boundary with the upstream-prescribed surface index
and claim table. Enrichment updates those recipes instead of appending to SKILL.md.
Unrelated fleet, telemetry and other-project examples are omitted. Historical
Pattern Agent recipes and the concurrent GarmentCode route are preserved.
A Claude directory symlink shares the canonical Codex skill without a drifting copy.
No command-menu/runtime discovery is claimed from file placement alone.

## Anthropic primary guidance read on 2026-11-16

[Official Claude Code skills documentation](https://code.claude.com/docs/en/skills):
- “Run and verify your app” documents bundled `/run`, `/verify` and
  `/run-skill-generator`. Verification drives the running app; tests/type checks
  alone are insufficient. A project recipe is recorded at
  `.claude/skills/verify/SKILL.md` and maintained when it steers a run wrong.
- “Add supporting files” recommends a short SKILL.md (under 500 lines) with
  linked supporting files loaded as needed.
- “Choose where skills load” documents project discovery and symlinked skill
  directories. This is the basis for the shared Claude entry point.
- “Run your checks before each commit” describes version-dependent Claude
  behavior (v2.1.286+). Repository AGENTS.md remains the explicit gate here;
  we do not assume the installed client implements that behavior.

These are documented implementation contracts, not a claim to have inspected
Anthropic's private bundled prompt source. dot-pi remains the source of this fork.
