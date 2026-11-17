# Proposed trigger cases

20 realistic queries: 10 positive and 10 nearby negative cases, interleaved; Chinese, English and mixed-language requests, with varied length and concrete working context. The JSON uses only the official `query` and boolean `should_trigger` fields. Queries do not name the skill.

Positive cases cover the complete photo-to-six-images/body/verification workflow, single-photo uncertainty, missing scale, loose garment ambiguity, real multi-view evidence, existing-view fitting, parameter provenance and mesh/viewer synchronization. Follow-up requests explicitly establish prior apparel-fitting context so their labels do not depend on hidden conversation history.

Negatives exercise tempting shared terms: six independent product images, apparel and sizes, adjustable avatars, viewer controls, OpenCV overlap metrics, body measurements and CSV exports. Their actual tasks are flat product editing (2), shopping/size charts (2), unrelated game/avatar work (2), general OpenCV (1), measurement-only pattern CAD (1), medical estimation (1), and CSV cleanup (1).

Ambiguities deliberately excluded from the labeled set: bare “make an adjustable body” or “fix my viewer” without apparel-reference context; “estimate dimensions from this picture” without defining the subject or intended use; and generic clothing multi-view generation without body fitting intent. Those require scope clarification rather than a confident trigger label. Generating six isolated product shots is kept negative because it clearly lacks the body-reconstruction workflow.

This is a proposed human-review set, not an empirical result. No model evaluations were run and no trigger rates or optimization scores are claimed. Guidance followed: `anthropic-skill-creator.md`, description optimization Step 1 (realistic detailed prompts, positive coverage, substantive near-misses), with official schema preserved.
