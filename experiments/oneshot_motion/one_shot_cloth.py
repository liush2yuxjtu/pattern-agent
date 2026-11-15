"""One authored file, one generation: preassembled short-sleeve T-shirt.
blender -b -t 2 --python one_shot_cloth.py -- --model model/model.blend --out cloth
No verifier is imported. Model geometry is read from the standalone model.blend.
This is a synthetic 3D control, not a measured paper pattern or sewing experiment.
"""
import argparse,hashlib,json,math,sys,time
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector

def mesh_arrays(ob):
    graph=bpy.context.evaluated_depsgraph_get();ob=ob.evaluated_get(graph);mesh=ob.to_mesh();mesh.calc_loop_triangles()
    v=np.array([ob.matrix_world@x.co for x in mesh.vertices],dtype=float);t=np.array([x.vertices[:] for x in mesh.loop_triangles],dtype=np.int32)
    ob.to_mesh_clear();return v,t

def generate(model,out):
    bpy.ops.wm.open_mainfile(filepath=str(model));scene=bpy.context.scene
    spec=json.loads(scene['ModelSpec']);body=bpy.data.objects['OneShotMannequin'];rig=bpy.data.objects['OneShotRig']
    n=48;levels=list(np.linspace(.85,1.25,17))+[1.28,1.31,1.34,1.37,1.40,1.43,1.46,1.49,1.52,1.55]
    rx=np.interp(levels,[.85,1.25,1.49,1.52,1.55],[.270,.255,.245,.150,.085])
    ry=np.interp(levels,[.85,1.25,1.49,1.52,1.55],[.145,.140,.132,.100,.075])
    verts=[(float(x*math.cos(2*math.pi*i/n)),float(y*math.sin(2*math.pi*i/n)),float(z)) for z,x,y in zip(levels,rx,ry) for i in range(n)]
    faces=[];regions=[];lo=levels.index(1.25);hi=levels.index(1.49);half=6
    for j in range(len(levels)-1):
        for i in range(n):
            if lo<=j<hi and any(((i-c)%n)<half or ((c-i-1)%n)<half for c in [0,n//2]):continue
            a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
            faces.extend([(a,b,c),(a,c,d)]);regions.extend(['torso','torso'])
    top={'units':'metres','armholes':{},'cuffs':{},'sleeve_triangles':{},'seam_pairs':[],'expected_openings':4,'expected_components':1,'preassembled':True,'seam_model':'shared vertices; not spring sewing','rest_state':'3D preassembled A pose','generation_count':1}
    for sign,side,center in [(1,'L',0),(-1,'R',n//2)]:
        left,right=center-half,center+half
        ring=[lo*n+i%n for i in range(left,right+1)]+[j*n+right%n for j in range(lo+1,hi+1)]+[hi*n+i%n for i in range(right-1,left-1,-1)]+[j*n+left%n for j in range(hi-1,lo,-1)]
        top['armholes'][side]=ring.copy();top['seam_pairs'] += [[i,i] for i in ring]
        base=np.array([verts[i] for i in ring]);shoulder=np.array([sign*.17,0,1.42])
        theta=math.radians(-30);axis=np.array([sign*math.cos(theta),0,math.sin(theta)])
        u=np.array([0,1,0]);w=np.array([-sign*math.sin(theta),0,math.cos(theta)])
        angle=np.unwrap(np.arctan2((base-shoulder)@w,(base-shoulder)@u))
        cuff=shoulder+.29*axis;prev=ring
        for step in range(1,9):
            t=step/8;curr=[]
            for k,a in enumerate(angle):
                target=cuff+.096*(math.cos(a)*u+math.sin(a)*w)
                point=(1-t)*base[k]+t*target;curr.append(len(verts));verts.append(tuple(point))
            for k in range(len(ring)):
                a,b=prev[k],prev[(k+1)%len(ring)];c,d=curr[(k+1)%len(ring)],curr[k]
                faces.extend([(a,b,c),(a,c,d)]);regions.extend([side,side])
            prev=curr
        top['cuffs'][side]=prev
    used=sorted(set(i for f in faces for i in f));mapping={v:i for i,v in enumerate(used)}
    verts=[verts[i] for i in used];faces=[tuple(mapping[i] for i in f) for f in faces]
    for kind in ['armholes','cuffs']:top[kind]={s:[mapping[i] for i in loop] for s,loop in top[kind].items()}
    top['seam_pairs']=[[mapping[i],mapping[j]] for i,j in top['seam_pairs']]
    mesh=bpy.data.meshes.new('OneShotShirtSurface');mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    ob=bpy.data.objects.new('OneShotTShirt',mesh);bpy.context.collection.objects.link(ob)
    mat=bpy.data.materials.new('Shirt teal');mat.diffuse_color=(.025,.41,.48,1);mesh.materials.append(mat)
    top['sleeve_triangles']={s:[i for i,r in enumerate(regions) if r==s] for s in ['L','R']}
    for kind in ['armholes','cuffs']:
        for s,ids in top[kind].items():g=ob.vertex_groups.new(name=kind+'.'+s);g.add(ids,1,'REPLACE')
    rest=np.array([v.co[:] for v in mesh.vertices],dtype=float);top['rest_vertices']=rest.tolist()
    tri=rest[np.array(faces)];area=float(.5*np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1).sum())
    mod=ob.modifiers.new('Blender Cloth','CLOTH');s=mod.settings;s.quality=20;s.mass=area*.18/len(rest)
    s.tension_stiffness=35;s.compression_stiffness=35;s.shear_stiffness=15;s.bending_stiffness=.5
    s.tension_damping=8;s.compression_damping=8;s.shear_damping=8;s.air_damping=3;s.use_sewing_springs=False
    c=mod.collision_settings;c.use_collision=True;c.collision_quality=8;c.distance_min=.004;c.use_self_collision=True;c.self_distance_min=.003;c.self_friction=.5
    mod.point_cache.frame_start=1;mod.point_cache.frame_end=121;mod.point_cache.use_disk_cache=False
    top['mass_model']={'assumed_density_kg_m2':.18,'area_m2':area,'total_mass_kg':area*.18,'mass_per_vertex_kg':s.mass,'calibrated':False}
    top['pinned_vertices']=[];top['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out.mkdir(parents=True,exist_ok=False);(out/'frames').mkdir();(out/'topology.json').write_text(json.dumps(top,indent=2))
    scene.gravity=(0,0,-9.81);scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'cloth.blend'),compress=True)
    start=time.monotonic()
    for frame in range(1,122):
        scene.frame_set(frame);bpy.context.view_layer.update();cv,ct=mesh_arrays(ob);bv,bt=mesh_arrays(body)
        data=dict(cloth_vertices=cv,cloth_triangles=ct,body_vertices=bv,body_triangles=bt,frame=frame)
        for side in ['L','R']:
            bone=rig.pose.bones['UpperArm.'+side];origin=rig.matrix_world@bone.head;direction=(bone.tail-bone.head).normalized()
            data['path_'+side]=np.array([origin+direction*x for x in np.linspace(-.10,.71,22)])
        np.savez_compressed(out/'frames'/f'frame-{frame:04d}.npz',**data)
        if frame==1 or frame%10==0:print('CLOTH_FRAME',frame,'seconds',round(time.monotonic()-start,2),flush=True)
    (out/'execution.json').write_text(json.dumps({'generation_count':1,'frames':121,'solver':'Blender '+bpy.app.version_string,'seconds':time.monotonic()-start,'source_sha256':top['source_sha256'],'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'physical_fit':'NOT_RUN'},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--out',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);generate(Path(a.model).resolve(),Path(a.out).resolve())
