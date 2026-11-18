# Source-bound human review and skill update

User request: update the skill and eval.html following Anthropic skill-creator,
with an immediately usable visual review. This update adds the missing human
feedback loop; it does not refit or regenerate the mannequin/images.

## Changes

- A lean SKILL pointer and an on-demand evaluation-workflow reference cover
  preserved baselines, genuine assertions, negative controls, evaluator critique,
  human review and scoped reruns. Native Claude trigger execution remains BLOCKED.
- Both existing evaluation URLs retain the four-image gallery and now show actual
  expectations/evidence and evaluator self-critique from the saved grading.json.
- Before/candidate feedback is separately bound to reference, state, posed OBJ
  and camera SHA. Two same-origin URLs share drafts. Empty feedback stays
  not_reviewed; human decisions do not overwrite independent automatic FAIL.
- feedback.json preserves reviews/run_id/feedback/timestamp/status and extends
  records with explicit acceptance and source fingerprints. Candidate review is
  complete only after an explicit decision. Feedback is local-only, never posted.
- The upstream-generated historical six-run viewer, its embedded data and feedback
  key remain byte-for-byte unchanged. All protected original/model artifacts and
  formal grades are unchanged (see preserved-evidence.json).

## Local /verify

Followed `.agents/skills/verify/SKILL.md` and product-case recipe. Read the fixed
`tools/skill_evals/upstream/SKILL.md` improvement loop and `agents/grader.md`.
Official quick validation/package readback PASS; package now contains 14 entries,
including evaluation-workflow.md. The domain skill is not Anthropic certified.

Commands executed from repository root:

```sh
PYTHONPATH=tools/skill_evals/upstream python tools/skill_evals/upstream/scripts/package_skill.py .agents/skills/garment-body-six-view skill-packages
python scripts/build_garment_body_skill_page.py
python tools/skill_evals/build_pose_guided_review.py
python tools/skill_evals/build_single_state_review.py
python scripts/build_pages.py
node --check tools/skill_evals/pose_review_feedback.js
node --check tools/skill_evals/verify_pose_feedback.cjs
python -m http.server 8942 --bind 127.0.0.1 --directory dist
node tools/skill_evals/verify_pose_guided_review.cjs --url http://127.0.0.1:8942/garment-body/single-state-evals/eval.html --out docs/verification/pose-review-feedback-20261118/original-url
node tools/skill_evals/verify_pose_guided_review.cjs --url http://127.0.0.1:8942/garment-body/pose-guided-fit/eval.html --out docs/verification/pose-review-feedback-20261118/focused-url
```

Both actual browser consumers PASS. Tests drive before/after, evidence, gallery,
model import, mobile and actual downloads, plus feedback save/reload, separate
versions, cross-URL sharing, blank draft export, explicit decision, and exported
source hashes. A deliberate manifest state-fingerprint mutation cannot inherit
an earlier review; malformed local JSON safely becomes unreviewed. Literal HTML
in feedback remains text. Tests also explicitly choose accepted and confirm that
this cannot rewrite the existing automatic FAIL, then restore needs_changes.
Automated feedback fixtures are labelled as such, not human acceptance.

Opened desktop and human-review screenshots. Browser errors/missing files: none.
Owned browsers and loopback server are closed after verification. The remote
fast-forward reconciled nonoverlapping work through a7da61b; the tested feature
sources and unchanged model digests are recorded in candidate-files.json.

This is a software/review workflow PASS. Original-photo/action matching remains
FAIL. No paired native Claude benchmark, trigger score or new measurement accuracy
claim is made. The existing Pages workflow is publication only, not a test gate.
