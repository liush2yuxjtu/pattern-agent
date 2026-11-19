import { createBodyCollider } from './body-contact.js';

export const TIMESTEP = 1 / 120;
const edgeKey = (a, b) => a < b ? `${a},${b}` : `${b},${a}`;
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const minus = (a, b) => a.map((v, i) => v - b[i]);

function closestTriangle(point, a, b, c) {
  const ab = minus(b, a), ac = minus(c, a), ap = minus(point, a), d1 = dot(ab, ap), d2 = dot(ac, ap);
  if (d1 <= 0 && d2 <= 0) return [1, 0, 0];
  const bp = minus(point, b), d3 = dot(ab, bp), d4 = dot(ac, bp);
  if (d3 >= 0 && d4 <= d3) return [0, 1, 0];
  const vc = d1 * d4 - d3 * d2;
  if (vc <= 0 && d1 >= 0 && d3 <= 0) { const v = d1 / (d1 - d3); return [1 - v, v, 0]; }
  const cp = minus(point, c), d5 = dot(ab, cp), d6 = dot(ac, cp);
  if (d6 >= 0 && d5 <= d6) return [0, 0, 1];
  const vb = d5 * d2 - d1 * d6;
  if (vb <= 0 && d2 >= 0 && d6 <= 0) { const v = d2 / (d2 - d6); return [1 - v, 0, v]; }
  const va = d3 * d6 - d5 * d4;
  if (va <= 0 && d4 - d3 >= 0 && d5 - d6 >= 0) { const v = (d4 - d3) / (d4 - d3 + d5 - d6); return [0, 1 - v, v]; }
  const scale = 1 / (va + vb + vc), v = vb * scale, w = vc * scale;
  return [1 - v - w, v, w];
}

function closestSegments(a, b, c, d) {
  const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2], vx = d[0] - c[0], vy = d[1] - c[1], vz = d[2] - c[2], rx = a[0] - c[0], ry = a[1] - c[1], rz = a[2] - c[2];
  const uu = ux * ux + uy * uy + uz * uz, vv = vx * vx + vy * vy + vz * vz, uv = ux * vx + uy * vy + uz * vz, ur = ux * rx + uy * ry + uz * rz, vr = vx * rx + vy * ry + vz * rz, denominator = uu * vv - uv * uv;
  let s = denominator > 1e-15 ? Math.max(0, Math.min(1, (uv * vr - ur * vv) / denominator)) : 0;
  let t = (uv * s + vr) / vv;
  if (t < 0) { t = 0; s = Math.max(0, Math.min(1, -ur / uu)); }
  else if (t > 1) { t = 1; s = Math.max(0, Math.min(1, (uv - ur) / uu)); }
  return [s, t];
}

