import { Teagan } from '@freesewing/teagan';
import earcut from 'earcut';
import { createBodyCollider } from './body-contact.js';

export const CASES = [
  { id: 'baseline', chestMm: 855, lengthMm: 650, sleeveMm: 200, easePct: 24, allowanceMm: 10 },
  { id: 'wider', chestMm: 895, lengthMm: 650, sleeveMm: 200, easePct: 24, allowanceMm: 10 },
  { id: 'longer', chestMm: 855, lengthMm: 710, sleeveMm: 200, easePct: 24, allowanceMm: 10 },
];
export const defaultInput = () => ({ ...CASES[0] });
const len = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const xy = p => [p.x, p.y];
const key = (a, b) => a < b ? `${a},${b}` : `${b},${a}`;
const area = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);

export function validateInput(input) {
  for (const [name, min, max] of [['chestMm', 800, 1150], ['lengthMm', 550, 780], ['sleeveMm', 185, 280], ['easePct', 12, 30], ['allowanceMm', 0, 20]]) {
    if (!Number.isFinite(input[name]) || input[name] < min || input[name] > max) throw new Error(`${name} must be between ${min} and ${max}.`);
  }
  return input;
}

function polyline(path) {
  const result = [];
  let previous;
  for (const op of path.ops) {
    if (op.type === 'move') { previous = xy(op.to); result.push(previous); }
    else if (op.type === 'line') { previous = xy(op.to); result.push(previous); }
    else if (op.type === 'curve') {
      const a = previous, b = xy(op.cp1), c = xy(op.cp2), d = xy(op.to);
      for (let j = 1; j <= 80; j++) {
        const t = j / 80, s = 1 - t;
        result.push([s ** 3 * a[0] + 3 * s * s * t * b[0] + 3 * s * t * t * c[0] + t ** 3 * d[0], s ** 3 * a[1] + 3 * s * s * t * b[1] + 3 * s * t * t * c[1] + t ** 3 * d[1]]);
      }
      previous = d;
    }
  }
  return result;
}

function resample(points, segments) {
  const cumulative = [0];
  for (let i = 1; i < points.length; i++) cumulative.push(cumulative.at(-1) + len(points[i - 1], points[i]));
  const out = [];
  let j = 1;
  for (let i = 0; i <= segments; i++) {
    const target = cumulative.at(-1) * i / segments;
    while (j < cumulative.length - 1 && cumulative[j] < target) j++;
    const t = (target - cumulative[j - 1]) / (cumulative[j] - cumulative[j - 1] || 1);
    out.push(points[j - 1].map((x, k) => x + (points[j][k] - x) * t));
  }
  return out;
}

function nearestFraction(points, point) {
  let length = 0, closest = Infinity, at = 0;
  const total = points.slice(1).reduce((v, p, i) => v + len(p, points[i]), 0);
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1], b = points[i], d = len(a, b), t = Math.max(0, Math.min(1, ((point[0] - a[0]) * (b[0] - a[0]) + (point[1] - a[1]) * (b[1] - a[1])) / (d * d || 1)));
    const distance = Math.hypot(point[0] - a[0] - t * (b[0] - a[0]), point[1] - a[1] - t * (b[1] - a[1]));
    if (distance < closest) { closest = distance; at = length + t * d; }
    length += d;
  }
  return at / total;
}

function slicePolyline(points, from, to) {
  const dense = resample(points, 1200), a = Math.round(from * 1200), b = Math.round(to * 1200);
  return dense.slice(a, b + 1);
}

function offsetPolygon(points, distance) {
  if (!distance) return points.map(p => p.slice());
  const positive = points.reduce((a, p, i) => a + p[0] * points[(i + 1) % points.length][1] - p[1] * points[(i + 1) % points.length][0], 0) > 0;
  return points.map((p, i) => {
    const before = points[(i + points.length - 1) % points.length], after = points[(i + 1) % points.length], s = positive ? 1 : -1;
    const n1 = [(p[1] - before[1]) * s / len(p, before), (before[0] - p[0]) * s / len(p, before)];
    const n2 = [(after[1] - p[1]) * s / len(after, p), (p[0] - after[0]) * s / len(after, p)];
    const scale = distance / Math.max(.3, 1 + n1[0] * n2[0] + n1[1] * n2[1]);
    return [p[0] + (n1[0] + n2[0]) * scale, p[1] + (n1[1] + n2[1]) * scale];
  });
}

