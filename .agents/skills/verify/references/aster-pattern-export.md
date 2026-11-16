# Aster pattern and review export surface

Working directory: `experiments/aster_dress/source`. Use the same exact candidate
and browser prerequisites as the Aster browser recipe. `node verify-dom.mjs`
checks export structure but does not exercise browser downloads or print scale.

## Required real-surface steps

1. Launch the built `dist/aster-studio.html` in a real browser or use the pinned live
   URL. Require WebGL pixels and record selected dimensions and allowance.
2. Download SVG with real input. Independently reopen it; require 16 panel pieces,
   millimetre units, seam/cut distinction, labels, allowance and 100 mm square.
   Compare measurements with the selected draft, not only the default archive.
3. Save a panel/seam note, export review, reopen/import it and confirm values.
   Reject malformed review input without losing the current draft.
4. Download the standalone HTML, reopen separately, and confirm draft persistence
   and functioning 3D/2D controls. Capture actual file hashes and screenshots.
5. Physical print: print at 100% and measure the calibration square before claiming
   print-scale PASS. Patternmaker review must assess grain, hems, closure,
   facings/lining/support and a sewn toile before any fit/production claim.
6. Close browser/test server; retain downloads and raw evidence in a new
   `docs/verification/` run directory. Remove only disposable scratch state.

Historical automated geometry/DOM evidence: `experiments/aster_dress/VERIFICATION.md`
and `docs/verification/aster-20261116/`. Real browser acceptance was BLOCKED before
interaction; physical printing, sewing and wear fit remain NOT_RUN. This recipe
does not claim that pending steps have already succeeded.
