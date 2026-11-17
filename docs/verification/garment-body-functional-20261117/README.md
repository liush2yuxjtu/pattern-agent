# Executed garment-body functional evaluation — 2026-11-17

[Review current iteration on GitHub Pages](https://liush2yuxjtu.github.io/pattern-agent/garment-body/eval.html) · [First iteration](https://liush2yuxjtu.github.io/pattern-agent/garment-body/iteration-1.html)

This follows the pinned Anthropic Skill Creator execution → independent grading → official aggregation/viewer → instruction revision → fresh old/new rerun workflow. These are actual file and browser executions by session subagents, **not Claude-native trigger tests**. Synthetic controls cover three functional sub-tasks; full six-image generation quality, real anatomical accuracy and physical garment fit remain **NOT_RUN**.

| Iteration | Candidate | Baseline | Frozen/expanded checks |
| --- | --- | --- | --- |
| 1 | v0 with skill:18/18 | no skill:18/18 | Three cases, six checks each |
| 2 | v1 cache guard:19/19 | frozen v0:18/19 | Original18 + one prospective cache regression |

The official second-iteration benchmark averages pass fractions across the three cases:1.0000 vs0.9524 (SD0 vs0.0825). This differs from pooled assertion counts because the viewer case has seven assertions. There is one execution per configuration/case, not three repetitions. No statistical superiority or production reliability is claimed.

## The hill-climb step

Independent Chromium inspection found that both first-iteration viewers accepted cached height170.5 while their integer-step range displayed171; geometry and label retained170.5. This was an extra finding, not a retroactive change to the original six viewer grades. The revised skill explains type/range/step normalization and one shared state for controls, labels, actual vertices and export. The second iteration repeats all three tasks with fresh-context candidate-v1 and frozen-v0 agents. Grader assertions were hidden from those executors; identical task prompts and file inputs were used between configurations. Five dev/sibling off-step cache probes all pass in v1 and fail in old-v0 outputs.

The narrow body-text improvement was adopted. Its trigger description remains the original v0; the previously proposed shorter description is not substituted. **Native Claude triggering is still BLOCKED**, separately, because its runtime is absent.

## Qualitative issues remain visible

- The v1 viewer output lacks viewport metadata: a real375px mobile device uses a981px desktop CSS layout. This is a separate recorded quality failure, not concealed by its no-overflow check. It also fixes maximum-height head clipping.
- The v1 fit output calls a search-outline approximation exact, though it differs from triangle rasterization by two pixels per view. Actual final exported masks and reported final metrics reproduce correctly.
- Supplemental VTK report additions are not fully recreated by some reproduction scripts. Narrative transcripts are not full tool-event logs, so historical process claims cannot all be independently proved.

These are shown in Benchmark notes and per-run claim/eval-feedback evidence. Original output files are preserved, including defects, for human review. There is no claim that the candidate dominates every qualitative dimension.

## Evidence and review

- [Iteration1 benchmark](iteration-1/benchmark.json), [iteration2 benchmark](iteration-2/benchmark.json), [proposal](hillclimb-proposal.json), [selection](selection.json).
- Every run retains task metadata, input files, actual outputs, narrative transcript, independent grading and artifact/browser evidence. Model token totals were not exposed; partial wallclock scopes differ. Comparative time/token values are omitted instead of invented.
- [Local browser receipt](local-browser/report.json), [local deployment-byte rehearsal](local-asset-readback.json), [commands](commands.json), [local verification](local-receipt.json). Hosted verification will be recorded under live/.
- [Frozen source](skill-snapshot-v0/SKILL.md), [revised candidate](skill-candidate-v1/SKILL.md), [synthetic fixtures/oracle](fixtures/). Shared workspace isolation was by fresh context and instructions, not filesystem permissions. Initial executors saw the frozen acceptance criteria; second-iteration executors read task.json only.

The official viewer is generated through a separate static adapter: pinned upstream bytes stay unchanged, embedded HTML is safely escaped, old/new labels are correct, unknown metrics are omitted, and feedback persists locally and downloads as **feedback.json**. Click Outputs to inspect files and formal grades; Benchmark shows numbers and analyst warnings. Submit All Reviews downloads feedback for a later human-guided iteration; automated fixture feedback is not human approval.

## Reproduce

From repository root, see tools/skill_evals/FUNCTIONAL_REVIEW.md and the project /verify recipe. Validators: `grade_functional_fit.py --case CASE`, `grade_functional_audit.py --case CASE`, `node grade_functional_viewer.cjs --case CASE`. All run from tools/skill_evals/. Aggregate with `aggregate_functional.py ITERATION`; publish static assets with `build_functional_assets.py`. Existing Pages publishing workflow is reused; no CI, branch-protection, authentication or paid-compute changes were made.

The hidden fixture target and oracle are disclosed only as retrospective verification evidence; these synthetic cases are not an untouched future generalization benchmark.