function contains(p, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const a = polygon[i], b = polygon[j];
    if ((a[1] > p[1]) !== (b[1] > p[1]) && p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
  }
  return inside;
}

function segmentDistance(p, a, b) {
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / len(a, b) ** 2));
  return Math.hypot(p[0] - a[0] - t * (b[0] - a[0]), p[1] - a[1] - t * (b[1] - a[1]));
}

function triangulate(boundary, spacing = 26) {
  const vertices = boundary.map(p => p.slice()), triangles = [];
  const raw = earcut(boundary.flat());
  for (let i = 0; i < raw.length; i += 3) {
    const signed = area(vertices[raw[i]], vertices[raw[i + 1]], vertices[raw[i + 2]]);
    if (Math.abs(signed) > 1e-6) triangles.push(signed > 0 ? raw.slice(i, i + 3) : [raw[i], raw[i + 2], raw[i + 1]]);
  }
  for (let n = 0; n < boundary.length; n++) {
    if (triangles.some(t => t.includes(n))) continue;
    const p = vertices[n];
    for (let i = 0; i < triangles.length; i++) {
      let done = false;
      for (let j = 0; j < 3; j++) {
        const a = triangles[i][j], b = triangles[i][(j + 1) % 3], c = triangles[i][(j + 2) % 3];
        if (segmentDistance(p, vertices[a], vertices[b]) < 1e-6 && len(p, vertices[a]) > 1e-5 && len(p, vertices[b]) > 1e-5) {
          triangles.splice(i, 1, [a, n, c], [n, b, c]); done = true; break;
        }
      }
      if (done) break;
    }
  }
  const minX = Math.min(...boundary.map(p => p[0])), maxX = Math.max(...boundary.map(p => p[0])), minY = Math.min(...boundary.map(p => p[1])), maxY = Math.max(...boundary.map(p => p[1]));
  let row = 0;
  for (let y = minY + spacing * .7; y < maxY; y += spacing * Math.sqrt(3) / 2, row++) {
    for (let x = minX + spacing * (.5 + (row % 2) * .5); x < maxX; x += spacing) {
      const p = [x, y];
      if (!contains(p, boundary) || boundary.some((a, i) => segmentDistance(p, a, boundary[(i + 1) % boundary.length]) < spacing * .43)) continue;
      const at = triangles.findIndex(([a, b, c]) => area(vertices[a], vertices[b], p) >= -1e-8 && area(vertices[b], vertices[c], p) >= -1e-8 && area(vertices[c], vertices[a], p) >= -1e-8);
      if (at < 0) continue;
      const [a, b, c] = triangles[at], n = vertices.length;
      if (Math.min(area(vertices[a], vertices[b], p), area(vertices[b], vertices[c], p), area(vertices[c], vertices[a], p)) < 1e-6) continue;
      vertices.push(p); triangles.splice(at, 1, [a, b, n], [b, c, n], [c, a, n]);
    }
  }
  const boundaryEdges = new Set(boundary.map((_, i) => key(i, (i + 1) % boundary.length)));
  for (let pass = 0; pass < 50; pass++) {
    const edges = new Map();
    for (let t = 0; t < triangles.length; t++) for (let j = 0; j < 3; j++) {
      const a = triangles[t][j], b = triangles[t][(j + 1) % 3], c = triangles[t][(j + 2) % 3], k = key(a, b);
      if (!edges.has(k)) edges.set(k, []);
      edges.get(k).push({ a, b, c, t });
    }
    let flips = 0;
    const used = new Set();
    for (const [k, pair] of edges) {
      if (pair.length !== 2 || boundaryEdges.has(k)) continue;
      const [e, f] = pair;
      if (used.has(e.t) || used.has(f.t)) continue;
      const a = vertices[e.a], b = vertices[e.b], c = vertices[e.c], d = vertices[f.c];
      if (area(c, d, b) <= 1e-8 || area(d, c, a) <= 1e-8) continue;
      const ax = a[0] - d[0], ay = a[1] - d[1], bx = b[0] - d[0], by = b[1] - d[1], cx = c[0] - d[0], cy = c[1] - d[1];
      const circle = (ax * ax + ay * ay) * (bx * cy - by * cx) - (bx * bx + by * by) * (ax * cy - ay * cx) + (cx * cx + cy * cy) * (ax * by - ay * bx);
      if (circle <= 1e-4) continue;
      triangles[e.t] = [e.c, f.c, e.b]; triangles[f.t] = [f.c, e.c, e.a];
      used.add(e.t); used.add(f.t); flips++;
    }
    if (!flips) break;
  }
  return { vertices, triangles: triangles.flat() };
}

