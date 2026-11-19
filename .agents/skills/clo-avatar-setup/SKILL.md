---
name: clo-avatar-setup
description: Select and measure a CLO 3D avatar for garment drafting and fitting. Use CLO stock avatars or a supplied avatar or project, adjust supported measurements, hand measured body dimensions to FreeSewing, and verify that the loaded fitting avatar matches the pattern's target body measurements.
---

# CLO avatar setup

Honor the user's skill approval and desktop-focus preferences. Prefer the existing CLO bridge. Keep the user's active project safe by using a working copy for changes.

## Select the avatar

1. Identify the target wearer, garment, required body dimensions, and test purpose. Reuse the avatar designated by the user or saved in the supplied CLO project. Otherwise choose a suitable stock model from [CLO Library → Avatar](https://support.clo3d.com/hc/en-us/articles/115013820508-Does-CLO-come-with-default-Avatars).
2. Check `clo_status` and `scene_info`, list scene and library assets with `avatar_list`, and load the selected asset using `avatar_load` in the working scene when needed. Confirm the loaded identity before measuring. If the bridge is unavailable, report which live actions are pending.
3. With target body measurements, select the closest body and adjust supported dimensions with [CLO Avatar Editor](https://support.clo3d.com/hc/en-us/articles/360013257553-Adjust-Avatar-Size) or a supported, verified bridge operation. Measure again after adjustments since other dimensions can change. For a generic prototype without wearer measurements, use the selected avatar as the sample body.

## Measure and hand off

- Read the loaded avatar through `avatar_measurements` or CLO measurement tools. Refresh after changing the scene or body. Record the reading source for each dimension and any estimate, unavailable value, or uncertain mapping. Verify that cached data belongs to the exact avatar and settings, and label mesh-derived measurements as estimates.
- For FreeSewing, inspect the actual design's required measurement keys. Map measurements only when anatomical landmarks, measurement paths, units, and side or front/back conventions agree. Normalize values to millimetres, record the mapping, and flag missing inputs. Pass the actual measured set to the drafting skill for avatar-first prototypes. Label any assumptions used for sample drafting.
- For an existing pattern or after drafting, compare the loaded avatar against the exact body dimensions used to produce the checked FreeSewing draft, or the target body measurements documented for a DXF. Use the garment's fit requirements and the user's acceptance criteria to assess differences. Record target, actual, difference, and reading source for each item. Resolve fit-relevant mismatches before claiming a matched fit. With missing targets or a proxy avatar, mark the result exploratory. Use finished pattern measurements separately to calculate garment ease.
- Pass the avatar identity, asset or project path when available, size adjustments, pose used for measurement, and the body measurement record to the next skill. For retests, confirm that the same avatar and sizing are loaded unless the test intentionally changes them.
