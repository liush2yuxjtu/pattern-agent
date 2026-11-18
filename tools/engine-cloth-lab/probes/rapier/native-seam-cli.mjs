import R from '@dimforge/rapier3d-compat';
import {stitch} from './native-seam.mjs';

await R.init();
const world = new R.World({x: 0, y: -9.81, z: 0});
world.timestep = 1 / 120;
const cloth = x => R.SoftBodyDesc.cloth({x, y: 1, z: 0}, {x: 0.2, y: 0, z: 0}, {x: 0, y: 0, z: 0.2}, 3, 3).setCanSleep(false).setAdditionalSolverIterations(4);
const a = world.createSoftBody(cloth(-0.5).setPinnedParticles([0, 1, 2]));
const b = world.createSoftBody(cloth(0.1));
for (let i = 0; i < 3; i++) stitch(world, a, 6 + i, b, i);
const gap = () => Math.max(...[0, 1, 2].map(i => {
  const p = a.particlePosition(6 + i), q = b.particlePosition(i);
  return Math.hypot(p.x - q.x, p.y - q.y, p.z - q.z);
}));
const initialGapM = gap();
for (let i = 0; i < 240; i++) world.step();
console.log(JSON.stringify({version: R.version(), steps: 240, dt: world.timestep, initialGapM, finalGapM: gap(), finalPositionsA: Array.from(a.particlePositions()), finalPositionsB: Array.from(b.particlePositions())}, null, 2));
world.free();
