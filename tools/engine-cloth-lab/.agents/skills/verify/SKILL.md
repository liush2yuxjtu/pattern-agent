---
name: verify
description: Verify the existing-engine cloth experiment without promoting engine fixtures to garment approval.
---

# Verify the existing-engine experiment

Working directory: `tools/engine-cloth-lab/` in Pattern Agent. Follow root main-only rules. This recipe adds no CI.

1. Run `npm ci`, `npm run build`, `npm run verify`, then the FreeSewing conformance, mesh conformance, Rapier engine-probe and independent advisor-checks commands in README. Record exit statuses, base commit and `dist/build-manifest.json`.
2. Open the exact delivered HTML through the environment-authorized browser preview. In managed Linux, use `sites-preview start ABSOLUTE_PACKAGE_PATH`; use its returned URL and the documented browser Playwright interface. Never launch a second preview server or bypass browser URL policy.
3. Read `document.documentElement.dataset.buildSourceSha` through a DOM-backed read and compare with the manifest. Golden must show U and BLOCKED; its simulation and 1:1 PDF controls must remain disabled.
4. Select the explicit FreeSewing source. Wait for READY. Run 30 steps, inspect collision, and download actual JSON, SVG and PDF. Preserve fixed front/back/side screenshots plus strain and fold views. Software rendering is not GPU validation.
5. Scrub the timeline. Export must retain exactly the same frames and native step count. Edit waist by 10mm: REV increments, frames/audit/native results clear, controls require rebuilding. Switch back to Golden: no demo result may survive.
6. Validate the actual files with `probes/pattern/output_oracle.py` using the README arguments. Capture screenshots and downloads through the documented browser file API, then promptly copy them from the transient shared area into `evidence/browser/`.
7. Keep scope verdicts separate: input/metric checks, browser behavior, engine fixtures, full garment, material stress and real fit. Default garment gap >2mm is FAIL even when body intersections are zero. Do not rewrite historical failures or weaken thresholds.
8. Public publication uses only the existing Pages deployment workflow. Read live `build-manifest.json`, compare hashes, then operate the actual public page. A successful deployment alone is not runtime PASS.

Current runtime gotchas: base64 JS packaging avoids HTML raw-text parser corruption from dependency strings; plain JS syntax checks missed that boundary. CSP blocks runtime external connections. Browser file:// is policy-BLOCKED and must not be bypassed. UI import filechooser disconnected during testing and is BLOCKED, rather than passed. A short 30-step job finished before a stop-click could interrupt, so interruption remains NOT_VERIFIED.

The artifact is an experimental handoff, not a completed garment. Stop only the preview owned by this package when finished. Preserve the useful user-facing tab.
