#!/usr/bin/env bash
set -euo pipefail
# Run from /workspace/work/pattern-agent; existing outputs are regenerated identically.
base=work/model-size-skill-evals-20261118
out="$base/iteration-1/eval-1-saved-model/with_skill/run-1/outputs"
python "$out/export_body_measurements.py" --state "$base/inputs/saved-model/final-state.json" --asset-json "$base/inputs/human.json" --neutral-mesh "$base/inputs/saved-model/neutral.obj" --posed-mesh "$base/inputs/saved-model/posed.obj" --out "$out/measurements.model.json" --csv "$out/measurements.model.csv"
python "$out/verify_saved_geometry.py"
