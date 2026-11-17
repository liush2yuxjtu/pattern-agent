# Single HTML Cloth Lab verification

The receipt binds the new source files and HTML digest to local Playwright and
independent export checks. The reported PASS covers the bounded digital skirt
demonstrator, not calibrated fabric behavior or manufacturing approval.

- `browser-report.json`: 38 actual UI/export/offline/printing/mobile checks.
- `independent.json`: source body and seam correspondence, topology, exact
  triangle intersections, solid-angle body membership, deformation tensors,
  actual OBJ/SVG/DXF reopening and six adversarial controls.
- `actual-downloads.zip`: actual saved HTML, pattern SVG/DXF, combined 3D OBJ,
  sewing/simulation JSON and 42-page A4 PDF.
- `fabric.png`, `strain.png`, `stress.png`, `seams.png`, `contact.png`,
  `side.png`, `back.png`, `mobile.png`: real rendered evidence.
- `console.json`, `snapshot.txt`, browser/independent logs: raw observations.
- Earlier failures are preserved with their original scope: an initial body
  projection defect, 278 earlier self-intersections, a managed-browser file URL
  policy block, and a too-tight paper-media-box test. The final measured pattern
  calibration is checked independently of Chromium paper-size rounding.

The source/physics example uses a pinned waist, no general cloth self-contact
solver and uncalibrated material assumptions. Peak principal stretch is about
137%; the hotspot is retained. Physical fit is NOT_VALIDATED. Hardware frame
rate and physical printer output remain untested.

The separate live receipt is added after publication and names the exact Pages
commit and anonymous public URL; publication success alone is not a browser PASS.
