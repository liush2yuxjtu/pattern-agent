# Offline viewer synchronization repair

`viewer.html` is standalone and uses no external dependencies or network assets. `body.json` and `body.obj` are unchanged copies of the authoritative final fixture. Open the viewer or serve the run directory over loopback.

## Change

The embedded final v2 parameters now initialize a single shared state. Only a validated v2 cache with the expected depth ratio and finite, in-range dimensions is restored; v1, malformed, incompatible or invalid caches are replaced by final defaults. Every dimension input rebuilds the actual triangulated mesh before rendering and saves the same parameters. Storage failure leaves the viewer usable. Existing dimension IDs, camera data-angle attributes and rotation remain functional. Responsive layout stacks the canvas and controls on narrow screens.

`window.evalState()` is a non-writable, non-configurable function returning defensive copies of `{version, params, vertices}` from the real current mesh. Mutating its return value does not affect the viewer.

## Executed checks

Executed headless `/usr/bin/chromium` through Node Playwright on `http://127.0.0.1:8767`, with real slider focus and keyboard input, real camera clicks, canvas RGBA comparisons, screenshots, reloads and direct mesh comparisons. `browser-results.json` contains the measured results.

- A pre-existing v1 cache migrated to height 170, chest 98, waist 74, hip 102, depth ratio 0.78, version 2.
- All 1,548 initial mesh vertices matched authoritative OBJ coordinates; maximum absolute coordinate difference was `4.939497078026989e-7`, below the six-decimal OBJ rounding tolerance.
- Height +1 changed 1,548 vertices / 139,413 RGBA channels; chest +1 changed 144 / 16,616; waist +1 changed 48 / 8,370; hip +1 changed 144 / 15,688. All coordinates remained finite.
- Front → side changed 242,313 canvas channels; side → back changed 242,137. Returning front reproduced front pixels exactly. Rotation keyboard input changed 134,527 channels without changing mesh state.
- Further keyboard edits created the visibly different after state: height 171, chest 130, waist 120, hip 103. Reload preserved all parameters and every vertex, and visible input values agreed. `edited-state.json` records this state; `initial-state.json` records the final defaults.
- Fresh storage and malformed storage both loaded final defaults.
- No JavaScript page errors and no horizontal overflow at 1100 px desktop or 375 px mobile.

## Evidence

- `original-stale.png`: actual unmodified fixture loaded with v1 cache.
- `desktop-before.png`: repaired viewer immediately after migrating stale v1 to final v2 defaults.
- `desktop-after.png`: repaired viewer after real slider keyboard interaction.
- `mobile.png`: 375 px viewport after reloading the edited state; full-page screenshot includes controls.

Screenshots were visually inspected; the narrower default torso and enlarged edited torso are visible. Pixel assertions compare canvas RGBA buffers, not labels or screenshot metadata.

## Reproduce

From the run directory:

```sh
python -m http.server 8767 --bind 127.0.0.1
# In another terminal:
node outputs/browser-check.cjs http://127.0.0.1:8767
```

The check closes its Chromium browser in `finally`. The execution service used for this delivery was stopped after checking.

## Assumptions and limits

This is **SYNTHETIC CONTROL** geometry, not a measured person or an anatomical fitting model. Units are assumed centimetres from a 170 cm prior. The original loft topology and orthographic painter-sorted Canvas renderer are preserved. Chest, waist and hip change their corresponding loft radii; height uniformly scales the whole mesh, including breadth, matching the fixture's existing construction. Thus a changed height also scales the effective circumferences; controls are model parameters, not independent validated physical measurements. The geometry has disconnected limb lofts by design. A legitimate saved v2 edit takes precedence on later visits; an obsolete v1 cache never does. `body.obj` remains the final default reference, while runtime edits are recorded by the diagnostic and browser storage. Browser execution used loopback because managed file URLs may be blocked. No external services were used.
