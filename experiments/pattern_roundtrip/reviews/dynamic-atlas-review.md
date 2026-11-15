# Independent follow-up: the complete garment still fails a causal control

The tiny keyed-dynamic experiment proves that the rest input affects physical
positions. It does not validate the complete garment solver. The frozen primary
review's static-rest-key proposal was a hypothesis; its zero-display-weight advice
does not apply to the later animated dynamic-base schedule. Frame1 remains3D;
frame2 onward uses an animated2D base input, while Cloth preserves physical state.

The unwrap agent independently examined the first completed full-garment frames:

- Initial positions, triangles and sewing correspondences are exactly identical.
- Rigidly rotating/translating the2D charts changes actual float32 structural
  rest lengths by at most0.346µm, below the predeclared1µm metric tolerance.
- Physical output nevertheless differs by6.94656mm atframe2 and18.5998mm atframe3.
  The predeclared1mm trajectory tolerance therefore fails.
- Blender4.3.2 explicitly skips sewing springs in dynamic rest-length updates;
  the investigation does not support blaming atlas distances as sewing rest lengths.
- Independently recomputing the planar bending rest angles with the official
  formula gives zero for both atlases. A ±π branch explanation is unsupported.

Quantization amplified by stiffness, coincident seam endpoints or collisions,
and other internal dependence on base input remain hypotheses. The cause was not
located. Do not explain this as a legitimate grain response: materials are assumed
isotropic and no measured grain basis exists. Keep the original tolerance and FAIL.
Next experiments should isolate sewing, collisions and precision separately.

Official implementation:
https://github.com/blender/blender/blob/v4.3.2/source/blender/blenkernel/intern/cloth.cc#L1197

This is a causal-wiring and invariance critique, not a new physical-fit verdict.
