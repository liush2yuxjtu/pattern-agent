# Restore the Anthropic eval viewer format

User requirement: keep eval.html in Anthropic skill-creator format. The default
page now uses the pinned official viewer through build_functional_review.py;
upstream sources are unchanged. Custom rendering is confined to the native
Output body. Prompt, Outputs/Benchmark, Previous Output, Formal Grades, Feedback,
Previous/Next and Submit All Reviews are the original components.

## Scope and preservation

- eval.html at both public URLs shows the saved round14 candidate and the saved
  baseline, with their actual five-assertion grades. Both overall results are FAIL.
- Benchmark is a descriptive n=1 saved-candidate comparison, not a new/old skill
  experiment. Both have 2/5 assertions; 40% is not pose or anatomy accuracy.
  No token/time improvement or new Claude execution is claimed.
- history.html preserves the original six-run payload and STATIC_REVIEW_KEY
  byte-for-byte, including the frozen historical grades/benchmark.
- The custom mannequin/overlay controls remain optional in details.html. The
  default official viewer is never collapsed under a custom dashboard.
- Native feedback is shared across the two same-origin official URLs. A legacy
  custom draft migrates only if there is no native draft and all reference/state/
  mesh/camera hashes match. Existing or explicitly cleared native feedback wins.
- The actual source images, body state, mesh and old grading are not refitted or
  relabelled. Gallery overlays are transparent OpenCV renderings of saved actual
  model masks; baseline did not use the subsequent Image Gen cue.

## Local /verify

Followed .agents/skills/verify/SKILL.md and its product-case recipe. Used the
pinned Anthropic generate_review.py through the existing static-host adapter
(local storage + actual feedback.json download; no feedback server).

```sh
python tools/skill_evals/build_pose_guided_review.py
python tools/skill_evals/build_single_state_review.py
PYTHONPATH=tools/skill_evals/upstream python tools/skill_evals/upstream/scripts/package_skill.py .agents/skills/garment-body-six-view skill-packages
python scripts/build_garment_body_skill_page.py
python scripts/build_pages.py
python -m http.server 8943 --bind 127.0.0.1 --directory dist
node tools/skill_evals/verify_official_pose_review.cjs --url http://127.0.0.1:8943/garment-body/single-state-evals/eval.html --out docs/verification/official-eval-format-20261118/main
node tools/skill_evals/verify_official_pose_review.cjs --url http://127.0.0.1:8943/garment-body/pose-guided-fit/eval.html --out docs/verification/official-eval-format-20261118/alias
node tools/skill_evals/verify_pose_guided_review.cjs --url http://127.0.0.1:8943/garment-body/pose-guided-fit/details.html --out docs/verification/official-eval-format-20261118/details
```

Both official consumers PASS; advanced details consumer PASS. Actually exercised
native controls, all four Output stages and image hashes, image keyboard focus,
case navigation, actual failure evidence, Previous Output, Benchmark notes,
local feedback reload, cross-URL feedback, and real Submit All Reviews download.
Migration checks reject changed-camera drafts, preserve newer native text and
keep explicitly cleared native feedback empty. The first clear-feedback probe
incorrectly reloaded after 500ms while native debounce is 800ms; the verifier now
waits for the real Saved status rather than a guessed delay, and both paths pass.
Browser errors: none. Opened the official desktop screenshot and confirmed the
native shell with the gallery inside Output. Screenshots and raw browser reports
are alongside this file; automated feedback fixtures are not human acceptance.

Official package validation/readback PASS (14 entries). Skill instructions now
make the default official shell explicit; interaction details cannot replace it.
Historical payload/key and unchanged upstream checks PASS (preserved-history.json).
The nonoverlapping remote fast-forward through 2217a8a did not change the tested
feature, viewer adapter, upstream template, body engine or Pages builder. Candidate
source hashes are in candidate-files.json. Owned browser/server processes are
closed after verification. Publication receipts are not live UI test results.
