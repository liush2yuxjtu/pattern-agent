# Subagent description hill climb — 2026-11-17

This run used independent subagents with fresh context to judge routing from one skill metadata card. It is a **surrogate**, not Claude Code triggering, Skill/Read event evidence or full skill execution. Native evaluation remains **BLOCKED**.

| Candidate | Development (24 cases, one pass each) | New holdout (24 cases × 3 agents) | Description characters |
| --- | --- | --- | --- |
| v0 original | 24/24 | 72/72 | 175 |
| v1 | 24/24 | not evaluated | 176 |
| v2 | 24/24 | not evaluated | 505 |
| v3 | 24/24 | not evaluated | 623 |
| v4 proposed | 24/24 | 72/72 | 155 |

v4 explicitly covers continuation, fitting audits and slider/mesh/export consistency. It is 20 Unicode characters shorter (11.4%). **No routing accuracy improvement was observed.** Character reduction is not a token, latency or cost measurement. The installed SKILL.md description and skill package retain v0 pending native evidence; v4 is saved as a candidate.

## Procedure

1. Four fresh-context subagents each received one blinded candidate and24 development queries, without labels. Each returned explicit Boolean routing decisions and scope reasons.
2. An independent optimizer saw development evidence only and proposed v4. A fifth independent routing pass checked v4 on the same development queries.
3. Before final evaluation, the selection rule and SHA256 of a new24-case holdout were recorded. The holdout was created by a separate agent that was instructed not to read prior queries or descriptions. v4 was selected by development correctness, then shorter character count.
4. Six fresh-context agents each saw only one description and shuffled holdout queries: three runs for v0 and three for v4. No labels or candidate IDs were provided. Final labels were not used to revise candidates.
5. Deterministic scoring rejected missing/duplicate IDs and non-Boolean values; an independent agent audited the calculations and limitations.

The optimizer never received holdout files. The primary orchestrator prepared files programmatically and aggregated results. Isolation was by instructions and fresh context, not filesystem access controls. All agents inherited the same session model family; no controlled model diversity or random seed is claimed. The holdout contains24 unique requests, not72 independent requests per candidate. A single-card prompted judgment may differ materially from real selection among installed skills. All results saturated on these small synthetic sets.

## Evidence and reproduction

- [Structured benchmark](benchmark.json)
- [Selection protocol](raw/selection-protocol.json), [proposal rationale](raw/notes.md), [fresh holdout rationale](raw/holdout-notes.md)
- [Raw labeled queries, blinded inputs, predictions and maps](raw/)
- [Independent audit](raw/audit.md)
- [Verification receipt](receipt.json)
- [Native runtime blocker](native-readiness.json)

From repository root, reproduce a score using actual saved decisions:

```sh
python tools/skill_evals/score_surrogate.py \
  --labels docs/verification/garment-body-subagent-hillclimb-20261117/raw/holdout-labels.json \
  --observations docs/verification/garment-body-subagent-hillclimb-20261117/raw/holdout-output-A.json \
  --out work/skill-evals/reproduced-surrogate-score.json
```

The scorer reproduces arithmetic only; running new routing agents requires the agent runtime. The original native runner and its untouched outer holdout remain separate. No Claude-native score is inferred from this experiment. Stop after one proposal: no remaining classification errors distinguish candidates, and final labels are now disclosed.
