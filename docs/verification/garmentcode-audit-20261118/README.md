# GarmentCode actual rerun and independent geometry audit

Date: 2026-11-18 (Asia/Shanghai). The existing project `/verify` workflow and
`garmentcode-preview` surface recipe were read and applied. No CI was added or
used to verify code. Existing GitHub Pages is only the publication mechanism.

## Candidate and results

Implementation: `tools/garmentcode-audit/`; generated reviewer:
`web/garmentcode-audit/index.html`. Base repository revision was
`7c7df4127f5a0369a048b769e63de968fefe7bf4`; actual generated HTML and data revision
are in `local-gate.json`. All existing source files and historical FAIL records
are unchanged.

| Scope | Observed result | Verdict |
| --- | --- | --- |
| Seven new audit regression methods, including 23 existing analytic probes | All passed; malformed arrays/files, containment-only failure, shared-edge control, fold control and actual old fault covered | PASS_CHECKER |
| Actual original CPU pipeline | 232 frames; maximum old/new OBJ coordinate error 0 cm | PASS_REPRODUCTION |
| Three instrumented CPU runs | 278/236/300 actual frames; final NumPy and CGAL face-pair counts 13/3/3 | FAIL_GARMENT |
| All supplied saved garment states | 32 audited; NumPy/CGAL pair sets agree for every garment state | PASS_AUDIT_EXECUTION |
| Original full body | Closed oriented topology; 145 CGAL and 61 NumPy self-intersection pairs | FAIL_BODY |
| Existing MakeHuman asset only | 4002 vertices, 8000 faces; both self-intersection counts 0 | PASS_BODY_GEOMETRY_ONLY |
| HTML local data/syntax | Four cases, 32 states, actual full collider identity, inline assets, both JS scripts parsed by Node | PASS_LOCAL_DATA |
| Browser before publication | Native launch blocked by socket policy; connected Playwright service unavailable; cloud browser cannot reach local server; file protocol rejected | BLOCKED |
| Physical material, units/time, continuous collision and real fit | Not calibrated/verified | NOT_VALIDATED / NOT_RUN |

The initial recording adapter lost its requested 300-frame lower bound when
upstream missing-attachment handling updated the simulation settings. Both
actual shortened trials are retained as rejected candidates. A corrected
`update_min_steps()` lower bound was verified by a new 300-frame physical run.

`old-independent-audit-v3.json`, `fixed-independent-audit.json`,
`refined-independent-audit.json`, and `contact-independent-audit.json` retain the
actual face IDs, body validity, per-frame outcomes and checker hashes. NPZ files
retain full arrays; run JSON files retain effective numerical choices and actual
frame times. Timings from parallel processes are not speed benchmarks.

The browser block is kept separate from the geometry result. HTTPS publication
and actual UI checks are recorded separately after driving the published page.
No file-protocol policy is disabled or bypassed.

## Commands actually used

From the task workspace, with the pinned upstream repositories and isolated
Python 3.11 environment:

```bash
venv/bin/python pattern-agent/.agents/skills/garmentcode-preview/scripts/setup_cpu.py \
  --warp-repo NvidiaWarp-GarmentCode --cache compiler-cache
venv/bin/python pattern-agent/.agents/skills/garmentcode-preview/scripts/garment_preview.py build \
  --pattern pattern-agent/.agents/skills/garmentcode-preview/assets/example-shirt_specification.json \
  --repo GarmentCode --mode simulate --resolution 1.5 --max-frames 600 \
  --max-seconds 600 --out run-baseline
venv/bin/python pattern-agent/tools/garmentcode-audit/run_instrumented.py \
  --repo GarmentCode --out run-refined --substeps 20 --iterations 2 \
  --min-frames 300 --max-frames 600
venv/bin/python pattern-agent/tools/garmentcode-audit/run_instrumented.py \
  --repo GarmentCode --out run-contact --contact-radius-cm 0.2 \
  --min-frames 300 --max-frames 600
venv/bin/python pattern-agent/tools/garmentcode-audit/run_instrumented.py \
  --repo GarmentCode --out run-fixed-recorder --min-frames 300 --max-frames 300
venv/bin/python pattern-agent/tools/garmentcode-audit/audit.py \
  --sequence run-fixed-recorder/checkpoints.npz --out fixed-independent-audit.json
venv/bin/python pattern-agent/tools/garmentcode-audit/build_viewer.py \
  --workspace /workspace/scratch/72793d054f5c \
  --out pattern-agent/web/garmentcode-audit/index.html
```

All failed quality audits returned the expected FAIL result, not a successful
garment classification. No parameter change fixed the garment. The next
physics gate needs a valid matched body and a checked unit chain before another
garment quality claim. The separate MakeHuman check does not establish that
body matching has already happened.
