# Reproduce these functional evaluations

Clone the Pattern Agent repository at the published verification commit. The
`.skill` alone does not contain the MakeHuman asset, JS editor or this evaluation
runtime. Python needs NumPy, SciPy and OpenCV; fitting also uses Node. Browser
replays use the existing Playwright/Chromium setup documented in the repo.

Create `work/single-state-skill-evals-20261117/fixtures/` and extract
`fixtures.zip` there. Extract each `artifacts/CASE/CONFIG.zip` into
`work/single-state-skill-evals-20261117/iteration-1/CASE/CONFIG/run-1/`.
These archives retain the original `outputs/`, metadata, traces, grading and
failed attempts. Keep those directory levels so the saved replay entrypoints
can find the shared fixture runtime and repository model source.

Each `outputs/reproduce.py` or `reproduce.cjs` records its executable workflow;
read that run's report and TRACE for its actual command and environment. The
public state JSON also opens in Human Studio via the page's corresponding link.
The editor rounds dimensions and angles to its documented 0.1 step.

`manifest.json` gives every public file hash plus each complete run ZIP hash.
The independent `grading.json` binds all original output-file bytes. The
controlled oracle is disclosed only after all grading completes; extract it
into `work/single-state-skill-evals-20261117/private-oracle/` for grader replay,
not as solver input. Real-photo pose quality and measurements remain separate
from controlled geometry agreement and file/interaction checks.

For replaying the original grades, copy the hash-bound human action review from
`docs/verification/garment-body-single-state-evals-20261117/independent/visual-review.json`
in the cloned repository to the workspace's `grade-evidence/visual-review.json`.
This preserves a recorded human judgment, not automatic recovery of pose truth;
new or changed candidates require new visual review and matching artifact hashes.
