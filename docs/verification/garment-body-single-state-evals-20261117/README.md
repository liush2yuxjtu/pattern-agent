# Same body, same target action — actual paired skill evaluation

Following the pinned Anthropic skill-creator workflow, freeze the predecessor,
clarify the skill, launch all paired runs, freeze assertions while they execute,
independently grade actual artifacts, run official aggregation and publish the
official review viewer with the existing visual-gallery adapter. Three tasks
were executed once per configuration by six independent subagents:

1. Controlled MakeHuman joint cm/bone/pose/camera optimization.
2. Actual Human Studio cm edits that preserve the complete target action across
   camera changes, export/import and persistence.
3. Original e-commerce photo fitting with one final body/pose and actual
   front/side/back projections.

Both groups receive identical project model and generic cm/FK/LBS runtime
infrastructure. Each executor implements its own optimizer. This is not a
standalone-offline test of the `.skill` package or native Claude triggering.
The current environment lacks Claude CLI. No new Image Gen was invoked.

The updated skill passes20/20 assertions; the frozen predecessor19/20.
Controlled fitting and editor assertions pass both. The single difference is
the unblinded coarse shirt-holding action judgment on the photo. Nineteen common
passes do not distinguish the skill. One subjective difference in single trials
does not establish general improvement, significance, token savings or speed.
Macro mean1.0 versus0.9524 is across three differently sized tasks; weighted
assertion counts are20/20 versus19/20.

Controlled front/side and withheld back IoU reach1.0 for both groups. Those inputs
include known projected joints from the actual anatomical fixture. Real-photo
final IoU is approximately0.645(updated)/0.697(old), under different optimized
camera protocols. The updated visible face/wrist error is242.42→3.30px and the
old271.93→3.95px. These are not perfect pixel matching, recovered original
dimensions or proof of physical grasp/contact. Keep the actual overlays and
unobserved-side hypotheses visible alongside the numeric benchmark.

The grader independently reopens OBJ and state, runs source Three.js skinning,
reconstructs neutral measurements, projects the same saved mesh, samples depth
rays and performs additional real browser consumers. It rejects four actual
faults: changing side pose behind common metadata, displacing a mesh vertex by
1cm with forged hashes, falsifying IoU, and changing a frozen reference.
The recorded human action judgments in
[visual-review.json](independent/visual-review.json) are hash-bound to those
images and states; changed candidates need fresh visual review.

Local browser verification passes168checks including6real model loads,77image
hashes, archive downloads/CRC, actual cm edits retaining pose, official feedback
and Benchmark, keyboard/lightbox/mobile. The skill guide/download passes18checks,
and all13package members match canonical source. Local helper/tool tests pass
24/20. [Receipt](receipt.json) · [Desktop](local/desktop.png) ·
[Actual editable fitted model](local/linked-model.png).

See the maintained [verification recipe](../../../.agents/skills/verify/references/skill-evals.md)
for replay. Public run archives retain unmodified outputs, failures, traces and
grades. Fixture/skill snapshots and the post-grading disclosed controlled oracle
are separately downloadable. Pinned upstream source remains unchanged.

Publication is verified separately on the exact deployed SHA; local PASS and a
publish-job conclusion alone are not live browser acceptance.

Published at `cc0df412a61f9afee9ec759072ae25f3213b931c`; exact same-commit local recheck passes169review/19guide checks. GitHub Pages publication succeeded and committed HTML/manifest/package blob hashes match local source. Live interactive browser verification is **BLOCKED** by the VM proxy and unavailable fallback browsers/credits, so no live browser pass is claimed. [Publication receipt](publication/receipt.json).