function makePiece(id, segments, allowance, title) {
  const boundary = [], seamEdges = [];
  for (const [name, points] of segments) {
    const ids = [];
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      if (boundary.length && len(boundary.at(-1), p) < .01) ids.push(boundary.length - 1);
      else if (i === points.length - 1 && boundary.length && len(boundary[0], p) < .01) ids.push(0);
      else { ids.push(boundary.length); boundary.push(p.slice()); }
    }
    seamEdges.push({ id: name, vertices: ids });
  }
  return { id, title, cutting: 'CUT 1', boundary, cutBoundary: offsetPolygon(boundary, allowance), seamEdges, ...triangulate(boundary) };
}

function prepareContact(initial, triangles, seams, body) {
  const count = initial.length / 3, parent = Array.from({ length: count }, (_, i) => i), find = i => parent[i] === i ? i : parent[i] = find(parent[i]);
  for (const seam of seams) for (const [a, b] of seam.pairs) parent[find(b)] = find(a);
  const map = parent.map((_, i) => find(i)), roots = [...new Set(map)], p = Array.from({ length: count }, (_, i) => initial.slice(i * 3, i * 3 + 3));
  const surface = Array.from({ length: triangles.length / 3 }, (_, i) => triangles.slice(i * 3, i * 3 + 3).map(v => map[v])), neighbors = p.map(() => new Set()), normals = p.map(() => [0, 0, 0]);
  const add = (a, b, weight) => { for (let axis = 0; axis < 3; axis++) a[axis] += b[axis] * weight; };
  const unit = a => { const norm = Math.hypot(...a) || 1; return a.map(v => v / norm); };
  for (const [a, b, c] of surface) {
    const ab = p[b].map((v, i) => v - p[a][i]), ac = p[c].map((v, i) => v - p[a][i]), normal = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]];
    for (const i of [a, b, c]) { add(normals[i], normal, 1); for (const j of [a, b, c]) if (i !== j) neighbors[i].add(j); }
  }
  for (const i of roots) normals[i] = unit(normals[i]);
  const collider = createBodyCollider(body), hints = [], result = { point: [0, 0, 0], normal: [0, 0, 0], signedDistance: 0, triangle: -1 };
  let rounds = 0, remainingSamples = 0, minimumDistance = Infinity;
  for (let round = 0; round < 90; round++) {
    let move = p.map(() => [0, 0, 0]), weight = new Float64Array(count), sample = 0, violations = 0, minimum = Infinity;
    function push(ids) {
      const point = [0, 0, 0], clothNormal = [0, 0, 0];
      for (const i of ids) { add(point, p[i], 1 / ids.length); add(clothNormal, normals[i], 1 / ids.length); }
      const contact = collider.closestPointInto(...point, hints[sample] ?? -1, result); hints[sample++] = contact.triangle;
      minimum = Math.min(minimum, contact.signedDistance);
      if (contact.signedDistance >= .01) return;
      violations++;
      const n = unit(clothNormal), alignment = Math.max(0, n.reduce((sum, v, axis) => sum + v * contact.normal[axis], 0)), direction = unit(n.map((v, axis) => v + contact.normal[axis] * alignment));
      for (const i of ids) { add(move[i], direction, Math.min(.002, .01 - contact.signedDistance)); weight[i]++; }
    }
    for (const i of roots) push([i]);
    for (const [a, b, c] of surface) {
      push([a, b, c]);
      if (round % 3 === 0) { push([a, b]); push([b, c]); push([c, a]); }
    }
    for (const i of roots) if (weight[i]) move[i] = move[i].map(v => v / weight[i]);
    for (let pass = 0; pass < 2; pass++) {
      const next = p.map(() => [0, 0, 0]);
      for (const i of roots) { add(next[i], move[i], .45); for (const j of neighbors[i]) add(next[i], move[j], .55 / neighbors[i].size); }
      move = next;
    }
    for (const i of roots) add(p[i], move[i], 1);
    rounds = round + 1; remainingSamples = violations; minimumDistance = minimum;
    if (!violations && round % 3 === 0) break;
  }
  for (let i = 0; i < count; i++) for (let axis = 0; axis < 3; axis++) initial[i * 3 + axis] = p[map[i]][axis];
  return { method: 'Smoothed outward displacement along original cloth normals and compatible real-mesh normals. Seam groups move together only during placement.', rounds, clearanceTargetMm: 10, stepLimitMm: 2, remainingSamples, lastMinimumSampleDistanceMm: minimumDistance * 1000 };
}

