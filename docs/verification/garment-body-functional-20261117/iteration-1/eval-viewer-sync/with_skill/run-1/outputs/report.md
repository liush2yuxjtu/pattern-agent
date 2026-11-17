# Repaired synthetic body viewer

Open `viewer.html` directly in Chromium or serve this folder over loopback. It is standalone: no CDN, network library, image generation, or paid service is used.

The source of truth is the supplied version 2 `body.json`: height 170, chest 98, waist 74, hip 102, depth ratio 0.78. Its assumed centimetre scale is a 170 cm prior. This is a synthetic lofted body proxy, not an anatomical reconstruction or measurement of a person. The fixture uses X horizontally, Y vertically and Z in depth; coordinates and topology are preserved at the defaults.

The original viewer automatically seeded v1 cache values, built the mesh once from that cache, and changed only labels after slider input. The repair removes the v1 seed, starts from final v2 parameters, and accepts edits only with the same explicit model identity and valid finite parameter ranges. Incompatible, malformed and unavailable storage fall back to the final defaults. Compatible edits intentionally persist on every slider input; “Reset final body” restores and persists the authoritative defaults.

Each height/chest/waist/hip input rebuilds the actual 3D vertex array consumed by the triangle renderer. Circumference controls adjust corresponding torso rings around their centres. Height scales vertical coordinates only, preserving independently selected girths; this is an intentional clarification of the original uniform scaling implementation. This simplified control geometry does not guarantee anatomical proportions, smooth joints, or a measured human fit. The model identity must be changed if the embedded final model changes.

`window.evalState()` is a non-writable diagnostic function returning frozen, detached copies of `{version,params,vertices}` from the actual mesh. Mutating returned data cannot change live geometry. “Export current state” downloads this same geometry and parameter state. The supplied `body.obj` and `body.json` remain the authoritative final defaults; `current-body-state.json` is the separately exported edited state.

Executed browser verification used Node Playwright and `/usr/bin/chromium`, with a Python server bound exclusively to 127.0.0.1. Real keyboard ArrowRight inputs changed each body slider by 8; real button clicks exercised front/side/back, export and reset. Rotation received real keyboard input. `browser-check.cjs` and `browser-fresh-check.cjs` create and close their own browser and loopback servers. Reproduce from any directory with `node /absolute/path/to/browser-check.cjs` and `node /absolute/path/to/browser-fresh-check.cjs` (Python, Chromium and the existing Node Playwright installation are required).

| Executed check | Result |
| --- | --- |
| Default mesh versus supplied OBJ | 1,548 vertices; maximum coordinate difference 0.00000049395, below 0.000001 rounding tolerance |
| Height 170 → 178 | 1,450 vertices changed; 192,526 rendered RGB channels changed |
| Chest 98 → 106 | 144 vertices changed; 33,686 rendered RGB channels changed |
| Waist 74 → 82 | 48 vertices changed; 16,092 rendered RGB channels changed |
| Hip 102 → 110 | 144 vertices changed; 31,890 rendered RGB channels changed |
| Stale v1 → repaired initial state | Exact final v2 parameters |
| Fresh storage / corrupted JSON | Exact final v2 defaults |
| Edited state after reload and downloaded export | Exact parameter and vertex equality |
| Front / side / back | Distinct rendered screenshot hashes; rotation slider matches camera angle |
| Rotation | Changed rendered pixels; geometry diagnostic unchanged |
| Reset and reload | Exact final v2 defaults |
| Desktop and 375 px mobile | No horizontal overflow; no page JavaScript errors in primary test |

`browser-results.json` and `browser-fresh-results.json` contain machine-readable results. Pixel counts compare actual canvas image data, independent of the diagnostic. They count changed RGB channels rather than changed whole pixels. These are regression checks of the supplied proxy, not physical measurement validation.

Evidence: `desktop-before.png` shows the unmodified fixture with explicitly injected stale v1 storage. `desktop-final-default.png` shows the repaired viewer immediately after that stale cache is rejected. `desktop-after.png` shows all four edited dimensions. `mobile.png` shows the same saved edited state at 375 px after camera/rotation interaction. Screenshots were captured by the browser, not composed. The mobile screenshot was visually inspected and shows all controls with no horizontal clipping.

Remaining limitations: faceted overlapping limb/torso lofts and painter-sorted Canvas projection are inherited from the synthetic fixture; this is not a physically shaded or anatomical model. No photograph-based measurements or mesh-section validation is claimed. A browser that disables local storage can edit for the current session but cannot retain edits. No external services were called. No task blockers remain.
