# Independent review of anatomical skill candidate v2

Verdict: safe to promote as a lean instruction revision with preserved documented domain coverage. No concrete lost domain requirement was found in the core plus its referenced documents. This is not evidence of full end-to-end capability, a statistically established performance improvement, or real-person measurement accuracy.

Read-only review covered repository AGENTS.md, the upstream analyzer instructions, v0/v2 SKILL.md and all linked references, iteration 1/2 benchmark and grading summaries, iteration 3 grading summaries, executor TRACE files, and the reported geometric metrics. Only these independent review files were written. Existing numerical outputs were inspected rather than rerun. External URLs were not fetched.

## Coverage

| Requirement | v2 location and assessment |
| --- | --- |
| Original garment photo provenance | Section 1 requires actual inspection, URL/attachment, pixels and SHA-256; section 2 retains reference/; Human Studio section 6 preserves original photo and hash. Preserved. |
| Six independent clothing images | Section 3 names front, 90-degree side, back, clothed close-up, pose and depth; bans collage crops/upscaling claims and ties appearance to original garment. Human Studio section 6 explicitly says six clothing images. Preserved; synthetic six renders do not prove this capability. |
| Actual anatomy, cm dimensions, real pose | Section 2 requires anatomical morph/skin model, real vertex changes and skeletal skinning. Human Studio describes 12 dimensions and 163 bones. Preserved. |
| Neutral versus posed | Section 2 and geometry reference require independent neutral reconstruction and prohibit seated bbox as stature; targets, actual values and residual remain distinct. Preserved/strengthened. |
| Units and camera | Core requires Y-up cm OBJ / metre GLB and recorded camera; geometry reference requires actual transformed vertex scale, projection/view matrices, compact index remapping, depth validity. Preserved/strengthened. |
| Actual OpenCV fitting | Section 4 requires real optimization and mesh rasterization with frozen protocol, IoU/Dice/mean/P95 and overlays; tools reference defines formulas and runnable helpers. Preserved. |
| Exports, viewer state/cache | Section 5 retains actual deformation, save/reload/import, version/asset checks, range/type/step normalization, old-cache isolation, mobile checks and height-vs-girth consistency. Human Studio and geometry references require real OBJ/GLB boundary verification. Preserved. |
| Truthful measurement basis | Section 6 retains all five basis categories, mesh_checked, null unavailable landmarks, scale sensitivity, no invented intervals; sections 1/4 separate observations, prior and generated-loop consistency. Preserved. |

All local Markdown links in both cores and their reference files resolve. The Human Studio reference is unchanged; v2 adds geometry-evidence.md and expands tools-and-evidence.md. Existing helper source is unchanged. Local reference validity does not establish availability of remote sites or external repository tools. The package still delegates full browser/export audits to repository tools or an equivalent audit; it does not bundle a generation backend or complete fitter.

## Length and package interpretation

Core SKILL.md: 6,522 to 3,911 Unicode characters, a 40.0337% reduction; UTF-8 bytes 15,725 to 9,290, a 40.9221% reduction. Lines fall from 219 to 117. The claimed 40% reduction is valid for the core instruction text.

All package Markdown is 27,354 to 26,531 characters, only 3.007% shorter. Source-package bytes excluding transient __pycache__ are 486,782 to 484,320, only about 0.506% smaller. New geometry text and expanded tools text offset much of the core reduction. This is progressive disclosure, not a demonstrated 40% reduction in total loaded context, model tokens, runtime or cost. A transient v0 bytecode cache was present at inspection; it is excluded from package comparisons and was not modified.

## Execution evidence and limits

Iteration 1: baseline and v1 both pass 22/22 frozen assertions. Baseline final front/side IoU is 0.989359/0.993843; v1 is 0.990450/0.995153. This does not establish a reliable superiority claim.

Iteration 2: v2 passes 22/22 and baseline 21/22. The sole baseline failure is the missing neutral_measurements_cm handoff field, not wrong anatomy or bad depth. Its trace measures all 12 neutral dimensions, keeps 179.9999101 cm neutral height distinct from 132.672357 cm seated height, preserves topology and passes independent ray/joint checks. v2 includes the required metric schema. Baseline fit IoUs (0.990687/0.994676) are slightly higher than v2 (0.989441/0.993139), while both improve substantially over initial 0.913046/0.916940 and pass frozen thresholds. Therefore the observed win is contract completeness, not more accurate fitting.

Iteration 3 camera-transfer holdout: both configurations pass 8/8. v2 metrics preserve 13,380 vertices / 26,756 triangles, report zero source-coordinate differences, all six replay mask IoUs 1.0, 163 exact joint projections, and 257 independent depth samples with maximum discrepancy about 1.90e-6 cm. This supports transfer to the changed orthographic 448×576/front-facing protocol. It remains one related synthetic task using the same asset family and renderer. Joint visibility is explicitly canvas inclusion rather than occlusion classification.

TRACE files show real bounded morph optimization, OpenCV mask/overlay calculation, saved meshes, independent neutral measurements and triangle-depth checks. They also explicitly exclude image-generation services, real-person recovery and physical fit. Six anatomical raster renders, including an anatomical close-up, cannot substitute for the six independent clothed images in the production contract.

Each configuration has only one run per task per iteration. Assertions within a case share artifacts and are correlated; 22 assertions are not 22 independent experiments. Repeated baseline draws vary. The reported across-task standard deviation is not repeated-run uncertainty. Candidate selection and iterative editing further prevent treating this as a clean generalization estimate. No statistical significance or causal benefit from shortening can be inferred. Geometry-reference additions, executor choices and sampling vary alongside length.

Instructions and relevant references were explicitly supplied, so native Claude skill triggering/routing was not measured. Token/tool-call metadata is unavailable and wallclock scopes differ; no efficiency comparison is supported. Renderer replay shares the supplied raster kernel; separately implemented triangle intersections and OBJ checks strengthen geometry consistency, but sampled rays do not exhaustively validate every rendered pixel. No end-to-end clothed generation, original-photo segmentation/fitting, real-human centimetre accuracy, live cache interaction, or physical garment fit is established by these cases.

## Promotion recommendation

Promote v2 if the acceptance claim is “approximately 40% shorter core with retained domain instructions and passing synthetic functional controls.” Retain the linked references and existing validators in the package. Do not label it a measured 40% token/cost improvement or a proven full workflow improvement. No specific coverage omission blocks this bounded promotion; a claim of full tested coverage would require additional production-scope evidence, especially original-photo provenance/segmentation and six independent clothed generations, plus native routing and live viewer/export behavior.
