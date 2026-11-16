# Aster 01 — decision record

Date: 16 November 2026. Revision: 1.0.

The brief requested a Three.js dress, removal of seams, unfolding to 2D with seam lines, an HTML handoff, saved decisions and verification, and links for viewers and garment experts.

## Garment and measurements

I chose a strapless A-line concept with 8 bodice sectors and 8 skirt gores because its continuous conical surfaces have exact planar developments. A freeform double-curved bodice cannot flatten without strain, darts, or extra cuts; substituting arbitrary 2D shapes would make the review misleading.

Default **finished geometric** dimensions are top ring 920 mm, waist 760 mm, hem 2400 mm, bodice height 270 mm, and skirt height 780 mm. These are editable draft parameters, not a clothing size or wearer measurements. In particular the top ring is not a fitted bust circumference. No standard size, ease or body shape was supplied. Every numbered piece is cut once.

## One source for 3D and 2D

For each section, `r0 = waist/(2π)`, `dr = r1-r0`, `s = sqrt(h²+dr²)`, and `k = dr/s`. A sector spans `Δθ = 2π/8`. Its flat radius is `L = r0/k + s*t`; its flat angle is `β = (u-0.5)*Δθ*k`. Planar coordinates follow `x=L*sin(β)` and `y=L*cos(β)-r0/k` (flipped for the bodice layout). The continuous 3D and 2D surface metrics agree. The visible triangle mesh has small chord approximation error.

There are 24 explicit seam pairs. B01–B08 and S01–S08 connect each panel's right edge to the next panel's left edge, cyclically. W01–W08 connect corresponding bodice/skirt waist edges. Pair notches sit at half the sewing-line length; waist notches sit at the center of the waist arc. Grain follows the central generator of each panel. The top and hem are finish edges, not seam connections.

## Seam removal and animation

Release removes a connection from the application's seam state and applies a small local gap at that edge. Rejoin restores it. Unfold releases all joins, then interpolates the vertices from their assembled coordinates to their analytically developed coordinates. These intermediate display positions are illustrative. They do not simulate cloth mechanics, preserve length during the animation, or prove that a partly joined garment can physically lie flat. Hiding seam lines only changes their visibility.

## Cut contours

The default allowance is 10 mm; 6, 15 and 20 mm are also available. Hem turn-up is 25 mm. The cut contour is an outward offset of the planar stitch-boundary polyline, using line intersection for mitered corners. There are 96 samples per boundary edge. Offsets and intersections were checked computationally. Corners, neckline finishing and conical hem turn-up/easing still require patternmaker review.

## Expert review

Panel IDs are identical in the 3D mesh, SVG and seam map. Compare links selection between views. Geometry checks are visible in the Review tab. Review notes and checklists are browser-local; JSON exports contain the draft and notes for handoff. There is no shared database or multi-user comment synchronization. Share links include the current dimensions, selected panel, color, seam state, and entry view; they do not include reviewer notes.

## Production work not represented

The top is an inverted conical surface, not a shaped anatomical bust. There are no bust darts, hip accommodation validation, fit ease, material stretch, shrinkage or drape simulation. B04/S04 mark the center-back closure location, but zipper openings/extensions are not cut or drafted. Facing, lining, interfacing, boning, waist stay, closure support and a sewing-operation specification are absent. A qualified patternmaker must refine these features, review grain and hem handling, and fit a toile before production. Checked review boxes are human annotations and do not certify a garment.

## Technical and visual choices

The interface uses a quiet cutting-table palette, a large 3D stage, an adjacent technical inspector, native controls, and an SVG pattern board. The app is responsive and respects reduced motion. Three.js r180 is bundled into one HTML with no CDN, remote assets, telemetry, or external API calls. Browser storage is guarded so file-based or storage-disabled sessions can still export notes. A 2D fallback is available if WebGL2 fails.

The SVG uses real millimetre width/height and includes a 100 mm calibration square. It is a full-scale large-format sheet, not tiled A4/Letter pages. The HTML can be downloaded directly and opened offline.

References consulted: [BufferGeometry](https://threejs.org/docs/pages/BufferGeometry.html), [OrbitControls](https://threejs.org/docs/pages/OrbitControls.html), [MeshPhysicalMaterial](https://threejs.org/docs/pages/MeshPhysicalMaterial.html). The implementation is pinned to Three.js 0.180.0 and includes its MIT license.
