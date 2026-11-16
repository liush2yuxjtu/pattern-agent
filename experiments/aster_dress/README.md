# Aster — Form & Pattern

[Live Three.js studio](https://aster-pattern-studio-161126.liushiyuxjtu.chatgpt.site/) · [Expert 3D and 2D review](https://aster-pattern-studio-161126.liushiyuxjtu.chatgpt.site/#review)

Archived as a standalone experiment. The complete downloadable ZIP is also available from the live studio handoff.

Open **aster-studio.html** in a modern WebGL2 browser. All JavaScript, CSS, and Three.js r180 are bundled. No server, CDN, font download, or network connection is required for local use.

## Review workflow

1. Orbit the dress by dragging. Scroll to zoom. Use F/B for front/back or the reset button.
2. In **Seams**, select a seam pair to highlight it. **Release** opens that join in the display; **Rejoin** restores it. Hiding seam lines does not remove connections.
3. **Unpick & unfold** releases every join and animates the same vertices into their 2D positions. The Assembly slider lets you inspect intermediate states. **Reassemble** joins everything again.
4. In **2D patterns**, scroll or use +/- to zoom, drag to pan, and choose **Focus panel** for detail. Solid lines are cut contours; dashed lines are sewing lines. Notches and grain arrows are marked.
5. **Compare** links the selected panel between the 3D and 2D views. Use the panel selector for keyboard access. Review checks and notes are in **Review**.
6. **Export review** saves dimensions, the seam map, notes, checks and checklist to JSON. Import restores them. Notes remain on the current browser/device until exported; share links contain draft settings but no notes.
7. **Download 1:1 pattern SVG** saves a single large-format pattern sheet in millimetres. Print at 100% without fit-to-page and measure the 100 mm calibration square. This is not an A4/Letter tiled layout.

## Deliverables

- `aster-studio.html`: complete offline interactive handoff.
- `DECISIONS.md`: design decisions, geometric method and outstanding garment work.
- `VERIFICATION.md`: executed checks and browser evidence.
- `dom-verification.json`: 13 DOM integration results (no GPU rendering).
- `geometry-verification.json`: numeric verification results, including four dimension/allowance cases.
- `aster-pattern-1-to-1.svg`: baseline full-scale pattern.
- `THREE-LICENSE.txt`: Three.js MIT license.
- `source/`: readable model, application, CSS, template, build and verification scripts.

To rebuild source: `npm ci`, `node build.mjs`, `node verify.mjs`, `node verify-dom.mjs`. Run `python3 make-handoff.py` after the checks to package a new ZIP.

## Scope

This is a developable geometric dress study, **not a fit-approved production pattern**. The model has no body scan, bust shaping, physical cloth drape, fit ease, zipper extension, facing, lining, boning or waist stay. Center-back joins B04 and S04 are closure review locations only. A pattern expert must draft those details and fit a toile before cutting final fabric.
