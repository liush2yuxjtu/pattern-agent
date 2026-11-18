import fs from 'node:fs';
import crypto from 'node:crypto';
import {create, RAPIER as R} from './adapter.mjs';
import {auditSurfaceCollisions} from '../../reference/benchmarks/collision/surface-audit.mjs';
import {MeshBodyCollider} from '../../reference/src/mesh-collider.js';
import {stitch} from './native-seam.mjs';

const dir = new URL('.', import.meta.url);
const hash = path => crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex');
const v = (x, y, z) => ({x, y, z});
const meanY = p => p.filter((_, i) => i % 3 === 1).reduce((a, b) => a + b, 0) / (p.length / 3);
const distance = (p, a, b) => Math.hypot(...[0, 1, 2].map(k => p[a * 3 + k] - p[b * 3 + k]));
function grid(n = 7, size = 1.2, y = 1) {
  const positions = [], triangles = [], edges = [], dihedrals = [], adjacent = new Map();
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) positions.push(-size / 2 + size * i / (n - 1), y, -size / 2 + size * j / (n - 1));
  for (let i = 0; i < n - 1; i++) for (let j = 0; j < n - 1; j++) {
    const a = i * n + j, b = a + n, c = a + 1, d = b + 1;
    triangles.push(a, c, b, b, c, d);
  }
  for (let i = 0; i < triangles.length; i += 3) for (let j = 0; j < 3; j++) {
    const a = triangles[i + j], b = triangles[i + (j + 1) % 3], c = triangles[i + (j + 2) % 3];
    const key = [a, b].sort((x, y) => x - y).join(':');
    if (adjacent.has(key)) dihedrals.push(a, b, adjacent.get(key), c);
    else {adjacent.set(key, c); edges.push(a, b);}
  }
  return {positions, triangles, edges, dihedrals};
}
function sphere(radius = 0.45, n = 12, m = 24) {
  const positions = [0, radius, 0], triangles = [];
  for (let i = 1; i < n; i++) for (let j = 0; j < m; j++) {
    const a = Math.PI * i / n, b = 2 * Math.PI * j / m;
    positions.push(radius * Math.sin(a) * Math.cos(b), radius * Math.cos(a), radius * Math.sin(a) * Math.sin(b));
  }
  const bottom = positions.length / 3;
  positions.push(0, -radius, 0);
  const id = (i, j) => 1 + (i - 1) * m + (j % m);
  for (let j = 0; j < m; j++) {
    triangles.push(0, id(1, j + 1), id(1, j));
    for (let i = 1; i < n - 1; i++) triangles.push(id(i, j), id(i, j + 1), id(i + 1, j), id(i + 1, j), id(i, j + 1), id(i + 1, j + 1));
    triangles.push(id(n - 1, j), id(n - 1, j + 1), bottom);
  }
  return {positions, triangles};
}
const cases = [];
const add = (name, status, data) => {cases.push({name, status, ...data}); console.log(name, status);};
async function run(name, config, steps, check, bodyMesh = sphere()) {
  const a = await create(config), initial = Array.from(a.getPositions());
  const topology = {particles: a.body.numParticles(), edges: a.body.numEdges(), dihedrals: a.body.numDihedrals(), meshes: a.body.numMeshes(), collisionEnabled: a.body.numMeshes() ? a.body.meshCollisionEnabled(0) : false};
  let maxCrossings = 0;
  const bodyCollider = config.colliders?.length ? new MeshBodyCollider(bodyMesh) : null;
  const samples = [];
  for (let i = 1; i <= steps; i++) {
    a.step();
    if (config.colliders?.length && (i % 30 === 0 || i === steps)) {
      const audit = auditSurfaceCollisions({cloth: {positions: a.getPositions(), triangles: config.triangles}, body: bodyMesh, bodyCollider, maxExamples: 2});
      maxCrossings = Math.max(maxCrossings, audit.bodySurface.strictCrossingPairs);
      samples.push({step: i, bodySurface: audit.bodySurface, selfSurface: audit.selfSurface, vertexInside: audit.vertexInside});
    }
  }
  const final = Array.from(a.getPositions()), result = check({initial, final, a});
  let audit = auditSurfaceCollisions({cloth: {positions: final, triangles: config.triangles}, body: bodyMesh, bodyCollider, maxExamples: 8});
  if (!config.colliders?.length) audit = {selfSurface: audit.selfSurface, continuousCollision: audit.continuousCollision, bodySurface: {status: 'UNKNOWN', reason: 'No rigid collider in this case.'}, vertexInside: {status: 'UNKNOWN', reason: 'No rigid collider in this case.'}};
  add(name, result.status, {parameters: config, dt: a.world.timestep, steps, topology, initialPositions: initial, finalPositions: final, ...result, audit, sampledCollisionAudit: {sampleEverySteps: 30, maxBodyCrossingPairs: maxCrossings, samples}});
  a.dispose();
}

