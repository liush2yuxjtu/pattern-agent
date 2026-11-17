# Viewer synchronization repair input
This standalone offline HTML renders real triangulated three-dimensional control geometry, with no CDN or server required. Open index.html in Chromium; Canvas is a painter-sorted orthographic projection of a loft mesh. body.obj and body.json are the authoritative final proxy. The HTML embeds the JSON to allow file:// use.

The current viewer initializes a stale v1 localStorage cache and shows obsolete geometry; controls change labels and cache values but leave the mesh unchanged. Repair synchronization with version 2 final data, make all four sliders change actual vertex geometry, keep front/side/back and rotation working, and keep persistence sensible after reload. Include visible browser evidence of final initial geometry and changed geometry after a slider interaction. A DOM label update alone is insufficient.

All geometry is SYNTHETIC CONTROL material and scale is a 170 cm prior, not a measurement of a person. Expected final dimensions are explicitly in body.json, which is the source of truth.

In managed Chromium configurations where file:// is blocked by policy, run `python -m http.server 8765 --bind 127.0.0.1` in this directory and open http://127.0.0.1:8765. This uses only loopback and no external network.
