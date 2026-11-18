#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
TASK_ROOT=../../../../..
python "$TASK_ROOT/skill-old/scripts/inspect_human_state.py" --state "$TASK_ROOT/inputs/saved-model/final-state.json" --asset-json "$TASK_ROOT/inputs/human.json" --out state-check.json
python measure_saved_model.py
