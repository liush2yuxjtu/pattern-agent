import bpy, math, json, os, bmesh, argparse, sys
parser=argparse.ArgumentParser()
parser.add_argument("--mesh",default="data/tshirt_mesh.json")
parser.add_argument("--output",default="output")
args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
from mathutils import Vector
OUT=args.output
os.makedirs(OUT,exist_ok=True)
data=json.load(open(args.mesh))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
cloth=bpy.data.materials.new('暖白针织面料 假定材质');cloth.use_nodes=True
n=cloth.node_tree.nodes;l=cloth.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.82,.79,.72,1);bs.inputs['Roughness'].default_value=.68;bs.inputs['Sheen Weight'].default_value=.24
noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1050;noise.inputs['Detail'].default_value=2
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.00014;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
seammat=cloth.copy();seammat.name='同色车缝线';seammat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.70,.67,.60,1)
garment=[]
def mesh(name,verts,faces,solid=True):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);ob.data.materials.append(cloth)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=True
 if solid:
  m=ob.modifiers.new('针织面料厚度 示意','SOLIDIFY');m.thickness=.0008;m.offset=0
 garment.append(ob);return ob
for name,p in data['panels'].items():mesh('前身 纸样轮廓重建' if name=='front' else '后身 纸样轮廓重建',p['verts'],p['faces'])
def curve(name,pts,r=.0005,mat=seammat):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=2;cu.bevel_depth=r;cu.bevel_resolution=2
 sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for p,co in zip(sp.points,pts):p.co=(*co,1)
 ob=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(ob);cu.materials.append(mat);garment.append(ob);return ob
paths=data['paths']
def bridge(name,a,b):
 # Match the end nearest the first point.
 if (Vector(a[0])-Vector(b[-1])).length<(Vector(a[0])-Vector(b[0])).length:b=b[::-1]
 verts=a+b;N=len(a);faces=[(i,i+1,N+i+1,N+i) for i in range(N-1)];return mesh(name,verts,faces)
for side in ['left','right']:
 bridge('侧缝连接 '+side,paths['front_'+side+'_side'],paths['back_'+side+'_side'])
 bridge('肩部连接 '+side,paths['front_'+side+'_shoulder'],paths['back_'+side+'_shoulder'])
 curve('肩缝 '+side,paths['front_'+side+'_shoulder'],.00065)
 # Sleeve top boundary follows the front and back armhole curves derived from DXF.
 a=paths['front_'+side+'_arm'];b=paths['back_'+side+'_arm']
 ring=a+b[::-1];N=len(ring);sgn=1 if side=='right' else -1
 center=Vector((sgn*.174,0,1.438));axis=Vector((sgn*.23,-.015,-.974)).normalized();B=Vector((0,1,0));C=axis.cross(B).normalized()
 angles=[]
 for p in ring:
  v=Vector(p)-center;angles.append(math.atan2(v.dot(C),v.dot(B)))
 verts=[];R=85
 for j in range(R):
  t=j/(R-1);dist=.515*t
  ctr=center+axis*dist
  ctr.y-=.006*math.sin(t*math.pi)
  width=data['sleeve_widths'][min(59,int(t*59))]/1000
  radius=width/(2*math.pi)
  w=min(1,t/.26);w=w*w*(3-2*w)
  for k,angle in enumerate(angles):
   regular=ctr+radius*(math.cos(angle)*B+math.sin(angle)*C)
   start=Vector(ring[k])+axis*dist
   p=start.lerp(regular,w)
   wrinkle=.0013*math.sin(t*72+angle*2)*math.exp(-((t-.57)/.15)**2)
   p+= (math.cos(angle)*B+math.sin(angle)*C)*wrinkle
   verts.append(tuple(p))
 faces=[]
 for j in range(R-1):
  for k in range(N):faces.append((j*N+k,j*N+(k+1)%N,(j+1)*N+(k+1)%N,(j+1)*N+k))
 mesh('长袖 '+side,verts,faces)
 curve('袖窿接缝 '+side,ring+[ring[0]],.0007)
 for j in [R-2,R-4]:curve('袖口双针线 '+side,[verts[j*N+k] for k in range(N)]+[verts[j*N]],.00035)
# Narrow neckband follows actual front/back neck contours.
neck=paths['front_neck']+paths['back_neck'][::-1];N=len(neck);vv=[]
for j in range(5):
 for p in neck:
  v=Vector(p);rad=Vector((v.x,v.y,0));rad.normalize();v+=rad*(j/4*.010);v.z-=j/4*.009;vv.append(tuple(v))
ff=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(4) for i in range(N)]
mesh('圆领领条 依领口曲线近似',vv,ff)
curve('领口车缝线',[vv[4*N+i] for i in range(N)]+[vv[4*N]],.0004)
for side in ['front','back']:
 for dz in [.004,.007]:
  pts=[]
  for p in paths[side+'_hem']:
   v=list(p);v[2]+=dz;v[1]+=-.0006 if side=='front' else .0006;pts.append(v)
  curve('下摆双针线 '+side,pts,.00035)
# Render stage.
stage=bpy.data.materials.new('摄影背景');stage.diffuse_color=(.31,.33,.34,1)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.83));floor=bpy.context.object;floor.name='摄影地面';floor.data.materials.append(stage)
world=bpy.context.scene.world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.58,.62,1);world.node_tree.nodes['Background'].inputs[1].default_value=.30
def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
def light(name,loc,power,size,target=(0,0,1.25)):
 bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object;ob.name=name;ob.data.energy=power;ob.data.shape='DISK';ob.data.size=size;aim(ob,target)
light('主柔光',(-1,-1.4,2.6),110,1.5);light('填充光',(1,-.6,1.8),55,1.0);light('轮廓光',(.2,1.2,2.1),140,1.1)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='展示相机';cam.data.type='ORTHO';cam.data.ortho_scale=.84;bpy.context.scene.camera=cam
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=False
scene.render.resolution_x=1100;scene.render.resolution_y=1300;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.render.film_transparent=False
scene['说明']='根据用户DXF缝合轮廓进行参数化三维重建。人体厚度、摆片方式及面料物性是假定值。未进行经过校准的布料仿真，不用于合身性或生产验证。'
scene['来源']='女紧身款T恤.dxf 中码'
# Save portable editable scene and export the garment only.
cam.location=(1,-2.5,1.8);aim(cam,(0,0,1.255))
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/女士紧身长袖上衣_三维示意.blend')
bpy.ops.object.select_all(action='DESELECT')
for ob in garment:ob.select_set(True)
try:bpy.ops.export_scene.gltf(filepath=OUT+'/女士紧身长袖上衣_三维示意.glb',export_format='GLB',use_selection=True,export_apply=True)
except Exception as e:print('GLB_EXPORT',str(e))
views={'front':((0,-3,1.42),(0,0,1.25)),'three_quarter':((1.8,-3,1.65),(0,0,1.25)),'back':((0,3,1.42),(0,0,1.25))}
for name,(loc,target) in views.items():
 cam.location=loc;aim(cam,target);scene.render.filepath=OUT+'/'+name+'.png';bpy.ops.render.render(write_still=True);print('RENDER_DONE',name,flush=True)
print('ALL_DONE',flush=True)