await R.init();
const cloth = grid();
await run('free-cloth-gravity', {...cloth}, 120, ({initial, final}) => ({status: final.every(Number.isFinite) && meanY(final) < meanY(initial) - 1 ? 'PASS' : 'FAIL', meanYInitial: meanY(initial), meanYFinal: meanY(final)}));
await run('pinned-cloth-gravity', {...cloth, pins: [0, 42]}, 240, ({initial, final}) => {
  const pinDrift = Math.max(...[0, 42].map(i => Math.hypot(...[0, 1, 2].map(k => final[i * 3 + k] - initial[i * 3 + k]))));
  return {status: final.every(Number.isFinite) && pinDrift < 1e-6 && meanY(final) < meanY(initial) - 0.05 ? 'PASS' : 'FAIL', pinDriftM: pinDrift, meanYFinal: meanY(final)};
});
const fixedSphere = sphere();
await run('fixed-trimesh-sphere-drape', {...cloth, colliders: [fixedSphere]}, 360, ({final}) => ({status: final.every(Number.isFinite) && meanY(final) > -0.3 ? 'PASS' : 'FAIL', meanYFinal: meanY(final), interpretation: 'PASS here means cloth was supported by the native collision solver. Inspect the independent surface audit separately.'}), fixedSphere);
const human = JSON.parse(fs.readFileSync(new URL('../../reference/assets/makehuman.json', import.meta.url)));
const torso = grid(7, 0.5, human.bounds?.max?.[1] || 2.1);
const humanBounds = [0, 1, 2].map(k => [Math.min(...human.positions.filter((_, i) => i % 3 === k)), Math.max(...human.positions.filter((_, i) => i % 3 === k))]);
torso.positions = torso.positions.map((x, i) => i % 3 === 1 ? humanBounds[1][1] + 0.2 : x);
await run('makehuman-same-mesh-contact', {...torso, colliders: [{positions: human.positions, triangles: human.triangles}]}, 240, ({final}) => ({status: final.every(Number.isFinite) && meanY(final) > humanBounds[1][1] - 0.5 ? 'PASS' : 'FAIL', meanYFinal: meanY(final), humanBounds, interpretation: 'The exact reference mesh is the collider. Vertex-inside and discrete face crossing statuses remain separate.'}), human);
const chest = grid(7, 0.24, 0);
for (let i = 0; i < chest.positions.length; i += 3) {
  chest.positions[i + 1] = chest.positions[i + 2] + 1.22;
  chest.positions[i + 2] = 0.26;
}
await run('makehuman-chest-normal-contact', {...chest, gravity: [0, 0, -1], colliders: [{positions: human.positions, triangles: human.triangles}]}, 240, ({final}) => {
  const meanZ = final.filter((_, i) => i % 3 === 2).reduce((a, b) => a + b, 0) / (final.length / 3);
  return {status: final.every(Number.isFinite) && meanZ > 0.05 && meanZ < 0.23 ? 'PASS' : 'FAIL', meanZ, interpretation: 'A free patch is accelerated toward the chest along -Z. Native body collision must stop it near the actual reference surface.'};
}, human);

