# Human Studio skill integration — 2026-11-17

The skill now defaults to the anatomical MakeHuman cm/pose editor, preserves all six independent image outputs, and distinguishes requested body sizes, actual neutral mesh measurements and photo-derived estimates. The linked reference records all 12 controls, 163 bones, state/API contracts, Y-up coordinates, OBJ cm / GLB m, pose-map replacement and missing camera/depth/generation APIs.

The new standard-library state helper checks saved state and can independently recompute neutral tape/landmark measurements from the matching asset. The downloadable skill includes the helper and regression fixtures, without mesh assets or secrets. Public resources are copied from canonical source and hash-manifested, with a real browser download/reopen check.

Local verification: **PASS** — 24 helper tests, 16 evaluation-tool tests, official format/package checks, 17 browser checks, real packaged CLI, and 3 negative CLI controls. [Receipt](receipt.json), [candidate hashes](candidate-files.json), [state audit](state-audit.json), [browser report](local-report.json).

[Desktop](local-desktop-top.png) · [Mobile](local-mobile-top.png) · [Returned adjustable model](local-model-return.png).

Historical embedded evaluation data and feedback keys remain unchanged. No new native trigger, six-image quality, real-person accuracy or physical-fit score is claimed. The previous model-specific 37 browser checks and OBJ/GLB audits remain separate evidence under ../human-studio-20261117/.

Publication evidence will be appended after exact-SHA GitHub Pages readback. Local browser uses loopback Chromium; ego-browser is unavailable. This is a scope-limited integration check, not a fresh full anatomical-model benchmark.
