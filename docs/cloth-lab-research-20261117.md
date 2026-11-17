# Single-file garment code: what the game examples establish

Research date: 17 November 2026. The new executable deliverable is [Cloth Lab](../web/cloth-lab.html), with readable [source and local validators](../experiments/single_html_cloth/). Existing experiments and their historical failures are unchanged.

## Conclusion

**Yes: an agent can produce a browser 3D application, procedural assets and a physics demonstration in one HTML file without MCP at runtime.** That conclusion is supported by inspectable Opus 5.5 and Fable 5.2 examples. It does not establish that a model produces the entire result in one inference, that Three.js is not third-party software, or that convincing cloth rendering constitutes accurate garment engineering.

Both model names are confirmed by Anthropic's first-party announcements: [Opus 5.5, 22 September 2026](https://www.anthropic.com/claude-opus-5-5), and [Fable 5.2, 9 November 2026](https://www.anthropic.com/claude-fable-and-mythos-5-2). The model attribution, original run conditions and costs of individual community games are author reports, not independently audited inference records. Source inspection can verify their implementation and dependencies, not retrospectively prove which model wrote every line.

Distinguish four claims:

| Claim | Evidence and qualification |
| --- | --- |
| One initial prompt | Common and supported by published accounts. The agent then runs many tools and revises its code. |
| One model response | Not established. Several cited runs explicitly involved hundreds of turns or hours of work. |
| One HTML deliverable | Supported by inspecting bundled source. Some examples are assembled from a modular build project. |
| No external dependencies | Depends on the example. Bundling Three.js removes a network dependency, not its third-party authorship. Several games request Google Fonts or a CDN library. |

## Games, original prompts and detailed code

### 1. Opus 5.5: pelican bicycle, FPS and racing

