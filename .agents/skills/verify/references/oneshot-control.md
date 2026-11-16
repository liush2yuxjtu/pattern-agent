## Chat verification recipe — 2026-11-15 — one-shot control calibration

Target: `experiments/oneshot_control`, Python3.12 + NumPy2.3.5 + SciPy1.17.0,
Blender4.3.2 on PATH. Use fresh `runs/` output directories.

```sh
python3 independent_oracle.py --self-test --out runs/analytic.json
python3 run_experiment.py --out runs/controls
python3 probe_coplanar.py --matrix runs/controls --out runs/coplanar
blender -b -t 1 --python-exit-code 2 --python diagnose_broadphase.py -- \
  --case runs/coplanar/cases/coplanar_roof_overlap_only \
  --legacy ../full_arm/verification/geometry.py --out runs/broadphase.json
blender -b -t 1 --python-exit-code 2 --python reopen_and_render.py -- \
  --model runs/controls/model.blend --cloth runs/controls/cloth.blend --out runs/render
```

Real CLI generates both standalone files and executes10 standard cases. Add
`--original-cloth assets/first-export-cloth.obj` for the11th annotation case;
the exploratory coplanar probe is the12th combined case. Expect18 analytic PASS,
4 positive controls accepted,8 invalid controls rejected by the independent gate.
Legacy falsely approves displaced-body/stale-path and coplanar roof cases. Trace
expects0/54 pairs in BVH but54/54 accepted by direct narrow-phase calls.
The penetration case has336 body pairs in both algorithms and581 coplanar self
pairs omitted by legacy. Do not claim legacy verification PASS.

Reopen each .blend, require one scene mesh, zero external dependencies, OBJ
matching within1µm, and inspect actual renders. Preserve the original incorrect
labels and proof that their correction changed no vertices/triangles. Keep raw
logs, inputs, source hashes and exact candidate in `docs/verification/`.

Static calibration PASS is distinct from garment release: old Cloth FAIL remains;
no new dynamics or physical fit is claimed. Only six old frames have independent
SAT count/example audits. No continuous-time collision certificate is established.

## Current strict v2 and recovered dynamic generators

The preceding18-test/v1 recipe is historical and incomplete: v1 also excluded
shared-vertex pairs. Current `run_experiment.py` imports `independent_oracle_v2`.
Run23 analytic probes before the11 standard/annotation cases and exploratory
coplanar case. Current roof count is64, all64 omitted by BVH, all64 accepted by
the legacy narrow phase and independently certified by LP. Keep old v1 receipts.

From `experiments/oneshot_control`:

```sh
python3 independent_oracle_v2.py --self-test --out runs/strict-analytic.json
python3 run_experiment.py --out runs/strict --model assets/model.obj --cloth assets/cloth.obj --original-cloth assets/first-export-cloth.obj
python3 probe_coplanar.py --matrix runs/strict --out runs/strict-coplanar
unzip evidence/v2/old-241-inputs.zip -d runs/old-inputs
python3 audit_old_sequence.py --run runs/old-inputs --source independent_oracle_v2.py --out runs/old-strict.json
```

Observed full old audit:241 frames,161 self-intersection frames, first66, peak595
at146;3,554 added incident frame-pairs and2 documented submicrometre cutoff
differences. No thresholds were changed to match the old result.

