"""Blender4.3.2 rest-key influence probe on an already triangular pinned sheet.
Each process uses one new scene. Initial coordinates/topology are fixed; only
rest key X scale and an optional geometric-noop Triangulate before Cloth vary.
"""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy,numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--rest-scale',type=float,required=True);p.add_argument('--constructive-noop',action='store_true');p.add_argument('--pad-rest-copy',action='store_true');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    n=5;v=np.array([[x,y,0.] for y in np.linspace(0,.4,n) for x in np.linspace(0,.6,n)])
    t=[]
    for j in range(n-1):
        for i in range(n-1):
            k=j*n+i;t.extend([[k,k+1,k+1+n],[k,k+1+n,k+n]])
    t=np.array(t,int);m=bpy.data.meshes.new('Probe triangles');m.from_pydata(v.tolist(),[],t.tolist());m.update()
    o=bpy.data.objects.new('Pinned sheet',m);bpy.context.collection.objects.link(o)
    o.shape_key_add(name='Basis');key=o.shape_key_add(name='Rest');rest=v.copy();rest[:,0]*=a.rest_scale;key.data.foreach_set('co',rest.ravel());key.value=0.
    if a.pad_rest_copy:
        copy=o.shape_key_add(name='RestStorageCopy');copy.data.foreach_set('co',rest.ravel());copy.value=0.
    group=o.vertex_groups.new(name='Pinned left');group.add([j*n for j in range(n)],1.,'REPLACE')
    if a.constructive_noop:
        no=o.modifiers.new('Constructive no-op on triangular input','TRIANGULATE');no.min_vertices=4
    # Establish no-op identity before the cloth modifier even exists.
    graph=bpy.context.evaluated_depsgraph_get();ev=o.evaluated_get(graph);mm=ev.to_mesh();mm.calc_loop_triangles()
    initial=np.array([x.co[:] for x in mm.vertices]);initial_t=np.array([x.vertices[:] for x in mm.loop_triangles]);ev.to_mesh_clear()
    assert np.max(abs(initial-v))<1e-7 and np.array_equal(initial_t,t)
    c=o.modifiers.new('Cloth','CLOTH');s=c.settings;s.rest_shape_key=key;s.use_dynamic_mesh=False;s.quality=10;s.mass=.01
    s.tension_stiffness=100;s.compression_stiffness=100;s.shear_stiffness=30;s.bending_stiffness=.05;s.air_damping=0.
    s.tension_damping=5;s.compression_damping=5;s.shear_damping=5;s.vertex_group_mass=group.name;s.use_sewing_springs=False
    c.collision_settings.use_collision=False;c.collision_settings.use_self_collision=False;c.point_cache.frame_start=1;c.point_cache.frame_end=8
    scene=bpy.context.scene;scene.gravity=(0,0,0);scene.frame_end=8;scene.render.fps=24
    samples=[]
    for frame in range(1,9):
        scene.frame_set(frame);bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());mm=ev.to_mesh();mm.calc_loop_triangles()
        vertices=np.array([x.co[:] for x in mm.vertices]);faces=np.array([x.vertices[:] for x in mm.loop_triangles]);ev.to_mesh_clear();assert np.array_equal(faces,t)
        samples.append(vertices)
    frames=np.array(samples);np.savez_compressed(a.out/'frames.npz',frames=frames,initial_vertices=initial,triangles=t,rest_key_coordinates=rest)
    receipt={'blender_version':bpy.app.version_string,'rest_scale':a.rest_scale,'pad_rest_copy':a.pad_rest_copy,'constructive_noop':a.constructive_noop,'rest_shape_key':s.rest_shape_key.name,'rest_key_value':key.value,'use_dynamic_mesh':s.use_dynamic_mesh,
             'initial_mesh_max_coordinate_difference_m':float(np.max(abs(initial-v))),'initial_and_all_frame_topology_identical':True,'source_vertex_count':len(v),'triangle_count':len(t),'pinned_vertices':[j*n for j in range(n)],
             'maximum_first_frame_coordinate_change_m':float(np.max(abs(frames[0]-initial))),
             'maximum_final_coordinate_change_m':float(np.max(abs(frames[-1]-initial))),
             'final_mean_free_right_edge_x_m':float(frames[-1,np.arange(n-1,n*n,n),0].mean()),
             'all_finite':bool(np.isfinite(frames).all()),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
