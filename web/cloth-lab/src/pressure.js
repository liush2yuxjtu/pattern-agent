// A calibration cloth coupon exercises the exact embedded solver on a
// plane of two triangles. Loads are equivalent acceleration times mass.
export async function solvePressureCoupon(wasmBytes, { loadPa, cells = 3, tilt = 0, detached = false, collision = true, steps = 45 }) {
  const { instance } = await WebAssembly.instantiate(wasmBytes, {});
  const w = instance.exports;
  const nv = (cells + 1) ** 2, nt = cells * cells * 2;
  const view = (ptr, length) => new Float32Array(w.memory.buffer, ptr, length);
  const writeFaces = (ptr, values) => new Int32Array(w.memory.buffer, ptr, values.length).set(values);
  const density = .22, side = .2, restArea = side * side;
  const angle = tilt * Math.PI / 180;
  const tangent = [Math.cos(angle), Math.sin(angle), 0];
  const n = [-tangent[1], tangent[0], 0];
  const at = (x, z, height) => [tangent[0] * x + n[0] * height, tangent[1] * x + n[1] * height, z];

  const corners = [at(-2,-2,0), at(-2,2,0), at(2,-2,0), at(2,2,0)];
  view(w.body_ptr(), 12).set(corners.flat());
  view(w.body_normal_ptr(), 12).set([...n, ...n, ...n, ...n]);
  writeFaces(w.body_face_ptr(), [0,1,2,1,3,2]);
  writeFaces(w.body_order_ptr(), [0,1]);
  const node = new DataView(w.memory.buffer, w.body_node_ptr(), 40);
  for (let axis = 0; axis < 3; axis++) {
    node.setFloat32(4 * axis, Math.min(...corners.map(p => p[axis])), true);
    node.setFloat32(12 + 4 * axis, Math.max(...corners.map(p => p[axis])), true);
  }
  for (const [index, value] of [-1,-1,0,2].entries()) node.setInt32(24 + index*4, value, true);
  w.configure_body(4, 2, 1);

  const positions = view(w.position_ptr(), nv*3);
  const uv = view(w.uv_ptr(), nv*2);
  const indices = [];
  const margin = w.pressure_margin();
  const height = detached ? margin + .045 : margin;
  for (let j = 0; j <= cells; j++) for (let i = 0; i <= cells; i++) {
    const index = j * (cells + 1) + i;
    const x = (i / cells - .5) * side, z = (j / cells - .5) * side;
    positions.set(at(x,z,height),index*3);
    uv.set([x,z],index*2);
    if (i < cells && j < cells) {
      const next = index + cells + 1;
      indices.push(index,next,index+1,next,next+1,index+1);
    }
  }
  writeFaces(w.face_ptr(), indices);
  w.configure_material(200000,120000,30000,.2,.0005,density);
  w.configure_cloth(nv,nt);
  w.finalize_seams();
  w.set_collision(+collision);
  w.set_gravity(...n.map(v => -v * loadPa / density));
  w.step(steps,0);
  w.analyze();
  const stats = view(w.pressure_summary_ptr(),10);
  const raw = view(w.pressure_lambda_ptr(),w.pressure_face_start()+nt);
  const response = {
    loadPa, cells, tilt, detached, collision, steps, restAreaM2:restArea, normal:n,
    expectedForceN:collision && !detached ? restArea * loadPa : 0,
    dtSeconds:w.pressure_dt(), marginM:margin, stiffnessPaPerM:w.pressure_stiffness(),
    totalNormalForceN:stats[1], resultantN:[stats[2],stats[3],stats[4]], activeSamples:stats[8],
    pressurePa:Array.from(view(w.pressure_ptr(),nv)), nodalAreaM2:Array.from(view(w.pressure_area_ptr(),nv)),
    nodalForceN:Array.from(view(w.pressure_force_ptr(),nv)),
    vertexLambdas:Array.from(raw.subarray(0,nv)),
    centroidLambdas:Array.from(raw.subarray(w.pressure_face_start())),
    positionsM:Array.from(positions), restUV:Array.from(uv), faces:indices
  };
  return response;
}
