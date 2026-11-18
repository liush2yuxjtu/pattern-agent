import R from '@dimforge/rapier3d-compat';
import {stitch} from './native-seam.mjs';

let initPromise;

export async function create({restXY, triangles, initialXYZ, seamPairs = [], seams = [], pinnedIDs = [], body = null, gravity = [0, -9.81, 0], dt = 1 / 120, particleRadius = 0.005, mass = 0.15, edgeFrequency = 20, bendFrequency = 4, dampingRatio = 1, additionalSolverIterations = 4, additionalPgsIterations = 8, solverIterations = 4, maxExtraSubsteps = 4, seamMode = 'spherical', seamStiffness = 1, seamDamping = 0.035}) {
  if (Array.isArray(restXY?.[0])) restXY = restXY.flat();
  if (Array.isArray(triangles?.[0])) triangles = triangles.flat();
  if (Array.isArray(initialXYZ?.[0])) initialXYZ = initialXYZ.flat();
  seamPairs = [...seamPairs, ...seams.flatMap(seam => seam.pairs)];
  if (!restXY?.length || restXY.length % 2 || !Array.from(restXY).every(Number.isFinite)) throw new Error('restXY requires finite xy pairs in mm');
  const n = restXY.length / 2;
  if (initialXYZ?.length !== n * 3 || !Array.from(initialXYZ).every(Number.isFinite)) throw new Error('initialXYZ requires matching finite xyz triples in m');
  const validIndex = i => Number.isInteger(i) && i >= 0 && i < n;
  if (!triangles?.length || triangles.length % 3 || !Array.from(triangles).every(validIndex)) throw new Error('Invalid triangles');
  if (!Array.from(pinnedIDs).every(validIndex)) throw new Error('Invalid pinnedIDs');
  if (!seamPairs.every(pair => pair.length === 2 && pair.every(validIndex) && pair[0] !== pair[1])) throw new Error('Invalid seamPairs');
  if (![dt, particleRadius, mass, edgeFrequency, bendFrequency].every(x => Number.isFinite(x) && x > 0)) throw new Error('Positive finite engine parameters required');
  if (gravity.length !== 3 || !gravity.every(Number.isFinite)) throw new Error('Invalid gravity');
  if (body && (!body.positions?.length || body.positions.length % 3 || !Array.from(body.positions).every(Number.isFinite) || !body.triangles?.length || body.triangles.length % 3 || !Array.from(body.triangles).every(i => Number.isInteger(i) && i >= 0 && i < body.positions.length / 3))) throw new Error('Invalid body mesh');
  const restXYZ = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    restXYZ[i * 3] = restXY[i * 2] * 0.001;
    restXYZ[i * 3 + 1] = restXY[i * 2 + 1] * 0.001;
  }
  const edgeMap = new Map(), edges = [], dihedrals = [];
  for (let i = 0; i < triangles.length; i += 3) {
    const ids = Array.from(triangles.slice(i, i + 3));
    const a = ids[0], b = ids[1], c = ids[2];
    const area = (restXY[b * 2] - restXY[a * 2]) * (restXY[c * 2 + 1] - restXY[a * 2 + 1]) - (restXY[c * 2] - restXY[a * 2]) * (restXY[b * 2 + 1] - restXY[a * 2 + 1]);
    if (Math.abs(area) <= 1e-8) throw new Error('Degenerate rest triangle');
    for (let j = 0; j < 3; j++) {
      const a = ids[j], b = ids[(j + 1) % 3], c = ids[(j + 2) % 3], key = a < b ? `${a}:${b}` : `${b}:${a}`;
      const previous = edgeMap.get(key);
      if (previous) {
        if (previous.used) throw new Error('Nonmanifold edge');
        dihedrals.push(a, b, previous.opposite, c);
        previous.used = true;
      } else {
        edges.push(a, b);
        edgeMap.set(key, {opposite: c, used: false});
      }
    }
  }
  initPromise ??= R.init();
  await initPromise;
  const world = new R.World({x: gravity[0], y: gravity[1], z: gravity[2]});
  world.timestep = dt;
  world.integrationParameters.numSolverIterations = solverIterations;
  world.integrationParameters.softBodiesMaxExtraSubsteps = maxExtraSubsteps;
  const material = new R.SoftBodyMaterial();
  material.edgeSoftness = {naturalFrequency: edgeFrequency, dampingRatio};
  material.bendSoftness = {naturalFrequency: bendFrequency, dampingRatio};
  const soft = world.createSoftBody(new R.SoftBodyDesc(restXYZ).setEdges(edges).setDihedrals(dihedrals).setSurface(triangles).setMaterial(material).setMass(mass).setSelfContacts(true).setParticleRadius(particleRadius).setLinearDamping(0.3).setCanSleep(false).setAdditionalSolverIterations(additionalSolverIterations).setAdditionalPgsIterations(additionalPgsIterations));
  for (let i = 0; i < n; i++) soft.setParticlePosition(i, {x: initialXYZ[i * 3], y: initialXYZ[i * 3 + 1], z: initialXYZ[i * 3 + 2]});
  for (const i of pinnedIDs) soft.setParticlePinned(i, true);
  const nativeSeams = seamPairs.map(([a, b]) => stitch(world, soft, a, soft, b, {mode: seamMode, stiffness: seamStiffness, damping: seamDamping}));
  if (body) world.createCollider(R.ColliderDesc.trimesh(new Float32Array(body.positions), new Uint32Array(body.triangles)).setFriction(0.5));
  const originalRestLengths = Array.from({length: soft.numEdges()}, (_, i) => soft.edgeRestLength(i));
  let disposed = false, stepCount = 0;
  const requireLive = () => {if (disposed) throw new Error('Engine disposed');};
  return {
    step(steps = 1) {
      requireLive();
      if (!Number.isInteger(steps) || steps < 0) throw new Error('Nonnegative integer steps required');
      for (let i = 0; i < steps; i++) world.step();
      stepCount += steps;
    },
    getPositions() {requireLive(); return soft.particlePositions();},
    nativeStats() {
      requireLive();
      const positions = soft.particlePositions(), restLengths = Array.from({length: soft.numEdges()}, (_, i) => soft.edgeRestLength(i));
      const gaps = seamPairs.map(([a, b]) => Math.hypot(...[0, 1, 2].map(k => positions[a * 3 + k] - positions[b * 3 + k])));
      return {engine: 'Rapier', version: R.version(), particles: soft.numParticles(), edges: soft.numEdges(), dihedrals: soft.numDihedrals(), collisionMeshes: soft.numMeshes(), nativeSeamJoints: nativeSeams.length, selfContacts: true, stepCount, dt: world.timestep, solverIterations, additionalSolverIterations, additionalPgsIterations, maxExtraSubsteps, edgePairs: Array.from(soft.edges()), edgeRestLengthsM: restLengths, structuralRestLengthsUnchanged: restLengths.every((v, i) => v === originalRestLengths[i]), seamGapsM: gaps, maxSeamGapM: gaps.length ? Math.max(...gaps) : 0};
    },
    dispose() {if (!disposed) world.free(); disposed = true;},
  };
}