for (const selfContacts of [false, true]) {
  const lower = grid(4, 1, 0), upper = grid(4, 1, 0.35), count = lower.positions.length / 3;
  const config = {positions: [...lower.positions, ...upper.positions], triangles: [...lower.triangles, ...upper.triangles.map(i => i + count)], edges: [...lower.edges, ...upper.edges.map(i => i + count)], dihedrals: [...lower.dihedrals, ...upper.dihedrals.map(i => i + count)], pins: Array.from({length: count}, (_, i) => i), selfContacts};
  await run(`self-contact-${selfContacts ? 'on' : 'off'}`, config, 180, ({final}) => {
    const minUpperY = Math.min(...final.slice(count * 3).filter((_, i) => i % 3 === 1));
    return {status: (selfContacts ? minUpperY >= -0.02 : minUpperY < -0.3) ? 'PASS' : 'FAIL', minUpperY, interpretation: selfContacts ? 'Native self contact must hold a falling disconnected cloth patch above the pinned patch in one soft body.' : 'Negative control must fall through the pinned patch.'};
  });
}

for (const seamEnabled of [false, true]) {
  const world = new R.World(v(0, -9.81, 0)); world.timestep = 1 / 120;
  const desc = R.SoftBodyDesc.cloth(v(-0.5, 1, 0), v(0.2, 0, 0), v(0, 0, 0.2), 3, 3).setPinnedParticles([0, 1, 2]).setCanSleep(false).setAdditionalSolverIterations(4);
  const a = world.createSoftBody(desc), b = world.createSoftBody(R.SoftBodyDesc.cloth(v(0.1, 1, 0), v(0.2, 0, 0), v(0, 0, 0.2), 3, 3).setCanSleep(false).setAdditionalSolverIterations(4));
  const joints = [];
  if (seamEnabled) for (let i = 0; i < 3; i++) {
    const ca = world.addSoftBodyCluster(a, [6 + i]), cb = world.addSoftBodyCluster(b, [i]);
    const joint = world.createImpulseJoint(R.JointData.spherical(v(0, 0, 0), v(0, 0, 0)), a.clusterProxy(ca), b.clusterProxy(cb), true);
    joint.setContactsEnabled(false); joints.push(joint.handle);
  }
  const initialA = Array.from(a.particlePositions()), initialB = Array.from(b.particlePositions());
  for (let i = 0; i < 240; i++) world.step();
  const finalA = Array.from(a.particlePositions()), finalB = Array.from(b.particlePositions());
  const seamGap = Math.max(...[0, 1, 2].map(i => Math.hypot(...[0, 1, 2].map(k => finalA[(6 + i) * 3 + k] - finalB[i * 3 + k]))));
  add(`cross-body-cluster-spherical-seam-${seamEnabled ? 'on' : 'off'}`, seamEnabled ? seamGap < 0.02 ? 'PASS' : 'FAIL' : seamGap > 1 ? 'PASS' : 'FAIL', {dt: world.timestep, steps: 240, joints, seamGapM: seamGap, initialPositions: [initialA, initialB], finalPositions: [finalA, finalB], nativeOnly: true});
  world.free();
}

for (const seamEnabled of [false, true]) {
  const a = grid(3, 0.4, 1), b = grid(3, 0.4, 1), n = a.positions.length / 3;
  b.positions = b.positions.map((x, i) => i % 3 === 0 ? x + 0.4 : x);
  const seamPairs = [0, 1, 2].map(i => [6 + i, n + i]);
  const config = {positions: [...a.positions, ...b.positions], triangles: [...a.triangles, ...b.triangles.map(i => i + n)], edges: [...a.edges, ...b.edges.map(i => i + n), ...(seamEnabled ? seamPairs.flat() : [])], dihedrals: [...a.dihedrals, ...b.dihedrals.map(i => i + n)], pins: [0, 1, 2], selfContacts: false};
  await run(`same-body-zero-rest-edge-seam-${seamEnabled ? 'on' : 'off'}`, config, 240, ({final}) => {
    const gap = Math.max(...seamPairs.map(([a, b]) => distance(final, a, b)));
    return {status: seamEnabled ? gap < 0.02 ? 'PASS' : 'FAIL' : gap > 1 ? 'PASS' : 'FAIL', seamGapM: gap, nativeOnly: true};
  });
}

