# Full Image Gen → adjustable body → overlay → measurement acceptance

User rejected a measurement-only verification: this run actually exercises the complete requested workflow. This is one candidate and one source photograph, not a paired skill superiority experiment or native Claude trigger evaluation. The exact executed skill is frozen and downloadable separately from subsequent documentation corrections.

## Actual execution

Original ASOS red pointelle outfit photo1000×1276 is preserved byte-identically with product URL/source hashes. Root viewed raw and mannequin input and invoked image_gen.imagegen seven times this round: six standalone deliverables plus separate raw-photo pose guide. Front uses original plus explicitly historical anatomical-render guidance; other five use original plus newly generated front. Each native file is copied byte-identically with actual prompt/reference hashes, original tool path and native dimensions in generation-receipts.json. Five deliverables1024×1536, closeup1199×1312; raw guide1110×1417. No collage crop or interpolation. Tool model/resolution controls unavailable, so no settings invented. Pose/depth are illustrative, not detector/Depth Anything/calibrated outputs. New final fit happened downstream and was not this batch's generation input.

Separate pose-fit subagent actually ran five candidates, including neutral initialization, upright constraints, wrist refinement and waistband-anchor semantic correction. Same saved final MakeHuman state drives all real views; camera matrices and neutral/posed mesh fingerprints are retained. Source original and generated-photo consistency are distinct scopes. Independent grader reads actual images and reimplements reconstruction/measurement/projection/ray checks rather than importing the exporter/runtime as oracle.

Fixed final-camera original-photo IoU0.6858→0.8220 and body outside clothing mask12.59%→3.72%. These are mask diagnostics, not human measurement accuracy or full contour fit. Left/right waist-hip P95 remains32/36px and right region outside10.38%; palms remain cup-like/upward and too far forward. Independent ray checks reproduce L455/1424 coverage/min18.436949435cm, R1424/1424/min4.518556425cm; partial coverage is not no-collision proof. Overall original-action visual/3D matching FAIL. Generated side/front/back same frozen3D pose is also not established.

Final model dimensions are actually remeasured from final neutral OBJ, not read from controls/cache: height169.99997868cm, bust90.00003182cm, waist71.00000242cm, hips96.00004043cm, shoulders36.39999983cm; full12-item JSON/CSV includes definitions/targets/residuals. These are a hypothetical M170 conditional model's measurements, not real-person measurements.

Human Studio public application: actual final-state import → waist+2cm preserves pose → upper-arm angle+7° preserves neutral measurements → export/reopen/reimport.22 checks PASS. Edited probe is separate and does not replace selected final model.

## /verify and scope

Project verifier: `.agents/skills/verify/SKILL.md`, `references/skill-evals.md`. Read before commit. Execution candidate began at e835ae7fbedd9426b159bfed17d6eae43a7cf23a; later reconciled unrelated remote changes, preserving task sources and artifacts.

Supporting tests:37 canonical skill tests PASS;20 eval-tool tests PASS; quick_validate valid. These support helper behavior; actual generated images, model fitting, independent audits and browser checks establish this run's end-to-end evidence.

Official pinned Anthropic reviewer is used with native Prompt/Output/Grades/Feedback/Benchmark/navigation. All four-stage galleries, failure summary and downloads are inside native Output. Missing/stale independent grades and source-generation fingerprints reject strict builds before publishing. Full executor intermediates remain in compressed reproduction ZIP; selected public files are separately inventoried, and complete output SHA inventory stays bound to independent grades. Absent baseline has no comparison delta; unknown token/duration telemetry stays null.

The skill documentation now explicitly prevents substituting a measurement-only suite for an end-to-end request and requires distinct generation-versus-final-model lineage. These are post-execution documentation changes, not retroactively substituted into the executed snapshot.

Functional chain executed; original pose/3D match FAIL. Real-person body-size accuracy NOT_VERIFIED; native Claude trigger BLOCKED; physical cloth fitting NOT_RUN. Historical physical cloth FAIL unchanged. Live public browser interaction is separate from local dist/browser and publisher status; do not infer it from publication success.

Final independent-grade/browser/package receipts are appended below after actual completion. Review: https://liush2yuxjtu.github.io/pattern-agent/garment-body/full-imagegen-evals/eval.html


## Independent final grading

Frozen expectations:11/13; overall FAIL. Assertion4 (same exact generated body/pose) and10 (original-action local/3D match) fail. This fraction is not match accuracy. All388 executor files are recursively SHA-bound; output changes invalidate grading. See public grading and independent audit ZIP. Independent neutral/posed reconstruction max~5e-9cm, measurement error<4e-15cm, photo mask exact pixel equality; separate ray-triangle implementation reproduces failures. All Image Gen input/output pixels/SHAs independently rechecked. Actual official full pending page was inspected independently before page-gallery assertion grading.


## Final local release acceptance

- `python tools/skill_evals/build_full_imagegen_review.py --workspace work/full-imagegen-skill-evals-20261118`:strict build succeeded against frozen independent grading. Missing-grade and stale-artifact negative controls really reject without altering public outputs. Runtime, independent-grader and executed-skill ZIPs are included; required human asset has an existing public URL and exact SHA.
- `python scripts/build_pages.py`:built actual dist.
- `node tools/skill_evals/verify_full_imagegen_review.cjs --url http://127.0.0.1:8965/garment-body/full-imagegen-evals/eval.html --out docs/verification/full-imagegen-skill-evals-20261118/browser/final-dist`:236 checks PASS. Actual six native originals, original Prompt/Output DOM, final-overlay default, explicit FAIL, galleries/lightbox, JSON/CSV reopen, feedback persistence/download/mobile, actual Human Studio handoff same final dimensions+163pose. Zero console/page/network errors and no external feedback writes. Browser success is page functionality, not body matching PASS.
- `node scripts/verify_garment_body_skill.cjs --url http://127.0.0.1:8965/ --output work/full-imagegen-skill-evals-20261118/skill-browser`:21 checks PASS. Root independently reopened actual downloaded updated .skill:20 entries source-identical with E2E scope correction.
- Root independently rehashed all388 original outputs against grading, rechecked all public manifest files, reopened full-run ZIP with CRC and all388 entries against grade. No executor output modified after grading. Independent grading SHA256:f065a100ef784f8c8fc7b04fa507ac48dd0a463ed94fd144742117f8d4ea3a6a.
- Root visually reviewed actual final overlay and real side render plus `browser/final-dist/four-stage-gallery-verified.png`. An initial screenshot scroll-position problem showed the dimension table instead of gallery; preserved faulty evidence, corrected capture timing/target and actually inspected a new distinct filename after re-verification.

Local release surface verdict PASS; task visual/3D acceptance verdict FAIL as independently graded. No partial task PASS. Source/dist servers are stopped after verification. Publication status does not substitute for live public browser interaction.
