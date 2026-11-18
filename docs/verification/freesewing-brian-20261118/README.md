# FreeSewing Brian standalone publication

Scope: the new `web/freesewing/` pages, the rebuildable Brian source under
`tools/freesewing-brian/`, README navigation and the existing verification recipe.
No Pages workflow, access setting or existing application was changed.

## Prepublication verification — PASS

- Base commit: `255581100bab299eea9e73bbb07bdabfa1e6c374`.
- The new dependency installation rebuilt the delivered HTML byte for byte.
- Brian 4.10.2: all ten files match the original npm archive.
- Local engine/UI checks: 11 required measurements, one optional measurement,
  13 range controls, 22 boundary cases, high-bust mode and current SVG payload.
- Independent direct-Brian reference: 27 inputs, 81 part comparisons; all
  three native outlines and exported SVG paths match.
- Real managed Chrome: reset; chest 100 to 110 cm produced 1100 mm input and
  302.5 mm quarter width; SVG ready; optional high bust enabled. This preview
  uses the exact delivered HTML digest recorded in the source manifest.
- Static site builder completed; the new entry and Brian HTML passed the
  standalone checks; `git diff --check` passed.

The local Chromium launch was BLOCKED by this host environment, and the
connected Grok browser returned UNAVAILABLE. Those attempts are not PASS.
A real managed browser supplied the rendering/interaction fallback.

## Meaning of the result

This verifies faithful software behavior with matching settings. The demo
sets chest ease to 10%; upstream defaults to 15%. The master slider scales
body-input lengths and is not a factory grading table. Annotation/layout
changes and two added guide lines do not change Brian's cut outlines.
The guide pages are archived single-file outputs from the same work.
No fabric simulation, sewn sample or physical-fit claim is made.

## Publication

The existing publication-only GitHub Pages workflow is reused. The deployed
revision, HTTP digests and actual live interactions are recorded separately
after push; a successful workflow alone does not establish hosted UI PASS.
