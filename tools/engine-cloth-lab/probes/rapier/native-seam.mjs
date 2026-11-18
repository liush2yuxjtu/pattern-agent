import R from '@dimforge/rapier3d-compat';

export function stitch(world, bodyA, particleA, bodyB, particleB, {mode = 'spherical', stiffness = 1, damping = 0.035} = {}) {
  const clusterA = world.addSoftBodyCluster(bodyA, [particleA]);
  const clusterB = world.addSoftBodyCluster(bodyB, [particleB]);
  if (clusterA === null || clusterB === null) throw new Error('Invalid seam particle');
  const zero = {x: 0, y: 0, z: 0};
  const joint = world.createImpulseJoint(
    mode === 'spring' ? R.JointData.spring(0, stiffness, damping, zero, zero) : R.JointData.spherical(zero, zero),
    bodyA.clusterProxy(clusterA), bodyB.clusterProxy(clusterB), true,
  );
  joint.setContactsEnabled(false);
  return {joint, clusterA, clusterB};
}
