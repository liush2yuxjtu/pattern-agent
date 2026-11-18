# Actual end-to-end execution trace

User correction: measurement-only was not accepted; run actual Image Gen + body fit + OpenCV + mesh measurements.

Root inspected original product and actual mannequin render; called image_gen.imagegen once for raw-photo pose guide, then once for front with original and historical anatomical-render guide. Five independent native calls generated side, back, closeup, fullbody pose and depth from original plus current front. Exact prompts, input/output SHA, native paths and actual native dimensions are in generation-receipts.json. Native files copied byte-identically, no cropping/upscaling. PNG 1024x1536 for five views, closeup1199x1312; separate raw guide1110x1417. Tool offers no explicit resolution/model setting: requested highest available native pixels; no invented setting.

Pose fitting delegated to e2e_pose_fit; full raw-photo guide is distinct from generated-front skeleton. Its actual command/optimization/render/measurement logs are retained under model-fit. Independent grader must inspect all stages and residual errors. Model input predates fresh fit: not a final-model-conditioned generation claim. The full workflow can be executed and still fail visual acceptance.
