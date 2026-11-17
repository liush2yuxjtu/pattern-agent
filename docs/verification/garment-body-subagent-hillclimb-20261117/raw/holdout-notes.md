# Sealed surrogate routing holdout

Created independently from the task contract, without reading repository evaluation queries or skill descriptions. This is a surrogate routing evaluation, not a Claude-native evaluation and not an assessment of image execution quality. The dataset contains 24 requests: 12 intended triggers and 12 exclusions; 12 English and 12 Chinese requests, balanced within each class. Indices below are one-based array positions.

## Rationales

1. In scope: worn-product photos anchor a multi-view apparel wearer handoff, adjustable body and qualified inferred dimensions.
2. Excluded: ordinary purchase-size advice from a sizing chart.
3. In scope: contextual follow-up debugging the fitted body's shoulder adjustment and geometry without new image generation.
4. In scope: completing the existing apparel wearer pack with structural outputs and mesh consistency checks; only height is known.
5. Excluded: isolated garment cutout/background/detail edits without a wearer.
6. Excluded: standalone video pose/depth computer vision for robotics.
7. In scope: product-photo-based pants wearer reconstruction, multiple references, adjustable body and explicit uncertainty.
8. Excluded: measurement-table normalization without photo-body fitting.
9. In scope: provenance correction on the body values of an existing apparel reconstruction workflow, preserving images.
10. Excluded: original game avatar design without product-photo fitting.
11. In scope: fitting-workflow parameter-panel follow-up with live body controls and multiple provenance classes.
12. Excluded: medical inference from appearance rather than apparel reconstruction.
13. Excluded: sewing-pattern data to garment preview on a stock mannequin, expressly without photo-based body fitting.
14. In scope: worn-dress images to independent reconstruction references, adjustable base body and actual checks.
15. Excluded: concept outfit design for a fixed virtual avatar, no product reconstruction or body fitting.
16. In scope: replacing estimated dimensions with supplied measurements in an existing fitted-body workflow and validating fit.
17. Excluded: multiple product-only shoe views; output count does not make it a wearer workflow.
18. In scope: body geometry and provenance completion for an existing apparel photo reference set; no regeneration required.
19. In scope: sparse worn-product photos to a complete apparel wearer handoff with separate outputs and qualified initial dimensions.
20. Excluded: standalone pose/depth algorithm comparison without the apparel body-fitting workflow.
21. Excluded: a single campaign image retouch, with no reconstruction handoff or editable body.
22. In scope: worn-overall photos to garment reconstruction references, adjustable anonymous body and evidence-based verification.
23. Excluded: measured-data schema conversion without rendering or fitting.
24. In scope: repair of a nonfunctional body slider in the established apparel reconstruction workflow, with validation and source retention.

## Design caveats

- Labels express intended routing under the supplied contract, not an observed router decision.
- Some requests deliberately use contextual continuations. Each includes enough prior-work context to be judged as a standalone request.
- Several positive requests focus entirely on fitting, control repair or measurement provenance after imagery is approved. A router that requires fresh image generation will miss these cases.
- Hard exclusions share surface features such as apparel, six outputs, neutral mannequins, dimensions or pose/depth processing, while lacking the required workflow relationship.
- The dataset is small and manually constructed. It probes boundaries rather than estimating production prevalence, comprehensive multilingual robustness or execution capability.
- Keep queries and labels sealed from prompt or skill tuning. Record only aggregate routing outcomes outside this directory until the final holdout evaluation.
