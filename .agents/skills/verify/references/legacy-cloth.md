# Historical cloth surface

The commands below are historical: root modules were not restored. Do not run
empty discovery and claim PASS. Use the matching current experiment recipe.

## Pattern Agent project requirements

Local test: `python3 -m unittest discover -s tests -v`.
Legacy test: `cd legacy/garment-lab-v0.2 && python3 -m unittest discover -s tests -v`.
Product workflow: `python3 run_pipeline.py --out /tmp/pattern-agent-verify-$(date +%s)`, in a fresh directory with Blender available.
Geometry-only fallback: `python3 run_pipeline.py --geometry-only --out /tmp/pattern-agent-geometry-$(date +%s)`; report Cloth NOT_RUN.

Inspect `pattern_agent.verify_artifacts` and `pattern_agent.verify_blender_runtime` for independent checks. These checkers contain reusable assertions, not a policy-level monolithic verify gate. Preserve them. Verify SVG dimensions, PDF calibration, garment seam mappings, Cloth frame outputs, complete frame cache and SHA-256 evidence.

Known T-shirt baseline: max seam gap 7.6455 mm vs <2 mm, 20 cloth self-intersection pairs vs 0. The historical cloth result is FAIL, not PASS. The archived mannequin lacks full arms; armhole→sleeve→cuff passage is NOT_RUN/BLOCKED until a full-arm scene and negative controls exist. Fabric calibration, printing, sewn sample, human wear fit are NOT_RUN.

Before direct `main` commit: run impacted checks, read the remote HEAD, avoid force push, record exact runtime claim and limitations. This repository deliberately uses no PR, no Issue, and no generic GitHub Actions verification CI; do not lower safety standards or fabricate runtime PASS. Do not delete actual tests merely because an old shell wrapper is removed.
