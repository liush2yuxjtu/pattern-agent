"""Bounded, profile-gated DXF to visual GLB. No Blender or persisted jobs required."""
from __future__ import annotations
import hashlib, json, math, struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial import Delaunay, QhullError

ENGINE_VERSION = '2.0.0'
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
    result=[None]*len(ref);maximum=0.0;mapping=[0]*len(ref);directions=[False]*len(ref)
    for i,j in zip(row,col):
        rev=reverse[i,j].mean()<normal[i,j].mean();deviation=float((reverse if rev else normal)[i,j].max());maximum=max(maximum,deviation)
        result[i]=np.round(normalized[j][::-1] if rev else normalized[j],6);mapping[int(i)]=int(j);directions[int(i)]=bool(rev)
    if maximum>cfg['max_match_deviation_mm']:
        raise ConversionError('PROFILE_REQUIRED','线段形状偏离已验证模板，不能可靠确认裁片和缝合关系。')
    return result,scale,{'profile':cfg['id'],'matched_polylines':len(result),'max_sampled_deviation_mm':round(maximum,6),'physical_scale':round(scale,8),'units':units,'registration':{'canonical_to_input':mapping,'input_reversed':directions}}

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

def encode_glb(parts,report,certificate=None):
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
    if certificate is not None:
        from copy import deepcopy
        certificate=deepcopy(certificate)
        for patch in certificate['patches'].values():
            patch['flat_accessor']=accessor(np.asarray(patch.pop('flat_points'),dtype='<f4'),'VEC2',5126,34962)
            patch['global_accessor']=accessor(np.asarray(patch.pop('global_vertices'),dtype='<u4'),'SCALAR',5125,34963)
            patch['local_faces_accessor']=accessor(np.asarray(patch.pop('local_faces'),dtype='<u4').reshape(-1),'SCALAR',5125,34963)
    doc={'asset':{'version':'2.0','generator':'Pattern Agent '+ENGINE_VERSION,'extras':{'profile':report['profile'],'conversion_id':report['conversion_id'],'physical_fit':'NOT_RUN','mode':report.get('mode','visual_preview')}},'scene':0,'scenes':[{'nodes':list(range(len(meshes)))}],'nodes':[{'mesh':i,'name':m['name']} for i,m in enumerate(meshes)],'meshes':meshes,'materials':[{'name':'展示用暖白面料','doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[.82,.79,.72,1],'metallicFactor':0,'roughnessFactor':.68}}],'buffers':[{'byteLength':len(binary)}],'bufferViews':views,'accessors':accessors}
    if certificate is not None:doc['asset']['extras']['sewing_certificate']=certificate
    js=json.dumps(doc,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode();js+=b' '*((-len(js))%4);binary+=b'\0'*((-len(binary))%4)
    total=12+8+len(js)+8+len(binary)
    return struct.pack('<III',0x46546c67,2,total)+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+bytes(binary)

def convert_dxf(data:bytes,*,units:str,profile:str='fitted-tshirt-v1')->Converted:
    from .sewn import build
    from verification.seams import audit_glb,CONTRACT_PATH
    polylines,source=parse_dxf(data);P,scale,match=register(polylines,units,profile)
    try:v,f,certificate=build(P)
    except (ValueError,QhullError) as exc:raise ConversionError('SEWING_ASSEMBLY_REJECTED','纸样不能按当前连接规则可靠装配：'+str(exc)) from exc
    # The actual exported surface is one welded Y-up mesh in metres.
    v=v[:,[0,2,1]];v[:,2]*=-1;v*=scale
    normal=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);n=np.zeros_like(v)
    for k in range(3):np.add.at(n,f[:,k],normal)
    n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-15)
    source_hash=hashlib.sha256(data).hexdigest();identifier=hashlib.sha256(json.dumps({'source':source_hash,'units':units,'profile':profile,'engine':ENGINE_VERSION},sort_keys=True).encode()).hexdigest()
    certificate.update(input_sha256=source_hash,input_units=units,physical_scale=scale,input_registration=match.pop('registration'),contract_sha256=hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest())
    report={'status':'completed','conversion_id':identifier,'engine_version':ENGINE_VERSION,'profile':profile,'input_sha256':source_hash,'input_bytes':len(data),'source':source,'matching':match,'mode':'verified_static_sewn_outer_shell','physical_fit':'NOT_RUN','material_mechanics':'NOT_RUN','production_cutting_approval':'NOT_RUN','cloth_body_collision':'NOT_RUN','meshes':1,'source_patches':5,'vertices':len(v),'triangles':len(f),'limitations':['原始纸样存在缝线差异；当前输出使用明确记录的修正缝合线，原文件字节未改动','连接验收仅适用于显示的静态单层外壳；领条隐藏内层和缝份叠层未建模','面料、人体厚度、姿态及真实试穿未标定，不构成生产纸样批准']}
    glb=encode_glb([('verified_sewn_garment',v.astype('<f4'),n.astype('<f4'),f.astype('<u4'))],report,certificate)
    if len(glb)>4_000_000:raise ConversionError('OUTPUT_LIMIT','带连接证书的模型超过直接响应限制。',413)
    # Re-open the exact returned float32 GLB, not only the generator's float64 arrays.
    verified=audit_glb(glb,data,units)
    if verified['verdict']!='PASS':raise ConversionError('SEWING_VERIFICATION_FAILED','裁片连接未通过独立检查，已停止输出：'+'; '.join(verified['failures'][:4]))
    report.update(strict_seam_and_intersection_release='PASS',connection_verification=verified,pattern_revision={'kind':'corrected_derivative_seam_lines','original_file_unchanged':True,'max_vertex_edit_mm':certificate['pattern']['max_vertex_edit_mm']*scale,'operations':certificate['pattern']['operations']},output_sha256=hashlib.sha256(glb).hexdigest(),output_bytes=len(glb))
    return Converted(glb,report)
