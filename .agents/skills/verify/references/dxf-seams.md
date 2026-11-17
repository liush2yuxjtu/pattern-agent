# Source-bound corrected sewing shell

Working directory: repository root. Runtime and independent reopener are under
`services/dxf-preview/`. This gate concerns the actual static outer-shell GLB
generated from an explicitly corrected derivative of the input sewing lines.
Original source bytes, v1 failures, unresolved back quantity, folded hidden neck
layer, material calibration and fit limits must remain visible.

## Local gate

```sh
SEWING_TEST_EVIDENCE=work/seam-tests PYTHONPATH=services/dxf-preview python -m unittest discover -s services/dxf-preview/tests -v
python scripts/reproduce_dxf_v1_baseline.py --out work/dxf-v1-baseline
cd services/dxf-preview
python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

Wait for `/api/health` 200, engine 2.0.0 and the current source hash. From root:

```sh
python scripts/verify_dxf_service.py --base-url http://127.0.0.1:8765 --output work/dxf-seams-browser
python services/dxf-preview/verify_connections.py --dxf services/dxf-preview/public/sample.dxf --glb work/dxf-seams-browser/downloaded.glb --units mm --out work/dxf-seams-independent.json
git diff --check
```

Prerequisites: pinned Python 3.12/NumPy/SciPy/FastAPI runtime; httpx for test
client, Pillow/Playwright and `/usr/bin/chromium` for UI. Blender is not required.
Standalone reopener exits 0 only for PASS, 2 for rejected/unverifiable artifacts.

The 27 tests include actual float32 export, source/dimension transformations,
the existing strict oracle's 23 analytic probes, and adversarial cases: wrong
hash, swapped source labels, undeclared ease, omitted/reversed seam, coincident
unwelded chart, a 3mm gap, deleted face, reversed face, a front point piercing
the back, shared-edge coplanar overlap and a hidden glTF scene transform.
All required negative cases must be rejected. Do not skip incident triangle
pairs merely because they share vertex IDs.

Require all 15 declared seams and all five source charts. Reopen exact GLB
bytes; check canonical registration against the original DXF, unchanged input
hash, bounded documented point edits, full flat-panel area/edge coverage and
the actual face-to-UV mapping. Verify source directions and localized ease,
shared seam vertex IDs, two incident source faces per sewn edge, one connected
component, four intended boundary cycles, Euler characteristic -2, valid vertex
links and zero duplicate/degenerate/nonmanifold/winding errors. Neck, hem and two
cuffs are intentional openings; a garment must not be made watertight to pass.

Frozen contract: gap <=2mm; residual after declared flat sewing process <=0.05mm;
derived point edit <=8mm; 3D seam length error <=2mm; proper intersections zero
at the independent oracle's 1 micrometre numerical tolerance. These are digital
geometry criteria, not material strain, manufacturing or wear approval.

Record source hashes, raw logs, failed intermediate attempts, source-line edits,
per-seam measurements, screenshots and candidate under
`docs/verification/dxf-seams-20261117/`. Source v1 commit 0f9edae reproducibly emits
GLB de34bed5… with 9 components and 340 proper intersections; retain that FAIL.
The still older cloth's 7.6455mm seam gap/20 intersections are separate history.

## Hosted gate

Use the existing `pattern-agent-convert` project and original protection. Follow
`dxf-service.md` for source-file upload, exact commit/health hash and actual live
browser checks; `verification/**` and the contract must be in the Python bundle.
The full browser verifier has 16 grouped checks, including numeric sewing PASS,
reopened output/downloads, original/derived pattern files and offline viewing.
Recheck the hosted downloaded GLB with the independent CLI and original bytes.
READY and screenshots alone do not establish the garment verdict.

For the proven public-only Firecrawl Bash fallback, run the pinned public
verifier after verifying its SHA-256. The full strict run may exceed one tool
call's 60 seconds: use a detached Python subprocess with a log and completion
file, then inspect that same process until completion. No TLS bypass. Retrieve
evidence in sub-megabyte chunks, validate archive hashes and stop the session.
Reuse the returned `scrapeId` for every follow-up; `conversationId` correlates
calls but does not select the same machine. Opening the URL again creates a new
session without the prepared files. Cross-CPU floating-point normal rounding
may change a GLB digest; independently compare all geometry accessors rather
than claiming cross-platform byte identity from the source hash alone.
Close local browsers and stop only the uvicorn instance started for this task.

## Inspecting and preserving the result

Apply [seam-inspector](seam-inspector.md) before claiming a graphical view is
evidence for this model. It binds displayed arrays and report values to the
independently reopened source/GLB, then verifies actual selection and downloads.
Use [seam-sites](seam-sites.md) for authenticated production interactions and
[seam-pages](seam-pages.md) for companion HTML file/content readback.

Compare flat lengths **after the declared localized sewing process**, not raw
edge lengths assumed equal: the corrected side has about321.220mm front and
305.220mm back; front gather6mm and back stretch10mm yield about315.220mm each.
Source-direction, process-window and actual 3D seam-length checks still apply.
Shared IDs alone cannot establish correct sewing: also require correct source
pairing, two incident source faces, full flat-domain coverage and intersections.
Diagram dots are presentation samples; numerical acceptance covers every actual
seam edge/vertex and all exported triangles. Preserve the original FAIL and
single-outer-layer scope alongside any new visual PASS.
