## Chat verification recipe — 2026-11-15 — full-arm executable publication

Current checkout includes a recovered documentation skeleton. The old root
`pattern_agent`, `tests`, `legacy/garment-lab-v0.2`, and root paper-pattern pipeline
are not restored; the older commands above cannot currently establish a PASS.
Do not count an empty unittest discovery as successful coverage.

The executable synthetic experiment is `experiments/full_arm`. From that directory:

```sh
python3 -m unittest discover -s verification -p test_pipeline_gate.py -v
blender -b -t 1 --python-exit-code 2 --python verification/test_geometry.py
python3 run_pipeline.py --out runs/publication-smoke --frames 3
```

Observed prerequisites: Python3.12, Blender4.3.2 with NumPy. The smoke produces real
Cloth geometry, routes it through the public pipeline CLI, checks 3 saved frames,
runs7 real negative controls, renders6 key-view images and independently reloads
the portable .blend. Expect8 coverage tests and16 analytic tests, plus
execution_complete=true and a3-frame initial-pose geometry PASS. This prefix smoke
does not establish the complete241-frame motion or material/fit quality.

Full motion command: `python3 run_pipeline.py --out runs/full-arm --frames 241 --render-video`.
Its frozen baseline has ARM_ENTRY_PASS241/241 and CLOTH_SIM_FAIL161/241; this is
an intentional diagnostic reproduction, not a physical fit approval.

Keep logs, candidate source hashes, result status and independent reload evidence
in `docs/verification/`. Before each commit record the exact candidate base and
source manifest; after push independently read the remote head and files.
