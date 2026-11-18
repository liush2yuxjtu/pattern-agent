# Model measurement branch: isolated skill functional evaluation

Candidate: working tree based on c72ae5deb2dce2ead4bfbe08d8885e95bffa2bbc, reconciled without overlap onto 1f42077 before commit. The six executions used frozen old/new skill snapshots; later canonical changes only add factual test status and eval specification. Snapshot manifests and runnable inputs/protocol/source are downloadable from the official reviewer.

## Actual session result

Six fresh isolated executor subagents: three identical-prompt cases × new/old skill, one execution per cell. Separate independent grader and analyst. Valid saved model:7/7 each; residual/cache:7/7 each; wrong-neutral geometry:5/5 each. Each configuration19/19. This is a tie, no demonstrated accuracy, reliability, latency or token improvement; missing telemetry remains null. The old skill independently wrote working measurement code.

Case2 control target waist108cm and deliberately corrupted cache1000cm produce actual OBJ waist99.08309951462296cm. Case3 supplied posed mesh under neutral name has max46.062761717058144cm mismatch; both correctly reject with null primary sizes. This is rejection success, not successful photo/model matching. Numeric tolerance0.01cm; mesh correspondence0.002cm.

Independent grader uses its own OBJ parser/scalar morph/path measurement, not the exporter. Fixed manual findings are bound to recursive output SHA. Five real fault controls rejected: fake108, fake1000, wrong-neutral success, missing definitions, stale TRACE. Original source/outputs/snapshots unchanged; freeze hashes independently checked again before commit. New case3 executor's claim of implementation-independent audit is explicitly unverified because its audit imports exporter helpers; correctness is separately confirmed by the independent grader. Assertion PASS does not verify every ancillary claim.

## Local /verify

Project verifier: `.agents/skills/verify/SKILL.md`, `references/skill-evals.md`.

- `python -m unittest discover -s .agents/skills/garment-body-six-view/tests -q`:37 PASS.
- `python -m unittest discover -s tools/skill_evals -p 'test_*.py' -q`:20 PASS.
- `python tools/skill_evals/upstream/scripts/quick_validate.py .agents/skills/garment-body-six-view`:valid.
- Official pinned Anthropic package CLI; skill/page builder and `python scripts/build_pages.py`:completed.
- `node scripts/verify_garment_body_skill.cjs --url http://127.0.0.1:8955/ --output work/model-size-skill-evals-20261118/skill-browser`:21 PASS. Actual downloaded .skill reopened;20 entries exact source bytes.
- `node tools/skill_evals/verify_model_size_review.cjs --url http://127.0.0.1:8955/garment-body/model-size-evals/eval.html --out docs/verification/model-size-skill-evals-20261118/browser/final-dist`:167 PASS;97 HTTP-file SHAs, JSON download reopen, feedback download/reload, galleries/lightbox/mobile, original native DOM and explicit false independence claim. Zero console/page/HTTP errors. Actual rendered screenshots independently reviewed by root.

The independent grader, aggregation and strict reviewer builder were executed by their respective subagents, raw evidence retained in the downloadable sources. Original grader freeze was not regenerated for presentation. Earlier browser reports are retained; only final-dist is final acceptance. Initial legacy enhancement layout hid native sections and was corrected: all additions now inside native Output; Prompt stays visible; Benchmark hides Output additions; native Grades/Feedback/navigation preserved.

Verdict: PASS for this bounded measurement-branch skill execution and local published-artifact candidate. Native Claude trigger execution BLOCKED (no native runtime). Full reference-photo/pose fitting, Image Gen and physical cloth fitting NOT_RUN in this experiment. Historical cloth FAIL is unchanged. Live Pages browser interaction remains NOT_RUN because available remote browser providers are blocked; local dist interaction and publication receipt must be read separately. Existing Pages publisher is delivery only, not CI verification.

Loopback root server8955 is stopped after verification. Review: https://liush2yuxjtu.github.io/pattern-agent/garment-body/model-size-evals/eval.html
