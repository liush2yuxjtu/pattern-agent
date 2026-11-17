# Viewer synchronization repair

Completed a self-contained offline `viewer.html`; no remote libraries or paid services are used. `body.json` and `body.obj` are unchanged authoritative v2 fixtures. The viewer embeds the exact OBJ vertex coordinates and uses the fixture topology. Default geometry agrees with all 1,548 OBJ vertices within 3.56e-15 cm floating-point error.

The cache is accepted only when both version 2 and model identifier `final-v2-obj` match. Stale v1, malformed, missing and incompatible caches fall back to final defaults: height 170, chest 98, waist 74, hip 102, depth ratio .78. Numeric cached inputs are bounded; storage failures leave the viewer functional. Slider input rebuilds the actual mesh from procedural deltas relative to final geometry, then persists parameters. Centered cross-sections retain their centers. `window.evalState()` is non-writable and returns detached snapshots of current renderer vertices and parameters.

Chromium 156.0.8078.79 checks passed. Run `node browser-check.cjs` from this directory (requires Playwright and `/usr/bin/chromium`). The script starts a loopback-only ephemeral HTTP server and closes both browser and server in finally. Sliders use actual pointer clicks and Home/ArrowRight keyboard events.

| Check | Result |
|---|---|
| Stale v1 to v2 visible change | 69,084 canvas pixels |
| Height slider | 1,548 vertices; 76,157 pixels changed |
| Chest slider | 144 vertices; 10,347 pixels changed |
| Waist slider | 48 vertices; 4,427 pixels changed |
| Hip slider | 144 vertices; 9,646 pixels changed |
| Front to side/back | 49,152 / 45,174 pixels changed |
| Rotation input | 35,781 pixels changed |
| Reload | Exact current vertices and parameters preserved |
| Mobile | Actual 390px viewport, no horizontal overflow |
| Runtime exceptions | None |

`desktop-before.png` shows the original stale v1 viewer; `desktop-after.png` shows repaired v2 initial geometry with identical desktop camera and canvas framing. `desktop-slider-after.png` shows the visibly deformed mesh after all four interactions, before reload. `mobile.png` shows the responsive fresh-default page. Screenshots were visually inspected. Pixel comparisons use rendered Canvas RGB values, independent of DOM labels and geometry diagnostics. Full results and current-geometry snapshots are provided as JSON.

Assumptions: this remains the fixture's simplified synthetic loft proxy, with assumed centimetres and a 170cm height prior. Coordinates preserve fixture X horizontal, Y up, Z depth. The existing procedural proportions and renderer are retained; height scales all axes, so circumference labels remain model controls rather than independently verified anatomical measurements at changed height. No image fitting, new anatomy, photorealism or real-person measurement accuracy is claimed. Shoulder control was outside the requested four-slider repair. Camera angles are functional; front/back geometric symmetry means differences also reflect triangle shading. Persistence assumes the same browser origin. File delivery is standalone, but Chromium execution was verified through loopback HTTP because managed file URLs are blocked.

No blockers remain for the requested repair.
