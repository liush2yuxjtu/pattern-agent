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

## Hosted publication and actual download — PASS

- Source/deployed commit: `4b806fcba0bdff2c567e50faa380b196c4894378`.
- [Publication run 44275662587](https://github.com/liush2yuxjtu/pattern-agent/actions/runs/44275662587): all deployment steps succeeded.
- [Public entry](https://liush2yuxjtu.github.io/pattern-agent/freesewing/)
  navigates to the [actual Brian tool](https://liush2yuxjtu.github.io/pattern-agent/freesewing/brian/).
- Eight published files return HTTP 200 and match both the committed SHA-256
  manifest and the deployed root `build.json` entries.
- Real Chromium: 13 sliders, three rendered pieces, 110 cm chest response,
  115% overall response, optional 97.5 cm high-bust response and reset.
- The actual SVG download was reopened independently: all three native part
  outlines match direct Brian with the same 1100 mm input; physical units are mm.
- See `hosted-http.json`, `hosted-browser.json`, `hosted-download.json`,
  `download-110cm.svg` and the actual `desktop.jpg` screenshot.
- The inspected console sample contained only managed-browser extension errors;
  it contained no application-origin error. Phone viewport testing was NOT_RUN
  because this browser exposes no viewport emulation API.

The follow-up evidence commit changes documentation only. Its verification
classification is SKIP for new runtime behavior; the hosted application PASS
above refers to the exact deployed source commit, not a later documentation SHA.
