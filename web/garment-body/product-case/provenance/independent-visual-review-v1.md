# Independent visual review v1

Verdict: **FAIL for faithful garment reproduction; PARTIAL for internal model/photo registration.**

Reviewed 2026-11-17. No edits outside these review files, network, generation, commits or physical fit checks. Read repository AGENTS.md; this review is not a /verify or commit verdict.

The ASOS candidate descriptor supplied by the parent says boatneck and three-quarter sleeves. No `reference/asos-*` images existed locally during this review, so exact product identity remains unverified.

## sleeves — FAIL

All generated color views show sleeves reaching wrist/hand junction. The source has bent elbows and exposed forearm; its crop alone does not safely establish full sleeve length. The official three-quarter-sleeve description supplied to this review conflicts with the generated wrist-length design.

Files: `reference/original-product.jpg`, `images/front.png`, `images/side.png`, `images/back.png`, `images/closeup.png`.

Required correction: Recheck official local product images, then regenerate with confirmed three-quarter cuff placement. Do not call current result faithful long sleeves.

## neck-trim — WARN

Wide shallow red neckline and central red/green bud are retained. Closeup invents a pronounced scalloped/picot inner edge and a larger, sharply resolved rose with green leaves; source collar appears narrow/smoother and bud much smaller. Closeup neckline reads more U-shaped than the source shallow boat shape.

Files: `reference/original-product.jpg`, `images/front.png`, `images/closeup.png`.

Required correction: Preserve source collar width/curve and tiny bud; avoid adding decorative trim unsupported by source.

## knit-and-color — PARTIAL

Saturated red and repeated vertical pointelle/rib-like columns visibly carry across views. Closeup makes perforated floral/diamond motifs much more explicit and regular than the low-contrast source. Exact knit repeat, hole scale and color cannot be certified from this source and differing light.

Files: `reference/original-product.jpg`, `images/front.png`, `images/side.png`, `images/back.png`, `images/closeup.png`.

## pants-and-unseen-details — UNVERIFIED

Red gathered waistband and its tiny centered red/green decoration are consistent with source. Source ends around upper thighs; generated full-length straight/relaxed legs, hems, bare feet, back cut and full top hem are inferred, not recovered evidence. Source top is lifted by hands; generated hip-level unlifted length is plausible but not directly verified.

Files: `reference/original-product.jpg`, `images/front.png`, `images/side.png`, `images/back.png`.

## views-and-framing — PARTIAL

Six standalone image files exist with clean unclipped full-body front/side/back/pose/depth and one torso detail. Front/back use a spread-arm stance; side bends visible forearm forward and hides far arm/leg; closeup has arms down. Back/side/frontal head size, hair silhouette, hem height and subject scale vary. These are coherent illustrative views, not synchronized projections of one captured pose or guaranteed identical person.

Files: `images/front.png`, `images/side.png`, `images/back.png`, `images/closeup.png`, `images/pose.png`, `images/depth.png`.

## generated-pose — ILLUSTRATIVE_ONLY

Orange/yellow diagram is legible but draws stylized extra central torso/face nodes and ambiguous shoulder branches. It is embedded in a separately generated photograph with slightly different garment proportions/framing. Metadata says manual visible wrist/ankle annotations and no pose detector; diagram cannot substantiate detector accuracy or 3D joint truth.

Files: `images/pose.png`, `images/landmarks.json`.

## generated-depth — ILLUSTRATIVE_ONLY

Generated depth image retains grayscale facial shading, pointelle texture, folds and photoreal hair. It looks like a relit monochrome portrait on black, not an independently measured/calibrated depth map. Actual model depth rendering is visibly distinct and corresponds to bare anatomical geometry, not clothed photo surface.

Files: `images/depth.png`, `model/final-renders/depth.png`.

## actual-body-fit — PARTIAL

Actual faceted anatomical surface is visible, and overlays put its cyan contour on generated photos with magenta manual wrist/ankle markers. Side before/after visibly improves ankle registration. Persistent side errors: face/chin cyan outline protrudes forward, hip/buttock and thigh/waist differ, fingers and toes do not align exactly. Front/back arm contours often sit outside clothed sleeves; hand/foot contours also diverge. These images are meaningful registration diagnostics, not proof of recovered bare-body dimensions or physical clothing fit.

Files: `model/final-renders/front.png`, `model/fit/front-final-photo-overlay.png`, `model/fit/side-before-after.png`, `model/fit/side-final-photo-overlay.png`, `model/fit/back-final-photo-overlay.png`, `model/fit/metrics.json`, `model/README.md`.

Full envelope IoU front 0.8161→0.8320, side 0.5891→0.6898, held-out back 0.7936→0.8142. P95 contour error worsens front 17.18→20.38px and back 17.00→17.18px. Shape is fixed prior; cameras were separately calibrated and frozen before pose comparison.

## Next acceptance check

- Visually check official product photos and confirm original garment before asserting exact product identity.
- Correct sleeve length and unsupported neckline trim, then review six replacement images.
- If generated references change, rerun matching with new frozen masks/annotations and distinguish camera, pose and body-shape contributions.
- Keep illustrative pose/depth separate from actual joint projection/Z-buffer outputs; retain limitations and metric regressions.

This report makes no exact-identity, real-body-accuracy, material-composition or physical garment-fit claim. JSON records hashes of the reviewed files so later replacements cannot silently inherit this review.