export function createSimulation(doc, body, options = {}) {
  const source = doc.mesh, count = source.restUV.length, parent = Int32Array.from({ length: count }, (_, i) => i);
  const find = i => parent[i] === i ? i : parent[i] = find(parent[i]);
  for (const seam of doc.seams) for (const [a, b] of seam.pairs) parent[find(b)] = find(a);
  const seamSets = new Map();
  for (let i = 0; i < count; i++) { const root = find(i); if (!seamSets.has(root)) seamSets.set(root, []); seamSets.get(root).push(i); }
  const seamGroups = [...seamSets.values()].filter(group => group.length > 1);
  const nodes = count, p = new Float64Array(nodes * 3), previous = new Float64Array(nodes * 3), velocity = new Float64Array(nodes * 3), output = new Float32Array(count * 3), mass = new Float64Array(nodes).fill(1);
  p.set(source.initial);
  const constraints = source.edges.map(e => ({ a: e.a, b: e.b, rest: e.restMm / 1000, compliance: 0 }));
  const triangles = [];
  for (let i = 0; i < source.triangles.length; i += 3) triangles.push(source.triangles.slice(i, i + 3));
  const bending = [];
  const restDistance = (a, b) => Math.hypot(source.restUV[a][0] - source.restUV[b][0], source.restUV[a][1] - source.restUV[b][1]) / 1000;
  for (const piece of doc.pieces) {
    const es = new Map();
    for (let i = 0; i < piece.triangles.length; i += 3) {
      const [a, b, c] = piece.triangles.slice(i, i + 3).map(v => v + piece.offset);
      for (const [x, y, z] of [[a, b, c], [b, c, a], [c, a, b]]) {
        const k = edgeKey(x, y);
        if (es.has(k)) { const other = es.get(k); bending.push({ a: other, b: z, rest: restDistance(other, z), compliance: .002 }); }
        else es.set(k, z);
      }
    }
  }
  const pinNodes = source.pins.slice(), pinTargets = pinNodes.map(i => Array.from(p.slice(i * 3, i * 3 + 3)));
  const initialPinTargets = pinTargets.map(point => point.slice());
  const collider = body && options.contact !== false ? createBodyCollider(body) : null;
  const contactResult = { point: [0, 0, 0], normal: [0, 0, 0], signedDistance: 0, triangle: -1 }, triangleResult = { point: [0, 0, 0], normal: [0, 0, 0], signedDistance: 0, triangle: -1 }, statsResult = { point: [0, 0, 0], normal: [0, 0, 0], signedDistance: 0, triangle: -1 };
  const bodyQuery = (x, y, z, hint, result) => collider.closestPointInto ? collider.closestPointInto(x, y, z, hint, result) : collider.closestPoint(x, y, z, hint);
  const clearance = options.clearance ?? .004, iterations = options.iterations ?? 50, contactHints = new Int32Array(nodes).fill(-1), normals = new Float64Array(nodes * 3), plane = new Float64Array(nodes * 3), activeContact = new Uint8Array(nodes);
  const bodySamples = [...triangles, ...source.edges.map(e => [e.a, e.b])];
  const sampleHints = new Int32Array(bodySamples.length).fill(-1);
  const sampleNormals = new Float64Array(bodySamples.length * 3), samplePlanes = new Float64Array(bodySamples.length * 3), sampleActive = new Uint8Array(bodySamples.length);
  const initialPinned = Boolean(options.pinned ?? false);
  let gravity = options.gravity ?? 9.81, steps = 0, pinned = initialPinned, phase = 'assembling', disposed = false;
  let selfConstraints = [];
  const selfVertexPoints = Array.from({ length: nodes }, () => [0, 0, 0]);
  const selfBoxes = triangles.map(ids => ({ min: [0, 0, 0], max: [0, 0, 0], points: ids.map(i => selfVertexPoints[i]) }));
  const collisionRoots = Int32Array.from({ length: nodes }, (_, i) => find(i));
  const featureMasks = new Uint16Array(triangles.length * triangles.length);
  const selfPairs = new Set();
  const selfBuckets = new Map();
  const bucketPool = new Map();
  let selfQueries = 0, topologyCacheHits = 0, topologyCacheMisses = 0;
  function featureMask(pair, a, b) {
    let mask = featureMasks[pair];
    if (mask & 32768) { topologyCacheHits++; return mask; }
    topologyCacheMisses++; mask = 32768;
    for (let j = 0; j < 3; j++) {
      const ar = collisionRoots[a[j]], br = collisionRoots[b[j]];
      if (ar !== collisionRoots[b[0]] && ar !== collisionRoots[b[1]] && ar !== collisionRoots[b[2]]) mask |= 1 << j;
      if (br !== collisionRoots[a[0]] && br !== collisionRoots[a[1]] && br !== collisionRoots[a[2]]) mask |= 1 << (j + 3);
      const nextA = collisionRoots[a[(j + 1) % 3]];
      for (let k = 0; k < 3; k++) {
        const firstB = collisionRoots[b[k]], nextB = collisionRoots[b[(k + 1) % 3]];
        if (ar !== firstB && ar !== nextB && nextA !== firstB && nextA !== nextB) mask |= 1 << (6 + j * 3 + k);
      }
    }
    featureMasks[pair] = mask;
    return mask;
  }
  const collisionReference = p.slice();
  let collisionReferenceReady = false, maxAttemptedCollisionMotion = 0, limitedCollisionIterations = 0;
  function limitCollisionMotion() {
    if (!collisionReferenceReady || options.selfContact === false) return false;
    let maximum = 0, limited = false;
    for (let i = 0; i < nodes; i++) {
      const at = i * 3, x = p[at] - collisionReference[at], y = p[at + 1] - collisionReference[at + 1], z = p[at + 2] - collisionReference[at + 2];
      const distance = Math.sqrt(x * x + y * y + z * z);
      maximum = Math.max(maximum, distance);
      if (distance > .001) {
        const scale = .001 / distance;
        p[at] = collisionReference[at] + x * scale; p[at + 1] = collisionReference[at + 1] + y * scale; p[at + 2] = collisionReference[at + 2] + z * scale; limited = true;
      }
    }
    maxAttemptedCollisionMotion = Math.max(maxAttemptedCollisionMotion, maximum);
    if (limited) limitedCollisionIterations++;
    return limited;
  }
  const preparedContact = Boolean(collider);
  function setPins() {
    mass.fill(1);
    if (pinned) for (let j = 0; j < pinNodes.length; j++) {
      const i = pinNodes[j]; mass[i] = 0;
      for (let a = 0; a < 3; a++) p[i * 3 + a] = pinTargets[j][a];
    }
  }
  function solveDistance(list, strength = 1) {
    for (let i = 0; i < list.length; i++) {
      const e = list[list.length - 1 - i], a = e.a, b = e.b, ia = a * 3, ib = b * 3;
      const dx = p[ia] - p[ib], dy = p[ia + 1] - p[ib + 1], dz = p[ia + 2] - p[ib + 2], d = Math.sqrt(dx * dx + dy * dy + dz * dz), w = mass[a] + mass[b];
      if (!w || d < 1e-12) continue;
      const alpha = e.compliance / (TIMESTEP * TIMESTEP), lambda = e.lambda ?? 0;
      let delta = (d - e.rest - alpha * lambda) * strength / (w + alpha);
      if (preparedContact && steps < 12) delta = Math.max(-.00025, Math.min(.00025, delta));
      e.lambda = lambda + delta;
      const correction = delta / d;
      p[ia] -= dx * correction * mass[a]; p[ia + 1] -= dy * correction * mass[a]; p[ia + 2] -= dz * correction * mass[a];
      p[ib] += dx * correction * mass[b]; p[ib + 1] += dy * correction * mass[b]; p[ib + 2] += dz * correction * mass[b];
    }
  }
  function solveSeams() {
    for (const group of seamGroups) {
      const fixed = group.find(i => !mass[i]), point = [0, 0, 0];
      if (fixed !== undefined) for (let axis = 0; axis < 3; axis++) point[axis] = p[fixed * 3 + axis];
      else for (const i of group) for (let axis = 0; axis < 3; axis++) point[axis] += p[i * 3 + axis] / group.length;
      for (const i of group) for (let axis = 0; axis < 3; axis++) p[i * 3 + axis] = point[axis];
    }
  }
  function queryContact(project = true) {
    if (!collider) return;
    const targetClearance = clearance;
    for (let i = 0; i < nodes; i++) {
      const at = i * 3, result = bodyQuery(p[at], p[at + 1], p[at + 2], contactHints[i], contactResult);
      contactHints[i] = result.triangle;
      activeContact[i] = result.signedDistance < targetClearance + .004;
      for (let a = 0; a < 3; a++) { normals[at + a] = result.normal[a]; plane[at + a] = result.point[a] + targetClearance * result.normal[a]; }
      if (project && result.signedDistance < targetClearance && mass[i]) for (let a = 0; a < 3; a++) p[at + a] += result.normal[a] * (targetClearance - result.signedDistance);
    }
  }
  function projectPlanes() {
    if (!collider) return;
    for (let i = 0; i < nodes; i++) {
      if (!activeContact[i] || !mass[i]) continue;
      const at = i * 3, d = (p[at] - plane[at]) * normals[at] + (p[at + 1] - plane[at + 1]) * normals[at + 1] + (p[at + 2] - plane[at + 2]) * normals[at + 2];
      if (d < 0) for (let a = 0; a < 3; a++) p[at + a] -= d * normals[at + a];
    }
  }
  function queryTriangleSamples() {
    if (!collider) return;
    const targetClearance = clearance;
    for (let t = 0; t < bodySamples.length; t++) {
      const ids = bodySamples[t], x = ids.reduce((v, i) => v + p[i * 3], 0) / ids.length, y = ids.reduce((v, i) => v + p[i * 3 + 1], 0) / ids.length, z = ids.reduce((v, i) => v + p[i * 3 + 2], 0) / ids.length;
      const result = bodyQuery(x, y, z, sampleHints[t], triangleResult); sampleHints[t] = result.triangle;
      sampleActive[t] = result.signedDistance < targetClearance + .004;
      for (let a = 0; a < 3; a++) { sampleNormals[t * 3 + a] = result.normal[a]; samplePlanes[t * 3 + a] = result.point[a] + targetClearance * result.normal[a]; }
    }
  }
  function projectTrianglePlanes() {
    if (!collider) return;
    for (let t = 0; t < bodySamples.length; t++) {
      if (!sampleActive[t]) continue;
      const ids = bodySamples[t], at = t * 3;
      let d = 0, w = 0;
      for (let axis = 0; axis < 3; axis++) d += (ids.reduce((v, i) => v + p[i * 3 + axis], 0) / ids.length - samplePlanes[at + axis]) * sampleNormals[at + axis];
      if (d >= 0) continue;
      for (const i of ids) w += mass[i];
      if (w) for (const i of ids) for (let axis = 0; axis < 3; axis++) p[i * 3 + axis] -= mass[i] * ids.length / w * sampleNormals[at + axis] * d;
    }
  }
  function querySelfTriangles() {
    solveSeams(); setPins();
    const thickness = options.selfThickness ?? .003, cell = .045, buckets = selfBuckets, pairs = selfPairs, boxes = selfBoxes;
    buckets.clear(); pairs.clear(); selfQueries++;
    const xyz = i => selfVertexPoints[i];
    for (let i = 0; i < nodes; i++) { const point = selfVertexPoints[i]; point[0] = p[i * 3]; point[1] = p[i * 3 + 1]; point[2] = p[i * 3 + 2]; }
    selfConstraints = [];
    for (let t = 0; t < triangles.length; t++) {
      const { points, min, max } = boxes[t];
      for (let axis = 0; axis < 3; axis++) { min[axis] = Math.min(points[0][axis], points[1][axis], points[2][axis]) - thickness; max[axis] = Math.max(points[0][axis], points[1][axis], points[2][axis]) + thickness; }
      if (min.some((v, axis) => !Number.isFinite(v) || max[axis] - v > .5)) throw new Error('Cloth diverged before self-contact broad phase.');
      for (let x = Math.floor(min[0] / cell); x <= Math.floor(max[0] / cell); x++) for (let y = Math.floor(min[1] / cell); y <= Math.floor(max[1] / cell); y++) for (let z = Math.floor(min[2] / cell); z <= Math.floor(max[2] / cell); z++) {
        const k = `${x},${y},${z}`;
        if (!buckets.has(k)) { let list = bucketPool.get(k); if (!list) { list = []; bucketPool.set(k, list); } list.length = 0; buckets.set(k, list); }
        const list = buckets.get(k);
        for (const other of list) pairs.add(other * triangles.length + t);
        list.push(t);
      }
    }
    function add(a, wa, b, wb) {
      let dx = 0, dy = 0, dz = 0;
      for (let j = 0; j < 3; j++) { dx += p[a[j] * 3] * wa[j] - p[b[j] * 3] * wb[j]; dy += p[a[j] * 3 + 1] * wa[j] - p[b[j] * 3 + 1] * wb[j]; dz += p[a[j] * 3 + 2] * wa[j] - p[b[j] * 3 + 2] * wb[j]; }
      const squared = dx * dx + dy * dy + dz * dz;
      if (squared >= (thickness + .002) ** 2) return;
      let distance = Math.sqrt(squared), normal = [dx, dy, dz];
      if (distance < 1e-8) {
        const ba = minus(xyz(b[1]), xyz(b[0])), ca = minus(xyz(b[2]), xyz(b[0]));
        normal = [ba[1] * ca[2] - ba[2] * ca[1], ba[2] * ca[0] - ba[0] * ca[2], ba[0] * ca[1] - ba[1] * ca[0]];
        const length = Math.hypot(...normal);
        if (length < 1e-12) return;
        normal = normal.map(v => v / length);
        let sign = 0;
        for (let j = 0; j < 3; j++) for (let axis = 0; axis < 3; axis++) sign += (previous[a[j] * 3 + axis] * wa[j] - previous[b[j] * 3 + axis] * wb[j]) * normal[axis];
        if (sign < 0) normal = normal.map(v => -v);
      } else normal = normal.map(v => v / distance);
      selfConstraints.push({ a, wa, b, wb, normal, thickness });
    }
    function pointNearBox(point, box) {
      let square = 0;
      for (let axis = 0; axis < 3; axis++) { const d = Math.max(box.min[axis] + thickness - point[axis], point[axis] - box.max[axis] + thickness, 0); square += d * d; }
      return square <= (thickness + .002) ** 2;
    }
    function segmentsNear(a, b, c, d) {
      let square = 0;
      for (let axis = 0; axis < 3; axis++) { const gap = Math.max(Math.min(a[axis], b[axis]) - Math.max(c[axis], d[axis]), Math.min(c[axis], d[axis]) - Math.max(a[axis], b[axis]), 0); square += gap * gap; }
      return square <= (thickness + .002) ** 2;
    }
    for (const pair of pairs) {
      const ta = Math.floor(pair / triangles.length), tb = pair % triangles.length, a = triangles[ta], b = triangles[tb], aa = boxes[ta], bb = boxes[tb];
      if ([0, 1, 2].some(axis => aa.min[axis] > bb.max[axis] || bb.min[axis] > aa.max[axis])) continue;
      const mask = featureMask(pair, a, b);
      for (let j = 0; j < 3; j++) {
        const w = [0, 0, 0]; w[j] = 1;
        if ((mask & (1 << j)) && pointNearBox(aa.points[j], bb)) add(a, w, b, closestTriangle(aa.points[j], ...bb.points));
        if ((mask & (1 << (j + 3))) && pointNearBox(bb.points[j], aa)) add(b, w, a, closestTriangle(bb.points[j], ...aa.points));

      }
      for (let j = 0; j < 3; j++) for (let k = 0; k < 3; k++) {
        if (!(mask & (1 << (6 + j * 3 + k)))) continue;
        if (!segmentsNear(aa.points[j], aa.points[(j + 1) % 3], bb.points[k], bb.points[(k + 1) % 3])) continue;
        const [s, t] = closestSegments(aa.points[j], aa.points[(j + 1) % 3], bb.points[k], bb.points[(k + 1) % 3]), wa = [0, 0, 0], wb = [0, 0, 0];
        wa[j] = 1 - s; wa[(j + 1) % 3] = s; wb[k] = 1 - t; wb[(k + 1) % 3] = t; add(a, wa, b, wb);
      }
    }
    collisionReference.set(p); collisionReferenceReady = true;
  }
  function projectSelfTriangles() {
    for (const c of selfConstraints) {
      const delta = [0, 0, 0];
      let w = 0;
      for (let j = 0; j < 3; j++) {
        w += mass[c.a[j]] * c.wa[j] ** 2 + mass[c.b[j]] * c.wb[j] ** 2;
        for (let axis = 0; axis < 3; axis++) delta[axis] += p[c.a[j] * 3 + axis] * c.wa[j] - p[c.b[j] * 3 + axis] * c.wb[j];
      }
      const normal = c.normal, d = dot(delta, normal);
      if (d >= c.thickness || !w) continue;
      const correction = Math.min(.002, (c.thickness - d) / w);
      for (let j = 0; j < 3; j++) for (let axis = 0; axis < 3; axis++) {
        p[c.a[j] * 3 + axis] += mass[c.a[j]] * c.wa[j] * correction * normal[axis];
        p[c.b[j] * 3 + axis] -= mass[c.b[j]] * c.wb[j] * correction * normal[axis];
      }
    }
  }
  function positions() {
    output.set(p);
    return output;
  }
  function stats() {
    const out = positions(), strain = source.edges.map(e => Math.abs(Math.hypot(out[e.a * 3] - out[e.b * 3], out[e.a * 3 + 1] - out[e.b * 3 + 1], out[e.a * 3 + 2] - out[e.b * 3 + 2]) * 1000 / e.restMm - 1)).sort((a, b) => a - b);
    let penetration = 0, speed = 0, seamResidual = 0;
    for (const seam of doc.seams) for (const [a, b] of seam.pairs) seamResidual = Math.max(seamResidual, Math.hypot(out[a * 3] - out[b * 3], out[a * 3 + 1] - out[b * 3 + 1], out[a * 3 + 2] - out[b * 3 + 2]) * 1000);
    if (collider) for (let i = 0; i < nodes; i++) penetration = Math.max(penetration, -bodyQuery(p[i * 3], p[i * 3 + 1], p[i * 3 + 2], contactHints[i], statsResult).signedDistance * 1000);
    for (let i = 0; i < nodes; i++) speed += Math.hypot(velocity[i * 3], velocity[i * 3 + 1], velocity[i * 3 + 2]) / nodes;
    const p95 = strain[Math.floor(strain.length * .95)], max = strain.at(-1);
    phase = steps >= 240 && p95 <= .05 && max <= .15 && penetration <= 1 && seamResidual <= 2 ? 'finished' : 'assembling';
    return { time: steps * TIMESTEP, steps, phase, finite: Array.from(out).every(Number.isFinite), particles: count, physicalParticles: nodes, triangles: triangles.length, pinCount: pinned ? pinNodes.length : 0, seamResidualMm: seamResidual, p95EdgeStrain: p95, maxEdgeStrain: max, maxBodyPenetrationMm: penetration, meanSpeedMps: speed, selfContactConstraints: selfConstraints.length, maxAttemptedCollisionMotionMm: maxAttemptedCollisionMotion * 1000, limitedCollisionIterations, seamMode: 'independent panel particles with zero-length equality seam constraints; no dynamic sewing closure', gravity };
  }
  setPins();
  queryContact();
  const initial = p.slice();
  const geometry = JSON.stringify([source.restUV, source.triangles, doc.seams.map(seam => seam.pairs), source.pins, body?.positions, body?.triangles]);
  let hashA = 2166136261, hashB = 2654435769;
  for (let i = 0; i < geometry.length; i++) { hashA = Math.imul(hashA ^ geometry.charCodeAt(i), 16777619); hashB = Math.imul(hashB ^ geometry.charCodeAt(i), 2246822519); }
  const documentKey = `cloth-v1-${(hashA >>> 0).toString(16)}-${(hashB >>> 0).toString(16)}-${geometry.length}`;
  const solverParameters = { timestep: TIMESTEP, iterations, clearance, selfThickness: options.selfThickness ?? .003, contact: Boolean(collider), selfContact: options.selfContact !== false, constraintSweep: 'fixed-backward', solverRevision: 'xpbd-panel-2' };
  function clearContactHistory() {
    collisionReference.set(p); collisionReferenceReady = true; selfConstraints = [];
    activeContact.fill(0); sampleActive.fill(0); contactHints.fill(-1); sampleHints.fill(-1);
  }
  positions();
  return {
    doc, body, collider, positions, stats,
    perfDiagnostics() { return { selfQueries, topologyCacheHits, topologyCacheMisses, maskBytes: featureMasks.byteLength, pooledCells: bucketPool.size }; },
    step(n = 1) {
      if (disposed) throw new Error('Simulation is disposed.');
      for (let step = 0; step < n; step++) {
        previous.set(p);
        collisionReference.set(p); collisionReferenceReady = true;
        for (const edge of constraints) edge.lambda = 0;
        for (const edge of bending) edge.lambda = 0;
        for (let i = 0; i < nodes; i++) if (mass[i]) {
          velocity[i * 3 + 1] -= gravity * TIMESTEP;
          for (let a = 0; a < 3; a++) p[i * 3 + a] += velocity[i * 3 + a] * TIMESTEP;
        }
        limitCollisionMotion();
        queryContact();
        limitCollisionMotion();
        queryTriangleSamples();
        if (options.selfContact !== false) querySelfTriangles();
        for (let iteration = 0; iteration < iterations; iteration++) {
          solveDistance(constraints); solveDistance(bending); projectPlanes(); projectTrianglePlanes(); projectSelfTriangles(); solveSeams(); setPins();
          const limited = limitCollisionMotion();
          if (iteration === Math.floor(iterations / 2)) { queryContact(); limitCollisionMotion(); queryTriangleSamples(); if (steps < 60 && options.selfContact !== false) querySelfTriangles(); }
          if (preparedContact && steps < 12 && iteration % 4 === 3) { queryContact(); limitCollisionMotion(); queryTriangleSamples(); if (options.selfContact !== false) querySelfTriangles(); }
          else if (limited && iteration % 4 === 3 && options.selfContact !== false) { queryContact(); limitCollisionMotion(); queryTriangleSamples(); querySelfTriangles(); }
        }
        queryContact();
        for (let iteration = 0; iteration < 4; iteration++) { solveSeams(); setPins(); }
        limitCollisionMotion();
        solveSeams(); setPins();
        for (let i = 0; i < nodes; i++) for (let a = 0; a < 3; a++) velocity[i * 3 + a] = collider && steps < 60 ? 0 : (p[i * 3 + a] - previous[i * 3 + a]) / TIMESTEP * .985;
        for (let i = 0; i < nodes; i++) if (activeContact[i]) {
          const at = i * 3, normalSpeed = velocity[at] * normals[at] + velocity[at + 1] * normals[at + 1] + velocity[at + 2] * normals[at + 2];
          for (let a = 0; a < 3; a++) velocity[at + a] = (velocity[at + a] - Math.min(0, normalSpeed) * normals[at + a]) * .85;
        }
        steps++;
      }
      return positions();
    },
    reset() { p.set(initial); previous.set(initial); velocity.fill(0); steps = 0; phase = 'assembling'; pinned = initialPinned; for (let i = 0; i < pinTargets.length; i++) pinTargets[i] = initialPinTargets[i].slice(); maxAttemptedCollisionMotion = 0; limitedCollisionIterations = 0; setPins(); clearContactHistory(); return positions(); },
    state() { return { format: 'cloth-studio-live-state', version: 1, units: 'm', documentKey, solverParameters: { ...solverParameters }, positions: Array.from(p), previous: Array.from(previous), velocities: Array.from(velocity), pinTargets: pinTargets.map(point => point.slice()), steps, time: steps * TIMESTEP, phase, gravity, pinned, maxAttemptedCollisionMotion, limitedCollisionIterations, contactHistory: 'Rebuilt from the current exact mesh and positions before the next step.' }; },
    restoreState(state) {
      if (state.format !== 'cloth-studio-live-state' || state.version !== 1 || state.documentKey !== documentKey || JSON.stringify(state.solverParameters) !== JSON.stringify(solverParameters) || state.positions?.length !== p.length || state.previous?.length !== p.length || state.velocities?.length !== velocity.length || state.pinTargets?.length !== pinTargets.length || state.pinTargets.some(point => point.length !== 3) || !Number.isSafeInteger(state.steps) || state.steps < 0 || !Number.isFinite(state.gravity) || ![...state.positions, ...state.previous, ...state.velocities, ...state.pinTargets.flat()].every(Number.isFinite)) throw new Error('Live state does not match this garment or contains invalid values.');
      p.set(state.positions); previous.set(state.previous); velocity.set(state.velocities); for (let i = 0; i < pinTargets.length; i++) pinTargets[i] = state.pinTargets[i].slice(); steps = state.steps; phase = state.phase; gravity = state.gravity; pinned = Boolean(state.pinned);
      maxAttemptedCollisionMotion = state.maxAttemptedCollisionMotion || 0; limitedCollisionIterations = state.limitedCollisionIterations || 0;
      setPins(); clearContactHistory(); return positions();
    },
    setGravity(value) { if (!Number.isFinite(value)) throw new Error('Gravity must be finite.'); gravity = value; },
    setPinned(value) { const next = Boolean(value); if (next && !pinned) for (let i = 0; i < pinNodes.length; i++) pinTargets[i] = Array.from(p.slice(pinNodes[i] * 3, pinNodes[i] * 3 + 3)); pinned = next; setPins(); },
    setPositions(value) {
      if (value.length !== count * 3 || !Array.from(value).every(Number.isFinite)) throw new Error('Invalid position array.');
      p.set(value);
      velocity.fill(0); phase = 'assembling'; setPins(); clearContactHistory(); return positions();
    },
    poke(index = -1, delta = [.06, .01, .12]) {
      if (index >= 0) { const i = index; for (let a = 0; a < 3; a++) if (mass[i]) velocity[i * 3 + a] += delta[a]; }
      else for (let i = 0; i < nodes; i++) if (mass[i]) { velocity[i * 3] += delta[0] * Math.sin(p[i * 3 + 1] * 7); velocity[i * 3 + 1] += delta[1]; velocity[i * 3 + 2] += delta[2]; }
    },
    dispose() { disposed = true; },
  };
}
