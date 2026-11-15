"""One-shot standalone full-body control asset. Run in Blender 4.3.2.

This analytic block mannequin deliberately has simple independently checkable
geometry. It is not an anthropometric or realistic-fit avatar. No garment or
legacy generator is imported. The .blend and OBJ each contain one body mesh.
"""
import argparse,json,math
from pathlib import Path
import sys
import bpy


def make_model(output):
    # name, xmin,xmax,ymin,ymax,zmin,zmax (metres); overlapping solids are united.
    boxes=[('torso',-.18,.18,-.09,.09,.84,1.48),
           ('pelvis',-.16,.16,-.10,.10,.72,.94),
           ('neck',-.05,.05,-.055,.055,1.45,1.62),
           ('head',-.08,.08,-.075,.075,1.59,1.79)]
    for sign,side in [(1,'L'),(-1,'R')]:
        def add(name,x0,x1,y,z0,z1):
            a,b=sorted((sign*x0,sign*x1));boxes.append((name+'.'+side,a,b,-y,y,z0,z1))
        add('upper_arm',.15,.48,.055,1.36,1.48)
        add('forearm',.47,.77,.047,1.365,1.475)
        add('hand',.76,.84,.055,1.365,1.475)
        add('leg',.035,.145,.07,.075,.78)
        a,b=sorted((sign*.035,sign*.145));boxes.append(('foot.'+side,a,b,-.13,.08,.025,.12))
    axes=[]
    for dim in range(3):
        edges=sorted({b[1+dim*2+k] for b in boxes for k in [0,1]})
        values=[]
        for lo,hi in zip(edges[:-1],edges[1:]):
            n=max(1,math.ceil((hi-lo)/.05));values.extend(lo+(hi-lo)*i/n for i in range(n))
        axes.append(values+[edges[-1]])
    xs,ys,zs=axes
    occupied=set()
    for i in range(len(xs)-1):
        for j in range(len(ys)-1):
            for k in range(len(zs)-1):
                x,y,z=(xs[i]+xs[i+1])/2,(ys[j]+ys[j+1])/2,(zs[k]+zs[k+1])/2
                if any(b[1]<x<b[2] and b[3]<y<b[4] and b[5]<z<b[6] for b in boxes):occupied.add((i,j,k))
    vertices=[];faces=[];ids={}
    def emit(points):
        face=[]
        for point in points:
            key=tuple(round(v,12) for v in point)
            if key not in ids:ids[key]=len(vertices);vertices.append(key)
            face.append(ids[key])
        faces.append(face)
    for i,j,k in sorted(occupied):
        a,b=xs[i:i+2];c,d=ys[j:j+2];e,f=zs[k:k+2]
        candidates=[((-1,0,0),[(a,c,e),(a,c,f),(a,d,f),(a,d,e)]),
                    ((1,0,0),[(b,c,e),(b,d,e),(b,d,f),(b,c,f)]),
                    ((0,-1,0),[(a,c,e),(b,c,e),(b,c,f),(a,c,f)]),
                    ((0,1,0),[(a,d,e),(a,d,f),(b,d,f),(b,d,e)]),
                    ((0,0,-1),[(a,c,e),(a,d,e),(b,d,e),(b,c,e)]),
                    ((0,0,1),[(a,c,f),(b,c,f),(b,d,f),(a,d,f)])]
        for (di,dj,dk),points in candidates:
            if (i+di,j+dj,k+dk) not in occupied:emit(points)
    paths={side:[[sign*s,0.,1.42] for s in [.07,.17,.30,.47,.60,.76,.84]]
           for sign,side in [(1,'L'),(-1,'R')]}
    contract={'asset':'independent analytic full-body T-pose mannequin','units':'metres',
              'construction':'boundary of a union of axis-aligned solids',
              'closed_expected':True,'components_expected':1,
              'boxes':[{'name':b[0],'bounds':list(b[1:])} for b in boxes],
              'path_L':paths['L'],'path_R':paths['R'],
              'anatomy':'head neck shoulders upper arms elbows forearms hands pelvis legs feet',
              'calibrated_human':False,'not_physics_evidence':True}
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mesh=bpy.data.meshes.new('OneShotFullBody');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('OneShotFullBody',mesh);bpy.context.collection.objects.link(obj)
    obj['asset_contract']=json.dumps(contract)
    mat=bpy.data.materials.new('Body');mat.diffuse_color=(.57,.40,.30,1);mesh.materials.append(mat)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise FileExistsError('Use a new asset filename')
    bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
    # OBJ is an optional transparent, dependency-free equivalent of this asset.
    with output.with_suffix('.obj').open('w') as stream:
        stream.write('# ASSET_CONTRACT '+json.dumps(contract,separators=(',',':'))+'\n')
        stream.write('o OneShotFullBody\n')
        for v in vertices:stream.write('v '+' '.join(f'{x:.12g}' for x in v)+'\n')
        for face in faces:stream.write('f '+' '.join(str(i+1) for i in face)+'\n')
    print('ONE_SHOT_MODEL',json.dumps({'vertices':len(vertices),'quads':len(faces),'blend':str(output),'external_assets':0}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);make_model(args.out)
