# Human Studio: anatomical body, centimetres and pose

Use the working anatomical editor for the product workflow:
https://liush2yuxjtu.github.io/pattern-agent/human-studio/

Repository implementation: `web/human-studio/`. The current adult-female
MakeHuman mesh/morphs/rig are CC0; the Three.js renderer is MIT. Record the
actual version and asset SHA256 from the saved state and provenance, rather
than assuming every future model uses the same asset or body template.

The editor has 13,380 surface vertices, 26,756 triangles and 163 bones. The
older loft models in the functional evaluation history are synthetic controls,
not the current product model. Reuse the anatomical model before constructing
another proxy. Use a different appropriately licensed anatomical template when
the task requires it; do not silently present this female template as every body.

## 1. Configure shape in cm, then pose in degrees

Open **Body dimensions**. The current keys are:

| Key | Dimension / definition |
| --- | --- |
| `height` | Standing height in neutral pose |
| `bust` | Closed mesh bust tape path |
| `waist` | Closed mesh waist tape path |
| `hips` | Closed mesh hip tape path |
| `shoulders` | Bilateral acromion landmark distance |
| `upperArm` | Upper-arm circumference |
| `thigh` | Thigh circumference |
| `neck` | Neck circumference |
| `upperArmLength` | Upper-arm landmark distance |
| `forearmLength` | Forearm landmark distance |
| `thighLength` | Thigh landmark distance |
| `calf` | Calf circumference |

Expand **Arms, legs & neck** for the additional controls. Current size inputs
are cm with 0.1 increments. Authored morph targets are numerically calibrated
against mesh paths/landmarks. Compare requested and measured values; if the
bounded morph envelope cannot reach a target, preserve the reported residual
and closest measured result. Do not report the requested value as achieved.

Use **Pose & joints** for local XYZ rotations in degrees, also with 0.1
increments in the current UI. Primary joints include shoulders, elbows, wrists,
hips, knees, ankles, spine, neck and head. The full menu includes fingers and
face bones. Mirror editing is optional. UI presets map to:

| UI preset | API name |
| --- | --- |
| Neutral | `neutral` |
| T-pose | `tpose` |
| Walking | `walk` |
| Seated | `sit` |
| Arms up | `reach` |

Verify actual vertex and image changes. A posed bounding-box height is not
standing height. Neutral dimensions stay separate from pose, and linear-blend
skinning is not a tissue, joint-collision or cloth simulation.

## 2. Supported programmatic integration

Wait for `window.humanStudio?.ready`. In the editor page's JavaScript context:

```js
const model = window.humanStudio;
model.setDimensions({height: 170, bust: 90, waist: 70, hips: 96});
const saved = model.getSnapshot();
model.setPose({...saved.poseDegrees, "lowerarm01.L": [65, 0, 0]});
const state = model.getSnapshot();
const geometry = model.getGeometry();
```

These numbers are an example mannequin configuration, not estimates of the
reference person. `setDimensions` merges supplied dimensions with current ones.
`setPose` replaces the entire pose map; merge the previous map when changing a
single joint. `preset(name)` resets existing joint edits. These APIs do not
provide photo fitting, image generation, inverse kinematics or medical measures.

`getGeometry()` returns actual renderer rest vertices (flat XYZ), posed surface
vertices, `bodyVertexIds`, triangle `indices` and world joint positions. Rest
data includes non-rendered landmarks; indices refer to the original vertex
buffer. When building a surface-only mesh from `posed`, remap original indices
through `bodyVertexIds` instead of assuming they index the compact posed array.

The model has no exposed camera-state restore or depth-export API. Do not invent
one. Dimensions, presets and Fit view can reframe the camera; grounding can
change the pose's world offset. For strict image comparisons, finish shape/pose
first and freeze explicitly recorded camera settings in an independent renderer.

## 3. Save state and real exports

Use **Save model** and keep the exported JSON with the run. Its contract is:

| Field | Meaning |
| --- | --- |
| `version` | Model/state implementation version |
| `asset` | SHA256 fingerprint of the matching `human.json` |
| `units` | `cm` |
| `dimensions` | Requested neutral-pose dimensions |
| `measuredNeutral` | Dimensions calculated on the neutral mesh |
| `maximumTargetErrorCm` | Largest requested/measured difference |
| `morphWeights` | Calibrated coefficients for exact shape restoration |
| `poseDegrees` | Complete edited joint map, local XYZ degree triples |

Import only compatible version/fingerprint data. Keep morph coefficients and
pose, not just visible numbers. Internal browser cache uses implementation
fields that differ from this export contract; use Import or the supported APIs
rather than writing arbitrary cache objects.

- **PNG 2×** rerenders the actual current view at double pixel dimensions. Save
  the observed width/height; it is a 3D snapshot, not a new photographic output.
