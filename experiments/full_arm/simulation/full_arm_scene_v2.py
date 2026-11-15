"""Reproducible, preassembled synthetic T-shirt fixture; not the lost 20261111 scene.

Run with Blender 4.3: blender -b -t 2 --python-exit-code 2 --python this.py -- --out PATH
The garment is an open, single connected, sewn/welded surface with four openings.
Nothing in this file assigns validation PASS statuses.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
import bmesh
import numpy as np
from mathutils import Quaternion, Vector


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Roughness'].default_value = 0.75
    return mat


def mesh_obj(name, verts, faces, mat=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if mat:
        mesh.materials.append(mat)
    return obj


def ellipsoid(name, center, scale, objects):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    objects.append(obj)


def capsule(name, p0, p1, r0, r1, objects):
    p0, p1 = Vector(p0), Vector(p1)
    direction = p1-p0
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=r0, radius2=r1,
                                    depth=direction.length, location=(p0+p1)/2)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = direction.to_track_quat('Z','Y').to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    objects.append(ob)
    ellipsoid(name+'_joint', p0, (r0,r0,r0), objects)
    ellipsoid(name+'_tip', p1, (r1,r1,r1), objects)


def build_body(mat):
    parts=[]
    ellipsoid('Chest', (0,0,1.27), (.184,.104,.235), parts)
    ellipsoid('Waist', (0,0,1.035), (.143,.094,.22), parts)
    ellipsoid('Pelvis', (0,0,.845), (.168,.104,.14), parts)
    capsule('Neck',(0,0,1.43),(0,0,1.58),.057,.052,parts)
    ellipsoid('Head', (0,0,1.68), (.075,.078,.111), parts)
    for sign,side in [(1,'L'),(-1,'R')]:
        capsule('UpperArm.'+side,(sign*.17,0,1.42),(sign*.47,0,1.42),.061,.047,parts)
        capsule('Forearm.'+side,(sign*.47,0,1.42),(sign*.74,0,1.42),.047,.033,parts)
        ellipsoid('Hand.'+side,(sign*.785,0,1.42),(.069,.038,.028),parts)
        capsule('Thigh.'+side,(sign*.087,0,.84),(sign*.094,0,.47),.078,.055,parts)
        capsule('Shin.'+side,(sign*.094,0,.47),(sign*.098,0,.10),.055,.036,parts)
        ellipsoid('Foot.'+side,(sign*.098,-.035,.07),(.046,.10,.041),parts)
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.object.join()
    body=bpy.context.object
    body.name='FullBody_Uncalibrated_Synthetic'
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    remesh=body.modifiers.new('WatertightUnion','REMESH')
    remesh.mode='VOXEL'
    remesh.voxel_size=.021
    remesh.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth=body.modifiers.new('SmoothUnion','SMOOTH')
    smooth.factor=.35
    smooth.iterations=2
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    body.data.materials.append(mat)
    return body


def make_rig(body):
    rigdata=bpy.data.armatures.new('ShoulderElbowForearmRig')
    rig=bpy.data.objects.new('MannequinRig',rigdata)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    root=rigdata.edit_bones.new('Root')
    root.head=(0,0,.8);root.tail=(0,0,1.10)
    for sign,side in [(1,'L'),(-1,'R')]:
        upper=rigdata.edit_bones.new('UpperArm.'+side)
        upper.head=(sign*.17,0,1.42)
        upper.tail=(sign*.47,0,1.42)
        lower=rigdata.edit_bones.new('Forearm.'+side)
        lower.head=upper.tail
        lower.tail=(sign*.74,0,1.42)
        lower.parent=upper
        lower.use_connect=True
        hand=rigdata.edit_bones.new('Hand.'+side)
        hand.head=lower.tail
        hand.tail=(sign*.83,0,1.42)
        hand.parent=lower
        hand.use_connect=True
    bpy.ops.object.mode_set(mode='OBJECT')
    groups={name:body.vertex_groups.new(name=name) for name in rigdata.bones.keys()}
    for v in body.data.vertices:
        x,y,z=v.co
        weight=min(1,max(0,(abs(x)-.12)/.10)) if z>=1.22 else 0.
        if weight<1:groups['Root'].add([v.index],1-weight,'REPLACE')
        if weight:
            side='L' if x>0 else 'R'
            bone='UpperArm' if abs(x)<.45 else 'Forearm' if abs(x)<.72 else 'Hand'
            groups[bone+'.'+side].add([v.index],weight,'REPLACE')
    arm=body.modifiers.new('ArmatureMotion','ARMATURE')
    arm.object=rig
    arm.use_deform_preserve_volume=True
    collision=body.modifiers.new('BodyCollision','COLLISION')
    body.collision.thickness_outer=.006
    body.collision.thickness_inner=.001
    body.collision.cloth_friction=.5
    return rig


def set_arm_pose(rig, angle, frame=None):
    for sign,side in [(1,'L'),(-1,'R')]:
        bone=rig.pose.bones['UpperArm.'+side]
        rest=rig.data.bones[bone.name].matrix_local.to_quaternion()
        bone.rotation_mode='QUATERNION'
        bone.rotation_quaternion=rest.inverted() @ Quaternion((0,1,0),-sign*math.radians(angle)) @ rest
        if frame is not None:
            bone.keyframe_insert(data_path='rotation_quaternion',frame=frame)


def sleeve_path(rig,side):
    pose=rig.pose.bones['UpperArm.'+side]
    origin=rig.matrix_world@pose.head
    direction=(pose.tail-pose.head).normalized()
    return np.array([origin+direction*s for s in np.linspace(-.10,.71,22)],dtype=float)


def build_shirt(mat):
    n=48
    levels=list(np.linspace(.83,1.27,19))+[1.29,1.32,1.35,1.38,1.41,1.44,1.47,1.49,1.51,1.53,1.55]
    rx=np.interp(levels,[.83,1.27,1.49,1.51,1.53,1.55],[.26,.245,.24,.19,.13,.085])
    ry=np.interp(levels,[.83,1.27,1.49,1.51,1.53,1.55],[.13,.125,.115,.095,.078,.065])
    verts=[]
    for z,xr,yr in zip(levels,rx,ry):
        verts.extend([(float(xr*math.cos(2*math.pi*i/n)),float(yr*math.sin(2*math.pi*i/n)),float(z)) for i in range(n)])
    faces=[]
    zlo=levels.index(1.29)
    zhi=levels.index(1.49)
    half=6
    def port_cell(j,i):
        if not zlo<=j<zhi:return False
        return any(((i-center)%n)<half or ((center-i-1)%n)<half for center in [0,n//2])
    for j in range(len(levels)-1):
        for i in range(n):
            if port_cell(j,i):continue
            a=j*n+i; b=j*n+(i+1)%n; c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
            faces.append((a,b,c,d))
    topology={'armholes':{},'cuffs':{},'sleeve_triangles':{},'seam_pairs':[],
              'expected_openings':4,'expected_components':1,
              'units':'metres','source':'new synthetic preassembled fixture; original T-shirt not recovered',
              'seam_model':'shared-vertex welded assembly, not spring sewing',
              'rest_state':'three-dimensional preassembled A pose, not flat pattern rest lengths'}
    sleeve_sets={}
    for sign,side,center in [(1,'L',0),(-1,'R',n//2)]:
        lo,hi=center-half,center+half
        loop=[zlo*n+i%n for i in range(lo,hi+1)]
        loop.extend(j*n+hi%n for j in range(zlo+1,zhi+1))
        loop.extend(zhi*n+i%n for i in range(hi-1,lo-1,-1))
        loop.extend(j*n+lo%n for j in range(zhi-1,zlo,-1))
        topology['armholes'][side]=loop
        topology['seam_pairs'].extend([[i,i] for i in loop])
        sleeve_sets[side]=set(loop)
        prev=loop
        # Parameterize the cuff by the angle around the shoulder; preserve loop order.
        base=np.array([verts[i] for i in loop])
        angles=np.unwrap(np.arctan2(base[:,2]-1.39,base[:,1]))
        for step in range(1,9):
            t=step/8
            ring=[]
            for k,a in enumerate(angles):
                target=np.array([sign*.49,.090*math.cos(a),1.42+.090*math.sin(a)])
                p=(1-t)*base[k]+t*target
                # Bend sleeve progressively toward initial A-pose without rotating the armhole into the torso.
                theta=math.radians(-35)*t
                dx=sign*p[0]-.17; dz=p[2]-1.42
                p[0]=sign*(.17+dx*math.cos(theta)-dz*math.sin(theta))
                p[2]=1.42+dx*math.sin(theta)+dz*math.cos(theta)
                ring.append(len(verts)); verts.append(tuple(p))
            for k in range(len(loop)):
                a,b=prev[k],prev[(k+1)%len(loop)]
                c,d=ring[(k+1)%len(loop)],ring[k]
                faces.append((a,b,c,d))
            sleeve_sets[side].update(ring)
            prev=ring
        topology['cuffs'][side]=prev
    used=sorted({v for face in faces for v in face})
    remap={v:i for i,v in enumerate(used)}
    verts=[verts[i] for i in used]
    faces=[tuple(remap[i] for i in face) for face in faces]
    for kind in ['armholes','cuffs']:
        topology[kind]={side:[remap[i] for i in loop] for side,loop in topology[kind].items()}
    topology['seam_pairs']=[[remap[i],remap[j]] for i,j in topology['seam_pairs']]
    sleeve_sets={side:{remap[i] for i in ids} for side,ids in sleeve_sets.items()}
    obj=mesh_obj('TShirt_Preassembled_Welded',verts,faces,mat)
    topology['sleeve_vertices']={side:sorted(ids) for side,ids in sleeve_sets.items()}
    obj.data.calc_loop_triangles()
    for side in ['L','R']:
        topology['sleeve_triangles'][side]=[t.index for t in obj.data.loop_triangles if set(t.vertices).issubset(sleeve_sets[side])]
        for label,ids in [('Armhole',topology['armholes'][side]),('Cuff',topology['cuffs'][side])]:
            vg=obj.vertex_groups.new(name=label+'.'+side);vg.add(ids,1.0,'REPLACE')
        vg=obj.vertex_groups.new(name='Sleeve.'+side);vg.add(list(sleeve_sets[side]),1.,'REPLACE')
    pin=obj.vertex_groups.new(name='CollarSupport')
    topology['collar_vertices']=[remap[i] for i in range((len(levels)-1)*n,len(levels)*n)]
    pinned=[]  # Clothing is supported by the collider, not a world-fixed neckline.
    if pinned:pin.add(pinned,1,'REPLACE')
    cloth=obj.modifiers.new('RealClothSolver','CLOTH')
    settings=cloth.settings
    settings.quality=24
    rest_v=np.array([v.co[:] for v in obj.data.vertices], dtype=float)
    obj.data.calc_loop_triangles()
    rest_t=np.array([t.vertices[:] for t in obj.data.loop_triangles], dtype=int)
    tri=rest_v[rest_t]
    surface_area=float(.5*np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1).sum())
    areal_density_kg_m2=.18
    target_mass_kg=surface_area*areal_density_kg_m2
    per_vertex_mass_kg=target_mass_kg/len(rest_v)
    settings.mass=per_vertex_mass_kg
    if abs(settings.mass-per_vertex_mass_kg)>per_vertex_mass_kg*1e-5:
        raise RuntimeError('Blender clamped per-vertex mass, physical target not represented')
    topology['mass_model']={'assumed_areal_density_kg_m2':areal_density_kg_m2,'rest_surface_area_m2':surface_area,'total_mass_kg':target_mass_kg,'per_vertex_mass_kg':settings.mass,'distribution':'uniform vertex lumping; no measured material calibration','source':'Blender4.3.2 cloth.cc verts->mass=sim_parms->mass'}
    settings.tension_stiffness=100
    settings.compression_stiffness=100
    settings.shear_stiffness=5
    settings.bending_stiffness=.03
    settings.tension_damping=8
    settings.compression_damping=8
    settings.shear_damping=8
    settings.air_damping=3
    settings.vertex_group_mass=pin.name
    settings.pin_stiffness=1
    settings.use_dynamic_mesh=False
    settings.use_sewing_springs=False
    cc=cloth.collision_settings
    cc.use_collision=True
    cc.collision_quality=12
    cc.distance_min=.004
    cc.use_self_collision=True
    cc.self_distance_min=.002
    cc.self_friction=.1
    output_tri=obj.modifiers.new('PostClothFixedTriangulation','TRIANGULATE')
    output_tri.quad_method='FIXED'
    output_tri.ngon_method='BEAUTY'
    topology['cloth_solver_faces']='native quads, allowing distinct warp/weft and shear springs'
    topology['output_triangulation']='Triangulate AFTER Cloth, quad_method FIXED'
    topology['collar_pinned_vertices']=pinned
    topology['cloth_vertex_count']=len(verts)
    topology['rest_vertices']=[list(v.co) for v in obj.data.vertices]
    return obj,cloth,topology


def arrays_for(obj,graph):
    evaluated=obj.evaluated_get(graph)
    mesh=evaluated.to_mesh()
    mesh.calc_loop_triangles()
    verts=np.array([evaluated.matrix_world@v.co for v in mesh.vertices],dtype=float)
    tris=np.array([t.vertices[:] for t in mesh.loop_triangles],dtype=np.int32)
    evaluated.to_mesh_clear()
    return verts,tris


def aim(obj,point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()


def configure_render(scene):
    scene.render.engine='CYCLES'
    scene.cycles.samples=8
    scene.cycles.use_denoising=False
    scene.render.resolution_x=720
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.world.color=(.18,.18,.18)
    scene.view_settings.view_transform='Standard'
    bpy.ops.object.camera_add(location=(2.9,-4.5,2.4))
    camera=bpy.context.object
    camera.name='EvidenceCamera'
    camera.data.type='ORTHO'; camera.data.ortho_scale=1.95
    aim(camera,(0,0,1.15));scene.camera=camera
    for name,loc,power,size in [('Key',(2,-3,4),650,4),('Fill',(-3,-1,2.5),450,3),('Back',(1,3,3),550,3)]:
        bpy.ops.object.light_add(type='AREA',location=loc)
        light=bpy.context.object;light.name=name;light.data.energy=power;light.data.shape='DISK';light.data.size=size
        aim(light,(0,0,1.1))
    return camera


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    parser.add_argument('--frames',type=int,default=241)
    parser.add_argument('--static',action='store_true')
    parser.add_argument('--no-render',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    out=Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    (out/'frames').mkdir();(out/'renders').mkdir()
    (out/'builder-source.py').write_text(Path(__file__).read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene.frame_start=1;scene.frame_end=args.frames;scene.render.fps=24
    scene.gravity=(0,0,-9.81)
    if scene.world is None: scene.world=bpy.data.worlds.new('World')
    body=build_body(material('SyntheticBody',(.51,.32,.24)))
    rig=make_rig(body)
    shirt,cloth,topology=build_shirt(material('GarmentTeal',(.035,.37,.44)))
    for frame,angle in [(1,-30),(21,-30),(81,0),(141,65),(221,-30),(241,-30)]:
        set_arm_pose(rig,angle if not args.static else -30,frame)
    action=rig.animation_data.action
    for curve in action.fcurves:
        for key in curve.keyframe_points:key.interpolation='LINEAR'
    cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=args.frames
    cloth.point_cache.use_disk_cache=False
    camera=configure_render(scene)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    first_graph=bpy.context.evaluated_depsgraph_get();first_graph.update()
    _,first_triangles=arrays_for(shirt,first_graph)
    topology['sleeve_triangles']={side:[i for i,t in enumerate(first_triangles) if set(map(int,t)).issubset(set(ids))] for side,ids in topology['sleeve_vertices'].items()}
    topology['triangle_connectivity_sha256']=hashlib.sha256(first_triangles.astype(np.int32).tobytes()).hexdigest()
    (out/'topology.json').write_text(json.dumps(topology,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'full-arm-cloth.blend'))
    started=time.time()
    keyframes={1,21,81,141,221,args.frames}
    records=[]
    for frame in range(1,args.frames+1):
        scene.frame_set(frame)
        graph=bpy.context.evaluated_depsgraph_get();graph.update()
        cv,ct=arrays_for(shirt,graph);bv,bt=arrays_for(body,graph)
        payload={'cloth_vertices':cv,'cloth_triangles':ct,'body_vertices':bv,'body_triangles':bt,
                 'path_L':sleeve_path(rig,'L'),'path_R':sleeve_path(rig,'R')}
        np.savez_compressed(out/'frames'/f'frame-{frame:04d}.npz',**payload)
        records.append({'frame':frame,'finite':bool(np.isfinite(cv).all()),
                        'max_abs_coordinate_m':float(np.abs(cv).max()),
                        'elapsed_s':round(time.time()-started,3)})
        if frame in keyframes or frame%20==0:
            print('SIM_FRAME',frame,records[-1],flush=True)
        if not args.no_render and frame in keyframes:
            for name,loc in [('front',(0,-4,1.5)),('oblique',(2.9,-4.5,2.4)),('back',(0,4,1.5))]:
                camera.location=loc;aim(camera,(0,0,1.16))
                scene.render.filepath=str(out/'renders'/f'{frame:04d}-{name}.png')
                bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'full-arm-cloth.blend'))
    config={'fixture':'synthetic_full_arm_preassembled_v2','blender_version':bpy.app.version_string,
            'frames':args.frames,'fps':24,'trajectory':'A(-30deg) -> T(0deg) -> raised(65deg) -> A',
            'cloth_quality_steps_per_frame':cloth.settings.quality,
            'mass_model':topology['mass_model'],
            'body_weight_model':'Root weight 1-armweight; sums1; no abrupt partialweight normalization',
            'garment_support':'unconstrained real Cloth, no garment pins; only mannequin is animated',
            'cloth_solver_faces':topology['cloth_solver_faces'],
            'output_triangulation':topology['output_triangulation'],
            'material_settings':{'tension':cloth.settings.tension_stiffness,'compression':cloth.settings.compression_stiffness,'shear':cloth.settings.shear_stiffness,'bending':cloth.settings.bending_stiffness},
            'contact_friction':{'body':body.collision.cloth_friction,'self':cloth.collision_settings.self_friction},
            'self_distance_min_m':cloth.collision_settings.self_distance_min,
            'body_collision_margin_m':body.collision.thickness_outer,
            'cloth_collision_margin_m':cloth.collision_settings.distance_min,
            'collision_quality':cloth.collision_settings.collision_quality,
            'simulation_seconds':time.time()-started,'sewing_springs':False,
            'pinned_vertices':len(topology['collar_pinned_vertices']),
            'cloth_vertices':len(topology['rest_vertices']),
            'preassembled':True,'material_calibrated':False,'human_calibrated':False,
            'original_scene_recovered':False,'frame_cache':'NPZ evaluated geometry; packed blend cache independently checked separately',
            'limits':['not the original T-shirt','no 2D-to-3D sewing validation','no physical fit proof','discrete frame sampling']}
    (out/'run-config.json').write_text(json.dumps(config,indent=2))
    (out/'execution-log.json').write_text(json.dumps(records,indent=2))
    print('SIMULATION_EXECUTED',json.dumps(config),flush=True)


if __name__=='__main__':main()
