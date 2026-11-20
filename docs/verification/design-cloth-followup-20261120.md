# Design Cloth Boat follow-up verification · 2026-11-20

Base commit: `9a25228c980a9a7aeb441f83c4efa630d5975731`

Verified staged tree, before this receipt: `dea025503c86c9aa38699fc31ef71dcd27c131c8`

| Local command | Observation | Verdict |
| --- | --- | --- |
| `python3 .agents/skills/design-cloth/evals/run-handoff-evals.py <empty-output-dir>` | 8/8 passed. Case 37 emitted compare → one native question → match on the same copy. Case 38 emitted only the open-zipper comparison. The first clean-checkout run repeated an async question in case 21. The revised handoff records an explicitly staged partial answer and waits for an executable next check before asking again. | PASS |
| `python3 .agents/skills/design-cloth/evals/test-zero-draft-gates.py -v` | Ten controls for digital failures, signed revision identity, and human evidence passed. | PASS |
| `python3 .agents/skills/design-cloth/evals/run-zero-draft-gates.py <saved-eval-outputs> <receipt.json>` | Independently reopened and rebuilt retained outputs for 33 and 34. The candidate achieved 7/7 per case. Command returned 2, the expected pending-human value. | PASS for digital checks |
| `python tools/skill_evals/upstream/scripts/quick_validate.py .agents/skills/design-cloth` | Frontmatter and skill format valid. | PASS |
| `python3 scripts/build_pages.py` and `node tools/skill_evals/verify_design_cloth_followup.cjs` | Chromium followed the historical review link, read two distinct prompts across four runs, opened grades and benchmark, and showed no page errors or 390 px overflow. Unknown route returned 404. New page SHA-256: `5a35206c7b2ecf89bd10c6fd1297425ef9acfaeed4c17847cf945aae2eed61ed`. The script closed its browser and loopback server. | PASS |

The Codex cases use an actual app-server interaction with isolated CAD fixture responses. Production garment simulations and physical fit were not rerun. The drafting exports still require a physical print check and human signoff.