- **Export OBJ** contains the actual posed surface in centimetres, without a rig.
- **Export GLB** contains current shape, pose and rig, using standard metre world
  coordinates. Its 0.01 conversion and centimetre dimension metadata are explicit.
  Recalibration in cm remains in this editor; GLB is not a standalone Blender
  centimetre-control plugin and does not bundle this skill's solver UI.

JSON and GLB exports do not save the viewer camera. Preserve camera/projection,
viewport, model/pose identity and file hashes separately for image evidence.

## 4. Coordinates and measurements

Human Studio uses X left/right, **Y up**, Z front/back. OBJ values are cm; GLB
world coordinates are metres. To express a Y-up cm mesh in a Z-up metre system,
one explicit right-handed transform is `(x, y, z) -> (x, -z, y) / 100`.
Apply transforms consistently to geometry, normals, joints and inverse binds.
If the importer already handles glTF units/axes, do not apply the conversion
again. Confirm actual dimensions/bounds rather than relabelling units.

Tape paths and mesh-plane intersections are different definitions. A tape path
can be nonplanar and should be reported as `surface_tape_path`; use
`landmark_distance` for shoulder/limb lengths and `standing_height` for height.
Do not substitute shoulder joint spacing, clothed outer width or posed height.
When using a Y-up horizontal section, the normal is `[0, 1, 0]`; choose actual
anatomical levels and component seeds instead of copying a fixed height.

These dimensions have basis `mesh_parameter` (or an explicitly labelled prior),
not `observed_scaled` simply because the model can be measured. Keep the original
image evidence, scale assumptions and unavailable landmarks separate.

## 5. Verify state, surface, pose and files at their actual boundaries

The bundled helper runs with Python standard library only:

```sh
python scripts/inspect_human_state.py --state human-model.json --out state-check.json
python scripts/inspect_human_state.py --state human-model.json \
  --asset-json PATH/TO/human.json --expected-asset ASSET_SHA256 \
  --require-match --out neutral-mesh-check.json
```

Without the matching asset, this validates structure only. With the asset it
checks its fingerprint, reconstructs neutral vertices from saved coefficients
and independently recomputes tape/landmark dimensions. A valid closest-supported
state is distinct from achieving all target sizes; `--require-match` rejects a
largest residual above 0.2 cm. This is a numerical model tolerance, not a human
measurement error bound. It does not validate posed GLB skinning or image fit.

For full repository verification, use the actual editor, save/download/reopen
files, and run the independent geometry validators from repository root:

```sh
node scripts/verify_human_studio.cjs --url HUMAN_STUDIO_URL --output RUN_DIR
python scripts/verify_human_studio_geometry.py --output RUN_DIR
python scripts/test_human_studio_geometry.py --fixture RUN_DIR
```

The browser verifier exercises all 12 dimensions, real elbow/finger deformation,
presets, framing, cameras, save/reload/import, actual mobile viewport and exports.
The independent NumPy audit decodes OBJ/GLB geometry, joint matrices, inverse
binds and weights. Corruption controls reject false dimensions, displaced
vertices and a 100× unit error. These repository tools are not bundled with the
small skill package; clone Pattern Agent or use an equivalent independent audit.

## 6. Use this model with the original product photo

Preserve the original photo's source/hash. Save calibrated body state, complete
pose, neutral mesh measurements and actual 3D snapshots before generation.
Provide the product photo for garment appearance and the versioned mannequin
renders for shape/pose. Keep the six independent clothing-image contract:
front, side, back, close-up, pose lines and relative depth.

Human Studio does not generate those six clothed images, reconstruct a person
from photos, run Depth Anything, or certify garment fit. Its skeleton overlay
is a 3D rig projection, not a detector result. Obtain depth from a real renderer
Z-buffer or an actually executed estimator; label illustrative alternatives.
Continue comparing original observations and generated-view consistency
separately, with unchanged references and a frozen final camera protocol.

Current editor: https://liush2yuxjtu.github.io/pattern-agent/human-studio/

Historical functional review:
https://liush2yuxjtu.github.io/pattern-agent/garment-body/eval.html

Model verification and actual screenshots:
https://github.com/liush2yuxjtu/pattern-agent/tree/main/docs/verification/human-studio-20261117


## 模型实测尺寸是主要输出

Body dimensions 输入框调整控制目标，其下 Model measured 始终显示实际 neutral mesh 数值。
Export measurements 与 CSV 从当前真实顶点重新测量，Neutral OBJ 导出对应中性表面；
Save model 仍保存可调状态，原有 Export OBJ 仍为摆姿后的 cm 网格。GLB 为 m。
实测 JSON 使用 measured_values_cm，目标另存 target_dimensions_cm，附完整捕获状态、
资源/网格/姿态指纹及测量路径。等待形体重建完成才导出，不用摆姿后包围盒替代站立身高。
导出后可用包内 export_body_measurements.py 在中性 OBJ 独立重测；方法/字段见
[模型实测合同](model-measurements.md)。模型实测不宣称原照片真人围度已验证。
