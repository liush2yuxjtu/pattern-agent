"""Test animated dynamic base-mesh rest lengths without a rest-shape-key pointer.
Fixed3D initialization is at z=.3; animated2D rest input is atz0 fromframe2.
No pin/collision/gravity: physical output must stay3D rather than copy the input.
"""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy,numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--rest-scale',type=float,required=True);p.add_argument('--dynamic',action='store_true');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=False);bpy.ops.wm.read_factory_settings(use_empty=True)
    n=5;v=np.array([[x,y,.3] for y in np.linspace(0,.4,n) for x in np.linspace(0,.6,n)]);t=[]
    for j in range(n-1):
        for i in range(n-1):
            k=j*n+i;t.extend([[k,k+1,k+1+n],[k,k+1+n,k+n]])
    t=np.array(t,int);m=bpy.data.meshes.new('Probe triangles');m.from_pydata(v.tolist(),[],t.tolist());m.update();o=bpy.data.objects.new('Free sheet',m);bpy.context.collection.objects.link(o)
    o.shape_key_add(name='Basis');key=o.shape_key_add(name='AnimatedRestInput');rest=v.copy();rest[:,0]*=a.rest_scale;rest[:,2]=0.;key.data.foreach_set('co',rest.ravel())
    key.value=0.;key.keyframe_insert('value',frame=1);key.value=1.;key.keyframe_insert('value',frame=2);key.keyframe_insert('value',frame=8)
    for curve in o.data.shape_keys.animation_data.action.fcurves:
        for point in curve.keyframe_points:point.interpolation='LINEAR'
    bpy.context.scene.frame_set(1)
    c=o.modifiers.new('Cloth','CLOTH');s=c.settings;s.use_dynamic_mesh=a.dynamic;s.quality=10;s.mass=.01
    s.tension_stiffness=100;s.compression_stiffness=100;s.shear_stiffness=30;s.bending_stiffness=.05;s.air_damping=0.;s.tension_damping=5;s.compression_damping=5;s.shear_damping=5;s.use_sewing_springs=False
    c.collision_settings.use_collision=False;c.collision_settings.use_self_collision=False;c.point_cache.frame_start=1;c.point_cache.frame_end=8
    scene=bpy.context.scene;scene.gravity=(0,0,0);scene.frame_end=8;scene.render.fps=24;samples=[];values=[]
    for frame in range(1,9):
        scene.frame_set(frame);bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());mm=ev.to_mesh();mm.calc_loop_triangles()
        vv=np.array([x.co[:] for x in mm.vertices]);tt=np.array([x.vertices[:] for x in mm.loop_triangles]);ev.to_mesh_clear();assert np.array_equal(tt,t);samples.append(vv);values.append(float(key.value))
    frames=np.array(samples);np.savez_compressed(a.out/'frames.npz',frames=frames,source_initial_vertices=v,triangles=t,rest_key_coordinates=rest)
    receipt={'blender_version':bpy.app.version_string,'dynamic':a.dynamic,'rest_scale':a.rest_scale,'rest_shape_key_explicitly_selected':False,'pin_groups':[],'gravity':[0,0,0],'collisions':False,'key_values':values,
             'first_frame_max_coordinate_error_m':float(np.max(abs(frames[0]-v))),'final_z_min_m':float(frames[-1,:,2].min()),'final_z_max_m':float(frames[-1,:,2].max()),
             'final_x_span_m':float(np.ptp(frames[-1,:,0])),'final_vs_flat_input_max_error_m':float(np.max(abs(frames[-1]-rest))),
             'final_vs_initial_max_error_m':float(np.max(abs(frames[-1]-v))),'all_finite':bool(np.isfinite(frames).all()),'topology_identical':True,
             'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
