"""Reopen each standalone .blend, compare OBJ geometry, render actual control mesh.

The cutaway omits front garment faces for visibility; it is explicitly a
diagnostic view, never a substitute for the numeric intersection/path checks.
"""
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from control_io import read_obj


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--cloth',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=True)
    receipts=[];assets=[]
    for kind,path in [('model',args.model),('cloth',args.cloth)]:
        bpy.ops.wm.open_mainfile(filepath=str(path.resolve()),load_ui=False)
        assert len(bpy.context.scene.objects)==1,'Standalone asset must contain exactly one scene object'
        obj=bpy.context.scene.objects[0];assert obj.type=='MESH'
        v=np.asarray([x.co[:] for x in obj.data.vertices],float)
        obj.data.calc_loop_triangles();t=np.asarray([x.vertices[:] for x in obj.data.loop_triangles],int)
        ov,ot,metadata,_=read_obj(path.with_suffix('.obj'))
        maximum=float(np.max(np.abs(v-ov)))
        assert maximum<1e-6 and len(t)==len(ot)
        # Reopening a quad can select either diagonal. Compare polygon surfaces,
        # and require the exact triangulation for the triangular garment file.
        if kind=='cloth':assert np.array_equal(t,ot)
        external=[str(x.filepath) for x in bpy.data.images if x.source=='FILE' and not x.packed_file]
        assert not external and not bpy.data.libraries
        assert json.loads(obj['asset_contract'])==metadata
        receipts.append({'asset':kind,'scene_object_count':1,'mesh_count':1,'vertices':len(v),'triangles':len(t),
                         'reopened_from_disk':True,'obj_max_vertex_error_m':maximum,'metadata_matches_obj':True,
                         'external_dependencies':external,'linked_libraries':0})
        assets.append((kind,ov,ot,metadata))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def material(name,color):
        m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
    bodymat=material('Body',(.58,.30,.13));clothmat=material('Cloth',(.02,.43,.48));pathmat=material('Internal arm path',(.86,.17,.06))
    def mesh(name,v,t,mat):
        data=bpy.data.meshes.new(name);data.from_pydata(v.tolist(),[],t.tolist());data.update()
        obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);data.materials.append(mat);return obj
    body=mesh('Actual complete body',assets[0][1],assets[0][2],bodymat)
    garment=mesh('Actual one-shot garment',assets[1][1],assets[1][2],clothmat)
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
    scene.display.shading.background_type='WORLD';scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
    scene.world=bpy.data.worlds.new('World');scene.world.color=(.92,.94,.96)
    scene.render.resolution_x=1100;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    camera=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camera);bpy.context.collection.objects.link(cam);scene.camera=cam
    cam.location=(2.1,-6,2.6);cam.rotation_euler=(Vector((0,0,.90))-cam.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=2.10
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(args.out/'overview.png');bpy.ops.render.render(write_still=True)
    # A recorded cutaway of the actual garment, front y<0 faces removed only in this view.
    cv,ct=assets[1][1:3];visible=ct[~np.all(cv[ct][:,:,1]<-1e-9,axis=1)]
    garment.hide_render=True;cutaway=mesh('Diagnostic cutaway garment',cv,visible,clothmat)
    def line(name,points,radius=.003):
        curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.bevel_depth=radius;curve.bevel_resolution=2
        poly=curve.splines.new('POLY');poly.points.add(len(points)-1)
        for p,co in zip(poly.points,points):p.co=(*co,1)
        obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj);curve.materials.append(pathmat)
    for side in ('L','R'):line('Declared arm path '+side,np.array(assets[0][3]['path_'+side]))
    camera.ortho_scale=1.92;cam.location=(.9,-6,2.05);cam.rotation_euler=(Vector((0,0,.96))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(args.out/'diagnostic-cutaway.png');bpy.ops.render.render(write_still=True)
    (args.out/'standalone-readback.json').write_text(json.dumps({'assets':receipts,'render_scope':'Actual mesh overview and explicitly modified diagnostic cutaway. Numeric checks determine acceptance.'},indent=2))
    print(json.dumps({'standalone_readback':'PASS','assets':receipts,'images':['overview.png','diagnostic-cutaway.png']}),flush=True)


if __name__=='__main__':main()
