import fs from 'node:fs';
import crypto from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {buildDemo, human} from '../../src/pipeline.mjs';
import {create} from './engine.mjs';
import {MeshBodyCollider} from '../../reference/src/mesh-collider.js';
import {auditSurfaceCollisions} from '../../reference/benchmarks/collision/surface-audit.mjs';
import {measure} from '../../src/metrics.mjs';

const spacingMM = Number(process.env.CANDIDATE_SPACING_MM || 40);
const mode = process.env.CANDIDATE_MODE || 'project-weld';
const output = new URL(`./garment-candidate-${mode}${process.env.CANDIDATE_TAG ? `-${process.env.CANDIDATE_TAG}` : ''}.json`, import.meta.url);
const maxSteps = Number(process.env.CANDIDATE_STEPS || 4);
const padding = Number(process.env.CANDIDATE_PADDING_M || 0.03);
const demo = buildDemo({spacingMM}), mesh = demo.mesh, collider = new MeshBodyCollider(human);
const positions = Array.from(demo.pose.positions), n = mesh.restXY.length;
const roots = Array.from({length: n}, (_, i) => i);
const find = i => {while (roots[i] !== i) {roots[i] = roots[roots[i]]; i = roots[i];} return i;};
for (const seam of mesh.seams) for (const [a, b] of seam.pairs) roots[find(b)] = find(a);
const groups = new Map();
for (let i = 0; i < n; i++) {const root = find(i); if (!groups.has(root)) groups.set(root, []); groups.get(root).push(i);}
if (mode.includes('cylinder')) for (let i = 0; i < n; i++) {
  const [u, v] = mesh.restXY[i], id = mesh.panelOfVertex[i];
  if (id === 'front' || id === 'back') {
    const angle = u / 246.0015 * Math.PI / 2;
    positions.splice(i * 3, 3, 0.19 * Math.sin(angle), 1.48 - v * 0.001, 0.035 + (id === 'front' ? 1 : -1) * 0.15 * Math.cos(angle));
  } else {
    const sign = id.endsWith('left') ? -1 : 1, radius = 0.065;
    const theta = Math.PI * u / 151.1578, axial = (v + 135.35799) * 0.001;
    positions.splice(i * 3, 3, sign * (0.18 + axial * 0.73 + radius * Math.cos(theta) * 0.68), 1.40 - axial * 0.68 + radius * Math.cos(theta) * 0.73, 0.018 + radius * Math.sin(theta) * -sign);
  }
}
if (mode.includes('planar')) for (let i = 0; i < n; i++) {
  const [u, v] = mesh.restXY[i], id = mesh.panelOfVertex[i];
  if (id === 'front' || id === 'back') positions.splice(i * 3, 3, u * 0.001, 1.5 - v * 0.001, id === 'front' ? 0.23 : -0.2);
  else {
    const sign = id.endsWith('left') ? -1 : 1;
    positions.splice(i * 3, 3, sign * (0.48 + v * 0.00073) + u * 0.00068, 1.4 - v * 0.00068 + sign * u * 0.00073, 0.23);
  }
}
if (mode.includes('inflate')) for (let i = 0; i < n; i++) {
  if (['front', 'back'].includes(mesh.panelOfVertex[i])) {
    positions[i * 3] *= 1.2;
    positions[i * 3 + 2] = 0.035 + (positions[i * 3 + 2] - 0.035) * 1.35;
  } else {
    const sign = mesh.panelOfVertex[i].endsWith('left') ? -1 : 1;
    positions[i * 3] += sign * 0.025;
    positions[i * 3 + 2] = 0.018 + (positions[i * 3 + 2] - 0.018) * 1.3;
  }
}
if (mode !== 'original') {
  for (let i = 0; i < n; i++) positions.splice(i * 3, 3, ...collider.project(...positions.slice(i * 3, i * 3 + 3), padding));
  if (mode.includes('weld')) for (const ids of groups.values()) if (ids.length > 1) {
    const mean = [0, 1, 2].map(k => ids.reduce((sum, i) => sum + positions[i * 3 + k], 0) / ids.length);
    const projected = Array.from(collider.project(...mean, padding));
    for (const id of ids) positions.splice(id * 3, 3, ...projected);
  }
}
const seams = mesh.seams.flatMap(s => s.pairs), samples = [];
function audit(p, step) {
  const start = performance.now();
  const result = auditSurfaceCollisions({cloth: {positions: p, triangles: mesh.triangles.flat()}, body: human, bodyCollider: collider, seams, maxExamples: 8});
  const metrics = measure(mesh, p);
  const sample = {step, auditMs: performance.now() - start, inside: result.vertexInside.count, maxDepthM: result.vertexInside.maxDepthM, bodyCrossings: result.bodySurface.strictCrossingPairs, selfCrossings: result.selfSurface.strictCrossingPairs, coplanarSelf: result.selfSurface.coplanarOverlapPairs, maxSeamGapMM: metrics.maxSeamGapMM, maxStretch: metrics.maxStretch, areaOver20Percent: metrics.areaOver20Percent, fullAudit: result};
  samples.push(sample);
  console.log(JSON.stringify({event: 'audit', ...sample, fullAudit: undefined}));
}
audit(positions, 0);
const tuned = mode.includes('gentle') || mode.includes('medium');
const config = {dt: 1 / 120, particleRadius: 0.005, edgeFrequency: tuned ? 60 : 15, bendFrequency: 2, additionalSolverIterations: 0, additionalPgsIterations: tuned ? 2 : 1, solverIterations: 4, maxExtraSubsteps: 0, ...(mode.includes('spring') ? {seamMode: 'spring', seamStiffness: mode.includes('medium') ? 0.2 : mode.includes('gentle') ? 0.01 : 1, seamDamping: mode.includes('medium') ? 0.015 : mode.includes('gentle') ? 0.0035 : 0.035} : {})};
const sourcePaths = ['src/pipeline.mjs', 'src/pose.mjs', 'probes/rapier/engine.mjs', 'probes/rapier/garment-candidates.mjs', 'reference/assets/makehuman.json'];
const pins = tuned ? demo.pose.pins.filter(i => mesh.panelOfVertex[i] === 'front') : demo.pose.pins;
const report = {schema: 'rapier-garment-candidate-1', spacingMM, mode, paddingM: padding, mesh: {particles: n, triangles: mesh.triangles.length, bodyTriangles: human.triangles.length / 3, seamPairs: seams.length}, config, positions, pins, sourceHashes: Object.fromEntries(sourcePaths.map(p => [p, crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')])), samples, timings: [], limits: ['One run, not a comparative performance conclusion.', 'Initialization projection and seam coincidence are one-time assembly preprocessing, not per-step collision handling.', 'Native dynamics only after engine creation.', 'Coarse mesh and visible shoulder supports are demonstration assumptions.']};
fs.writeFileSync(output, JSON.stringify(report, null, 2));
if (maxSteps > 0) {
  const creationStart = performance.now();
  const engine = await create({restXY: mesh.restXY, triangles: mesh.triangles, initialXYZ: positions, seams: mesh.seams, pinnedIDs: report.pins, body: human, ...config});
  report.creationMs = performance.now() - creationStart;
  report.nativeBefore = engine.nativeStats();
  console.log(JSON.stringify({event: 'created', ms: report.creationMs, particles: n}));
  for (let step = 1; step <= maxSteps; step++) {
    const start = performance.now(); engine.step(1); const elapsed = performance.now() - start;
    const p = Array.from(engine.getPositions());
    if (!p.every(Number.isFinite)) throw new Error('Nonfinite particle output');
    report.timings.push({step, nativeStepMs: elapsed, positionsFinite: true, positionChanged: p.some((v, i) => v !== positions[i])});
    if (step < 4 || step % 10 === 0) console.log(JSON.stringify({event: 'step', step, ms: elapsed}));
    if (step % 30 === 0 || step === maxSteps || elapsed > 10000) audit(p, step);
    if (step % 10 === 0 || step === maxSteps || elapsed > 10000) {report.finalPositions = p; report.nativeAfter = engine.nativeStats(); fs.writeFileSync(output, JSON.stringify(report, null, 2));}
    if (elapsed > 10000) break;
  }
  report.nativeAfter = engine.nativeStats();
  engine.dispose();
  fs.writeFileSync(output, JSON.stringify(report, null, 2));
}
