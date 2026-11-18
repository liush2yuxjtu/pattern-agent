# Conditional-avatar skill hill climb

User requested continued improvement until this full reference-photo workflow passes verification. Historical11/13 remains immutable at `/garment-body/full-imagegen-evals/eval.html`. Current original13 semantic statements are preserved verbatim. The inherited regional-v1 limits8% outside/25px P95/min1000px/scanlinecenter45px,width0.55..1.15 are unchanged and now all actually executed. New prospective observable generation/grasp limits were frozen before inspecting new generated candidates; they do not prove exact hidden3D or real-person body dimensions.

## What actually changed

- Real body camera/root/spine/hip/upperleg fitting: previously unoptimized hip/leg articulation caused waist-hip drift. Dimensions stayed fixed; shrinking the avatar cannot rescue containment. Standing support is a disclosed unobserved-leg prior, not force/balance verification. Sampling domains now scale with actual neutral height; actual170 replay unchanged and180 domain probe nonempty.
- Grasp solver uses camera/body-relative wrist/MCP/pinch targets, actual arm-skin envelope, whole hand/torso clearance and hand/finger surface repulsion. Fixed a real FK/LBS floor mismatch after standing changes (~23px), not a label-only issue. Helper finger-tail vertices are not rendered body surface; tail-gap alone previously hid terminal finger intersections. Actual same-hand and inter-hand surface checks are separate.
- Bundled `run_model_fit.py` runs actual raw-guide registration, body stages, grip and final OBJ measurement with input/runtime hashes. Cases carry coordinates/regions/contact assumptions. Frozen skill61 files and runtime11 files were supplied to a fresh executor, which reran from the old failed input rather than copying a development final.
- Generation uses each final model camera render as its actual condition. Flat grey side rendering confused the generator's near arm with chest; a same-camera semantic render resolves near/far limb identity. Side guide deliberately uses+Z screen-horizontal/+X front-depth (horizontal reflection of a conventional+X camera); projection parity is declared, not per-output fitted warp.

## Actual execution and retained failures

A fresh isolated executor actually ran registration +70/100/100body stages +grip +neutral-mesh exporter. The independent grader reimplemented/reopened actual geometry, camera projection, measurements, contact and surface checks. Editor integration was actually driven again,22 checks: import fresh state, waist+2cm, arm+7deg, real JSON/CSV/OBJ download/reopen/reimport. Original final state was preserved.

The executor made16 actual Image Gen calls:15 native PNG outputs and1 output-moderation refusal with no image. Root separately made the current raw-guide call. Failed/retired views and the blocked receipt are preserved, not counted as successful images. No retry of anatomical closeup refs after refusal: the replacement path uses fully clothed references and the binary model silhouette. A fixed2.5x camera-transform image is clearly an input correspondence reference only; the delivered closeup is a new independent native Image Gen result. Versions4/5 incorrectly lowered the hem and were rejected despite good containment; version6 restores the actual hem-lifting action.

Selected native files are front2,side3,back1,closeup6,pose2,depth2, each1024×1536 with byte-identical original tool output, actual prompts/ref paths/SHA/native paths. Root independently rechecked all six native and reference hashes. No collage cropping or external upscaling is represented as native output. The editor-probe is a separate edited model copy, not the selected final state.

The frozen-skill execution received independent diagnostic feedback and real retakes. It is not a blind, one-shot autonomous result or a fresh paired old/new superiority benchmark. Historical baseline is REUSED_HISTORY in official Previous Output. Current semantic-input tool and documentation lessons added during feedback are separately marked post-freeze; they are not retroactively attributed to the frozen runtime.

## Independent quantitative evidence

Current original-photo model: all7 inherited regions and4 anti-shrink scanlines pass. Hand/torso covered rays have zero inside classifications with98.95%/99.93% coverage; uncovered rays are not proof of no collision. Actual interhand and terminal thumb/index contact pairs are zero. Fingerpad proximity and helper bone endpoints have separate definitions. Independent arm audit finds zero remote upperarm/elbow/forearm–torso intersections;8 proximal axilla lines are within4 topology hops and explicitly disclosed local folding, not a claim of globally collision-free physical skin.

Full-body generated views use27 independently annotated visible/surface-approximate anchors and fixed4/3 canvas normalization only: front mean0.598%H/max0.908%; side1.309%/2.007%; back0.859%/1.758%. Body outside generated-clothing envelope: front2.235%, side7.9543% (close to8% boundary), back6.119%; this is not a robust across-prompt guarantee. Pose/depth foreground IoU with accepted front is0.992158/0.979970. Closeup6 envelope outside1.5393%,P9518px;8 known-crop anchors mean1.167%H/max1.942%. No output is warped/reframed to obtain a pass.

