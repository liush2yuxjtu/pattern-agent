---
name: design-cloth
description: Run one garment workflow from brief or an existing pattern through fabric and avatar setup, pattern work, native CLO simulation, diagnosis, repair, and final verification. Start or resume from intent, a FreeSewing source, prototype or graded DXFs, a CLO project, or existing fit evidence. Call specialist skills as needed.
---

# Design cloth

Drive the garment project through [one workflow](references/workflows.md). The user brings a goal and available artifacts here. Choose the first unfinished step, reuse valid evidence, and carry the work through the requested stopping point. Use the [runtime support matrix](references/runtime-support.md) when choosing between native CLO, Rust MCP or CLI, and Boat VM.

1. Confirm the design goal, candidate revision, target sizes and poses, and acceptance scope. Use the same workflow for a new project, an existing DXF, a single check, or a retest.
2. Honor the user's skill-use approval rule. Name the specialist skills the scope needs and wait for approval when required. Call an approved specialist when a step needs its output. Ask before implementing fit-derived design changes.
3. Pass each specialist the current revision, inputs, and expected evidence. Continue from completed results. Use `verify-finish` for the final verdict when the scope includes full acceptance. Route only the checks or repairs needed and return their results to the same workflow.
4. Report the result, evidence, unresolved findings, and next step or blocker. Keep the original files and earlier evidence available when revising the garment.
