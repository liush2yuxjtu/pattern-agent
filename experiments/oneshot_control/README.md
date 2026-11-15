# One-shot assets and verifier calibration

**Current method: v2, with incident triangle pairs retained.** The original v1
oracle and its18-test/six-frame receipts are historical and incomplete: v1 shared
the legacy method's blanket shared-vertex exclusion. V2 passes23 analytic probes
and has now audited all241 old frames. See `evidence/v2/` for current results.

**Both the old garment and the verification method have problems.** Independently
checking six saved old frames confirms real garment self-intersections. New
controls expose two false approvals by the frozen legacy checker: an absent body
with stale paths, and coplanar cloth overlaps omitted by Blender's BVH.

## Two standalone files

- [`assets/model.blend`](assets/model.blend): one connected closed full-body mesh,
  including shoulders, arms, elbows, forearms, hands, legs and feet.
- [`assets/cloth.blend`](assets/cloth.blend): one connected preassembled T-shirt
  surface, with neck, hem and two open cuffs.
- Equivalent OBJ files carry readable geometry and embedded JSON annotations.

Each generator is one self-contained Python file. They import neither the old
garment generator, each other, nor external assets. The block shape is intentional:
its sleeve cavity and correct route are analytically checkable. These are static
T-pose controls, not realistic anatomy, sewn patterns, cloth simulation or fit.

```sh
blender -b -t 1 --python-exit-code 2 --python generate_model.py -- --out runs/body.blend
blender -b -t 1 --python-exit-code 2 --python generate_cloth.py -- --out runs/shirt.blend
```

The first garment export had incorrect sleeve face labels: lower torso side
faces were included. The legacy checker correctly rejected them. Only the
annotations were corrected; vertices and triangles are exactly identical.
The original annotation and equality receipt are retained. No geometry or cloth
physics parameters were tuned to obtain a positive control.

## Reproduce the experiment

Observed prerequisites: Python3.12, NumPy2.3.5, SciPy1.17.0, Blender4.3.2 on PATH.
From this directory, use fresh output directories:

```sh
python3 independent_oracle_v2.py --self-test --out runs/analytic.json
python3 run_experiment.py --out runs/controls
python3 probe_coplanar.py --matrix runs/controls --out runs/coplanar
blender -b -t 1 --python-exit-code 2 --python diagnose_broadphase.py -- \
  --case runs/coplanar/cases/coplanar_roof_overlap_only \
  --legacy ../full_arm/verification/geometry.py --out runs/broadphase.json
blender -b -t 1 --python-exit-code 2 --python reopen_and_render.py -- \
  --model runs/controls/model.blend --cloth runs/controls/cloth.blend --out runs/render
```

The public CLI generates both files, builds actual invalid mesh/path cases, runs
the frozen checker in Blender, then the independent checker. Exit0 means the
independent classifications meet the control expectations. It **does not mean
the legacy method passed**: inspect `all_collision_counts_agree` and each case.
Add `--original-cloth assets/first-export-cloth.obj` for the annotation error.
Add `--model assets/model.obj --cloth assets/cloth.obj` to reuse delivered assets.

## Independent method and measured cases

The v2 oracle uses NumPy/SciPy cKDTree bounding spheres/AABBs, triangle SAT, separate
coplanar area construction, topology and signed solid angles. It imports no
legacy code, Blender, mathutils or BVHTree. Twenty-three analytic tests ran before
the old-data comparisons. This is implementation independence, not formal proof.

For the rectangular sleeve, a separate analytic route oracle intersects the
actual polyline with x=±0.25m armholes and x=±0.53m cuffs, requiring outward order
and the complete intervening polyline inside the sleeve box. Current-route
segment midpoints must lie inside the actual body: unrelated supplied internal
coordinates cannot replace them. Connectivity, marked sleeve boundaries,
self-overlaps, cloth/body crossings and sampled containment must also pass.

| Actual case | Legacy arm / cloth geometry flags | Independent static wearing |
| --- | --- | --- |
| New body and garment | PASS / PASS | PASS |
| Both rotated and translated | PASS / PASS | PASS |
| Both uniformly scaled2x | PASS / PASS | PASS |
| Opposite diagonal on every quad | PASS / PASS | PASS |
| Left/right paths exchanged | FAIL / FAIL | FAIL |
| Path through sleeve fabric | FAIL / FAIL | FAIL |
| Path stops before cuff | FAIL / FAIL | FAIL |
| Body displaced2m, stale paths retained | **PASS / PASS** | **FAIL** |
| Sleeve roof pushed through lower wall | PASS / FAIL,6 self pairs | FAIL,6 self pairs |
| Front cloth pushed into body | PASS / FAIL,336 body pairs | FAIL,336 body pairs; additional self-overlaps |
| Original incorrect sleeve labels | FAIL / FAIL | FAIL |
| Coplanar roof fold, added diagnostic | **PASS / PASS**,0 self pairs | **FAIL**,64 overlapping pairs |