{
  const a = grid(3, 0.4, 1), b = grid(3, 0.4, 1), n = a.positions.length / 3;
  b.positions = b.positions.map((x, i) => i % 3 === 0 ? x + 0.6 : x);
  const config = {positions: [...a.positions, ...b.positions], triangles: [...a.triangles, ...b.triangles.map(i => i + n)], edges: [...a.edges, ...b.edges.map(i => i + n)], dihedrals: [...a.dihedrals, ...b.dihedrals.map(i => i + n)], pins: [0, 1, 2], selfContacts: true};
  const adapter = await create(config), body = adapter.body;
  const seamPairs = [0, 1, 2].map(i => [6 + i, n + i]);
  for (const [a, b] of seamPairs) stitch(adapter.world, body, a, body, b);
  const initial = Array.from(body.particlePositions());
  const beforeRestLengths = Array.from({length: body.numEdges()}, (_, i) => body.edgeRestLength(i));
  adapter.step(240);
  const final = Array.from(body.particlePositions());
  const afterRestLengths = Array.from({length: body.numEdges()}, (_, i) => body.edgeRestLength(i));
  const gap = Math.max(...seamPairs.map(([a, b]) => distance(final, a, b)));
  add('same-body-cluster-spherical-seam-self-contact-on', gap < 0.02 ? 'PASS' : 'FAIL', {parameters: config, initialPositions: initial, finalPositions: final, dt: adapter.world.timestep, steps: 240, seamGapM: gap, structuralRestLengthsBefore: beforeRestLengths, structuralRestLengthsAfter: afterRestLengths, restLengthsUnchanged: beforeRestLengths.every((v, i) => v === afterRestLengths[i])});
  adapter.dispose();
}
{
  const mesh = grid(3, 0.4, 1);
  const assembledPositions = mesh.positions.map((x, i) => i % 3 === 1 ? x + 0.5 + mesh.positions[i + 1] * 0.25 : i % 3 === 2 ? x * 1.1 : x);
  const a = await create({...mesh, assembledPositions, gravity: [0, 0, 0]});
  const nativeEdges = a.body.edges(), restLengths = Array.from({length: a.body.numEdges()}, (_, i) => a.body.edgeRestLength(i));
  const maxError = Math.max(...restLengths.map((length, i) => Math.abs(length - distance(mesh.positions, nativeEdges[i * 2], nativeEdges[i * 2 + 1]))));
  const initial = Array.from(a.getPositions());
  a.step(120);
  const final = Array.from(a.getPositions());
  const unchanged = restLengths.every((length, i) => length === a.body.edgeRestLength(i));
  a.dispose(); a.dispose();
  let rejectsDisposed = false;
  try {a.getPositions();} catch {rejectsDisposed = true;}
  add('two-dimensional-rest-three-dimensional-assembly-lifecycle', maxError < 1e-6 && unchanged && rejectsDisposed ? 'PASS' : 'FAIL', {parameters: {...mesh, assembledPositions}, dt: 1 / 120, steps: 120, maxRestLengthErrorM: maxError, restLengthsUnchanged: unchanged, doubleDisposeAccepted: true, rejectsDisposed, initialPositions: initial, finalPositions: final});
}
for (const [name, changes] of [['bad-nonfinite', {positions: [0, NaN, 0]}], ['bad-index', {triangles: [0, 1, 100000]}], ['bad-pin', {pins: [100000]}]]) {
  try {const a = await create({...cloth, ...changes}); a.dispose(); add(name, 'FAIL', {reason: 'Unexpected acceptance'});} catch (error) {add(name, 'PASS', {error: error.message});}
}
for (const stage of ['rest-original', 'rest-assembled', 'rest-assembled-without-restore']) {
  const world = new R.World(v(0, 0, 0)); world.timestep = 1 / 120;
  const original = new Float32Array([-1, 0, 0, -0.5, 0, 0, 0.5, 0, 0, 1, 0, 0]);
  const assembled = new Float32Array([-1, 0, 0, 0, 0, 0, 0.001, 0, 0, 1, 0, 0]);
  const desc = new R.SoftBodyDesc(original).setEdges([0, 1, 2, 3]).setPinnedParticles([0, 3]).setNoSurfaceCollider().setSoftness(20, 1).setAdditionalSolverIterations(4).setCanSleep(false);
  const raw = desc.intoRaw();
  if (stage !== 'rest-original') raw.setPositions(assembled);
  raw.addEdges(new Uint32Array([1, 2]));
  if (stage === 'rest-assembled') raw.setPositions(original);
  const body = world.createSoftBody({intoRaw: () => raw});
  const edgeRestLengths = Array.from({length: body.numEdges()}, (_, i) => body.edgeRestLength(i));
  const initial = Array.from(body.particlePositions());
  for (let i = 0; i < 240; i++) world.step();
  const final = Array.from(body.particlePositions());
  add(`raw-builder-setPositions-${stage}`, stage !== 'rest-original' ? edgeRestLengths[2] < 0.002 && Math.abs(edgeRestLengths[0] - 0.5) < 1e-6 ? 'PASS' : 'FAIL' : Math.abs(edgeRestLengths[2] - 1) < 1e-6 ? 'PASS' : 'FAIL', {steps: 240, dt: world.timestep, originalPositions: Array.from(original), assembledPositions: Array.from(assembled), initialPositions: initial, finalPositions: final, edgeRestLengths, finalSeamGapM: distance(final, 1, 2), interpretation: 'Pins are deliberately incompatible with a short seam plus original half-meter material edges. Rest-length inspection decides whether setPositions preserved structural rest state.'});
  world.free();
}
const sources = ['node_modules/@dimforge/rapier3d-compat/package.json', 'node_modules/@dimforge/rapier3d-compat/dist/rapier.mjs', 'node_modules/@dimforge/rapier3d-compat/dist/rapier.mjs.map', 'node_modules/@dimforge/rapier3d-compat/dist/rapier_wasm3d_bg.wasm', 'node_modules/@dimforge/rapier3d-compat/dist/dynamics/soft_body.d.ts', 'node_modules/@dimforge/rapier3d-compat/dist/pipeline/world.d.ts', 'reference/assets/makehuman.json', 'reference/benchmarks/collision/surface-audit.mjs', 'reference/src/mesh-collider.js', 'probes/rapier/adapter.mjs', 'probes/rapier/native-seam.mjs', 'probes/rapier/probe.mjs'];
const report = {schema: 'rapier-native-cloth-probe-1', version: R.version(), sourceHashes: Object.fromEntries(sources.map(p => [p, hash(p)])), cases, limitations: ['Small deterministic probes are not CLO certification.', 'A final sample does not prove continuous collision.', 'Zero inside vertices do not prove no face crossings.', 'Self contact of disconnected patches tests one native collision case, not arbitrary garment entanglement.', 'Native edges infer rest length from input positions. Zero-rest seams require coincident assembly positions. Cluster spherical joints can close an initial gap.']};
fs.writeFileSync(new URL('report.json', dir), JSON.stringify(report, null, 2));
console.log(JSON.stringify(cases.map(({name, status, seamGapM, meanYFinal, minUpperY}) => ({name, status, seamGapM, meanYFinal, minUpperY})), null, 2));
