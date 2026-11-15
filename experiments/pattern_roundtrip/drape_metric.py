"""Test 2D rest-metric influence from a fixed preplaced 3D configuration.

This is not flat-panel sewing or a donning experiment. Source 3D coordinates are
used only as initial placement; from frame2, dynamic-base rest lengths come from
the keyed 2D panels. Fresh processes isolate baseline, atlas-rigid and sleeve-size
controls. No calibrated mechanics or physical-fit approval is claimed.
"""
import argparse,hashlib,json,sys,time
from pathlib import Path
import bpy
from mathutils import Vector
import numpy as np


def mesh_arrays(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();m.calc_loop_triangles()
    v=np.asarray([ev.matrix_world@x.co for x in m.vertices]);t=np.asarray([x.vertices[:] for x in m.loop_triangles],int);ev.to_mesh_clear();return v,t


def main():
    p=argparse.ArgumentParser();p.add_argument('--pattern',type=Path,required=True);p.add_argument('--pair',type=Path,required=True);p.add_argument('--topology',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--case',choices=['baseline','atlas_rigid','left_sleeve_90'],default='baseline');p.add_argument('--frames',type=int,default=31)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=False);(args.out/'frames').mkdir()
    pattern=json.loads(args.pattern.read_text());source=np.asarray(pattern['source']['rest_vertices_3d_m'],float);top=json.loads(args.topology.read_text())
    with np.load(args.pair) as f:bv,bt=f['body_vertices'],f['body_triangles'];paths={s:f['path_'+s] for s in ('L','R')}
    vertices=[];flat=[];faces=[];global_ids=[];ranges={};panels=pattern['panels']
    for j,(name,panel) in enumerate(panels.items()):
        offset=len(vertices);ids=np.asarray(panel['source_vertex_ids'],int);uv=np.asarray(panel['vertices_2d_m'],float).copy()
        if args.case=='left_sleeve_90' and name=='left_sleeve':uv[:,1]*=.9
        if args.case=='atlas_rigid':
            angle=.23+.17*j;R=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
            uv=uv@R.T+np.array([.31-.11*j,.18+.07*j])
        # Translation is arbitrary layout, not a material rest constraint.
        uv+=np.array([.8*j,-2.])
        vertices.extend(source[ids]);flat.extend(np.column_stack([uv,np.zeros(len(uv))]));global_ids.extend(ids.tolist())
        faces.extend((np.asarray(panel['faces'],int)+offset).tolist());ranges[name]={'offset':offset,'count':len(ids)}
    initial=np.asarray(vertices,float);flat=np.asarray(flat,float);triangles=np.asarray(faces,int)
    sewing=set();seam_indices={}
    for seam in pattern['seams']:
        a=np.asarray(seam['a']['vertices'])+ranges[seam['a']['panel']]['offset'];b=np.asarray(seam['b']['vertices'])+ranges[seam['b']['panel']]['offset']
        assert len(a)==len(b);pairs=[(int(x),int(y)) for x,y in zip(a,b) if x!=y];seam_indices[seam['id']]=pairs
        sewing.update(tuple(sorted(pair)) for pair in pairs)
    sewing=sorted(sewing);edges=np.unique(np.sort(np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]]),axis=1),axis=0)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def mesh(name,v,t,edges=()):
        m=bpy.data.meshes.new(name);m.from_pydata(v.tolist(),list(edges),t.tolist());m.update(calc_edges=True,calc_edges_loose=True)
        o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o);return o
    body=mesh('Frozen human collider',bv,bt);body.modifiers.new('Body collision','COLLISION');body.collision.thickness_outer=.005;body.collision.thickness_inner=.001;body.collision.cloth_friction=.5
    cloth=mesh('Metric driven cut panels',initial,triangles,sewing);cloth.shape_key_add(name='Basis')
    key=cloth.shape_key_add(name='PatternRest2D');key.data.foreach_set('co',flat.ravel());cloth.active_shape_key_index=0
    # Animate before evaluation. Assigning a static rest_shape_key did not affect
    # physical output in our Blender4.3.2 controls. Dynamic-base mesh updates
    # xrest from the input without teleporting the simulated physical positions.
    key.value=0.;key.keyframe_insert('value',frame=1)
    key.value=1.;key.keyframe_insert('value',frame=2);key.keyframe_insert('value',frame=args.frames)
    for curve in cloth.data.shape_keys.animation_data.action.fcurves:
        for point in curve.keyframe_points:point.interpolation='LINEAR'
    actual=np.asarray([x.co[:] for x in key.data]);key_error=float(np.max(np.abs(actual-flat)));assert key_error<1e-6
    modifier=cloth.modifiers.new('2D rest metric Cloth','CLOTH');settings=modifier.settings
    settings.use_dynamic_mesh=True;settings.quality=20;settings.mass=top['mass_model']['total_mass_kg']/len(initial)
    settings.tension_stiffness=35;settings.compression_stiffness=35;settings.shear_stiffness=15;settings.bending_stiffness=.5
    settings.tension_damping=8;settings.compression_damping=8;settings.shear_damping=8;settings.air_damping=3
    settings.use_sewing_springs=True;settings.sewing_force_max=5.
    collision=modifier.collision_settings;collision.use_collision=True;collision.collision_quality=8;collision.distance_min=.004;collision.use_self_collision=True;collision.self_distance_min=.003;collision.self_friction=.5
    modifier.point_cache.frame_start=1;modifier.point_cache.frame_end=args.frames;modifier.point_cache.use_disk_cache=False
    material=bpy.data.materials.new('Cloth');material.diffuse_color=(.02,.43,.48,1);cloth.data.materials.append(material)
    material=bpy.data.materials.new('Human');material.diffuse_color=(.55,.40,.31,1);body.data.materials.append(material)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.render.fps=24;scene.frame_end=args.frames;scene.gravity=(0,0,-9.81);scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'metric-project.blend'),compress=True)
    rest_lengths=np.linalg.norm(actual[edges[:,0]]-actual[edges[:,1]],axis=1);initial_lengths=np.linalg.norm(initial[edges[:,0]]-initial[edges[:,1]],axis=1)
    probe=panels['left_sleeve']['grainline']['anchor_vertex_ids'];probe=np.asarray(probe)+ranges['left_sleeve']['offset']
    probe_rest=float(np.linalg.norm(actual[probe[1]]-actual[probe[0]]));probe_initial=float(np.linalg.norm(initial[probe[1]]-initial[probe[0]]))
    np.savez_compressed(args.out/'input-metrics.npz',initial_vertices=initial,actual_key_coordinates=actual,structural_edges=edges,rest_lengths=rest_lengths,initial_lengths=initial_lengths,cloth_triangles=triangles,source_vertex_ids=np.asarray(global_ids),sewing_pairs=np.asarray(sewing))
    input_report={'case':args.case,'pattern_sha256':hashlib.sha256(args.pattern.read_bytes()).hexdigest(),'source_pair_sha256':hashlib.sha256(args.pair.read_bytes()).hexdigest(),
                  'rest_key_name':key.name,'rest_key_value_frame1':key.value,'dynamic_base_mesh':settings.use_dynamic_mesh,'static_rest_shape_key_selected':settings.rest_shape_key is not None,
                  'rest_input_schedule':'frame1 original3D, frame2 onward flattened2D; animated key established before first evaluation','actual_key_max_coordinate_error_m':key_error,
                  'structural_edge_count':len(edges),'loose_sewing_edge_count':sum(e.is_loose for e in cloth.data.edges),'sewing_pairs':len(sewing),
                  'rest_lengths_from':'2D panel coordinates read back from animated dynamic-base input; causal controls required','initial_placement':'frozen original3D rest surface; not generated by sewing flat panels',
                  'left_grain_probe_rest_length_m':probe_rest,'left_grain_probe_initial_length_m':probe_initial,'left_grain_probe_initial_stretch_ratio':probe_initial/probe_rest,
                  'mass_per_vertex_kg':settings.mass,'total_nominal_mass_fixed_kg':top['mass_model']['total_mass_kg'],'sewing_force_max_N':settings.sewing_force_max,
                  'material':'assumed isotropic numerical settings, not calibrated fabric','body_motion':'frozen A pose to isolate2D rest metric','fabric_grain_response':'NOT_CALIBRATED; isotropic solver does not prove warp/weft behavior'}
    (args.out/'input-report.json').write_text(json.dumps(input_report,indent=2)+'\n')
    rows=[];started=time.monotonic()
    for frame in range(1,args.frames+1):
        scene.frame_set(frame);bpy.context.view_layer.update();v,t=mesh_arrays(cloth);assert np.array_equal(t,triangles) and np.isfinite(v).all()
        gaps=np.linalg.norm(v[np.asarray(sewing)[:,0]]-v[np.asarray(sewing)[:,1]],axis=1)
        lengths=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1);strain=lengths/rest_lengths-1
        data={'cloth_vertices':v,'cloth_triangles':t,'body_vertices':bv,'body_triangles':bt,'path_L':paths['L'],'path_R':paths['R'],'frame':frame}
        np.savez_compressed(args.out/'frames'/f'frame-{frame:04d}.npz',**data)
        rows.append({'frame':frame,'rest_key_value':float(key.value),'sewing_max_gap_mm':float(gaps.max()*1000),'sewing_p95_gap_mm':float(np.percentile(gaps,95)*1000),'edge_abs_strain_p95_pct':float(np.percentile(np.abs(strain),95)*100),'edge_abs_strain_max_pct':float(np.max(np.abs(strain))*100)})
        if frame==1 or frame%10==0:print(json.dumps({'case':args.case,**rows[-1]}),flush=True)
    (args.out/'seam-indices.json').write_text(json.dumps({'ranges':ranges,'seam_pairs':seam_indices,'all_sewing_pairs':sewing},indent=2)+'\n')
    # A cache-free final snapshot for inspection, separate from the solver project.
    bpy.data.objects.remove(cloth,do_unlink=True);cloth=mesh('Measured final cloth',v,t);cloth.data.materials.append(bpy.data.materials['Cloth'])
    scene['Scope']='2D rest metric from preplaced3D initialization. Not flat sewing, donning, calibrated fit or human try-on.'
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'drape-final.blend'),compress=True)
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True
    camera=bpy.data.cameras.new('Camera');o=bpy.data.objects.new('Camera',camera);bpy.context.collection.objects.link(o);scene.camera=o;o.location=(2.2,-5,2.1);o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=2.0
    scene.render.resolution_x=800;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(args.out/'drape-final.png');bpy.ops.render.render(write_still=True)
    result={'input':input_report,'frames':rows,'execution_complete':True,'frame_count':len(rows),'seconds':time.monotonic()-started,
            'verdict':'DIAGNOSTIC_EXECUTED; no manufacturing/wearing/fit approval','flat_panel_sewing':'NOT_RUN','physical_fit':'NOT_RUN'}
    (args.out/'drape-report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'case':args.case,'complete':True,'seconds':result['seconds']}),flush=True)


if __name__=='__main__':main()
