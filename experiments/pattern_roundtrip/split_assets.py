"""Separate frozen one-shot human and rest garment into independent files.

Each file reopens without the other. The human retains its original rig/motion;
the garment contains only its unstrained source-rest mesh, not a failed drape.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def obj_file(path,name,vertices,triangles):
    with path.open('w') as f:
        f.write('# units: metres; separate one-shot asset\no '+name+'\n')
        for p in vertices:f.write('v '+' '.join(format(float(x),'.12g') for x in p)+'\n')
        for t in triangles:f.write('f '+' '.join(str(int(x)+1) for x in t)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--human',type=Path,required=True);p.add_argument('--topology',type=Path,required=True);p.add_argument('--source-frame',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=False)
    top=json.loads(args.topology.read_text())
    with np.load(args.source_frame) as f:
        cv=np.asarray(top['rest_vertices'],float);ct=f['cloth_triangles'];bv=f['body_vertices'];bt=f['body_triangles']
        paths={s:f['path_'+s] for s in ('L','R')}
    source={'human_source_sha256':digest(args.human),'topology_sha256':digest(args.topology),'frame_sha256':digest(args.source_frame),
            'garment_geometry':'unstrained source rest_vertices, source-frame triangulation','physical_fit':'NOT_RUN','measured_human':False}
    bpy.ops.wm.open_mainfile(filepath=str(args.human.resolve()),load_ui=False);scene=bpy.context.scene;scene.frame_set(1)
    assert all(o.type in ('MESH','ARMATURE') for o in scene.objects)
    body=bpy.data.objects['OneShotMannequin'];body['SeparatedRole']='Human only; no garment';body['SourceProvenance']=json.dumps(source)
    graph=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(graph);mesh=ev.to_mesh();mesh.calc_loop_triangles()
    live=np.asarray([ev.matrix_world@v.co for v in mesh.vertices]);live_t=np.asarray([t.vertices[:] for t in mesh.loop_triangles]);ev.to_mesh_clear()
    assert np.array_equal(live_t,bt) and np.max(np.abs(live-bv))<1e-7
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'human.blend'),compress=True)
    obj_file(args.out/'human.obj','Human',bv,bt)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data=bpy.data.meshes.new('Unstrained source garment');data.from_pydata(cv.tolist(),[],ct.tolist());data.update()
    ob=bpy.data.objects.new('ClothOnly',data);bpy.context.collection.objects.link(ob);ob['SeparatedRole']='Cloth only; no human';ob['SourceProvenance']=json.dumps(source)
    for kind in ('armholes','cuffs'):
        for side,ids in top[kind].items():g=ob.vertex_groups.new(name=kind+'.'+side);g.add(ids,1.,'REPLACE')
    mat=bpy.data.materials.new('Garment teal');mat.diffuse_color=(.02,.43,.48,1);data.materials.append(mat)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'cloth.blend'),compress=True)
    obj_file(args.out/'cloth.obj','Cloth',cv,ct)
    np.savez_compressed(args.out/'source-pair.npz',cloth_vertices=cv,cloth_triangles=ct,body_vertices=bv,body_triangles=bt,path_L=paths['L'],path_R=paths['R'])
    receipts=[]
    for name in ('human','cloth'):
        bpy.ops.wm.open_mainfile(filepath=str(args.out/(name+'.blend')),load_ui=False);s=bpy.context.scene;s.frame_set(1)
        meshes=[o for o in s.objects if o.type=='MESH'];assert len(meshes)==1
        assert not bpy.data.libraries and not any(im.source=='FILE' and not im.packed_file for im in bpy.data.images)
        target=meshes[0];ev=target.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();m.calc_loop_triangles()
        v=np.array([ev.matrix_world@x.co for x in m.vertices]);t=np.array([x.vertices[:] for x in m.loop_triangles]);ev.to_mesh_clear()
        expected_v,expected_t=(bv,bt) if name=='human' else (cv,ct)
        delta=float(np.max(np.abs(v-expected_v)));assert np.array_equal(t,expected_t) and delta<1e-7
        receipts.append({'file':name+'.blend','mesh_count':1,'scene_objects':[o.type for o in s.objects],
                         'other_asset_present':False,'max_vertex_delta_m':delta,'triangles_match':True,'external_geometry_dependencies':0,
                         'sha256':digest(args.out/(name+'.blend'))})
    # Actual separated presentation; independent deliverable files above stay unchanged.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def show(name,v,t,color,offset):
        m=bpy.data.meshes.new(name);m.from_pydata((v+offset).tolist(),[],t.tolist());m.update();o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o)
        mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);m.materials.append(mat)
    show('Human',bv,bt,(.57,.39,.26),np.array([-.82,0,0]));show('Cloth',cv,ct,(.02,.43,.48),np.array([.85,0,0]))
    s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.light='STUDIO';s.display.shading.show_cavity=True
    camera=bpy.data.cameras.new('Camera');o=bpy.data.objects.new('Camera',camera);bpy.context.collection.objects.link(o);s.camera=o;o.location=(1,-7,2.5);o.rotation_euler=(Vector((0,0,1.0))-o.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=3.5
    s.render.resolution_x=1300;s.render.resolution_y=850;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.filepath=str(args.out/'separate-parts.png');bpy.ops.render.render(write_still=True)
    result={'source':source,'assets':receipts,'status':'SEPARATE_ASSETS_PASS','scope':'Same frozen one-shot geometry, separated and independently reopened. Not a fit approval.'}
    (args.out/'split-report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
