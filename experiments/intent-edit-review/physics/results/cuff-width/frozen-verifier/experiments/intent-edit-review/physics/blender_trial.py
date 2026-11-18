"""Cross-engine research trial. Run inside Blender, never a substitute PASS.

The source panels remain separate, each material rest state is its actual 2D
pattern. Loose edges form Blender's native sewing springs. All collision and
self-collision settings and all output coordinates are archived for reopening.
"""
import bpy
import sys
import json
import base64
from pathlib import Path
import numpy as np

directory = Path(sys.argv[sys.argv.index('--')+1]).resolve()
data = json.loads((directory/'input.json').read_text())
def unpack(name, dtype, width):
    return np.frombuffer(base64.b64decode(data['body'][name]), dtype).reshape(-1, width)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.fps = 120; scene.frame_start = 1; scene.frame_end = 181
scene.gravity = (0, -9.81, 0)
body_mesh = bpy.data.meshes.new('actual-standard-body')
body_mesh.from_pydata(unpack('positions','<f4',3), [], unpack('indices','<i4',3))
body = bpy.data.objects.new('Actual MakeHuman body (not user measurements)', body_mesh)
scene.collection.objects.link(body); body.modifiers.new('Actual triangle collision', 'COLLISION')
body.collision.thickness_outer = .003; body.collision.thickness_inner = .001
body.collision.cloth_friction = 5
cloth_mesh = bpy.data.meshes.new('unaltered-source-material-panels')
cloth_mesh.from_pydata(data['positions'], data['seams'], data['triangles'])
cloth_mesh.update()
cloth = bpy.data.objects.new('Source-bound T-shirt sewing springs', cloth_mesh)
scene.collection.objects.link(cloth); bpy.context.view_layer.objects.active = cloth; cloth.select_set(True)
cloth.shape_key_add(name='Basis'); rest = cloth.shape_key_add(name='Actual 2D rest pattern')
uv = np.asarray(data['uv']); flat = np.column_stack([uv, np.zeros(len(uv))])
rest.data.foreach_set('co', flat.ravel()); rest.value = 0
mod = cloth.modifiers.new('Real Blender cloth', 'CLOTH'); settings = mod.settings
settings.rest_shape_key = rest
settings.quality = 20; settings.mass = .155
settings.tension_stiffness = 15; settings.compression_stiffness = 15; settings.shear_stiffness = 5
settings.tension_damping = 5; settings.compression_damping = 5; settings.shear_damping = 5
settings.bending_stiffness = .1; settings.bending_damping = .5; settings.air_damping = 1
settings.use_sewing_springs = True; settings.sewing_force_max = 0
collision = mod.collision_settings; collision.use_collision = True; collision.use_self_collision = True
collision.distance_min = .003; collision.self_distance_min = .001
collision.collision_quality = 8; collision.self_friction = 5
mod.point_cache.frame_start = 1; mod.point_cache.frame_end = 181
settings_dump = {p.identifier: getattr(settings, p.identifier) for p in settings.bl_rna.properties
                 if p.type in ['FLOAT','INT','BOOLEAN'] and not p.is_readonly}
collision_dump = {p.identifier: getattr(collision, p.identifier) for p in collision.bl_rna.properties
                  if p.type in ['FLOAT','INT','BOOLEAN'] and not p.is_readonly}
(directory/'blender-settings.json').write_text(json.dumps({'version': bpy.app.version_string, 'settings': settings_dump,
    'collision': collision_dump, 'scope': 'Uncalibrated cross-engine research trial; independent acceptance required.'}, indent=2, default=list))
frames = []
for frame in range(1,182):
    scene.frame_set(frame); depsgraph = bpy.context.evaluated_depsgraph_get(); obj = cloth.evaluated_get(depsgraph)
    mesh = obj.to_mesh(); values = np.empty(len(mesh.vertices)*3, np.float32); mesh.vertices.foreach_get('co', values)
    obj.to_mesh_clear(); frames.append(values.reshape(-1,3).copy())
    if frame % 10 == 0: print('BLENDER_FRAME', frame, flush=True)
    if frame in [1,31,61,121,181]: np.savez_compressed(directory/f'blender-frame-{frame:03d}.npz', positions=frames[-1])
np.savez_compressed(directory/'blender-trajectory.npz', positions=np.asarray(frames))
bpy.ops.wm.save_as_mainfile(filepath=str(directory/'blender-trial.blend'))
print('BLENDER_RECORDING_COMPLETE', len(frames), flush=True)
