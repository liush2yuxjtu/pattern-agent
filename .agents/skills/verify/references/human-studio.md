# Anatomical human editor

Working directory: repository root. Surface: `web/human-studio/` and its source
asset builder. Follow root AGENTS: local verification, direct-main non-force
push; existing Pages publication only, no CI or permission changes.

## Run and verify

Build with `python scripts/build_pages.py`, then serve `dist/` on loopback HTTP.
The browser verifier launches and closes its own Chromium. Use
`CHROMIUM_BIN=/usr/bin/google-chrome` on the documented public remote host.

```sh
node scripts/verify_human_studio.cjs --url http://127.0.0.1:PORT/human-studio/ \
  --output work/human-studio-verify
python scripts/verify_human_studio_geometry.py --output work/human-studio-verify
python scripts/test_human_studio_geometry.py --fixture work/human-studio-verify
```

Require actual range/number input to change anatomical mesh vertices and pixels;
all 12 measured dimensions must match their targets within 0.2 cm for the exercised
cases. Check neutral measurements independently of pose; move an elbow and
finger, exercise all presets, and require finite skinned vertices. Test the
195cm height framing, actual 375CSSpx mobile viewport, stale/off-step state,
save/reload and import equality. PNG must have actual double renderer dimensions.

Save and reopen actual JSON, OBJ and rigged GLB downloads. The independent NumPy
validator recomputes tape paths from actual renderer vertices and decodes GLB
accessors, node matrices, inverse binds and skin weights without importing the
browser calibration/skinning code. Require posed OBJ coordinates in cm and
GLB world coordinates in metres to match the visible model. Negative controls
must reject a falsified body dimension, displaced OBJ vertex and 100×GLB unit
error. Do not promote numerical model agreement to anatomical recovery or
physical garment fit.

Open the desktop, adjusted-pose, seated and mobile screenshots with view_image.
Persist source hashes, exact candidate/base, raw observations, commands, verdict
and cleanup under `docs/verification/human-studio-20261117/`.

## Publication

Preserve existing Pages routes. Use the existing publish-only workflow after
the verified main push. Rebuild/recheck the exact candidate before push; add
`--expected-commit SHA` to the browser verifier when `build.json` is available.
Check the actual deployment SHA and live URL; a workflow conclusion alone is
not browser acceptance. The local VM may block the Pages domain: use the
documented public-only Firecrawl Bash/standalone Chrome fallback. Transfer only
public pinned verifier sources, verify their hashes, run the same verifier and
independent file audit, recover only the task-owned evidence, and stop the
session. Never inspect unrelated remote processes or temporary files.

Record a documentation-only SKIP gate if later committing already-verified live
receipts. Close task browsers/servers; preserve historical cloth FAIL/NOT_RUN.


## Actual model measurement export

Run `node tools/human_fit/verify_measurement_export.cjs --url URL --out OUT`
against an actual saved model link or the default editor. It independently
remeasures all12 values from actual renderer vertices and the real downloaded
neutral OBJ, reopens JSON/CSV, and checks source hashes. Exercise shape edits
with full pose preservation, pose-only edits with neutral dimensions preserved,
false cached measurements, wrong units, pending65ms shape updates and an
unreachable target combination. Input targets must not replace achieved mesh
values. Save screenshots and downloaded files; the report is model-size export
verification, not photo or person accuracy. Run the existing full editor and
independent OBJ/GLB validators to preserve the original export contract.

Reopen neutral downloads with the packaged standard-library CLI:

```sh
python .agents/skills/garment-body-six-view/scripts/export_body_measurements.py \
  --state OUT/edited-state.json --asset-json web/human-studio/assets/human.json \
  --neutral-mesh OUT/edited-neutral.obj --out OUT/independent-measurements.json \
  --csv OUT/independent-measurements.csv
```

Use the matching initial/edited/residual state and OBJ, never a posed OBJ.
Original historical eval files/grades remain immutable; post-run remeasurement
is published separately under each commerce case review/. The commerce browser
verifier independently remeasures all displayed primary dimensions from the
actual OBJ and checks real JSON/CSV download hashes.
