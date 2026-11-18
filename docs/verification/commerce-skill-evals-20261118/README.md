# Commerce skill functional evals — 2026-11-18

The pinned Anthropic skill-creator guide, grader/comparator/analyzer and official
viewer are under tools/skill_evals/upstream. Two paired actual rounds use explicit
Codex subagent skill injection; native Claude triggering is BLOCKED (no CLI).

Three original retailer inputs: Everlane boatneck fitted cotton shirt, Everlane
loose blue cotton shirt with pocket pose, and Reformation Janu linen dress.
Original response bytes/source URLs/dimensions/SHA remain intact. Generic M170
is a conditional prior, not real-person measurements. C was activated only
after skill-v2 froze and is not used to tune that candidate.

| Round / case | Revised skill | Frozen old skill | Overall |
| --- | --- | --- | --- |
| i1 A full six | v1 6/9 | v0 6/9 | both FAIL |
| i1 B pose-fit | v1 4/7 | v0 5/7 | both FAIL |
| i2 A full six | v2 6/9 | v0 6/9 | both FAIL |
| i2 B pose-fit | v2 5/7 | v0 4/7 | both FAIL |
| i2 C heldout pose-fit | v2 5/7 | v0 4/7 | both FAIL |

I1 task means61.90% versus69.05%; I2 task means69.84% versus60.32%. These
assertion fractions are not pose accuracy. All10 strict overall outcomes FAIL.
There is one run per case/configuration; across-task SD is not repeatability.
The baseline also changes between fresh executions, so no causal/statistical
superiority or speed/cost claim follows. Blinds favor v2 on B/C but v0 on A.
V2 remains a diagnostic/functional candidate, not an accepted photograph fit.

34 actual ImageGen calls: each full-six execution has1 guide+6 native role
images; B/C only test the guide/pose/body branch. Native receipts and exact
input state/render versions are retained. Generated/model posture drift and
grayscale-depth failures remain separate important eval gaps; complete file
counts do not verify them. Several guides were only reviewed after optimization,
so guide-driven correction is not established in those runs.

Actual independent source-engine cm/FK/LBS replay, matrix projection, regions
and skin intervals accompany source/front/side/back visual review. Blind files
are frozen before full TRACE/native receipt audits. C synthetic-prior wording
was initially misread as a source-photo claim and independently corrected; no
false provenance advantage remains. The original v1.1 grader is hash-pinned; a
versioned receipt adapter verifies the different receipt layout and lossless
JPEG-to-PNG identity, retaining raw parser failure and correction evidence.
Five grader fault/invariance controls and three receipt fault controls execute
through guarded CLIs and pass without changing numerical thresholds.

The real official editor consumes all6 i2 states:5 preserve exact action and
permit cm edits; Aold changes continuous angles on import and FAILS. One Bv2
probe additionally exercises actual joint UI, mesh response, download/reimport
(12checks PASS). Initial B consumer failures were a verifier race against the
app's65ms debounce; explicit readiness waiting fixes the invalid test, with raw
failures preserved. The new pose probe likewise waits for actual asynchronous
file-import completion before comparing all angles; its initial premature-read
failure is retained. No model output was repaired during grading.

Official viewer: /garment-body/commerce-evals/eval.html; iteration1 remains
available with native Previous Output in iteration2. Four-stage galleries are
inside Output. Thin overlays independently project actual OBJ by saved3x4
camera with10%fill; no source warp. Critical failures and extra editor scope
are visible alongside the gallery, separately from Formal Grades. Full unmodified
runs stay in ZIPs; linked gallery files are also published, avoiding duplicate
intermediate renders. Reproducibility ZIP includes frozen skills, released
protocol/annotations, analysis, audits and grader correction code. New proposed
criteria are explicitly DRAFT/NOT_RUN and never backfilled into old9/7 grades.

The canonical package retains tested v2 operational content plus dated status
records/eval specifications; description unchanged. The model/runtime supplied
to both groups is a repository dependency, not a standalone skill-only optimizer.

Local /verify and exact public Pages browser receipts are separate from task
acceptance. I1 live379 UI/hash/navigation/feedback checks PASS on0932b0c; its
first network-byte mismatch and unchanged-script successful rerun are retained.
The root's earlier local404s overlapped a dist rebuild; stable rerun passed.
No CI, PR, Issue, spending or security changes. Physical cloth fit NOT_RUN;
historical cloth seam/intersection FAIL is not superseded. Token/time null.

## Final live publication

Verified the actual public a564373322f821e5b0d7e689186a57f83710135f build.
Latest official reviewer462 checks PASS; retained first round229 PASS; public
skill/download21 PASS including exact commit. Actual downloaded package reopens
with17 exact canonical members. All6 model links bind exact archive state/OBJ;
three revised models load exact cm/163pose, and the old A rounding failure is
still explicitly recorded. See live-i2/receipt.json, actual screenshots, feedback
downloads and model-link reports. These are delivery/interaction checks, not
original-photo matching. Every actual fitting outcome remains FAIL. The remote
session was stopped. Later unrelated pressure-lab main additions do not change
the tested skill, Human Studio, generic runtime or commerce site subtree.
