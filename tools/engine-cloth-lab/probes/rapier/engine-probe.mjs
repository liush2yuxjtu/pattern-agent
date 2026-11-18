import fs from 'node:fs';
import crypto from 'node:crypto';
import {create} from './engine.mjs';
import {auditSurfaceCollisions} from '../../reference/benchmarks/collision/surface-audit.mjs';
import {MeshBodyCollider} from '../../reference/src/mesh-collider.js';

function patch(n, sideMM, offsetMM = 0) {
  const restXY = [], triangles = [];
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) restXY.push(offsetMM + sideMM * i / (n - 1), sideMM * j / (n - 1));
  for (let i = 0; i < n - 1; i++) for (let j = 0; j < n - 1; j++) {
    const a = i * n + j, b = a + n, c = a + 1, d = b + 1;
    triangles.push(a, c, b, b, c, d);
  }
  return {restXY, triangles};
}
const cases = [];
const left = patch(3, 400), right = patch(3, 400, 600);
const restXY = [...left.restXY, ...right.restXY];
const seamInput = {restXY, triangles: [...left.triangles, ...right.triangles.map(i => i + 9)], initialXYZ: Array.from({length: 18}, (_, i) => [restXY[i * 2] * 0.001 - 0.5, 1, restXY[i * 2 + 1] * 0.001]).flat(), seamPairs: [[6, 9], [7, 10], [8, 11]], pinnedIDs: [0, 1, 2]};
const nestedSeamInput = {...seamInput, restXY: Array.from({length: 18}, (_, i) => seamInput.restXY.slice(i * 2, i * 2 + 2)), triangles: Array.from({length: seamInput.triangles.length / 3}, (_, i) => seamInput.triangles.slice(i * 3, i * 3 + 3)), initialXYZ: Array.from({length: 18}, (_, i) => seamInput.initialXYZ.slice(i * 3, i * 3 + 3)), seamPairs: [], seams: [{id: 'test-seam', pairs: seamInput.seamPairs}]};
const seam = await create(nestedSeamInput), seamInitial = Array.from(seam.getPositions()), seamBefore = seam.nativeStats();
seam.step(240);
const seamAfter = seam.nativeStats(), seamFinal = Array.from(seam.getPositions());
const pinDrift = Math.max(...seamInput.pinnedIDs.map(i => Math.hypot(...[0, 1, 2].map(k => seamFinal[i * 3 + k] - seamInitial[i * 3 + k]))));
const sourceRestError = Math.max(...seamBefore.edgeRestLengthsM.map((rest, i) => {
  const a = seamBefore.edgePairs[i * 2], b = seamBefore.edgePairs[i * 2 + 1];
  return Math.abs(rest - Math.hypot(restXY[a * 2] - restXY[b * 2], restXY[a * 2 + 1] - restXY[b * 2 + 1]) * 0.001);
}));
cases.push({name: 'engine-two-panel-seam-gravity-pin', status: seamAfter.maxSeamGapM < 0.02 && pinDrift < 1e-6 && sourceRestError < 1e-6 && seamAfter.structuralRestLengthsUnchanged ? 'PASS' : 'FAIL', input: nestedSeamInput, steps: 240, before: seamBefore, after: seamAfter, sourceRestErrorM: sourceRestError, pinDriftM: pinDrift, initialPositions: seamInitial, finalPositions: seamFinal});
seam.dispose(); seam.dispose();
let disposedRejected = false;
try {seam.getPositions();} catch {disposedRejected = true;}
cases.push({name: 'engine-dispose', status: disposedRejected ? 'PASS' : 'FAIL', doubleDisposeAccepted: true, disposedRejected});

const human = JSON.parse(fs.readFileSync(new URL('../../reference/assets/makehuman.json', import.meta.url)));
const humanMesh = {positions: human.positions, triangles: human.triangles};
const p = patch(7, 240);
const initialXYZ = Array.from({length: 49}, (_, i) => [p.restXY[i * 2] * 0.001 - 0.12, p.restXY[i * 2 + 1] * 0.001 + 1.1, 0.26]).flat();
for (const particleRadius of [0.003, 0.005]) {
const humanInput = {...p, initialXYZ, gravity: [0, 0, -1], body: humanMesh, particleRadius};
const chest = await create(humanInput), bodyCollider = new MeshBodyCollider(humanMesh), samples = [];
for (let i = 1; i <= 240; i++) {
  chest.step();
  if (i % 30 === 0) {
    const audit = auditSurfaceCollisions({cloth: {positions: chest.getPositions(), triangles: p.triangles}, body: humanMesh, bodyCollider});
    samples.push({step: i, vertexInside: audit.vertexInside, bodySurface: audit.bodySurface, selfSurface: audit.selfSurface, summary: audit.summary});
  }
}
const humanFinal = Array.from(chest.getPositions()), meanZ = humanFinal.filter((_, i) => i % 3 === 2).reduce((a, b) => a + b, 0) / 49;
const finalAudit = auditSurfaceCollisions({cloth: {positions: humanFinal, triangles: p.triangles}, body: humanMesh, bodyCollider});
cases.push({name: `engine-makehuman-chest-contact-radius-${particleRadius}`, status: meanZ > 0.05 && meanZ < 0.23 && samples.every(s => s.bodySurface.strictCrossingPairs === 0 && s.vertexInside.count === 0) ? 'PASS' : 'FAIL', input: {...humanInput, body: {source: 'reference/assets/makehuman.json', positionsCount: human.positions.length, trianglesCount: human.triangles.length}}, steps: 240, nativeStats: chest.nativeStats(), meanZ, initialPositions: initialXYZ, finalPositions: humanFinal, samples, finalAudit});
chest.dispose();
}
for (const [name, input] of [['invalid-rest', {...seamInput, restXY: [0, NaN]}], ['invalid-assembly', {...seamInput, initialXYZ: []}], ['invalid-seam', {...seamInput, seamPairs: [[0, 1000]]}]]) {
  try {const engine = await create(input); engine.dispose(); cases.push({name, status: 'FAIL'});} catch (error) {cases.push({name, status: 'PASS', error: error.message});}
}
const paths = ['probes/rapier/engine.mjs', 'probes/rapier/native-seam.mjs', 'reference/assets/makehuman.json', 'node_modules/@dimforge/rapier3d-compat/dist/rapier_wasm3d_bg.wasm'];
const report = {schema: 'rapier-engine-adapter-probe-1', sourceHashes: Object.fromEntries(paths.map(path => [path, crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex')])), cases, scope: 'Native Rapier 0.21.0 cloth simulation, native single-particle cluster spherical stitches, unchanged 2D structural rest, exact reference MakeHuman mesh contact.', limitations: ['Small meshes and 30-step discrete audit samples do not certify a complete garment.', 'The chest probe accelerates cloth along the surface normal to isolate body contact. It does not test wearing under vertical gravity.', 'No material calibration, arbitrary self-entanglement guarantee, swept collision proof, or CLO certification.', 'Seam joints couple particle locations. They do not add seam-line bending or a fabric sewing material model.', 'No runtime topology edits are implemented. Recreate the engine after topology changes.']};
fs.writeFileSync(new URL('engine-report.json', import.meta.url), JSON.stringify(report, null, 2));
console.log(JSON.stringify(cases.map(c => ({name: c.name, status: c.status, maxSeamGapM: c.after?.maxSeamGapM, pinDriftM: c.pinDriftM, sourceRestErrorM: c.sourceRestErrorM, meanZ: c.meanZ})), null, 2));
