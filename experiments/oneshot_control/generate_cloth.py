"""One-shot single-mesh T-shirt control; no simulation, sewing, or body import.

The four open boundaries are the neck, hem and cuffs. Separate analytic solids
define a T-shaped garment cavity; its boundary is tessellated directly.
"""
import argparse,json,math
from pathlib import Path
import sys
import bpy


def make_cloth(output):
    def subdivide(knots):
        result=[]
        for a,b in zip(knots[:-1],knots[1:]):
            n=max(1,math.ceil((b-a)/.04));result.extend(a+(b-a)*i/n for i in range(n))
        return result+[knots[-1]]
    xs=subdivide([-.53,-.25,-.10,.10,.25,.53])
    ys=subdivide([-.14,-.07,.07,.14])
    zs=subdivide([.81,1.27,1.53])
    occupied=set()
    for i in range(len(xs)-1):
        for j in range(len(ys)-1):
            for k in range(len(zs)-1):
                x,z=(xs[i]+xs[i+1])/2,(zs[k]+zs[k+1])/2
                if abs(x)<.25 or z>1.27:occupied.add((i,j,k))
    vertices=[];faces=[];lookup={}
    def emit(points):
        face=[]
        for p in points:
            key=tuple(round(v,12) for v in p)
            if key not in lookup:lookup[key]=len(vertices);vertices.append(key)
            face.append(lookup[key])
        faces.append(face)
    def opening(points):
        x,y,z=(sum(p[d] for p in points)/4 for d in range(3))
        return (abs(z-.81)<1e-10 or abs(abs(x)-.53)<1e-10 or
                (abs(z-1.53)<1e-10 and abs(x)<.10 and abs(y)<.07))
    for i,j,k in sorted(occupied):
        a,b=xs[i:i+2];c,d=ys[j:j+2];e,f=zs[k:k+2]
        sides=[((-1,0,0),[(a,c,e),(a,c,f),(a,d,f),(a,d,e)]),
               ((1,0,0),[(b,c,e),(b,d,e),(b,d,f),(b,c,f)]),
               ((0,-1,0),[(a,c,e),(b,c,e),(b,c,f),(a,c,f)]),
               ((0,1,0),[(a,d,e),(a,d,f),(b,d,f),(b,d,e)]),
               ((0,0,-1),[(a,c,e),(a,d,e),(b,d,e),(b,c,e)]),
               ((0,0,1),[(a,c,f),(b,c,f),(b,d,f),(a,d,f)])]
        for (di,dj,dk),points in sides:
            if (i+di,j+dj,k+dk) not in occupied and not opening(points):emit(points)
    triangles=[t for face in faces for t in [(face[0],face[1],face[2]),(face[0],face[2],face[3])]]
    armholes={};cuffs={};sleeves={}
    for sign,side in [(1,'L'),(-1,'R')]:
        def ring(x):
            ids=[i for i,p in enumerate(vertices) if abs(p[0]-x)<1e-9 and 1.27-1e-9<=p[2]<=1.53+1e-9
                 and (abs(abs(p[1])-.14)<1e-9 or abs(p[2]-1.27)<1e-9 or abs(p[2]-1.53)<1e-9)]
            return sorted(ids,key=lambda i:math.atan2(vertices[i][2]-1.40,vertices[i][1]))
        armholes[side]=ring(sign*.25);cuffs[side]=ring(sign*.53)
        sleeves[side]=[i for i,t in enumerate(triangles) if all(
            sign*vertices[v][0]>=.25-1e-9 and vertices[v][2]>=1.27-1e-9 for v in t)]
    topology={'armholes':armholes,'cuffs':cuffs,'sleeve_triangles':sleeves,
              'seam_pairs':[[i,i] for side in ['L','R'] for i in armholes[side]],
              'expected_components':1,'expected_openings':4,'rest_vertices':vertices,
              'units':'metres','seam_model':'direct shared-vertex construction; no sewing process',
              'construction':'new extruded rectilinear T-shaped open boundary, no prior garment mesh',
              'independent_control_dimensions':{'armhole_abs_x':.25,'cuff_abs_x':.53,'y_min':-.14,'y_max':.14,'sleeve_z_min':1.27,'sleeve_z_max':1.53}}
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mesh=bpy.data.meshes.new('OneShotTShirt');mesh.from_pydata(vertices,[],triangles);mesh.update()
    obj=bpy.data.objects.new('OneShotTShirt',mesh);bpy.context.collection.objects.link(obj)
    obj['asset_contract']=json.dumps(topology)
    for kind in ['armholes','cuffs']:
        for side,indices in topology[kind].items():
            group=obj.vertex_groups.new(name=kind+'.'+side);group.add(indices,1.,'REPLACE')
    mat=bpy.data.materials.new('Garment');mat.diffuse_color=(.025,.40,.46,1);mesh.materials.append(mat)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise FileExistsError('Use a new asset filename')
    bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
    with output.with_suffix('.obj').open('w') as stream:
        stream.write('# ASSET_CONTRACT '+json.dumps(topology,separators=(',',':'))+'\n')
        stream.write('o OneShotTShirt\n')
        for v in vertices:stream.write('v '+' '.join(f'{x:.12g}' for x in v)+'\n')
        for t in triangles:stream.write('f '+' '.join(str(i+1) for i in t)+'\n')
    print('ONE_SHOT_CLOTH',json.dumps({'vertices':len(vertices),'triangles':len(triangles),'blend':str(output),'cloth_simulation':False,'external_assets':0}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);make_cloth(args.out)
