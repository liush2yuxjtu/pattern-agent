# Aster 01 — verification record

## Executed numeric and packaging checks

- `node build.mjs`: built a self-contained HTML with Three.js 0.180.0 inlined.
- `node verify.mjs`: passed four draft configurations spanning small, large and narrow-taper cases, and all four allowance options.
- 30,720 sampled 3D/2D mesh edge comparisons across those configurations.
- 96 seam-pair checks across the configurations, with 65 paired coordinate samples per join.
- Default maximum relative mesh edge error: 0.0024878841%. Default triangle area difference: 0.0024878808%. These are finite tessellation/chord differences, not claimed fabric strain.
- Default maximum seam length mismatch: 0 mm. Maximum coincident-edge gap: 9.36 × 10^-14 mm (floating-point noise).
- Every cut-contour segment's perpendicular allowance checked against 6, 10, 15 or 20 mm, with 25 mm hems. All matched within 0.00001 mm.
- No cut-contour self-intersections in the four tested configurations.
- HTML checked for external script/stylesheet dependencies and size below 2 MB.

Full numeric evidence: `geometry-verification.json`. Reproducible checks: `source/verify.mjs`.

## DOM integration verification

`node verify-dom.mjs` passed 13 integration checks using Node.js and jsdom 26. These execute the bundled application with WebGL explicitly unavailable; they are not real-browser or GPU tests:

1. Application initialization and usable 2D fallback.
2. Individual seam release remains distinct from hiding seam overlays.
3. Release-all, assembly-slider state and reassembly.
4. Unfold completion to 2D with all joins released.
5. Compare mode and common panel selection.
6. Dimension updates, invalid-taper rejection and allowance recalculation.
7. Review notes rendered as safe text and exported to JSON.
8. Review JSON imports restore the draft and notes.
9. SVG export includes 16 panels, millimetre dimensions and the calibration square.
10. Downloaded HTML opens with current settings in file-origin DOM emulation, and can be downloaded and reopened again.
11. Share links restore draft settings without leaking local review notes.
12. The direct `#review` link opens Compare and Review.
13. No unhandled DOM integration errors.

Evidence: `dom-verification.json`; reproducible script: `source/verify-dom.mjs`.

## Browser and hosting verification

Managed preview was attempted with the supported `sites-preview` CLI. Its relay timed out opening browser port 4173, and status reported the preview stopped. The workspace browser tool also failed during initialization with “the gaas-browser node_repl sandbox cannot be disabled.” A shell HTTP check was blocked by the execution environment's network proxy (HTTP CONNECT 403). No attempt was made to bypass those restrictions.

Consequently **GPU rendering, the visual layout, real pointer/touch interactions, mobile visual behavior, and actual browser downloads remain unverified**. The application includes responsive layouts and pointer controls in source, but those are not claimed as visually tested. No browser screenshots are supplied.

Sites returned a successful production deployment and the public URL. The access API confirmed `public` access. The pushed source commit was verified against the remote branch before the deployment archive was saved. The publishing result establishes deployment; it does not substitute for the browser checks above.

## Corrections made during verification

- Cached the flat-panel layout once per geometry update instead of recomputing all cut offsets for every animated vertex.
- Confined the saved-draft metadata replacement to the HTML head so repeated HTML exports do not modify the embedded application's own source strings.
- Added direct expert-review entry and explicit review targets for panel or seam findings.

## Limits

Numeric checks cover geometry and exported pattern construction. They do not establish body fit, fabric behavior, production sewing suitability, printed output calibration on a physical printer, or expert acceptance. No physical toile has been made. Source inspections alone do not establish browser behavior.
