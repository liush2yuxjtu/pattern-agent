# Aster dress handoff verification

This candidate archives the already published Aster Three.js dress studio under
`experiments/aster_dress/` and adds its entry to the repository README. Existing
Blender experiments, OpenSloper assets, the T-shirt review workbench and GitHub
Pages build configuration are unchanged.

The root `.agents/skills/verify/SKILL.md` was invoked before the direct-to-main
commit. Local checks run against the copied source, not against a mock of the
geometry module. The source manifest records the exact candidate files.

## Commands

From `experiments/aster_dress/source`:

```sh
npm ci --ignore-scripts
node build.mjs
node verify.mjs
node verify-dom.mjs
```

The generated HTML, SVG and test results are compared byte-for-byte with the
archived deliverables. The command log, source SHA-256 manifest and JSON receipt
are stored beside this file.

## Verdict

Overall application acceptance: **BLOCKED**. The original managed preview relay
and workspace browser could not start. No real GPU, desktop/mobile layout,
pointer/touch or browser-download acceptance is claimed. The existing runtime
failure evidence is preserved in `experiments/aster_dress/VERIFICATION.md`.

Geometry checks and DOM integration assertions pass. DOM tests deliberately
exercise the WebGL-unavailable path and are not a substitute for real-browser
acceptance. Physical cloth behavior, printer calibration, sample sewing and
human fit remain NOT_RUN. Archiving this study does not change the historical
T-shirt FAIL results.

For real-surface follow-up, open `experiments/aster_dress/aster-studio.html` in a
WebGL2 browser. Exercise orbit/zoom, individual release/rejoin, unfold/reassemble,
linked Compare selection, dimension validation, review export/import, SVG
download and saved-HTML reopening. Capture the exact candidate hash, actual
screenshots, console/network failures and the observed result of each action.
Keep this acceptance pending until the real surface is reachable.
