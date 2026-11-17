# Quick visual eval galleries — 2026-11-17

Each case now has input reference, Image Gen output, simulation/3D render and overlay sections. Image-bearing cases open first; the case/configuration picker remains synchronized with Anthropic's run/grade view. Each available image opens in a keyboard-accessible lightbox with previous/next and original-file links. Long prompts and raw file listings are collapsed.

Image Gen is NOT_RUN in this dataset and is never replaced by a simulation image. State-only audits explicitly show no image evidence. Supplied synthetic references and review-derived source projections/replay overlays carry separate provenance captions and hashes. The gallery preserves all14original run archives, frozen grades, benchmarks and feedback keys.

Local verification: **PASS**, 52/52/34gallery checks across6/6/2runs and31existing review checks, plus20tool tests. [Receipt](receipt.json), [integrity](integrity.json), [desktop](local/selected/desktop.png), [lightbox](local/selected/lightbox.png), [mobile](local/selected/mobile.png).

Build: `python tools/skill_evals/build_anatomical_review.py --workspace work/anatomical-skill-evals-20261117 --site web/garment-body/anatomical-evals --evidence work/visual-gallery-build`, then `python scripts/build_pages.py`. Canonical gallery data adapter and assets are under tools/skill_evals/. Pinned upstream Anthropic source remains unchanged. Current source images/scores are synthetic controls, not an actual clothed-generation quality score.

Live publication **PASS** at `fe8b81d4a29bb122244728b90f1b3743c77524fe`: all14case entries,52/52/34gallery checks,31feedback regression checks,106public file/image hashes. [Live receipt](live/receipt.json) · [Live desktop](live/selected/desktop.png) · [Live lightbox](live/selected/lightbox.png) · [Live mobile](live/selected/mobile.png).
