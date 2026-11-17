"""Bind an inspection view to the independently reopened DXF and actual GLB.

Display PASS strings, screenshots and self-reported HTML datasets are not inputs
to the geometry verdict. The command calls the existing independent oracle.
"""
from pathlib import Path
from html.parser import HTMLParser
import base64,hashlib,json,math,sys
import numpy as np

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'services/dxf-preview'))
from verification.seams import audit_glb,decode_glb

LABELS=dict(zip([
    'side.left','shoulder.left','armhole.left.front','armhole.left.back','underarm.left',
    'side.right','shoulder.right','armhole.right.front','armhole.right.back','underarm.right',
    'neck.back.neck.left','neck.back.neck.right','neck.front.neck.right','neck.front.neck.left','band.end'
],['左侧缝','左肩缝','左袖窿·前段','左袖窿·后段','左袖底缝','右侧缝','右肩缝','右袖窿·前段','右袖窿·后段','右袖底缝','后领·左段','后领·右段','前领·右段','前领·左段','领条合口']))
PATCH_LABELS={'front':'前身','back':'后身','sleeve.left':'左袖','sleeve.right':'右袖','band':'领条外半层'}

def require(ok,message):
    if not bool(ok):raise ValueError(message)

def digest(raw):return hashlib.sha256(raw).hexdigest()

class Blocks(HTMLParser):
    def __init__(self):super().__init__();self.active=None;self.blocks={}
    def handle_starttag(self,tag,attrs):
        key=dict(attrs).get('id')
        if tag=='script' and key in ['sp-data','sp-report']:
            require(key not in self.blocks,'DUPLICATE_DATA_BLOCK '+key);self.blocks[key]='';self.active=key
    def handle_data(self,text):
        if self.active:self.blocks[self.active]+=text
    def handle_endtag(self,tag):
        if tag=='script':self.active=None

def read_view(html):
    parser=Blocks();parser.feed(html)
    require(set(parser.blocks)=={'sp-data','sp-report'},'MISSING_INSPECTOR_DATA_OR_REPORT')
    raw_report=base64.b64decode(parser.blocks['sp-report'].strip(),validate=True)
    return json.loads(parser.blocks['sp-data']),json.loads(raw_report),raw_report

def same_facts(actual,expected,path='report'):
    if isinstance(expected,dict):
        require(isinstance(actual,dict) and set(actual)==set(expected),'FACT_KEYS '+path)
        for k in expected:same_facts(actual[k],expected[k],path+'.'+k)
    elif isinstance(expected,list):
        require(isinstance(actual,list) and len(actual)==len(expected),'FACT_LENGTH '+path)
        for i,(a,b) in enumerate(zip(actual,expected)):same_facts(a,b,path+'.'+str(i))
    elif isinstance(expected,(float,int)) and not isinstance(expected,bool):
        require(isinstance(actual,(float,int)) and not isinstance(actual,bool) and math.isfinite(actual) and math.isclose(actual,expected,rel_tol=0,abs_tol=1e-8),'FACT_VALUE '+path)
    else:require(actual==expected,'FACT_VALUE '+path)

