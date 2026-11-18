# Prospective commerce assertions — DRAFT / NOT_RUN

These outcomes were missing from the frozen 9/7 assertions. They are proposals
for a new, separately frozen round, not additional passes/failures assigned to
iteration1/2. Keep those original grades unchanged.

1. **Guide adoption has an auditable dataflow.** Inspect the generated native
   guide before final optimization. Preserve registration, visible/hidden
   semantics and the decision to adopt or reject each cue. If a guide-driven
   correction is claimed, demonstrate guide → accepted targets → actual solver
   residual/state change → final render. Reject misleading guide cues using the
   original photograph, and record a justified manual-observation fallback.
   Merely generating/registering a guide after fitting is not this outcome.
2. **Generated pose remains compatible with the saved body.** Compare every
   generated role with its exact retained model input and original action;
   inspect torso, shoulder–elbow–wrist chains and visible legs in corresponding
   cameras. Do not replace a saved posed body with neutral generated standing
   images and then claim the generator preserved the pose. Hidden back anatomy
   remains a hypothesis.
3. **The depth role communicates depth.** Independently inspect near/far ordering
   and form rather than accept any grayscale photograph. ImageGen depth is an
   illustration, not calibrated geometry; the actual renderer's numeric depth
   and validity mask remain a separate geometric deliverable.
4. **The real editor consumes the saved model faithfully.** Load the exact state
   through Human Studio; compare all163 joint angles and real mesh with the
   archive, switch cameras, edit cm preserving the target action, edit one joint
   preserving other joints/cm, export and reimport. Test normalization before
   the state is used for final generation. Save before/after screenshots and
   actual downloaded state; an API/file existing is insufficient.

Freeze annotation uncertainty and any numerical tolerances before new runs.
Have independent graders critique these criteria and run meaningful fault
controls. Use fresh development inputs or an untouched new holdout when changing
the skill; the already-opened Reformation case is no longer a fresh holdout.
