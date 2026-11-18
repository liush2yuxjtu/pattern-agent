#!/usr/bin/env bash
set -eu
python work/model-size-skill-evals-20261118/iteration-1/eval-3-consistency-check/old_skill/run-1/outputs/audit_consistency.py
python work/model-size-skill-evals-20261118/skill-old/scripts/inspect_human_state.py --state work/model-size-skill-evals-20261118/inputs/consistency-check/final-state.json --asset-json work/model-size-skill-evals-20261118/inputs/human.json --out work/model-size-skill-evals-20261118/iteration-1/eval-3-consistency-check/old_skill/run-1/outputs/state-reconstruction.json
