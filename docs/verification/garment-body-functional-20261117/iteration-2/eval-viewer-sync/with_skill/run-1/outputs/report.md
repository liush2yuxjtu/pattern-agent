# Viewer synchronization repair

Completed and exercised in real Chromium 156.0.8078.79. Open `viewer.html` through a loopback HTTP server; it is self-contained and makes no external requests. Example: `python -m http.server 8765 --bind 127.0.0.1 --directory outputs`, then visit `http://127.0.0.1:8765/viewer.html`.

The authoritative v2 defaults are 170 cm height, 98 cm chest, 74 cm waist, 102 cm hip, depth ratio 0.78. The viewer embeds the exact exported OBJ vertices and faces. Changing controls computes continuous loft deformation deltas relative to these defaults and applies them to those actual vertices. Height affects the vertical axis only, preserving chest/waist/hip circumferences. The fixture uses X left/right, Y up, Z depth (retained rather than changing its export convention). Front looks along depth; side rotates 90 degrees.

A v1 or malformed cache is discarded. Same-version values must be finite numbers and are clamped and rounded to each range control's bounds/step before labels, controls, mesh, and persistence are initialized. Fixed v2 depth ratio is authoritative. `window.evalState()` is a non-writable read-only diagnostic function returning copied parameters and copied current mesh vertices; it does not expose mutable live arrays. It describes exactly the geometry rendered by Canvas. Existing IDs and camera data attributes remain.

`node outputs/browser-check.cjs` reproduces the tests using Playwright and pngjs, `/usr/bin/chromium`, and an automatically selected loopback HTTP port. The script closes its browser/server in `finally`. Run from any directory using its absolute path. Baseline fixture is included as `fixture-original.html` solely to reproduce before evidence.

53 assertions passed with no runtime errors (see `browser-results.json` for the precise executed list). Tests include stale cache migration, zero maximum default vertex error versus body.obj, all four keyboard sliders changing actual vertices and rendered pixels, pointer chest deformation, reload preserving current vertices and identical rendered pixels, front/side/back and rotation pixel changes, out-of-range/invalid-type/fractional-step v2 caches, height-independent actual girths, maximum-height canvas fit, and mobile overflow. Pixel checks compare decoded RGB pixels of actual canvas screenshots rather than DOM labels. Migration changed 67,025 canvas pixels (baseline and repaired views also use different fixed projection scales, so this count is visible-change evidence, not a pure shape metric).

Evidence:
- `desktop-before.png`: original broken viewer with stale v1 state.
- `desktop-initial-v2.png`: repaired viewer after the same stale cache migrates to v2.
- `desktop-after.png`: repaired viewer after real keyboard changes to all four dimensions and pointer chest change (171/121/75/103 cm).
- `mobile.png`: 390 px viewport at maximum height, controls below canvas, no horizontal overflow.
- `eval-state-initial.json` and `eval-state-after.json`: actual diagnostic snapshots, not substitutes for pixel assertions.

Visual inspection found that the original projection clipped the head at maximum height; lowering its fixed scale to 3.25 pixels/cm preserves the complete body through 195 cm. Reviewed resulting desktop and mobile evidence.

Assumptions and limits: this is the supplied synthetic, faceted, disconnected simplified body proxy; no anatomical or photographic fit is claimed. Units are assumed centimetres from the fixture's 170 cm prior. Parameters denote ideal ellipse girths; the actual 48-sided OBJ sections measure approximately 97.9300, 73.9472, and 101.9272 cm for labels 98/74/102. This approximately 0.071% polygon approximation is inherited from the authoritative export, not silently calibrated away. Height deformation preserves those actual ring values. Source body.json/body.obj are final defaults, not overwritten by browser interactions. Camera angle resets to front on reload; body dimensions persist. No external services, image generation, or paid services were used.
