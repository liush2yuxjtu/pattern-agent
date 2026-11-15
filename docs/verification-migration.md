# Verification migration / evidence provenance

This repository uses `.agents/skills/verify/SKILL.md` derived from [dot-pi](https://github.com/liush2yuxjtu/dot-pi/blob/main/agent/skills/verify/SKILL.md).

## Source archives (recovered and tested locally)
- `pattern-agent-tshirt-validation-20261111.zip`: T-shirt Blender 4.3.2 / 120-frame evidence.
- `garment-lab-linux-v0.2.0.zip`: Garment Lab v0.2, 12 synthetic skirt candidates, historical Boat dual-host evidence.
- `digital_tshirt_lab.zip`: earlier source snapshot.

## Retained checker boundaries
- `pattern_agent/verify_artifacts.py`: independent artifact scale/geometry checks.
- `pattern_agent/verify_blender_runtime.py`: independent Blender frame/cache checks.
- `tests/test_geometry.py`, `legacy/garment-lab-v0.2/tests/`: executable assertions.
- `run_pipeline.py`: product generation pipeline, not generic verification policy.

Historical `legacy/garment-lab-v0.2/verify.sh` and `run_verified.py` were redundant orchestration; do not reintroduce them. Retain real computational checks. No new generic GitHub Actions workflow should be added; there were no workflows identified in the recovered archives.

## Results and constraints
Recovery environment local suite: 13 Pattern Agent tests PASS, 50 Garment Lab tests PASS. Geometry-only execution and independent artifact check PASS. Cloth reference quality FAIL: seam gap 7.6455 mm (>2 mm) and 20 nonadjacent cloth face intersections (>0). Full-arm passage BLOCKED; physical sewing/fit NOT_RUN. Running the full software tests does not mean the garment is fit-approved.

## Remote import status
The archive recovered locally includes 53 UTF-8 source/evidence files, but GitHub MCP does not accept a filesystem archive as its content argument. **Until all source paths are committed and re-read, remote repository code import is INCOMPLETE.** Do not claim full repository verification from local-only results.

Use direct small commits to `main`; no PR or Issue. Verify remote HEAD before changes, never force push.