12 primary dimensions are independently remeasured from final neutral OBJ; JSON/CSV error~3.55e-15cm and neutral/posed reconstruction~5e-9cm. These are the conditional M170 avatar's actual geometric measurements, not measurements of the photographed person. Source wrist audit also catches a misleading Image Gen blue dot: raw(184,773) lies on hand-back proxy, actual cuff/skin wrist≈(145,760). Markers remain use_for_fit:false; the44px wrong-node difference is not falsely reported as model wrist error.

## Verification scope

Project `/verify`: `.agents/skills/verify/SKILL.md`, `references/skill-evals.md`. Existing37 skill tests and20 eval-tool tests passed; actual CLI positive replay, malformed-case/asset controls, semantic-render camera/topology probes, independent geometry fault controls and real browser actions are the substantive evidence. Final grading/browser/archive receipts are appended after execution completes.

This is one known reference-photo task, N=1. Hidden mathematical3D identity and real-person size accuracy NOT_VERIFIED; native Claude triggering BLOCKED (no native runtime); physical cloth fit NOT_RUN. Historical cloth FAIL is unchanged. Official gallery/feedback supports human review; automation feedback is test data, not user approval. Publication success is distinct from live public browser interaction.

Review: https://liush2yuxjtu.github.io/pattern-agent/garment-body/hillclimb-evals/eval.html


## Final local /verify

Original semantics13/13, prospective quantitative gates18/18, overall conditional-case PASS. Final grading SHA256 `43244ceccaf54ba8828b019e1e02e74fc5065ca7480be9b840a3aa294e167f9e`, frozen204 outputs and203 independent evidence files. Root rechecked the actual204 output inventory against this final grade. Fixed manual observations are hash-bound; missing manual and stale TRACE real controls reject without generating PASS. Preliminary draft40d98 was superseded before final archives, not published as final grade.

- `python -m unittest discover -s .agents/skills/garment-body-six-view/tests -q`:37 PASS.
- `python -m unittest discover -s tools/skill_evals -p 'test_*.py' -q`:20 PASS after shared-builder changes; old native receipt/default-path regression remains valid.
- Pinned Anthropic package CLI and quick_validate:valid. Actual downloaded updated23-member .skill reopened by root, every entry source-identical and CRC clean.
- Actual fresh human editor22/22; standalone skill-page browser22/22.
- `node tools/skill_evals/verify_hillclimb_review.cjs --url http://127.0.0.1:8967/garment-body/hillclimb-evals/eval.html --out .../browser/final-source --expect-acceptance PASS`:314 PASS.
- Same CLI at root dist8971 final-dist:314 PASS, zero page/console/HTTP errors. Actual6 local primary native images, all original13+18 displayed, real12-item JSON/CSV downloads/reopen, remote full-run and selected-six ZIP click/download/CRC/entries, four rejected external native PNGs HTTP/SHA/decode, Previous Output history, feedback persistence/download, mobile, actual final-state Human Studio handoff. Root actually viewed `browser/final-dist/four-stage-gallery-verified.png` and verified final hero overlay/selected images. Automation feedback is not human acceptance.

Source's first Node APIRequest remote probe hit EAI_AGAIN because it did not inherit the existing HTTPS_PROXY; preserve that failure. Verification CLI now explicitly uses the same configured proxy already used by curl/Chromium. Endpoints/TLS are unchanged, no response mocking. Final source and dist actually downloaded the real raw GitHub data.

## Publication data and site budget

Global site exceeded the Pages budget with this evidence. Only this new site's ZIP presentation copies and four rejected closeup history PNG copies were moved to content-addressed files under `eval-artifacts/full-imagegen-hillclimb-20261118`; all bytes remain in the same GitHub repository. Eight byte-identical derived-input aliases deduplicate4,290,348bytes. Six selected primary native images remain directly in Pages; old historical sites/grade bytes were not rebuilt or edited.

Artifact-only `/verify` receipt was committed and non-force pushed as `2d301c8eeb7448cb8d590ce5ce41bcf3844655cb` after reconciling unrelated main changes. Root actually downloaded all8ZIP+4PNG raw URLs, verified sizes/SHA and allZIP CRC; selected-six canonical files match actual selected native files, full-run holds all204 bound outputs and exact final grade. Remote readback receipt is retained. No source/page release was represented by that data-only commit.

Final `python scripts/build_pages.py` plus source-verifier copy synchronization yields1,066,788,495bytes (<1GiB1,073,741,824), about6.95MB headroom. Current input/reference/runtime/grade fingerprints retained. Source and dist browser servers are stopped after verification. Final code/skill/page commit follows these checks; existing publisher is delivery only, not hosted CI verification. A publisher success does not substitute for live public browser interaction.
