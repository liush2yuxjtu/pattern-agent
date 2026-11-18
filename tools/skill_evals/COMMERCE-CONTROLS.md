# Reproduce the commerce grader controls

These five checks verify specific grader behavior. They do not establish that a
human model matches an e-commerce photograph. Keep actual functional outputs
and independent source/3D review separate.

Requirements: the repository Python runtime with NumPy, OpenCV and SciPy; Node;
the matching Human Studio asset; a completed pose-fit run and frozen case files.

```bash
python tools/skill_evals/test_commerce_grade_controls.py \
  --candidate work/commerce-skill-evals-20261118/iteration-1/eval-2-everlane-pocket-pose/with_skill/run-1/outputs \
  --case work/commerce-skill-evals-20261118/protocol/cases/everlane-blue-shirt/case.json \
  --out /tmp/commerce-controls-new
```

Use an empty/new output directory. The CLI refuses overlap with actual outputs,
checks unchanged original hashes afterwards, and never refits the human. It
requires the frozen `commerce_grade.py` v1.1 SHA-256:
`e2908f7a4da8ab9eeb79cb05283e5fdc048e47e5604bee28fa73682ec0ed1757`.
Thresholds come from the same frozen case/global protocol; the controls introduce
no replacement acceptance thresholds.

| Control | Expected evidence |
| --- | --- |
| Actual side PNG tampering | Independent side RGB replay fails despite unchanged mask, joint projections and claimed state hashes. |
| Actual posed OBJ translated 15 cm | Saved-state reconstruction fails and independently reports about 15 cm error. |
| Non-authoritative camera alias modified | With the original 3×4 matrix unchanged, source-photo content still replays. |
| Disconnected skin intervals | Crossings at 0, 2, 5, 7 produce two intervals; the air at 3 is not inside skin. |
| Odd/open skin ray | Three unique crossings are UNKNOWN, never certified collision-free. |

The CLI writes `controls.json` and the three full grader outputs. Exit status is
nonzero if a control fails. No image generation, paid call or fitting is run.

Actual rerun evidence from this session is in
`work/commerce-skill-evals-20261118/grade-evidence/reproducible-controls-v1.1/`.

## Receipt-layout compatibility

The independent adapter reads `receipts/{view}.json` without changing the frozen
numeric grader. It verifies six distinct native outputs, exact input byte hashes,
original JPEG/PNG decoded-pixel identity, and retained generation-state render
replays. It does not certify image quality or pose accuracy.

```bash
python tools/skill_evals/commerce_receipt_adapter.py \
  --candidate work/commerce-skill-evals-20261118/iteration-2/eval-1-everlane-six-view/old_skill/run-1/outputs \
  --source work/commerce-skill-evals-20261118/inputs/everlane-boatneck/original.jpg \
  --out /tmp/receipt-audit.json
python tools/skill_evals/test_commerce_receipt_adapter.py \
  --candidate work/commerce-skill-evals-20261118/iteration-2/eval-1-everlane-six-view/old_skill/run-1/outputs \
  --source work/commerce-skill-evals-20261118/inputs/everlane-boatneck/original.jpg \
  --out /tmp/receipt-controls.json
```

The three fault injections reject an altered output PNG, a false input hash, and
a self-consistently hashed but non-equivalent source PNG. Receipt-layout audit
results carry the adapter implementation SHA. Final grades retain the raw parser
failure and explicit compatibility correction evidence; no quality threshold is
changed and no actual output is rewritten.
