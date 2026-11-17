"""Bounded, profile-gated DXF to visual GLB. No Blender or persisted jobs required."""
from __future__ import annotations
import hashlib, json, math, struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial import Delaunay, QhullError

ENGINE_VERSION = '1.0.0'
MAX_INPUT_BYTES = 512 * 1024
MAX_VERTICES = 6000
MAX_COORDINATE = 1e7
UNIT_FACTORS = {'mm': 1.0, 'cm': 10.0, 'inch': 25.4}

class ConversionError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message); self.code=code; self.status=status

@dataclass(frozen=True)
class Converted:
    glb: bytes
    report: dict

@lru_cache(maxsize=1)
def get_profile():
    return json.loads(Path(__file__).with_name('profile.json').read_text())

def parse_dxf(data: bytes):
    if not data or len(data)>MAX_INPUT_BYTES:
        raise ConversionError('INPUT_SIZE', '文件为空或超过512千字节限制。',413 if data else 400)
    try:
        try: text=data.decode('utf-8-sig')
        except UnicodeDecodeError: text=data.decode('gb18030')
        lines=text.splitlines()
        if len(lines)%2: raise ValueError('incomplete pair')
        pairs=[(int(lines[i].strip()),lines[i+1].strip()) for i in range(0,len(lines),2)]
    except (ValueError,UnicodeDecodeError) as exc:
        raise ConversionError('INVALID_DXF','需要完整的文本格式二维纸样文件。',400) from exc
    if not pairs or pairs[-1]!=(0,'EOF') or (0,'SECTION') not in pairs:
        raise ConversionError('INVALID_DXF','文件缺少完整的图形段或结束标记。',400)
    entities=[]
    for code,value in pairs:
        if code==0: entities.append([value,{}])
        elif entities: entities[-1][1][code]=value
    polylines=[]; current=None; count=0; texts=[]
    try:
        for kind,a in entities:
            if kind=='POLYLINE':
                if current is not None: raise ValueError('unclosed polyline')
                current=[]
            elif kind=='VERTEX':
                if current is None: raise ValueError('orphan vertex')
                point=[float(a[10]),float(a[20])]
                if not all(math.isfinite(v) and abs(v)<=MAX_COORDINATE for v in point):raise ValueError('invalid coordinate')
                current.append(point); count+=1
                if count>MAX_VERTICES:raise ConversionError('VERTEX_LIMIT','纸样顶点数超过本接口限制。',413)
            elif kind=='SEQEND':
                if current is None or len(current)<2:raise ValueError('invalid sequence')
                polylines.append(np.asarray(current,dtype=np.float64)); current=None
                if len(polylines)>256:raise ConversionError('PROFILE_REQUIRED','纸样结构不属于当前已验证模板。')
            elif kind=='TEXT': texts.append(a.get(1,''))
        if current is not None:raise ValueError('unclosed final polyline')
    except (ValueError,KeyError) as exc:
        raise ConversionError('INVALID_GEOMETRY','纸样线段不完整，或包含无效坐标。',400) from exc
    return polylines,{'polylines':len(polylines),'vertices':count,'text_entities':len(texts)}

def sample(q,n=32):
    d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
    unique=np.r_[True,np.diff(d)>1e-10];d=d[unique];q=q[unique]
    if len(d)<2 or d[-1]<1e-8:raise ConversionError('DEGENERATE_LINE','存在零长度线段，无法匹配纸样。')
    return np.array([np.interp(np.linspace(0,d[-1],n),d,q[:,j]) for j in range(q.shape[1])]).T

