# Verification surfaces

Load only the recipe for each affected boundary. Cross-surface claims require all
applicable recipes; local checks do not stand in for hosted or physical acceptance.

| Surface | Public caller boundary | Operational recipe |
| --- | --- | --- |
| aster-geometry | local model assertions and rebuilt artifacts | [aster-geometry.md](aster-geometry.md) |
| browser-aster | rendered WebGL and real pointer input | [browser-aster.md](browser-aster.md) |
| aster-pattern-export | download, reopen, measured SVG/HTML/review | [aster-pattern-export.md](aster-pattern-export.md) |
| vercel-live-deploy | exact deployment and anonymous live URL | [vercel-live-deploy.md](vercel-live-deploy.md) |
| github-pages | OpenSloper CLI/MCP, PDFs, live Pages browser | [github-pages.md](github-pages.md) |
| garmentcode-preview | GLB/downloaded HTML and live browser | [garmentcode-preview.md](garmentcode-preview.md) |
| full-arm | pipeline CLI and independently reopened Blender | [full-arm.md](full-arm.md) |
| oneshot-control | experiment CLI and independent oracle | [oneshot-control.md](oneshot-control.md) |
| oneshot-motion | saved meshes and independently reopened replay | [oneshot-motion.md](oneshot-motion.md) |
| pattern-roundtrip | physical-size PDF, independent verifier, replay | [pattern-roundtrip.md](pattern-roundtrip.md) |
| legacy-cloth | archived evidence; unavailable legacy runtime | [legacy-cloth.md](legacy-cloth.md) |
