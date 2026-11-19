---
name: verify
description: Rebuild the Garment GPU Studio, verify WebGPU and independent geometry, and check the GitHub Pages copy.
---

Use Node.js 22+, npm and Chromium with a working WebGPU adapter. Run from the experiment directory:

```sh
npm ci --ignore-scripts --no-audit --no-fund
node scripts/build-verifier.js
node scripts/verify.js
cmp dist/garment-gpu-studio.html ../../web/garment-gpu-studio/index.html
cmp dist/verify-garment.js ../../web/garment-gpu-studio/verify-garment.js
```

Set `GARMENT_CHROMIUM` to the browser executable when needed. The verifier starts and closes a loopback server and Chromium. Require 48 module assertions, 48 real browser assertions and independent geometry PASS for 855 mm and 935 mm chest sizes. Preserve `evidence/verification-js.json`, `browser-report-js.json` and `independent-report-js.json` with the SHA-256 and adapter. Preserve hardware, material, continuous collision and human fit as separate claims.

Run the repository Pages builder from the root, then compare the output HTML and verifier bytes before pushing. After the existing publication workflow completes, compare the live HTML and verifier bytes with `build.json` and exercise WebGPU, size application and grading at the public URL.