def register(polylines,units,profile_id):
    cfg=get_profile()
    if profile_id!=cfg['id']:raise ConversionError('UNKNOWN_PROFILE','未知纸样模板。')
    if units not in UNIT_FACTORS:raise ConversionError('UNITS_REQUIRED','必须明确指定毫米、厘米或英寸。',400)
    if len(polylines)!=cfg['expected_polylines']:
        raise ConversionError('PROFILE_REQUIRED','当前仅支持已验证上衣的126条多段线导出结构；其他纸样需要新的裁片与缝合配置。')
    ref=[np.asarray(p,dtype=float) for p in cfg['reference']]
    pts=np.vstack(polylines)*UNIT_FACTORS[units]; rp=np.vstack(ref)
    lo,hi=pts.min(0),pts.max(0);rlo,rhi=rp.min(0),rp.max(0)
    if np.any(hi-lo<1e-6):raise ConversionError('INVALID_EXTENT','纸样范围退化。')
    ratios=(hi-lo)/(rhi-rlo);scale=float(np.mean(ratios))
    if not cfg['min_scale']<=scale<=cfg['max_scale']:
        raise ConversionError('UNITS_OR_SCALE','纸样的实际尺寸超出此模板支持范围，请核对单位或选择适用模板。')
    if float(np.max(np.abs(ratios/scale-1)))>.025:
        raise ConversionError('PROFILE_REQUIRED','纸样布局或横纵比例与已验证模板不一致。')
    center=(lo+hi)/2; rcenter=(rlo+rhi)/2
    normalized=[(p*UNIT_FACTORS[units]-center)/scale+rcenter for p in polylines]
    a=np.stack([sample(p) for p in ref]);b=np.stack([sample(p) for p in normalized])
    normal=np.linalg.norm(a[:,None,:,:]-b[None,:,:,:],axis=-1)
    reverse=np.linalg.norm(a[:,None,:,:]-b[None,:,::-1,:],axis=-1)
    costs=np.minimum(normal.mean(-1),reverse.mean(-1))
    row,col=linear_sum_assignment(costs)
    result=[None]*len(ref);maximum=0.0
    for i,j in zip(row,col):
        rev=reverse[i,j].mean()<normal[i,j].mean();deviation=float((reverse if rev else normal)[i,j].max());maximum=max(maximum,deviation)
        result[i]=normalized[j][::-1] if rev else normalized[j]
    if maximum>cfg['max_match_deviation_mm']:
        raise ConversionError('PROFILE_REQUIRED','线段形状偏离已验证模板，不能可靠确认裁片和缝合关系。')
    return result,scale,{'profile':cfg['id'],'matched_polylines':len(result),'max_sampled_deviation_mm':round(maximum,6),'physical_scale':round(scale,8),'units':units}

def inside(points,poly):
    """Even-odd test on actual contour; no bounding-box substitute."""
    x,y=points[:,0],points[:,1];keep=np.zeros(len(points),dtype=bool)
    previous=poly[-1]
    for current in poly:
        x1,y1=previous;x2,y2=current
        if abs(y2-y1)>1e-10:
            keep^=((y1>y)!=(y2>y)) & (x<(x2-x1)*(y-y1)/(y2-y1)+x1)
        previous=current
    return keep

def make_panels(P):
    cfg=get_profile()
    def join(spec):
        out=[]
        for i,rev in spec:
            q=P[i][::-1] if rev else P[i]
            if out and np.linalg.norm(np.asarray(out[-1])-q[0])<.1:q=q[1:]
            out.extend(q)
        return np.asarray(out)
    def mappt(q,front):
        name='front' if front else 'back';x=(q[0]-cfg['center_x'][name])/1000
        z=(q[1]+(cfg['front_z_offset_mm'] if front else 0)+cfg['origin_z_mm'])/1000
        alpha=np.clip((z-1.35)/.15,0,1);half=np.interp(z,[1.01,1.20,1.337,1.55],[.213,.180,.2164,.2164])
        theta=np.clip(x/half,-1,1)*math.pi/2;X=(1-alpha)*half*.735*math.sin(theta)+alpha*x
        Y=((1-alpha)*half*.47+alpha*.064)*math.cos(theta)
        if front:
            Y+=.018*math.exp(-((abs(X)-.065)/.065)**2-((z-1.385)/.065)**2)*max(0,math.cos(theta))
            Y+=.0015*math.sin((z-1.10)*125+X*24)*math.exp(-((z-1.16)/.09)**2)*(math.sin(theta)**2)
        return [X,Y*(-1 if front else 1),z]
    panels={};paths={}
    for name,spec in cfg['body'].items():
        poly=join(spec);lo,hi=poly.min(0),poly.max(0)
        xx,yy=np.meshgrid(np.arange(lo[0],hi[0],5),np.arange(lo[1],hi[1],5));g=np.c_[xx.ravel(),yy.ravel()];g=g[inside(g,poly)]
        pts=np.unique(np.round(np.vstack([poly,g]),4),axis=0)
        try:tri=Delaunay(pts).simplices
        except QhullError as exc:raise ConversionError('TRIANGULATION_FAILED','无法对裁片进行稳定三角化。') from exc
        keep=np.ones(len(tri),dtype=bool)
        # Off-boundary centroids avoid treating exact boundary midpoints as outside.
        for w in [(1/3,1/3,1/3),(.499,.499,.002),(.499,.002,.499),(.002,.499,.499)]:
            centers=sum(pts[tri[:,i]]*w[i] for i in range(3));keep &= inside(centers,poly)
        panels[name]={'verts':[mappt(q,name=='front') for q in pts],'faces':tri[keep].tolist()}
        def path(label,spec,n=64):paths[name+'_'+label]=np.asarray([mappt(q,name=='front') for q in sample(join(spec),n)])
        path('neck',[(93,False),(110,True)] if name=='front' else [(52,True),(30,False)],100)
        path('right_arm',[(112,False)] if name=='front' else [(28,False)],45)
        path('left_arm',[(95,False)] if name=='front' else [(50,False)],45)
        path('right_shoulder',[(111,False)] if name=='front' else [(29,True)],24)
        path('left_shoulder',[(94,False)] if name=='front' else [(51,True)],24)
        path('right_side',[(113,False)] if name=='front' else [(27,True),(26,False)],100)
        path('left_side',[(96,False)] if name=='front' else [(49,True),(48,False)],100)
    y=np.linspace(-1529.4,-1982,60)
    def at(q):
        order=np.argsort(q[:,1]);return np.interp(y,q[order,1],q[order,0])
    widths=at(P[70])-at(P[73])
    if np.any(widths<80) or np.any(widths>400):raise ConversionError('SLEEVE_RANGE','袖片宽度超出当前模板的可接受范围。')
    return panels,paths,widths

