# GarmentCode independent audit and saved-state review

This directory continues the existing official-example experiment. It preserves
the original garment, body, failures, solver source versions, and paper pattern.
It does not change Golden Garment YAML 1.1 or claim a CLO/Style3D replacement.

## Result, 2026-11-18

| Run | Actual final frame | Upstream self-edge hits | NumPy self-face pairs | CGAL self-face pairs | Cloth/body face pairs |
| --- | --- | --- | --- | --- | --- |
| Reproduced historical baseline | 232 | 2 | 3 | 3 | 0 |
| More substeps and iterations, 20 × 2 | 278 | 9 | 13 | 13 | 0 |
| Collision radius 0.2 cm | 236 | 2 | 3 | 3 | 0 |
| Corrected recorder, unchanged baseline | 300 | 2 | 3 | 3 | 0 |

**Garment quality is FAIL.** All 32 supplied garment states were audited.
The two independent face-pair sets agree in every supplied garment state. The
historical rerun has zero maximum coordinate difference from the archived OBJ.
Counters measure different events; edge hits are not face-pair counts.

The 23,752-vertex, 47,500-face upstream `mean_all` body is closed and consistently
oriented, but CGAL finds 145 self-intersection pairs. The NumPy predicate, using a
1 micrometre strict crossing threshold and separate coplanar rule, finds 61.
These counts have different contact/tolerance semantics. Neither is zero.
Inside/outside classification therefore stays UNKNOWN, including frames whose
cloth/body surface intersection count is zero.

An existing 4,002-vertex, 8,000-face MakeHuman CC0 asset separately passes both
self-intersection checks with zero pairs and passes the closed-body topology
check. That result certifies the asset geometry only. It is not a matched body
for the official shirt and did not replace the original collider in these runs.

The first recorder requested 300 minimum frames, but upstream missing-attachment
handling reset that setting. Both rejected candidate runs retain their actual
236/278-frame endpoints. `ResearchConfig.update_min_steps()` now preserves the
requested lower bound, and a fresh actual 300-frame run verifies the correction.
No early run is relabelled as a 300-frame result.

## Reproduce

Use the existing `.agents/skills/garmentcode-preview/references/setup.md` for the
pinned Python 3.11 CPU environment. CGAL, NumPy, SciPy, trimesh and rtree are
required by the audit. Build the actual GarmentCode Warp fork; stock Warp is not
a substitute. The original scripts and the two upstream repositories are not
modified by these tools.

From this repository root:

```bash
PYTHON=/absolute/venv/bin/python
$PYTHON -m unittest discover -s tools/garmentcode-audit -p 'test_*.py' -v
$PYTHON tools/garmentcode-audit/audit.py \
  --mesh web/garmentcode-preview/demo/mesh_sim.obj \
  --body /absolute/GarmentCode/assets/bodies/mean_all.obj \
  --out work/garmentcode-audit/archived.json
$PYTHON tools/garmentcode-audit/run_instrumented.py \
  --repo /absolute/GarmentCode --out work/garmentcode-audit/recorded \
  --min-frames 300 --max-frames 300
$PYTHON tools/garmentcode-audit/audit.py \
  --sequence work/garmentcode-audit/recorded/checkpoints.npz \
  --out work/garmentcode-audit/recorded-audit.json
```

An audit exits 2 for a geometry FAIL, 0 for its narrow discrete-surface PASS.
Malformed input raises an error; it never yields an empty successful report.
Existing output paths are refused. The CLI controls include true enclosed
geometry without surface crossings, a valid shared edge, an actual folded
overlap, source corruption, invalid body volume and the historical actual fault.

`build_viewer.py --workspace WORKSPACE --out FILE` creates the offline HTML from
the original local run directories and reports, after checking source topology,
collider identity and frame identity. The exact dated source arrays and reports
are in `docs/verification/garmentcode-audit-20261118/`. Display coordinates are
rounded to 1e-8 m; audits use full saved precision. The review page uses the
existing project's WebGL viewer, extended here with fault highlighting and
saved-state selection; its source is retained alongside the builder.

## Limits and next gate

- The HTML **replays** actual Python results. It contains no browser cloth solver.
- Paper preview is the actual unchanged SVG; editing/new-size solving is absent.
- Cloth topology has one component and four expected boundary loops; this does
  not by itself establish correct body correspondence or wearable fit.
- Initial assembly crossings and late self-crossings are retained. There is no
  continuous-time collision guarantee or clearance certification.
- Material parameters are uncalibrated. The upstream centimetre/gravity/time
  chain is not validated. This work does not report physical stress or pressure.
- Before another garment quality claim, use a valid, measurement-matched body,
  retain explicit body/source bindings, check the unit chain, then rerun the
  original paper-to-mesh pipeline and both independent predicates. Simply
  increasing iterations or radius did not fix this case.

## Sources and licenses

- GarmentCode d449629979028123a5c4dc9e732a2ec19b7fce31, MIT. Pattern hash:
  `048aac4e8b90ffcda38f2b928eebe6354c48a4528ed7f31a885ce38e38ccf88e`.
- NvidiaWarp-GarmentCode 63baf6855efdd89b2834b74640f84b3bb0d86b50. Its upstream
  NVIDIA license applies to that separate toolchain; no solver code/binary is
  distributed by this review page.
- GarmentCode `assets/bodies/Readme.md` identifies `mean_all` as based on
  https://github.com/mbotsch/GarmentMeasurements, whose LICENSE is GPL-3.0.
  This new review tool and its embedded derived body are distributed with source
  and the included GPL-3.0 text. This license does not alter other repository
  directories. Upstream MIT/CC0 materials retain their notices.
- The NumPy oracle is reused unchanged from
  `experiments/oneshot_control/independent_oracle_v2.py` and is independent of
  Warp/CGAL. CGAL performs its own polygon-mesh self-intersection test.
- MakeHuman asset source, original hashes, preprocessing and CC0 terms remain in
  `tools/engine-cloth-lab/reference/assets/avatar-source.json`.
