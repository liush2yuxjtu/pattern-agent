"""One authored file, one generation: full synthetic mannequin with arm motion.
blender -b -t 2 --python one_shot_model.py -- --out model
No garment geometry or verification decisions are used by this generator.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector,Quaternion

def sphere(name,center,scale,parts):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=center)
    ob=bpy.context.object;ob.name=name;ob.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);parts.append(ob)

def limb(name,start,end,r0,r1,parts):
    a,b=Vector(start),Vector(end)
    bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=r0,radius2=r1,depth=(b-a).length,location=(a+b)/2)
    ob=bpy.context.object;ob.name=name;ob.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);parts.append(ob)
    sphere(name+' joint',a,(r0,r0,r0),parts);sphere(name+' end',b,(r1,r1,r1),parts)

def generate(out):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    parts=[]
    sphere('Ribcage',(0,0,1.28),(.180,.100,.235),parts)
    sphere('Abdomen',(0,0,1.04),(.145,.094,.23),parts)
    sphere('Hips',(0,0,.85),(.170,.105,.14),parts)
    limb('Neck',(0,0,1.43),(0,0,1.58),.054,.050,parts)
    sphere('Head',(0,0,1.68),(.076,.080,.11),parts)
    for sign,side in [(1,'L'),(-1,'R')]:
        limb('Upper arm '+side,(sign*.17,0,1.42),(sign*.47,0,1.42),.060,.046,parts)
        limb('Forearm '+side,(sign*.47,0,1.42),(sign*.74,0,1.42),.046,.032,parts)
        sphere('Hand '+side,(sign*.785,0,1.42),(.070,.036,.027),parts)
        limb('Thigh '+side,(sign*.087,0,.84),(sign*.094,0,.47),.076,.054,parts)
        limb('Shin '+side,(sign*.094,0,.47),(sign*.098,0,.10),.054,.035,parts)
        sphere('Foot '+side,(sign*.098,-.034,.065),(.045,.10,.040),parts)
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
    body=bpy.context.object;body.name='OneShotMannequin'
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    mod=body.modifiers.new('Union','REMESH');mod.mode='VOXEL';mod.voxel_size=.020
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=body.modifiers.new('Surface smoothing','SMOOTH');mod.factor=.3;mod.iterations=2
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
    mat=bpy.data.materials.new('Mannequin clay');mat.diffuse_color=(.55,.40,.31,1);body.data.materials.append(mat)
    data=bpy.data.armatures.new('OneShotSkeleton');rig=bpy.data.objects.new('OneShotRig',data);bpy.context.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    r=data.edit_bones.new('Root');r.head=(0,0,.80);r.tail=(0,0,1.10)
    for sign,side in [(1,'L'),(-1,'R')]:
        u=data.edit_bones.new('UpperArm.'+side);u.head=(sign*.17,0,1.42);u.tail=(sign*.47,0,1.42)
        l=data.edit_bones.new('Forearm.'+side);l.head=u.tail;l.tail=(sign*.74,0,1.42);l.parent=u;l.use_connect=True
        h=data.edit_bones.new('Hand.'+side);h.head=l.tail;h.tail=(sign*.83,0,1.42);h.parent=l;h.use_connect=True
    bpy.ops.object.mode_set(mode='OBJECT')
    groups={n:body.vertex_groups.new(name=n) for n in data.bones.keys()}
    for v in body.data.vertices:
        x,y,z=v.co;w=min(1,max(0,(abs(x)-.12)/.10)) if z>=1.22 else 0
        if w<1:groups['Root'].add([v.index],1-w,'REPLACE')
        if w:
            side='L' if x>0 else 'R';n='UpperArm' if abs(x)<.45 else 'Forearm' if abs(x)<.72 else 'Hand'
            groups[n+'.'+side].add([v.index],w,'REPLACE')
    mod=body.modifiers.new('Arm motion','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
    body.modifiers.new('Cloth collider','COLLISION');body.collision.thickness_outer=.005;body.collision.thickness_inner=.001;body.collision.cloth_friction=.5
    poses=[(1,-30),(11,-30),(41,0),(71,65),(111,-30),(121,-30)]
    for frame,angle in poses:
        for sign,side in [(1,'L'),(-1,'R')]:
            bone=rig.pose.bones['UpperArm.'+side];rest=data.bones[bone.name].matrix_local.to_quaternion()
            bone.rotation_mode='QUATERNION';bone.rotation_quaternion=rest.inverted()@Quaternion((0,1,0),-sign*math.radians(angle))@rest
            bone.keyframe_insert('rotation_quaternion',frame=frame)
    for curve in rig.animation_data.action.fcurves:
        for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.frame_end=121;scene.render.fps=24;scene.frame_set(1)
    scene['Synthetic mannequin']='Uncalibrated dimensions; complete head, torso, arms, hands, legs, feet.'
    out.mkdir(parents=True,exist_ok=False)
    spec={'units':'metres','shoulders':{'L':[.17,0,1.42],'R':[-.17,0,1.42]},'motion_keyframes':poses,'frames':121,'fps':24,'measured_human':False,'generation_count':1,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    scene['ModelSpec']=json.dumps(spec);(out/'model-spec.json').write_text(json.dumps(spec,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'model.blend'),compress=True)
    print('MODEL_GENERATED',json.dumps(spec),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);generate(Path(a.out).resolve())
