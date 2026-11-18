import RAPIER from '@dimforge/rapier3d-compat';
import {stitch} from './native-seam.mjs';

export async function create({positions, assembledPositions = null, triangles, edges, dihedrals = [], pins = [], seams = [], selfContacts = true, radius = 0.005, gravity = [0, -9.81, 0], dt = 1 / 120, softness = [20, 1], colliders = []}) {
  if (!positions?.length || positions.length % 3 || !Array.from(positions).every(Number.isFinite)) throw new Error('Finite xyz positions required');
  const count = positions.length / 3;
  for (const [values, stride] of [[triangles, 3], [edges, 2], [dihedrals, 4]]) {
    if (!values || values.length % stride || !Array.from(values).every(i => Number.isInteger(i) && i >= 0 && i < count)) throw new Error('Invalid topology');
  }
  if (!Array.from(pins).every(i => Number.isInteger(i) && i >= 0 && i < count)) throw new Error('Invalid pin');
  if (assembledPositions && (assembledPositions.length !== positions.length || !Array.from(assembledPositions).every(Number.isFinite))) throw new Error('Invalid assembly positions');
  if (!seams.every(pair => pair.length === 2 && pair.every(i => Number.isInteger(i) && i >= 0 && i < count))) throw new Error('Invalid seam');
  if (!(Number.isFinite(dt) && dt > 0 && Number.isFinite(radius) && radius > 0)) throw new Error('Positive finite timestep and radius required');
  await RAPIER.init();
  const world = new RAPIER.World({x: gravity[0], y: gravity[1], z: gravity[2]});
  world.timestep = dt;
  const desc = new RAPIER.SoftBodyDesc(new Float32Array(positions))
    .setSurface(triangles).setEdges(edges).setDihedrals(dihedrals)
    .setPinnedParticles(pins).setSelfContacts(selfContacts).setParticleRadius(radius)
    .setSoftness(...softness).setLinearDamping(0.3).setCanSleep(false)
    .setAdditionalSolverIterations(4).setAdditionalPgsIterations(8);
  const body = world.createSoftBody(desc);
  if (assembledPositions) for (let i = 0; i < count; i++) {
    body.setParticlePosition(i, {x: assembledPositions[i * 3], y: assembledPositions[i * 3 + 1], z: assembledPositions[i * 3 + 2]});
  }
  const seamJoints = seams.map(([a, b]) => stitch(world, body, a, body, b));
  for (const collider of colliders) {
    world.createCollider(RAPIER.ColliderDesc.trimesh(new Float32Array(collider.positions), new Uint32Array(collider.triangles)).setFriction(0.5));
  }
  let disposed = false;
  return {
    world,
    body,
    seamJoints,
    step(steps = 1) {
      if (disposed) throw new Error('Adapter disposed');
      if (!Number.isInteger(steps) || steps < 0) throw new Error('Nonnegative integer steps required');
      for (let i = 0; i < steps; i++) world.step();
    },
    getPositions() {
      if (disposed) throw new Error('Adapter disposed');
      return body.particlePositions();
    },
    dispose() {
      if (!disposed) world.free();
      disposed = true;
    },
  };
}

export {RAPIER};