[Author repository and complete original prompts](https://github.com/xiiyioozzz/opus55-3d-games). Inspected revision: `05527c0ec8d3b3e85d9cc599db6079678fd95dcb`.

The pelican's published instruction is:

> 生成一个鹈鹕骑自行车的 3D 页面，尽可能把你所有的能力全部都用上. 然后上传到 CDN 上, 把访问链接给我

The other two prompts ask for an accurate Transport Ship FPS and a QQ Speed-style racer with the relevant controls and drifting; their verbatim text is in the linked README. The author describes one starting prompt per game and a single agent session, with modular sources bundled by esbuild into roughly 700–850 KB HTML files. The README also documents later mobile fixes and post-deployment corrections, so the currently published revisions should not be described as untouched initial output.

Detailed assets and physics sources:

- [pelican.js](https://github.com/xiiyioozzz/opus55-3d-games/blob/05527c0ec8d3b3e85d9cc599db6079678fd95dcb/pelican-bike/src/pelican.js): deformed sphere geometry, lofted beak sections, curved feather shapes, vertex colors and physical materials. This is constructed geometry rather than an imported bird model.
- [textures.js](https://github.com/xiiyioozzz/opus55-3d-games/blob/05527c0ec8d3b3e85d9cc599db6079678fd95dcb/pelican-bike/src/textures.js): seeded noise, Canvas 2D image generation and `CanvasTexture` materials. A texture can be generated in code while still becoming an ordinary GPU texture.
- [effects.js, Scarf class](https://github.com/xiiyioozzz/opus55-3d-games/blob/05527c0ec8d3b3e85d9cc599db6079678fd95dcb/pelican-bike/src/effects.js): Verlet scarf simulation. Useful for motion and procedural art; it does not retain manufacturing pattern pieces, sewing allowances, seam contracts or calibrated fabric tensors.
- [build.mjs](https://github.com/xiiyioozzz/opus55-3d-games/blob/05527c0ec8d3b3e85d9cc599db6079678fd95dcb/pelican-bike/build.mjs): the distribution step that makes the HTML self-contained.

### 2. Opus 5.5: Hill Bomb, direct WebGL2

[Prompt and all demos](https://claude.rich/games), [complete single-file racer code](https://claude.rich/games/hill-bomb.html).

The published prompt specifies a small downhill San Francisco time trial, a procedurally generated city, vehicle grip/drift, a ghost replay, synthesized sound, adaptive resolution and explicit browser acceptance checks. The creator reports **96 minutes and 192 turns**, despite a single initiating prompt.

The downloaded source is 160,892 bytes, has no external script tags, and contains its own WebGL2 shader/program and buffer creation. It contains eight GLSL ES 3.00 shader-version declarations. This is a concrete example of using browser GPU APIs without Three.js. See the associated code-inspection receipt for the source digest; it is not an independent audit of the original model run.

### 3. Fable 5.2: Saltline

[Original shared artifact](https://claude.ai/artifact/BGY1SztrAYcJQHSsnHHGmp), [organizer's post](https://x.com/felixrieseberg/status/2119925633564463609), [inspectable source mirror](https://github.com/realcodebear/saltline-fable-5.2/blob/09c51774cd77aad750bd2d6c42af2b1020cb668d/index.html).

The mirror attributes the original to Felix Rieseberg and Fable 5.2 and reports about eight hours, 2.7 million output tokens, 445 million input tokens with heavy caching, and approximately $550 at API prices. These are organizer-reported figures. The mirror is not an official Anthropic repository or an independently established license grant for reusing the game.

The [community prompt transcript](https://github.com/retsnomJ/claude-fable-games/blob/main/docs/02-prompts.md) reproduces a brief request for an FPS with very detailed graphics but a tiny level. It is useful as a prompt example, but the original post could not be retrieved through the research tool in this session, so the transcript's exact wording remains secondhand. The opening request is “You know, you should also build me a FPS.” The full transcript is linked rather than presented as independently authenticated.

The inspected mirror is approximately 1.4 MB and embeds Three.js. Geometry, material effects and audio are generated in code, including custom GLSL. There are no external script tags, but **Google Fonts requests are present**. The strict “zero external requests” claim is therefore false for that published version. No Saltline code was copied into this garment implementation.

### Useful counterexamples

[Felt World](https://github.com/az9713/opus-5.5-open-world-game) is an attractive procedural example, but its README explicitly describes a sequence of requests and CDN dependencies. [Ethan Hann's examples](https://github.com/ethan-hann/claude-fun) publish detailed prompts and code, but disclose follow-up steering; some use external libraries, fonts, Blender and CC0 texture assets. They demonstrate agentic creation, not a universal no-tools or no-reuse result.

## Which open-source packages are relevant?

| Need | Project / package | Practical recommendation |
| --- | --- | --- |
| Node / browser sewing-pattern drafting | [FreeSewing](https://codeberg.org/freesewing/freesewing), including `@freesewing/core` | Strong basis for parametric 2D drafting and SVG. Its old GitHub repository is archived because development moved to Codeberg. It is not a complete cloth simulator. MIT. |
| Python garment programming and sewing representation | [GarmentCode / PyGarment](https://github.com/maria-korosteleva/GarmentCode) | Closest research foundation for a pattern agent: panels, edges, interfaces, sewing and a 3D data-generation pipeline. Core library MIT. [Installation](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Installation.md) documents `pip install pygarment`; its simulator requires a separately installed Warp fork and native dependencies. |
| Pattern-to-body prototype | [Costumy](https://github.com/cdrinmatane/Costumy) | Uses FreeSewing designs, body measurements and Blender-based draping/export. Explicitly a prototype. GPL-3.0. Check body-asset licenses independently. |
| Desktop pattern CAD | [Seamly2D](https://github.com/FashionFreedom/Seamly2D) / [Valentina](https://smart-pattern.com.ua/en/valentina/) | Useful open drafting applications. Not browser-native equivalents of CLO's integrated cloth pipeline. |
| Human asset generation | [MakeHuman](https://github.com/makehumancommunity/makehuman), [MPFB](https://github.com/makehumancommunity/mpfb2) | Anatomical mesh and authored morphs, rather than a person assembled from spheres. MakeHuman core assets are CC0; the application code is AGPL. Third-party assets may differ. |
| Native Python GPU simulation | [NVIDIA Warp](https://github.com/NVIDIA/warp), `pip install warp-lang` | Current upstream uses Apache-2.0 and supports CPU/CUDA kernels. It does not run in a browser merely because Python code generated it. |
| Garment-specific Warp collision changes | [NvidiaWarp-GarmentCode](https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode) | Implements cloth self-contact, body collision and garment initialization constraints. Its pinned older license differs from current upstream and states a non-commercial restriction: do not assume the upstream license covers this fork. |
| Self-contained browser viewer | Three.js + a custom WASM or WebGPU solver | Good for interactive review and bounded simulation. A complete production garment solver, measured fabric database and authoring CAD remain substantial engineering work. |

There is no verified single npm/pip package in this research that supplies the complete CLO/Style3D experience with equivalent fabric calibration, CAD, sewing, continuous collision, fitting, grading and manufacturing outputs.

## What transfers from games to 服装制版、人体和布料仿真?

Use a common procedural data model and retain its physical meaning. For games, a mesh plus textures can be sufficient. For garments, retain **flat material coordinates, physical units, grain, cut quantities, seam correspondence, notches, seam allowance, material properties and simulation boundary conditions**. A render mesh alone loses much of this information.

The closest game analogues are constraint graphs/joints for sewing, collision geometry for body contact, rest-state mesh metrics for deformation, and procedural asset generators for parametric panels. A UV layout alone is not a manufacturable sewing pattern: texture coordinates can distort freely, whereas fabric material coordinates must preserve a meaningful metric and topology.

WebGL2 is a browser GPU rendering API. It draws triangles and shaders; it does not inherently know about sewing or cloth. Three.js wraps much of that rendering work. WebGPU also supplies general compute pipelines, which can parallelize cloth constraints and collision work. WASM executes compiled numerical code in the browser; it does not automatically make that code GPU-accelerated. This deliverable uses **WASM for integration and XPBD distance constraints, JavaScript/BVH for actual body-mesh contacts, and WebGL2 for rendering**. It does not claim to use WebGPU.

## What CLO actually documents

The [Creator's Field Guide](https://support.clo3d.com/hc/en-us/article_attachments/48293801440281) describes checking sewing length differences, aligning notches, checking/reversing sewing directions, arranging panels, and selecting particle distance, garment collision thickness and avatar skin offset. Length differences can be intentional ease or gathering, so a general pattern agent must compare against **declared ease**, not blindly reject every unequal pair. This skirt declares equal-length side seams.

The guide recommends coarse particle distance around 20 mm during assembly and approximately 5 mm or below for final detail. Those are workflow recommendations, not proof that a simulation is physically calibrated.

[Garment Fit Maps](https://support.clo3d.com/hc/en-us/articles/360000436368-Garment-Fit-Maps) and the [current strain-map instructions](https://support.clo3d.com/hc/en-us/articles/56500755006617--Fit-Map-Strain-Map) distinguish stretch percentage from stress. CLO uses **100% at rest**; engineering strain uses **0 at rest**. The [stress documentation](https://support.clo3d.com/hc/en-us/articles/115012227307-Stress-Map) explicitly distinguishes fabric stress from pressure on the avatar. A pressure/contact map should not be relabeled a stress map.

These are public observable verification principles. CLO's internal proprietary solver and its full internal validation process were not available and have not been reverse-engineered here.

## What the new single HTML delivers

- An actual 170 cm MakeHuman surface: 13,380 vertices and 26,756 triangles. The pre-existing source OBJ is fingerprinted at build time; generated body data is embedded rather than fetched.
- Four annular-sector panels with millimetre pattern geometry, 10 mm cut allowance, grain direction, cut count, seam colors, notches and four explicit seam maps.
- One welded sewn shell with 1,856 solver vertices, 3,584 cloth triangles, Euler characteristic 0, and two intended openings: waist and hem. Sewing constraints are represented by common degrees of freedom; this is not a simulation of a sewing machine pulling stitches together.
- WASM Verlet integration and XPBD distance constraints; gravity, an explicit pinned waist support and adjustable wind. Body contact queries use the actual triangle mesh. Barycentric contacts on edges and triangle centres prevent the particle-only collision defect found during testing.
- Procedural material-coordinate weave shading, orbit/probe controls, strain/stress/seam/contact views and saved-state single-HTML export.
- SVG and DXF in physical millimetres, tiled A4 printing, simulation/sewing JSON, and OBJ containing body and deformed garment with material coordinates.

For every cloth triangle, `F = Ds · inverse(Dm)` maps its flat pattern to its current 3D shape. Principal stretch comes from the eigenvalues of `FᵀF`. Green strain feeds a stated, uncalibrated isotropic plane-stress model; the estimated maximum principal stress is displayed in kPa. The independent validator reconstructs these quantities with NumPy rather than calling the app's functions.

**Limits:** the assumed cotton/linen/silk constants are illustrative, the distance-constraint solver is not a calibrated textile constitutive model, and peak strain can be large. A digital-check PASS does not mean the garment has passed a wearable fit criterion. There is no general cloth self-contact solver; zero self-intersections is established for the checked exported state, not every possible future trajectory. The pinned waist is an explicit support, not a finished waistband. Closure, waistband, hem finishing, fabric testing, grading tolerances and an actual sewn sample are needed before manufacturing. SVG/DXF are pattern-plotter/cutter geometry; the zero-thickness OBJ is not a watertight 3D-printable solid.

Managed Chromium blocks `file://` navigation in this environment. Saved HTML is instead reopened as the only local HTTP document with all subresources blocked, after which browser network access is disabled. Exact saved garment coordinates and design controls are compared. Direct double-click opening on an unrestricted personal browser remains untested here.

## A reusable garment-agent prompt

This is an original prompt derived from the engineering lessons, not a claim that it was used by the game authors:

```text
Build a single self-contained HTML garment laboratory for one four-panel skirt.
Use an actual CC0 MakeHuman body, with provenance and physical units. Generate
the garment, fabric shading, panels and sewing metadata in code. Bundle all
runtime libraries, mesh data and WASM bytes; require no network or MCP at runtime.

Use one source of truth for 2D panels, grain, cut quantities, seam allowances,
notches, seam pairs, rest coordinates, 3D triangulation and exports. Preserve
waist and hem openings. Export SVG/DXF at 1:1 millimetres with a 100 mm ruler,
A4 print tiles, OBJ and a sewing/simulation JSON document.

Implement gravity and explicit supports with a fixed-step cloth solver. Test
against the actual body triangle mesh, including cloth faces and edges rather
than particle vertices alone. Display strain and stress with units and a stated
constitutive model. Do not call a decorative color overlay a measured stress map.

Drive the real UI with Playwright. Reopen downloads and the saved HTML. Review
front, side, back, seam, contact and heatmap screenshots. Log console, network,
heap, solver timings, triangle count and draw calls. Independently reconstruct
seams, topology, intersections and deformation from actual exported arrays.
Inject reversed seams, wrong panel IDs, a seam gap, body penetration and altered
rest coordinates; the validators must reject them. Preserve failures, correct
their causes and rerun. Report digital geometry, calibrated fabric accuracy and
manufacturing acceptance as separate claims. Continue until the bounded digital
acceptance checks pass; never silently convert an untested physical claim to PASS.
```

The useful pattern is a small, complete scope with measurable acceptance conditions and autonomous iteration. A short aspirational prompt alone cannot replace those invariants in a garment system.