def assemble(panels,paths,widths,scale):
    parts=[]
    def add(name,v,f,flip=False):
        v=np.asarray(v,dtype=float);f=np.asarray(f,dtype=np.uint32)
        if flip:f=f[:,::-1]
        # Export Y-up metres, preserving a right-handed frame.
        v=v[:,[0,2,1]];v[:,2]*=-1;v*=scale
        edges1=v[f[:,1]]-v[f[:,0]];edges2=v[f[:,2]]-v[f[:,0]];norm=np.cross(edges1,edges2)
        good=np.linalg.norm(norm,axis=1)>1e-12;f=f[good];norm=norm[good]
        if not len(f):raise ConversionError('EMPTY_SURFACE','生成了空裁片。')
        # Remove unused vertices and construct smooth normals from the actual triangles.
        used,inv=np.unique(f,return_inverse=True);v=v[used];f=inv.reshape(-1,3).astype(np.uint32)
        n=np.zeros_like(v)
        for k in range(3):np.add.at(n,f[:,k],norm)
        lengths=np.linalg.norm(n,axis=1);n/=np.maximum(lengths[:,None],1e-12)
        if not np.isfinite(v).all() or not np.isfinite(n).all():raise ConversionError('NONFINITE_OUTPUT','三维模型含无效数值。')
        parts.append((name,v.astype('<f4'),n.astype('<f4'),f))
    for name,panel in panels.items():add(name,panel['verts'],panel['faces'],flip=name=='back')
    def bridge(name,a,b):
        if np.linalg.norm(a[0]-b[-1])<np.linalg.norm(a[0]-b[0]):b=b[::-1]
        N=len(a);v=np.vstack([a,b]);f=[]
        for i in range(N-1):f.extend([[i,i+1,N+i+1],[i,N+i+1,N+i]])
        add(name,v,f)
    for side in ['left','right']:
        bridge('side_'+side,paths['front_'+side+'_side'],paths['back_'+side+'_side'])
        bridge('shoulder_'+side,paths['front_'+side+'_shoulder'],paths['back_'+side+'_shoulder'])
        ring=np.vstack([paths['front_'+side+'_arm'],paths['back_'+side+'_arm'][::-1]]);N=len(ring);sign=1 if side=='right' else -1
        center=np.array([sign*.174,0,1.438]);axis=np.array([sign*.23,-.015,-.974]);axis/=np.linalg.norm(axis);B=np.array([0,1,0]);C=np.cross(axis,B);C/=np.linalg.norm(C)
        delta=ring-center;angles=np.arctan2(delta@C,delta@B);radial=np.cos(angles)[:,None]*B+np.sin(angles)[:,None]*C;v=[];R=64
        for j in range(R):
            t=j/(R-1);distance=.515*t;ctr=center+axis*distance;ctr[1]-=.006*math.sin(t*math.pi)
            radius=widths[min(59,int(t*59))]/1000/(2*math.pi);w=min(1,t/.26);w=w*w*(3-2*w)
            q=(ring+axis*distance)*(1-w)+(ctr+radius*radial)*w
            q+=radial*(.0013*np.sin(t*72+angles*2)*np.exp(-((t-.57)/.15)**2))[:,None];v.extend(q)
        f=[]
        for j in range(R-1):
            for k in range(N):
                a=j*N+k;b=j*N+(k+1)%N;c=(j+1)*N+(k+1)%N;d=(j+1)*N+k;f.extend([[a,b,c],[a,c,d]])
        add('sleeve_'+side,v,f)
    neck=np.vstack([paths['front_neck'],paths['back_neck'][::-1]]);N=len(neck);v=[]
    radial=neck.copy();radial[:,2]=0;radial/=np.maximum(np.linalg.norm(radial,axis=1)[:,None],1e-12)
    for j in range(5):
        q=neck+radial*(j/4*.010);q[:,2]-=j/4*.009;v.extend(q)
    f=[]
    for j in range(4):
        for i in range(N):
            a=j*N+i;b=j*N+(i+1)%N;c=(j+1)*N+(i+1)%N;d=(j+1)*N+i;f.extend([[a,b,c],[a,c,d]])
    add('neckband',v,f)
    return parts