The first ten cases were specified in `protocol.json` before generation. The
annotation receipt preserves an actual export mistake. The final case was added
after the penetration control exposed a disagreement; it is explicitly exploratory.
All four positive controls pass and all eight invalid cases are rejected by the
independent static gate. This12-case result is not a general accuracy estimate.

## Two demonstrated false approvals

**Body/path association:** a valid closed full body translated2m away has zero
collisions with the garment. Supplied paths remain in the sleeves, so the old
flags both pass. All12 current-route internal samples are outside the body; the
new gate rejects it. The legacy router assumes trusted paths: that contract
cannot by itself support the stronger claim that the actual body wears the shirt.

**Coplanar overlaps:** moving one roof vertex from `(0.39,0.105,1.53)` to
`(0.39,-0.105,1.53)` folds cloth over cloth above the arm. The independent oracle
finds64 positive-area overlapping pairs, including10 incident pairs omitted by
v1's policy. All64 are absent from the legacy BVH candidate list, although direct
legacy narrow-phase calls accept all64. Passing a narrow-phase unit test did not
establish the integrated detector.
Independent interior-point/barycentric witnesses confirm real overlap, well above
tolerance-scale contact; receipts and a witness reproducer are included.

## Full old-cloth audit with v2

All241 saved frames were audited:161 contain self-intersections, with the first
at66 and a peak of595 pairs at146. Retaining incident pairs finds3,554 genuine
shared-vertex intersections previously excluded. A separate LP witness confirms
one intersection extends36.4948mm beyond its shared vertex. Two further count
differences are submicrometre segments counted under the SAT policy but ignored
by the legacy1µm common-segment cutoff; they are documented separately and are
not described as additional large penetrations. Body/self and cloth/body pair
counts remain0 in all241 frames. The geometry remains FAIL.

V2 detects crossings beyond a shared point/edge and ignores legitimate contact
using geometry, rather than dropping a pair merely because indices overlap.
V1's earlier table below is retained as a versioned result, not the final count.

## Historical v1 six-checkpoint result

| Saved old frame | Old self-pair count | Independent count |
| --- | --- | --- |
| 1 | 0 | 0 |
| 66 | 2 | 2 |
| 81 | 0 | 0 |
| 141 | 298 | 298 |
| 153 | 535 | 535 |
| 241 | 174 | 174 |

Cloth/body and body self-pair counts are0 in these six independent audits.
Every saved legacy example pair is in the independent set. The old report stores
at most20 examples per frame: this is count/example agreement, not complete
legacy pair-set equality. A full241-frame independent SAT audit has not been run.
The sampled failures already established genuine cloth defects. V2's complete
audit above supersedes v1 as the current result.

```sh
python3 independent_oracle.py --old-run evidence/old-fixtures --out runs/old-audit.json
```

Reproduce the complete current audit from the delivered synthetic inputs:

```sh
unzip evidence/v2/old-241-inputs.zip -d runs/old-inputs
python3 audit_old_sequence.py --run runs/old-inputs --source independent_oracle_v2.py --out runs/old-v2.json
python3 certify_shared_vertex.py --npz runs/old-inputs/frames/frame-0153.npz --pair 2349 2351 --out runs/shared-witness.json
```

`MANIFEST-v1.sha256.json` belongs to the frozen v1 publication at commit76c3c4c.
`MANIFEST.sha256.json` describes this current checkout. V1 and v2 receipts remain
separate so their different adjacency/contact policies can be compared honestly.

Inputs, hashes, receipts and actual Blender renders are under `evidence/`.
Each .blend was reopened: one mesh, no linked libraries/external assets, matching
OBJ coordinates within0.00006mm. The cutaway is labeled as a diagnostic view.

Old full-motion Cloth FAIL remains. This static package itself runs no cloth
simulation. Recovered exact generator sources and a new121-frame dynamic
reproduction are in `../oneshot_motion`; they do not approve physical fit.
See [`HANDOFF.md`](HANDOFF.md) for the next engineering steps.
