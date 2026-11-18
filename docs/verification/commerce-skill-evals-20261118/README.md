# Commerce skill functional evals — 2026-11-18

Anthropic skill-creator's pinned guide, graders, comparator and analyzer are
under tools/skill_evals/upstream. This is an explicitly injected Codex functional
experiment, not native Claude routing (CLI unavailable / BLOCKED).

Iteration1 executes two new original Everlane images, each with skill-v1 and
frozen skill-v0. CaseA: seven real ImageGen calls per run (one guide then six
independent final images); caseB: one guide plus actual pose-fitting branch.
All actual state, source, native receipts, code and raw depth are downloadable.

Independent actual-geometry and photo-region grades: A new6/9, old6/9; B new4/7,
old5/7. All four strict overall verdicts FAIL. Unweighted task means: new61.90%,
old69.05%, delta−7.15 percentage points. Assertion completion is not pose accuracy.
Blind visual comparison preferred the new posture in both cases, but visible
wrist residuals regressed. This disagreement motivates v2; it is not evidence
of a general win. Each task has one execution; no repeatability claim.

Official viewer: /garment-body/commerce-evals/eval.html. Native shell is retained;
actual four-stage galleries appear only inside Output. Thin overlays independently
project saved OBJ by saved3x4 camera at original resolution, with10% fill.

UI/file checks cover navigation, real image hashes, Formal Grades, Benchmark,
feedback persistence/download and mobile. These do not certify the body fit.
The first root browser run overlapped a dist rebuild and observed transient404s;
its raw failure remains in ignored work/root-i1-browser/report.json. The stable
build is rerun before publication. No CI was used.

V2 was frozen before heldout-C was opened. Iteration2 is running and not part of
this initial publication. Timing/tokens unavailable from subagent notifications
remain null; numerical solver timing is not total agent runtime.

True-person circumference/depth remain UNKNOWN; M170 is an explicit conditional
prior. Physical cloth fit NOT_RUN; historical cloth failure is not superseded.