def validate_view(data,embedded,vertices,faces,certificate,measured,glb_sha,dxf_sha):
    """Check a view against supplied decoded data; CLI obtains measured via audit_glb."""
    require(measured['verdict']=='PASS','INDEPENDENT_GEOMETRY_NOT_PASS')
    require(data['model_sha256']==glb_sha,'VIEW_MODEL_HASH_MISMATCH')
    require(data['source_sha256']==dxf_sha==certificate['input_sha256'],'VIEW_DXF_HASH_MISMATCH')
    same_facts(embedded,measured)
    pos=np.frombuffer(base64.b64decode(data['vertices'],validate=True),'<f4').reshape(-1,3)
    idx=np.frombuffer(base64.b64decode(data['indices'],validate=True),'<u2').reshape(-1,3)
    require(np.array_equal(pos,vertices) and np.isfinite(pos).all(),'VIEW_POSITIONS_NOT_ACTUAL_GLB')
    require(np.array_equal(idx,faces),'VIEW_INDICES_NOT_ACTUAL_GLB')
    require(data['vertex_count']==len(vertices) and data['face_count']==len(faces),'VIEW_MESH_COUNTS')
    require(set(data['patches'])==set(certificate['patches']),'VIEW_PATCH_SET')
    require(set(data['segments'])==set(certificate['segments']),'VIEW_SEGMENT_SET')
    for name,patch in certificate['patches'].items():
        shown=data['patches'][name];n=patch['boundary_count'];xy=patch['flat_points'][:n].astype(float)
        origin=(xy.min(0)+xy.max(0))/2
        require(shown['label']==PATCH_LABELS[name],'VIEW_PATCH_LABEL '+name)
        require(np.array_equal(shown['boundary_ids'],patch['global_vertices'][:n]),'VIEW_PATCH_IDS '+name)
        require(np.allclose(shown['origin'],origin,rtol=0,atol=1e-9),'VIEW_PATCH_ORIGIN '+name)
        require(np.array_equal(shown['boundary'],np.round(xy-origin,2)),'VIEW_PATCH_XY '+name)
        base='sleeve' if name.startswith('sleeve.') else name
        loops=json.loads((REPO/'services/dxf-preview/converter/sewing_contract.json').read_text())['source_loops']
        if base in loops:
            original=np.vstack([np.asarray(certificate['pattern']['original_edges'][key])[::-1] if reverse else certificate['pattern']['original_edges'][key] for key,reverse in loops[base]])
        else:original=np.asarray(patch['boundary_points'])
        require(np.array_equal(shown['original'],np.round(original-origin,2)),'VIEW_PATCH_ORIGINAL '+name)
    for name,edge in certificate['segments'].items():
        shown=data['segments'][name];origin=np.asarray(data['patches'][edge['patch']]['origin'])
        require(shown['patch']==edge['patch'],'VIEW_SEGMENT_OWNER '+name)
        require(shown['ids']==edge['vertices'],'VIEW_SEGMENT_IDS '+name)
        require(np.array_equal(shown['xy'],np.round(np.asarray(edge['flat_points'])-origin,2)),'VIEW_SEGMENT_XY '+name)
        base=name.replace('sleeve.left.','sleeve.').replace('sleeve.right.','sleeve.')
        source=certificate['pattern']['original_edges'].get(base,edge['flat_points'])
        require(np.array_equal(shown['original'],np.round(np.asarray(source)-origin,2)),'VIEW_ORIGINAL_CURVE '+name)
        same_facts(shown['original_length_mm'],float(np.linalg.norm(np.diff(np.asarray(source),axis=0),axis=1).sum()),'original_length.'+name)
    pairs={s['name']:s for s in certificate['seams']};reports={s['name']:s for s in measured['checks']['seams']}
    require(len(data['seams'])==len(pairs) and {s['name'] for s in data['seams']}==set(pairs),'VIEW_SEAM_SET')
    for s in data['seams']:
        p=pairs[s['name']];require(s['a']==p['a'] and s['b']==p['b'],'VIEW_PAIRING '+s['name'])
        require(s['label']==LABELS[s['name']],'VIEW_SEAM_LABEL '+s['name']);same_facts(s['measurement'],reports[s['name']],'seam.'+s['name'])
    edges=np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1)
    unique,counts=np.unique(edges,axis=0,return_counts=True);actual={tuple(x) for x in unique[counts==1]};shown=[]
    require(len(data['openings'])==4,'VIEW_OPENING_COUNT')
    for cycle in data['openings']:
        require(len(cycle)>3 and cycle[0]==cycle[-1] and len(set(cycle[:-1]))==len(cycle)-1,'VIEW_OPENING_NOT_SIMPLE_CYCLE')
        shown.extend(tuple(sorted(e)) for e in zip(cycle[:-1],cycle[1:]))
    require(set(shown)==actual and len(shown)==len(actual),'VIEW_OPENINGS_NOT_ACTUAL_BOUNDARIES')
    checks=measured['checks']
    same_facts(data['checks'],{'verdict':measured['verdict'],'intersections':checks['proper_self_intersections'],'components':checks['topology']['connected_components'],'max_edit_mm':checks['flat_patterns']['max_vertex_edit_mm'],'original_verdict':checks['flat_patterns']['original_pattern_connection']['verdict']},'summary')

def bind_artifact(html,glb_path,dxf_path,units):
    blob=Path(glb_path).read_bytes();source=Path(dxf_path).read_bytes();data,embedded,raw=read_view(html)
    measured=audit_glb(blob,source,units)
    vertices,faces,certificate,_=decode_glb(blob)
    validate_view(data,embedded,vertices,faces,certificate,measured,digest(blob),digest(source))
    return data,raw,measured,{'verdict':'PASS','scope':'source/DXF + exact exported GLB + independent report + displayed geometry binding','model_sha256':digest(blob),'dxf_sha256':digest(source),'positions':len(vertices),'triangles':len(faces),'seam_pairs':len(data['seams']),'openings':len(data['openings']),'flat_display_precision_mm':.01,'unrounded_report_values':True}
