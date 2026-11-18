# Cloth Lab self-contact candidate

This is a new version of the four-panel single HTML workbench. The original
`web/cloth-lab.html` and its historical receipts are preserved. The target build
is `web/cloth-lab-self-contact.html`; publication is gated by fresh browser and
independent geometry results, not by compilation or screenshots alone.

The additional verification on 18 November 2026 found 11 proper cloth
self-intersections in the original after 360 zero-wind steps plus 120 steps at
the actual slider maximum (5 m/s²). Its body-collision/sewing checks passed at
that state. This new boundary must not be called an original-version PASS.

The candidate adds inverse-mass weighted vertex-triangle and edge-edge contact,
an immutable pre-step position history, and a linearized swept vertex/triangle
crossing check. Contacts use a 3 mm numerical separation. Interior-edge bending
distances come from unfolding the two adjacent rest triangles, including seams.
The existing WASM gravity/distance solver uses 120 iterations. Body contact still
queries the actual MakeHuman mesh. There is no formal continuous-collision
guarantee or calibrated material/fit claim.

Saved HTML now retains previous-position arrays as well as current positions,
parameters and simulation clock, so the next step can be compared exactly.

From repository root:

```sh
npm ci --prefix experiments/single_html_cloth_self_contact
node experiments/single_html_cloth_self_contact/test_self_contact.mjs
node experiments/single_html_cloth_self_contact/build.mjs
python -m http.server 8770 --bind 127.0.0.1 --directory web
```

In another terminal:

```sh
python experiments/single_html_cloth_self_contact/verify_dynamics.py \
  --url http://127.0.0.1:8770/cloth-lab-self-contact.html --output work/self-contact-dynamics
python experiments/single_html_cloth_self_contact/verify_browser.py \
  --url http://127.0.0.1:8770/cloth-lab-self-contact.html --out work/self-contact-browser
python experiments/single_html_cloth_self_contact/independent.py \
  work/self-contact-browser/simulation.json --repo . --out work/self-contact-browser/independent.json
```

Use the same commands against the public URL after publication. Review actual
front/side/back, stress/strain/contact, mobile and saved-state screenshots.
Root project `/verify` and this directory's scoped recipe govern commit/push.

The build uses a function-valued string replacement to insert JavaScript. A
literal replacement string can corrupt bundled identifiers such as `$&&`
because `$&` is a special replacement token. The builder reparses the actual
embedded module before writing the final file.

Stress remains an assumed-model estimate, not measured cloth calibration. High
stretch must remain visible. Printed hardware dimensions, finished construction,
wearer fit, arbitrary high-speed contact and hardware frame rate are unvalidated.