export function draft(raw = defaultInput(), body = null) {
  const input = validateInput({ ...defaultInput(), ...raw });
  const measured = body?.measurements;
  const measurements = {
    chest: input.chestMm, neck: measured ? measured.neck.circumference * 1000 : 314.5456,
    waist: measured ? measured.waist.circumference * 1000 : 670.4762, hips: measured ? measured.hip.circumference * 1000 : 968.6076,
    shoulderToShoulder: measured ? measured.shoulderWidth * 1000 : 375.988,
    hpsToWaistBack: 340, waistToArmpit: 184, waistToHips: 204, shoulderSlope: 16, biceps: 245,
    hpsToBust: 215, waistToFloor: 1080.5563, waistToSeat: 220, seat: 970,
    shoulderToElbow: 295, shoulderToWrist: 520, wrist: 155, highBust: input.chestMm * .96,
  };
  const options = { draftForHighBust: false, chestEase: input.easePct / 100, armholeDepth: .18, lengthBonus: input.lengthMm / (measurements.hpsToWaistBack + measurements.waistToHips) - 1, sleeveLength: .3 };
  const build = () => { const p = new Teagan({ measurements, sa: input.allowanceMm, complete: false, options }).draft(); p.render(); return p; };
  let pattern = build(), sleeve = pattern.parts[0]['teagan.sleeve'];
  options.sleeveLength = Math.max(.2, Math.min(1, (input.sleeveMm + sleeve.points.top.y) / sleeve.points.bicepsRight.x));
  pattern = build();
  const front = pattern.parts[0]['teagan.front'], back = pattern.parts[0]['teagan.back']; sleeve = pattern.parts[0]['teagan.sleeve'];
  const pieces = [];
  const counts = { hem: 22, side: Math.ceil((input.lengthMm - front.points.armhole.y) / 25), arm: 12, shoulder: 5, neck: 7 };
  for (const [id, part] of [['front', front], ['back', back]]) {
    const p = part.points, ops = part.paths.saBase.ops;
    const arm = resample(polyline({ ops: [ops[0], ops[1], ops[2]] }), counts.arm);
    const shoulder = resample([xy(p.shoulder), xy(p.neck)], counts.shoulder);
    const neck = resample(polyline({ ops: [{ type: 'move', to: p.neck }, ops[4]] }), counts.neck);
    const side = resample(polyline(part.paths.sideSeam), counts.side), mirror = points => points.map(([x, y]) => [-x, y]);
    pieces.push(makePiece(id, [
      ['rightSide', side], ['rightArmhole', arm], ['rightShoulder', shoulder], ['neck', [...neck, ...mirror(neck).reverse().slice(1)]],
      ['leftShoulder', mirror(shoulder).reverse()], ['leftArmhole', mirror(arm).reverse()], ['leftSide', mirror(side).reverse()], ['hem', resample([[-p.hem.x, p.hem.y], xy(p.hem)], counts.hem)],
    ], input.allowanceMm, id.toUpperCase()));
  }
  const sp = sleeve.points, cap = polyline(sleeve.paths.sleevecap), frontNotch = nearestFraction(cap, xy(sp.frontNotch)), backNotch = nearestFraction(cap, xy(sp.backNotch));
  const frontLength = front.paths.saBase.split(front.points.shoulder)[0].length(), backLength = back.paths.saBase.split(back.points.shoulder)[0].length();
  const shoulderFraction = frontNotch + (backNotch - frontNotch) * (frontLength / 2) / ((frontLength + backLength) / 2);
  const capFront = [...resample(slicePolyline(cap, 0, frontNotch), counts.arm / 2), ...resample(slicePolyline(cap, frontNotch, shoulderFraction), counts.arm / 2).slice(1)];
  const capBack = [...resample(slicePolyline(cap, shoulderFraction, backNotch), counts.arm / 2), ...resample(slicePolyline(cap, backNotch, 1), counts.arm / 2).slice(1)];
  const sleeveSide = Math.max(2, Math.ceil(len(xy(sp.hemRight), xy(sp.bicepsRight)) / 24));
  for (const id of ['rightSleeve', 'leftSleeve']) pieces.push(makePiece(id, [
    ['frontUnderarm', resample([xy(sp.hemRight), xy(sp.bicepsRight)], sleeveSide)], ['frontCap', capFront], ['backCap', capBack],
    ['backUnderarm', resample([xy(sp.bicepsLeft), xy(sp.hemLeft)], sleeveSide)], ['hem', resample([xy(sp.hemLeft), xy(sp.hemRight)], 16)],
  ], input.allowanceMm, id === 'rightSleeve' ? 'RIGHT SLEEVE' : 'LEFT SLEEVE'));
  const restUV = [], triangles = [], initial = [], edges = [], seams = [];
  let offset = 0, printX = 20;
  const centerZ = body?.landmarks?.shoulderRight?.[2] ?? .010152, topY = (measured?.shoulderHeight ?? 1.381622) + front.points.shoulder.y / 1000 + .012;
  const width = front.points.armhole.x, radius = 2 * width / Math.PI / 1000, armholeY = front.points.armhole.y;
  const sideProfile = polyline(front.paths.sideSeam).reverse();
  function torsoWidth(y) {
    if (y <= sideProfile[0][1]) return sideProfile[0][0];
    for (let i = 1; i < sideProfile.length; i++) if (y <= sideProfile[i][1]) {
      const a = sideProfile[i - 1], b = sideProfile[i], f = (y - a[1]) / (b[1] - a[1]);
      return a[0] + (b[0] - a[0]) * f;
    }
    return sideProfile.at(-1)[0];
  }
  for (const piece of pieces) {
    piece.offset = offset;
    const minX = Math.min(...piece.cutBoundary.map(p => p[0])), maxX = Math.max(...piece.cutBoundary.map(p => p[0])), minY = Math.min(...piece.cutBoundary.map(p => p[1])), maxY = Math.max(...piece.cutBoundary.map(p => p[1]));
    piece.x = printX - minX; piece.y = 35 - minY; piece.width = maxX - minX; piece.height = maxY - minY; printX += piece.width + 25;
    piece.initial = piece.vertices.map(([x, y]) => {
      if (piece.id === 'front' || piece.id === 'back') {
        const rowWidth = torsoWidth(y), rowRadius = 2 * rowWidth / Math.PI / 1000, theta = x / rowWidth * Math.PI / 2, cylinderX = rowRadius * Math.sin(theta), lineY = front.points.neck.y + (Math.abs(x) - front.points.neck.x) * (front.points.shoulder.y - front.points.neck.y) / (front.points.shoulder.x - front.points.neck.x);
        const t = Math.max(0, Math.min(1, (y - lineY) / Math.max(40, armholeY - lineY))), f = Math.sin(t * Math.PI / 2);
        return [x / 1000 * (1 - t) + cylinderX * t, topY - y / 1000, centerZ + (piece.id === 'front' ? 1 : -1) * rowRadius * Math.cos(theta) * f];
      }
      const hand = piece.id === 'rightSleeve' ? 1 : -1, f = Math.max(0, Math.min(1, y / sp.hemRight.y));
      const halfWidth = sp.bicepsRight.x + (sp.hemRight.x - sp.bicepsRight.x) * f, r = halfWidth / Math.PI / 1000, theta = x / halfWidth * Math.PI;
      const shoulder = [hand * measurements.shoulderToShoulder / 2000, measured?.shoulderHeight ?? 1.381622, centerZ];
      const centers = [shoulder, ...(body?.landmarks?.armCenters?.[hand > 0 ? 'right' : 'left'] ?? [[hand * .2282, 1.26, .0118], [hand * .28, 1.2, .017], [hand * .32, 1.16, .036]])];
      let distance = Math.max(0, (y - sp.top.y) / 1000 - r), center = centers.at(-1), axis = [hand * .66, -.751, 0];
      for (let j = 1; j < centers.length; j++) {
        const a = centers[j - 1], b = centers[j], length = Math.hypot(...a.map((v, k) => b[k] - v));
        if (distance <= length || j === centers.length - 1) {
          const f = distance / length; center = a.map((v, k) => v + (b[k] - v) * f); axis = a.map((v, k) => (b[k] - v) / length); break;
        }
        distance -= length;
      }
      let forward = [-axis[2] * axis[0], -axis[2] * axis[1], 1 - axis[2] ** 2];
      const fl = Math.hypot(...forward); forward = forward.map(v => v / fl);
      const side = [hand * (forward[1] * axis[2] - forward[2] * axis[1]), hand * (forward[2] * axis[0] - forward[0] * axis[2]), hand * (forward[0] * axis[1] - forward[1] * axis[0])];
      return center.map((v, k) => v + side[k] * r * Math.cos(theta) + forward[k] * r * Math.sin(theta));
    });
    restUV.push(...piece.vertices.map(p => p.slice())); initial.push(...piece.initial.flat());
    const flip = piece.id === 'front' || piece.id === 'leftSleeve';
    for (let i = 0; i < piece.triangles.length; i += 3) {
      const t = piece.triangles.slice(i, i + 3).map(v => v + offset); triangles.push(...(flip ? [t[0], t[2], t[1]] : t));
    }
    const unique = new Set();
    for (let i = 0; i < piece.triangles.length; i += 3) for (let j = 0; j < 3; j++) {
      const a = piece.triangles[i + j], b = piece.triangles[i + (j + 1) % 3], k = key(a, b);
      if (!unique.has(k)) { unique.add(k); edges.push({ a: a + offset, b: b + offset, restMm: len(piece.vertices[a], piece.vertices[b]), piece: piece.id }); }
    }
    offset += piece.vertices.length;
  }
  function sew(id, aId, aEdge, bId, bEdge, reverse = false) {
    const a = pieces.find(p => p.id === aId), b = pieces.find(p => p.id === bId), aa = a.seamEdges.find(e => e.id === aEdge).vertices, bb0 = b.seamEdges.find(e => e.id === bEdge).vertices, bb = reverse ? bb0.slice().reverse() : bb0;
    if (aa.length !== bb.length) throw new Error(`Unmatched seam samples ${id}.`);
    const length = (piece, ids) => ids.slice(1).reduce((v, b, i) => v + len(piece.vertices[ids[i]], piece.vertices[b]), 0);
    seams.push({ id, a: { piece: aId, edge: aEdge }, b: { piece: bId, edge: bEdge }, directionA:1, directionB:reverse?-1:1, pairs: aa.map((v, i) => [a.offset + v, b.offset + bb[i]]), lengthAmm: length(a, aa), lengthBmm: length(b, bb) });
  }
  for (const hand of ['right', 'left']) {
    sew(`${hand}-side`, 'front', `${hand}Side`, 'back', `${hand}Side`);
    sew(`${hand}-shoulder`, 'front', `${hand}Shoulder`, 'back', `${hand}Shoulder`);
    sew(`${hand}-front-sleeve`, 'front', `${hand}Armhole`, `${hand}Sleeve`, 'frontCap', hand === 'left');
    sew(`${hand}-back-sleeve`, 'back', `${hand}Armhole`, `${hand}Sleeve`, 'backCap', hand === 'right');
    sew(`${hand}-underarm`, `${hand}Sleeve`, 'frontUnderarm', `${hand}Sleeve`, 'backUnderarm', true);
  }
  for (const piece of pieces.filter(p => p.id.endsWith('Sleeve'))) {
    const parameters = piece.vertices.map(([x, y]) => [.5, .5]), fixed = new Set(), capTargets = new Map();
    for (const seam of seams.filter(s => s.b.piece === piece.id && s.id.includes('sleeve'))) for (const [a, b] of seam.pairs) {
      const local = b - piece.offset;
      capTargets.set(local, initial.slice(a * 3, a * 3 + 3));
    }
    const edge = name => piece.seamEdges.find(e => e.id === name).vertices;
    const cap = [...edge('frontCap'), ...edge('backCap').slice(1)], cuff = edge('hem').slice().reverse();
    for (let j = 0; j < cap.length; j++) { parameters[cap[j]] = [j / (cap.length - 1), 0]; fixed.add(cap[j]); }
    for (let j = 0; j < cuff.length; j++) { parameters[cuff[j]] = [j / (cuff.length - 1), 1]; fixed.add(cuff[j]); }
    for (const [name, u, reverse] of [['frontUnderarm', 0, true], ['backUnderarm', 1, false]]) {
      const ids = reverse ? edge(name).slice().reverse() : edge(name);
      for (let j = 0; j < ids.length; j++) { parameters[ids[j]] = [u, j / (ids.length - 1)]; fixed.add(ids[j]); }
    }
    const neighbors = piece.vertices.map(() => new Set());
    for (let i = 0; i < piece.triangles.length; i += 3) for (let j = 0; j < 3; j++) {
      const a = piece.triangles[i + j], b = piece.triangles[i + (j + 1) % 3]; neighbors[a].add(b); neighbors[b].add(a);
    }
    for (let iteration = 0; iteration < 400; iteration++) for (let i = 0; i < parameters.length; i++) if (!fixed.has(i)) {
      for (let axis = 0; axis < 2; axis++) parameters[i][axis] = [...neighbors[i]].reduce((v, n) => v + parameters[n][axis], 0) / neighbors[i].size;
    }
    const capPoints = cap.map(i => capTargets.get(i)), cuffPoints = cuff.map(i => piece.initial[i]);
    function interpolate(points, fraction) {
      const f = Math.max(0, Math.min(1, fraction)) * (points.length - 1), i = Math.min(points.length - 2, Math.floor(f));
      return points[i].map((v, axis) => v + (points[i + 1][axis] - v) * (f - i));
    }
    for (let i = 0; i < piece.vertices.length; i++) {
      const [u, v] = parameters[i], a = interpolate(capPoints, u), b = interpolate(cuffPoints, u);
      piece.initial[i] = a.map((value, axis) => value * (1 - v) + b[axis] * v);
      for (let axis = 0; axis < 3; axis++) initial[(piece.offset + i) * 3 + axis] = piece.initial[i][axis];
    }
  }
  const pins = [];
  for (const hand of ['rightShoulder', 'leftShoulder']) {
    const ids = pieces[0].seamEdges.find(e => e.id === hand).vertices;
    pins.push(pieces[0].offset + (hand === 'rightShoulder' ? ids[0] : ids.at(-1)));
  }
  const preparation = body ? prepareContact(initial, triangles, seams, body) : null;
  if (body) for (const piece of pieces) piece.initial = piece.vertices.map((_, i) => initial.slice((piece.offset + i) * 3, (piece.offset + i) * 3 + 3));
  return {
    format: 'cloth-studio-document', version: 1, units: 'mm', simulationUnits: 'm', input,
    design: { name: 'FreeSewing Teagan', version: '4.10.2', source: 'https://freesewing.eu/docs/designs/teagan/', adaptation: 'Expanded front and back. Two mirrored sleeves. Chest, waist, hip, neck and shoulder width use the reference mesh measurements. Remaining drafting measurements are explicit estimates.' },
    measurementSources: { measured: ['neck', 'waist', 'hips', 'shoulderToShoulder'], parameter: ['chest'], estimated: ['hpsToWaistBack', 'waistToArmpit', 'waistToHips', 'shoulderSlope', 'biceps', 'hpsToBust', 'waistToFloor', 'waistToSeat', 'seat', 'shoulderToElbow', 'shoulderToWrist', 'wrist', 'highBust'] },
    measurements, garmentChestMm: input.chestMm * (1 + input.easePct / 100), pieces, seams,
    mesh: { restUV, initial, triangles, edges, pins, pinTargets: pins.map(i => initial.slice(i * 3, i * 3 + 3)) },
    width: Math.ceil(printX + 20), height: Math.ceil(Math.max(...pieces.map(p => p.height)) + 190),
    calibration: { x: 20, y: Math.ceil(Math.max(...pieces.map(p => p.height)) + 65), size: 100 },
    assembly: { mode: 'presewn-equality-seams', dynamicClosure: false, contactPrepared: Boolean(body), preparation, description: 'Independent panel UVs retain their own rest lengths. Seam equality constraints close the initial assembled garment. Contact preparation changes only the starting placement.' },
    bodySource: body?.provenance || null,
  };
}
