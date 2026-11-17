# Single-state functional benchmark

| Configuration | Mean ± SD across cases |
| --- | --- |
| with_skill | 1.0000 ± 0.0000 |
| old_skill | 0.9524 ± 0.0825 |

- Three cases, one execution per configuration/case. Standard deviation is across heterogeneous tasks, not repeated-run reliability.
- Both configurations receive the same existing anatomical model and generic cm/FK/LBS runtime. The runtime is evaluation infrastructure, not an optimizer bundled in the skill.
- Case1 is controlled anatomical reconstruction; case2 is an actual editor workflow; case3 uses the original e-commerce photo. No new Image Gen call was made.
- Same-state body/pose consistency and actual joint optimization are functional claims; passing them is not perfect photograph matching, true-person measurement accuracy, or physical garment contact.
- Different camera protocols and self-declared objective scales in the photo runs prevent treating their raw loss delta as a causal skill-quality gain.
- Missing token/duration metadata remains null. Native Claude trigger testing remains BLOCKED.
- benchmark-upstream-raw.json retains unmodified official aggregation output; this adapter only corrects context and removes unavailable resource placeholders.
- Each of the three tasks ran once per configuration: six explicitly injected subagent executions. There are no repeated-run reliability estimates, native Claude trigger results, or measured token/time advantages.
- Controlled joint-fit and real-editor tasks pass in both configurations (13/13 each): the source anatomy can actually optimize cm/bone/pose/camera and preserve one action across cm edits and camera changes. These 13 assertions do not discriminate a revision benefit in this sample.
- Case1 both configurations independently reach front/side IoU1.0 and held-out back IoU1.0, from biased initial silhouettes near0.697. These are controlled MakeHuman images with exact synthetic joint observations, not a photographed-person reconstruction accuracy result.
- The one differing assertion is an unblinded independent coarse visual review of the original-photo shirt-holding action: updated7/7, old6/7. The old side view shows a more forward/open-hand action hypothesis; updated hands return near the abdomen. This single qualitative decision is not statistical or causal evidence of general skill superiority.
- Original-photo raw whole-clothed IoU is higher for the old execution (~0.6973 vs updated~0.6447). Their nuisance cameras/projections and optimization objectives differ (perspective vs oblique orthographic), so this is disclosed output data rather than a fair isolated skill-effect estimate. Neither pixel overlap is a true naked-body accuracy score.
- Both original-photo executions greatly improve visible eye/nose/wrist error and export a single complete body/pose shared by all views. The updated coarse pose passes the frozen plausibility criterion, but fine finger gripping, real cloth contact, precise depth, identity and a perfect pixel match remain unverified.
- The generic runtime was shared evaluation infrastructure outside the shipped skill, and contains no solver or hidden answers. Executors wrote and ran their own optimization code. Passing does not mean the skill package already embeds a standalone joint-fitting engine.
- Independent grader reads actual neutral/posed OBJ and uses separate Three.js source skinning; independently reprojects masks/matrices and samples20ray/triangle depth points. Editor grading additionally repeats actual browser cm input, bone-length response, camera actions, download/import/reload and375px behavior.
- Four real-file fault controls are rejected: changed side pose hidden behind common metadata,1cm OBJ displacement with forged mesh hashes, falsified saved IoU, and changed reference bytes. Grading is bound to executor artifact SHA256 maps.
- Exactly20 frozen assertions per configuration yield weighted20/20 vs19/20. The official aggregate macro-averages the three case rates, giving1.0 vs0.952381; its SD is across heterogeneous tasks, not repeated trials. No fresh ImageGen call or full six-photo generation score is inferred.
