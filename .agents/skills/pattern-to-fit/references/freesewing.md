# FreeSewing pattern design and verification

## Draft

- Start with the user's FreeSewing workspace and its pinned package versions. For a standalone design, use the [FreeSewing Studio From scratch template](https://freesewing.dev/tutorials/pattern-design/part1/sde/) or a minimal version-pinned ESM project. Follow the [new design tutorial](https://freesewing.dev/tutorials/pattern-design/part2/our-first-design/) for the package entry point.
- Keep each reusable part in its own module. Export the named parts, PascalCase design constructor, and translations from `src/index.mjs`. Construct the design with `new Design({ data, parts })` from `@freesewing/core`. Declare each part's stable name, draft function, standard required measurements, dependencies, and option ranges. Work in mm. Percentage options use percent in configuration and fractions in the draft. Return the part from its draft function.
- Preserve the construction meaning of each path. Keep sewing outlines, allowance offsets, internal marks, and debug geometry identifiable. Record the cut count, fold and mirror rules, grain direction, and how each seam or closure is assembled whenever they apply.
- Run a real draft through the exported constructor and render the baseline SVG. Check the draft logs and physical dimensions. Use the X-Ray view or structured path data to trace geometry back to control points if the shape is wrong.

## Verify the parametric behavior

Follow [Testing your designs](https://freesewing.dev/tutorials/pattern-design/part3/tests/) and [Pattern sampling](https://freesewing.dev/reference/api/pattern/sample/). Use Studio or the installed core API. For API details and the tutorial bib's expected results, read [FreeSewing checks](freesewing/freesewing-checks.md).

- Sweep each supported option with other inputs fixed and inspect actual sampled values, including both endpoints. Check intended effects and unexpected changes to other garment dimensions.
- Sweep each relevant measurement around nominal (the tutorial uses ±10%) and run complete, realistic measurement sets. Include interacting corners when one-variable sweeps may miss bad geometry.
- Run the antperson comparison with body measurements at 1:10. Normalize the outlines to compare shape and identify fixed-mm effects. Report intentional fixed allowances separately from unintended shape drift.
- Check finite, closed, non-self-intersecting outlines, seam lengths and intended ease, and usable notches or closure locations in the cases where they matter. Save overlays and concrete measurements so the user can see which checks passed or failed.

## Verify in CLO 3D

Continue from the exact FreeSewing draft and settings already checked. Read [CLO transfer and fit](freesewing/clo-verification.md) for the handoff, construction, and evidence. Return the editable project and relevant screenshots with the source measurement set, options, avatar, fabric, and any transfer or construction approximations. Give the 2D sampling, CLO transfer, construction, and on-avatar fit results individually. A fit check requires a settled garment on the intended or explicitly agreed representative avatar in its correct worn configuration.
