# Synthetic neutral proxy fitting control
All images are SYNTHETIC CONTROLS generated from a simplified proxy; no person or anatomical ground truth is represented. Lengths are in centimetres only under an assumed 170 cm height prior. Target front and side masks are supplied; target parameters are intentionally absent. No back reference is observed.

Run `python generator.py --params initial-params.json --out initial` to regenerate the biased initial geometry and previews. NumPy and Pillow are the only dependencies. JSON parameters are height, chest/waist/hip ellipse circumference, and depth_ratio (depth radius / width radius). The head and limbs are fixed except global height scaling. Mesh is a collection of capped, disconnected lofts with OBJ groups.

Target and candidate images must use camera.json: frozen orthographic projection, 384×640 canvas, x in [-50,50], y in [-4,180], +y up. Masks are white foreground on black. Changing image size, camera or translating the body to hide mismatch is outside this control. Target labels are in this README rather than burned into binary mask pixels.

Fit a neutral proxy by constrained silhouette fitting; keep height=170 and physically positive circumferences with 0.45<=depth_ratio<=1.05. Report initial/final mask errors on both supplied views, publish actual fitted OBJ and front/side/back previews, and distinguish the assumed scale and inferred depth from observed reference evidence. Utility `generator.py` only constructs/renders geometry; it does not optimize it.
