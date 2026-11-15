"""Pack measured solver geometry into a portable animated .blend and render it.

The replay contains actual evaluated Cloth outputs, never a generated illustration.
Shape keys store each sample in the .blend, so replay has no external cache paths.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import bpy
import numpy as np
from mathutils import Vector


def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1)
    m.use_nodes=True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
    return m


def add_mesh(name,vertices,triangles,mat):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],triangles);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    for p in mesh.polygons:p.use_smooth=True
    obj.shape_key_add(name='Basis')
    return obj


def add_key(obj,values,frame):
    key=obj.shape_key_add(name=f'MeasuredFrame_{frame:04d}')
    key.data.foreach_set('co',np.asarray(values,dtype=np.float32).ravel())
    key.value=0;key.keyframe_insert('value',frame=frame-1)
    key.value=1;key.keyframe_insert('value',frame=frame)
    key.value=0;key.keyframe_insert('value',frame=frame+1)


def mark_loop(name,coords,mat):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D'
    curve.bevel_depth=.002;curve.bevel_resolution=2
    spline=curve.splines.new('POLY');spline.points.add(len(coords)-1)
    for point,co in zip(spline.points,coords):point.co=(*co,1)
    spline.use_cyclic_u=True
    obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj)
    curve.materials.append(mat)
    return obj


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',required=True);p.add_argument('--out',required=True)
    p.add_argument('--render',action='store_true');p.add_argument('--limit',type=int,default=0)
    p.add_argument('--stills',action='store_true',help='Render real front/oblique/back key poses with measured boundary annotations')
    p.add_argument('--engine',choices=['workbench','cycles'],default='workbench')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    run=Path(args.run).resolve();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    files=sorted((run/'frames').glob('*.npz'))
    if not files:raise RuntimeError('No measured solver frames')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    first=np.load(files[0])
    shirt=add_mesh('MeasuredCloth',first['cloth_vertices'],first['cloth_triangles'],material('Teal',(.035,.39,.45)))
    body=add_mesh('MeasuredFullBody',first['body_vertices'],first['body_triangles'],material('Body',(.56,.39,.30)))
    topology=json.loads((run/'topology.json').read_text())
    for kind in ['armholes','cuffs']:
        for side,ids in topology[kind].items():
            vg=shirt.vertex_groups.new(name=kind+'.'+side);vg.add(ids,1.,'REPLACE')
    for frame,file in enumerate(files[1:],2):
        with np.load(file) as data:
            add_key(shirt,data['cloth_vertices'],frame);add_key(body,data['body_vertices'],frame)
    for obj in [shirt,body]:
        action=obj.data.shape_keys.animation_data.action
        for curve in action.fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=len(files);scene.render.fps=24
    scene.unit_settings.system='METRIC'
    scene.world=bpy.data.worlds.new('EvidenceWorld');scene.world.color=(.045,.055,.065)
    bpy.ops.object.camera_add(location=(2.2,-5,2.1))
    camera=bpy.context.object;camera.name='EvidenceCamera';camera.data.type='ORTHO';camera.data.ortho_scale=2.35
    camera.rotation_euler=(Vector((0,0,1.0))-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.camera=camera
    scene.render.resolution_x=640;scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    if args.engine=='workbench':
        scene.render.engine='BLENDER_WORKBENCH'
        scene.display.render_aa='8'
        shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL'
        shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH'
        shade.show_specular_highlight=False;shade.background_type='WORLD'
    else:
        scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=False
        for loc,power in [((2,-3,4),600),((-3,-1,3),450),((1,3,3),500)]:
            bpy.ops.object.light_add(type='AREA',location=loc)
            bpy.context.object.data.energy=power;bpy.context.object.data.size=3
            bpy.context.object.rotation_euler=(Vector((0,0,1))-bpy.context.object.location).to_track_quat('-Z','Y').to_euler()
    scene['Evidence']='Actual evaluated Blender Cloth outputs. New synthetic fixture. NOT PHYSICAL FIT APPROVED.'
    scene['SourceRun']=run.name
    scene['ReplayType']='self-contained per-frame shape keys; no external cache dependency'
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'measured-replay.blend'),compress=True)
    if args.render:
        (out/'video-frames').mkdir(exist_ok=True)
        last=args.limit or len(files)
        for frame in range(1,min(last,len(files))+1):
            scene.frame_set(frame)
            scene.render.filepath=str(out/'video-frames'/f'{frame:04d}.png')
            bpy.ops.render.render(write_still=True)
            if frame%20==0:print('RENDERED_FRAME',frame,flush=True)
    if args.stills:
        stills=out/'stills';stills.mkdir(exist_ok=True)
        amber=material('ArmholeAnnotation',(1,.52,.045))
        pink=material('CuffAnnotation',(1,.18,.39))
        for frame in sorted({f for f in [1,21,81,141,221,len(files)] if f<=len(files)}):
            scene.frame_set(frame)
            with np.load(files[frame-1]) as data:
                cv=data['cloth_vertices']
            markers=[]
            for kind,mat in [('armholes',amber),('cuffs',pink)]:
                for side,ids in topology[kind].items():
                    markers.append(mark_loop(kind+'.'+side,cv[ids],mat))
            for view,location in [('front',(0,-5,1.2)),('oblique',(2.2,-5,2.1)),('back',(0,5,1.2))]:
                camera.location=location
                camera.rotation_euler=(Vector((0,0,1.0))-camera.location).to_track_quat('-Z','Y').to_euler()
                scene.render.filepath=str(stills/f'{frame:04d}-{view}.png')
                bpy.ops.render.render(write_still=True)
            for obj in markers:bpy.data.objects.remove(obj,do_unlink=True)
    (out/'replay-config.json').write_text(json.dumps({'source_run':run.name,'frame_count':len(files),
         'blender_version':bpy.app.version_string,'engine':scene.render.engine,
         'rendered_frames':min(args.limit or len(files),len(files)) if args.render else 0,
         'boundary_annotation_stills':bool(args.stills),
         'external_geometry_dependencies':False,'geometry':'evaluated solver NPZ arrays'},indent=2))


if __name__=='__main__':main()