def encode_glb(parts,report):
    binary=bytearray();views=[];accessors=[];meshes=[]
    def accessor(array,kind,component,target):
        while len(binary)%4:binary.append(0)
        offset=len(binary);raw=array.tobytes();binary.extend(raw)
        view=len(views);views.append({'buffer':0,'byteOffset':offset,'byteLength':len(raw),'target':target})
        a={'bufferView':view,'componentType':component,'count':len(array),'type':kind}
        if kind=='VEC3':a.update(min=array.min(0).astype(float).tolist(),max=array.max(0).astype(float).tolist())
        accessors.append(a);return len(accessors)-1
    for name,v,n,f in parts:
        p=accessor(v,'VEC3',5126,34962);normal=accessor(n,'VEC3',5126,34962);index=accessor(f.reshape(-1).astype('<u4'),'SCALAR',5125,34963)
        meshes.append({'name':name,'primitives':[{'attributes':{'POSITION':p,'NORMAL':normal},'indices':index,'material':0,'mode':4}]})
    doc={'asset':{'version':'2.0','generator':'Pattern Agent '+ENGINE_VERSION,'extras':{'profile':report['profile'],'conversion_id':report['conversion_id'],'physical_fit':'NOT_RUN','mode':'visual_preview'}},'scene':0,'scenes':[{'nodes':list(range(len(meshes)))}],'nodes':[{'mesh':i,'name':m['name']} for i,m in enumerate(meshes)],'meshes':meshes,'materials':[{'name':'展示用暖白面料','doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[.82,.79,.72,1],'metallicFactor':0,'roughnessFactor':.68}}],'buffers':[{'byteLength':len(binary)}],'bufferViews':views,'accessors':accessors}
    js=json.dumps(doc,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode();js+=b' '*((-len(js))%4);binary+=b'\0'*((-len(binary))%4)
    total=12+8+len(js)+8+len(binary)
    return struct.pack('<III',0x46546c67,2,total)+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+bytes(binary)

def convert_dxf(data:bytes,*,units:str,profile:str='fitted-tshirt-v1')->Converted:
    polylines,source=parse_dxf(data);P,scale,match=register(polylines,units,profile)
    panels,paths,widths=make_panels(P);parts=assemble(panels,paths,widths,scale)
    source_hash=hashlib.sha256(data).hexdigest();identifier=hashlib.sha256(json.dumps({'source':source_hash,'units':units,'profile':profile,'engine':ENGINE_VERSION},sort_keys=True).encode()).hexdigest()
    report={'status':'completed','conversion_id':identifier,'engine_version':ENGINE_VERSION,'profile':profile,'input_sha256':source_hash,'input_bytes':len(data),'source':source,'matching':match,'mode':'visual_preview','physical_fit':'NOT_RUN','strict_seam_and_intersection_release':'NOT_RUN','material':'assumed off-white; no calibrated fabric mechanics','meshes':len(parts),'vertices':sum(len(p[1]) for p in parts),'triangles':sum(len(p[3]) for p in parts),'limitations':['仅支持已验证的紧身长袖上衣导出拓扑，不支持任意服装纸样','输入单位必须显式指定；人物厚度、缝合连接及材质为展示假定','输出不是布料物理仿真，不用于生产尺寸或合身性批准']}
    glb=encode_glb(parts,report)
    if len(glb)>4_000_000:raise ConversionError('OUTPUT_LIMIT','生成结果超过直接响应限制，请降低模型复杂度。',413)
    report.update(output_sha256=hashlib.sha256(glb).hexdigest(),output_bytes=len(glb))
    return Converted(glb,report)
