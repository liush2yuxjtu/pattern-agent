# Real garment six-view case and adjustable body handoff

This change delivers an actual source-backed case, separate from the earlier
synthetic skill benchmarks. Source: ASOS product 211010805, a red cotton
pointelle boatneck three-quarter-sleeve top. The recovered original photo is
visually/pixel-correlated with the official product-page screenshot. The
published real model is 171 cm and wears S; the editable demonstration starts
from the user's authorized generic M prior at 170 cm.

Two actual six-call Image Gen batches are preserved at native resolution,
including the first generation's incorrect long sleeves. Generation 2 edits
the original and generation-1 anchors. Initial M anatomical renders guided
generation 1; the final waist69/thigh50 avatar was fitted afterwards and was
**not** sent back into Image Gen. Generated pose/depth are illustrative; real
projected joints and raw Z-buffer are separate downloadable files.

The selected MakeHuman avatar has 12 editable cm controls and 163 bones. Real
camera registration, shared-pose fitting, 78 bounded source-calibrated cm
candidates, and view-specific pose diagnostics are preserved. Waist72→69 and
thigh54→50 improve one-sided clothed-envelope containment; side outside pixels
3578→2850. Full clothed IoU declines relative to fixed-M pose: front
0.81420→0.80564, side0.68676→0.68376, back0.74962→0.74437. These are different
objectives; none is real-person measurement accuracy. Back shared wrists remain
misaligned; per-view adaptation is in-sample, not held-out validation.

Original-photo near-abdomen shirt-holding pose is **POSE_FAIL / UNRESOLVED /
DEPTH_AMBIGUOUS**. Actual front/side meshes reject low-2D-error candidates with
hands hidden in the torso, displaced elbows, or hands21–25cm in front of the
abdomen. All rejected states and the depth-branch calculation are retained.
This limitation applies to the fixed avatar, approximate crop camera and
uncertain clothed joint annotations; it does not claim the real action is
impossible. No candidate was accepted as a recovered original pose.

The public page uses Anthropic's pinned official review viewer plus the
four-stage gallery: actual inputs, six independent Image Gen outputs, actual
3D renders, and OpenCV overlays. File/interaction assertions are separate from
the independent visual domain review. No causal skill gain is claimed from
this one product's revision history. Native Claude routing remains BLOCKED;
physical garment fit is NOT_RUN. Missing measurements remain null.

Local `/verify` follows
[product-case recipe](../../../.agents/skills/verify/references/product-case.md),
the Human Studio geometry recipe and skill package recipe. Evidence under
`local/` records actual file mutation controls, native-image byte checks,
editor input/export/reload, independent neutral reconstruction and GLB skinning,
browser gallery/feedback/download behavior, and unchanged historical eval data.
The installable package is compared member-for-member with canonical source.

The final public manifest binds selected state, mesh, camera, renders, raw
depth, masks and generated input hashes. `reproduce.zip` is a documented
selected reproducible subset, content-deduplicated with a checked restore
script; the complete working history also remains in the local workspace.

Live publication evidence is recorded separately after the exact pushed SHA
is deployed and exercised. A local browser pass or publish-job success does
not substitute for live verification.

Live publication **PASS** at `28f46861f7f1cc83327e9b09bedd114f78c4eb06`:126gallery,30model-handoff and19guide checks. The real86.586MiB ZIP restores461paths/137aliases; downloaded skill has13members identical to canonical source. [Live receipt](live/receipt.json) · [Desktop](live/case/desktop.png) · [Original-photo failed pose](live/case/original-reference.png) · [Editable model](live/handoff/linked-model.png). Original pose matching remains **FAIL**; this publication pass concerns working evidence and editor behavior.
