# Bounded DXF conversion service

Working directory: repository root. Runtime: `services/dxf-preview/`, Python 3.12,
FastAPI with pinned NumPy/SciPy. This is profile-bounded visual assembly, not an
arbitrary DXF converter or a cloth/fit release. Preserve all historical FAILs.

## Local gate

```sh
PYTHONPATH=services/dxf-preview python -m unittest discover -s services/dxf-preview/tests -v
cd services/dxf-preview
python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

Wait for `/api/health` HTTP 200. From repository root:

```sh
python scripts/verify_dxf_service.py --base-url http://127.0.0.1:8765 \
  --output work/verify-dxf-service
git diff --check
```

Prerequisites beyond runtime: httpx for TestClient, Playwright, Pillow and existing
`/usr/bin/chromium`. No downloaded browser or Blender is required. The verifier
launches browsers and closes them; separately stop the exact uvicorn process.

Require independent GLB decoding, finite nondegenerate triangles, changed geometry
for contour edits and uniform scale, correct units, reordered/reversed/translated
input, unrelated/same-count-wrong-shape rejection. Drive actual raw-DXF HTTP and
file-picker upload, sample conversion, mesh pixels, drag/zoom/wireframe/reset,
model/report downloads with hashes, invalid upload clearing stale model, saved-pattern
reuse button/form repopulation/re-generation, direct reuse link, unknown saved-ID
rejection, 375px
mobile, network-disabled self-contained HTML and WebGL-disabled fallback.

Capture `verification.json`, raw test output and PNGs under
`docs/verification/dxf-service-20261117/`; record base commit, source manifest,
source health digest and scope. The expected 400 console message from deliberately
invalid input is recorded separately; unexpected browser/server errors must fail.
Earlier driver errors remain tooling failures, not product PASS evidence.

## Hosted gate

Deploy only the verified service root to the separately identified
`pattern-agent-convert` Vercel project. Do not replace other projects or change
deployment protection. No new CI, queue, store or compute subscription.
Use connector deployment state/logs, and record ID, fixed URL, production alias,
artifact commit and uploaded SHA-256 manifest. READY only proves build completion.

Observed packaging detail: Vercel rewrites runtime `vercel.json`. Health therefore
hashes explicit application/code/profile/pyproject/public files, not that generated
deployment config or optional empty-package markers. Preserve the uploaded
configuration's own hash in the source/deployment manifest separately.

Run the same verifier against the live URL with `--expected-source` from local
health, and retain separate live evidence. Compare original sample and generated
GLB hashes against the local result. Probe fixed deployment health separately
when access permits; authenticated fetch is not anonymous-browser acceptance.

Local Chromium can reject this environment's proxy certificate. Do not disable
TLS checks or change trust. The public-only Firecrawl interact Bash fallback from
`fitted-tshirt.md` can run the pinned public verifier with `/usr/bin/google-chrome`;
SHA-256 check the downloaded script before execution. Only use already public
sample data, no private fixtures or credentials. Preserve the first blocker,
retrieve the PNG/JSON evidence with archive integrity checks, then stop session.

Physical fit and strict seam/intersection release remain NOT_RUN even if the
service and browser pass. No load/availability SLA follows from this acceptance.
