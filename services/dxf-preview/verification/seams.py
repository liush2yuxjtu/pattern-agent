"""Independent, fail-closed source/flat-pattern/sewn-surface acceptance.

No generator functions are imported. Source parsing, arclength measurement,
polygon coverage, seam incidence and vertex-link topology are re-read here.
Proper intersections use the repository's independently calibrated strict v2
SAT/coplanar oracle, including incident faces. Coordinates are metres in 3D.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib,json,struct
from pathlib import Path
import numpy as np
from .geometry import mesh_audit,intersect_pairs

ROOT=Path(__file__).resolve().parents[1]
CONTRACT_PATH=ROOT/'converter/sewing_contract.json'

def arclength(points):return float(np.sqrt(np.sum(np.diff(np.asarray(points),axis=0)**2,axis=1)).sum())
def point_positions(points,curve):
    points,curve=np.asarray(points),np.asarray(curve);a=curve[:-1];d=np.diff(curve,axis=0);size=np.linalg.norm(d,axis=1);valid=size>1e-10;a,d,size=a[valid],d[valid],size[valid]
    lengths=np.r_[0,np.cumsum(size)];delta=points[:,None]-a[None];t=np.clip(np.einsum('nkd,kd->nk',delta,d)/(size**2),0,1);foot=a[None]+t[:,:,None]*d[None];distance=np.linalg.norm(points[:,None]-foot,axis=2);k=distance.argmin(1)
    return distance[np.arange(len(points)),k],lengths[k]+t[np.arange(len(points)),k]*size[k]

def parse_original(raw,units,registration):
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError:text=raw.decode('gb18030')
    rows=text.splitlines();lines=[];current=None
    for i in range(0,len(rows),2):
        code=int(rows[i].strip());value=rows[i+1].strip()
        if code==0:
            kind=value
            if kind=='POLYLINE':current=[]
            elif kind=='VERTEX':current.append([None,None])
            elif kind=='SEQEND':lines.append(np.asarray(current,float));current=None
        elif current is not None and kind=='VERTEX' and code in [10,20]:current[-1][0 if code==10 else 1]=float(value)
    cfg=json.loads((ROOT/'converter/profile.json').read_text());ref=[np.asarray(q) for q in cfg['reference']];factor={'mm':1.,'cm':10.,'inch':25.4}[units]
    if len(lines)!=len(ref):raise ValueError('SOURCE_LINE_COUNT')
    index=registration['canonical_to_input'];rev=registration['input_reversed']
    if sorted(index)!=list(range(len(lines))) or len(rev)!=len(lines):raise ValueError('SOURCE_REGISTRATION_NOT_BIJECTIVE')
    physical=np.vstack(lines)*factor;reference=np.vstack(ref);lo,hi=physical.min(0),physical.max(0);rl,rh=reference.min(0),reference.max(0);scale=float(np.mean((hi-lo)/(rh-rl)));center=(lo+hi)/2;rc=(rl+rh)/2
    normalized=[]
    for n,j in enumerate(index):
        p=(lines[j]*factor-center)/scale+rc
        if rev[n]:p=p[::-1]
        # Independently confirm the artifact's claimed semantic registration.
        # A different 126-line layout cannot acquire this template's seam labels.
        t=np.linspace(0,1,64);rp=ref[n]
        def samples(q):
            d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))];keep=np.r_[True,np.diff(d)>1e-10];d=d[keep];q=q[keep]
            if len(d)<2 or d[-1]<=0:raise ValueError('DEGENERATE_REGISTERED_SOURCE')
            return np.c_[np.interp(t*d[-1],d,q[:,0]),np.interp(t*d[-1],d,q[:,1])]
        if np.max(np.linalg.norm(samples(p)-samples(rp),axis=1))>cfg['max_match_deviation_mm']:raise ValueError('SOURCE_REGISTRATION_SHAPE_MISMATCH')
        normalized.append(p)
    return normalized,scale

def source_edges(lines,contract):
    result={}
    for name,refs in contract['source_edges'].items():
        pts=[]
        for i,reverse in refs:
            q=lines[i][::-1] if reverse else lines[i]
            if pts and np.linalg.norm(pts[-1]-q[0])<.05:q=q[1:]
            pts.extend(q)
        result[name]=np.asarray(pts)
    return result

def polygon_area(p):
    p=np.asarray(p,dtype=np.float64);q=np.roll(p,-1,axis=0);return abs(float(np.sum(p[:,0]*q[:,1]-p[:,1]*q[:,0])))/2

def within_polygon(points,polygon):
    x,y=np.asarray(points,dtype=np.float64).T;keep=np.zeros(len(points),bool)
    for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
        if abs(b[1]-a[1])>1e-12:keep^=((a[1]>y)!=(b[1]>y))&(x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])
    return keep

def vertex_link_failures(faces):
    links=defaultdict(list)
    for a,b,c in faces:
        links[int(a)].append((int(b),int(c)));links[int(b)].append((int(c),int(a)));links[int(c)].append((int(a),int(b)))
    failures=[]
    for v,edges in links.items():
        graph=defaultdict(list)
        for a,b in edges:graph[a].append(b);graph[b].append(a)
        degree=[len(x) for x in graph.values()];todo=[next(iter(graph))];seen=set()
        while todo:
            a=todo.pop()
            if a not in seen:seen.add(a);todo.extend(graph[a])
        valid=(len(seen)==len(graph) and all(d in [1,2] for d in degree) and degree.count(1) in [0,2])
        if not valid:failures.append(v)
    return failures

def capped_orientation_volume(vertices,faces,boundary_edges):
    """Translation-invariant outward test; virtual caps never change the artifact."""
    v=np.asarray(vertices,float);origin=v.mean(0);p=v[faces]-origin;volume=float(np.einsum('ij,ij->i',p[:,0],np.cross(p[:,1],p[:,2])).sum())/6
    graph=defaultdict(list)
    for a,b in boundary_edges:graph[a].append(b);graph[b].append(a)
    centers={};unseen=set(graph)
    while unseen:
        todo=[unseen.pop()];component=[]
        while todo:
            a=todo.pop();component.append(a)
            for b in graph[a]:
                if b in unseen:unseen.remove(b);todo.append(b)
        center=v[component].mean(0)-origin
        for a in component:centers[a]=center
    for face in faces:
        for a,b in zip(face,np.roll(face,-1)):
            if tuple(sorted([int(a),int(b)])) in boundary_edges:volume+=float(np.dot(v[b]-origin,np.cross(v[a]-origin,centers[int(a)])))/6
    return volume

def decode_glb(blob):
    if len(blob)<28:raise ValueError('TRUNCATED_GLB')
    magic,version,total=struct.unpack_from('<III',blob)
    if (magic,version,total)!=(0x46546c67,2,len(blob)):raise ValueError('INVALID_GLB_HEADER')
    length,kind=struct.unpack_from('<II',blob,12)
    if kind!=0x4e4f534a:raise ValueError('INVALID_GLB_JSON')
    doc=json.loads(blob[20:20+length]);start=20+length;size,kind=struct.unpack_from('<II',blob,start);binary=blob[start+8:]
    if kind!=0x004e4942 or size!=len(binary):raise ValueError('INVALID_GLB_BUFFER')
    if len(doc.get('nodes',[]))!=1 or doc.get('scene')!=0 or doc['scenes'][0]['nodes']!=[0] or doc['nodes'][0].get('mesh')!=0:raise ValueError('UNVERIFIED_SCENE_GRAPH')
    if any(key in doc['nodes'][0] for key in ['matrix','translation','rotation','scale','children']):raise ValueError('UNVERIFIED_NODE_TRANSFORM')
    def read(i):
        acc=doc['accessors'][i];view=doc['bufferViews'][acc['bufferView']];dtype={5126:'<f4',5125:'<u4'}[acc['componentType']];width={'SCALAR':1,'VEC2':2,'VEC3':3}[acc['type']];offset=view.get('byteOffset',0)+acc.get('byteOffset',0);count=acc['count']*width
        if view.get('byteStride') or offset+count*4>len(binary):raise ValueError('UNSUPPORTED_OR_INVALID_ACCESSOR')
        a=np.frombuffer(binary,dtype=dtype,count=count,offset=offset).copy();return a.reshape(-1,width) if width>1 else a
    if len(doc['meshes'])!=1 or len(doc['meshes'][0]['primitives'])!=1:raise ValueError('SEWN_SHELL_MUST_HAVE_ONE_ACTUAL_MESH')
    p=doc['meshes'][0]['primitives'][0];v=read(p['attributes']['POSITION']);f=read(p['indices']).reshape(-1,3);m=doc['asset']['extras']['sewing_certificate'];n=read(p['attributes']['NORMAL']).astype(float)
    if p.get('mode',4)!=4 or n.shape!=v.shape or not np.isfinite(n).all() or np.max(np.abs(np.linalg.norm(n,axis=1)-1))>.02:raise ValueError('INVALID_EXPORTED_NORMALS')
    weighted=np.zeros_like(v,dtype=float);fv=v[f].astype(float);fn=np.cross(fv[:,1]-fv[:,0],fv[:,2]-fv[:,0])
    for corner in range(3):np.add.at(weighted,f[:,corner],fn)
    weighted/=np.maximum(np.linalg.norm(weighted,axis=1)[:,None],1e-20)
    if np.any(np.einsum('ij,ij->i',weighted,n)<.99):raise ValueError('EXPORTED_NORMALS_OPPOSE_ACTUAL_FACES')
    for patch in m['patches'].values():
        patch['flat_points']=read(patch.pop('flat_accessor'));patch['global_vertices']=read(patch.pop('global_accessor')).astype(int);patch['local_faces']=read(patch.pop('local_faces_accessor')).reshape(-1,3).astype(int)
    return v.astype(float),f.astype(int),m,doc

def audit_arrays(vertices,faces,manifest,source,units,*,check_intersections=True):
    """Return measured facts plus failures; never trust artifact PASS fields."""
    cfg=json.loads(CONTRACT_PATH.read_text());v=np.asarray(vertices,float);f=np.asarray(faces,int);errors=[];checks={};scale=1.
    def require(condition,message):
        if not bool(condition):errors.append(message)
    try:
        require(hashlib.sha256(source).hexdigest()==manifest['input_sha256'],'INPUT_HASH_MISMATCH')
        require(manifest['contract_sha256']==hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),'CONTRACT_HASH_MISMATCH')
        normalized,scale=parse_original(source,units,manifest['input_registration']);require(abs(scale-manifest['physical_scale'])<1e-8,'SOURCE_SCALE_MISMATCH')
        raw=source_edges(normalized,cfg);original=manifest['pattern']['original_edges'];derived={k:np.asarray(q,float) for k,q in manifest['pattern']['derived_edges'].items()}
        require(set(original)==set(raw)==set(derived),'SOURCE_EDGE_SET_CHANGED')
        max_edit=0.
        protected={k for k in raw if k.startswith('back.') or '.arm.' in k or k=='sleeve.side.front'}
        for key in raw:
            o=np.asarray(original[key]);d=derived[key];require(o.shape==raw[key].shape==d.shape,'SOURCE_VERTEX_COUNT '+key)
            require(np.max(np.abs(o-raw[key]))<1e-6,'SOURCE_EDGE_NOT_FROM_DXF '+key)
            edit=float(np.max(np.linalg.norm(d-raw[key],axis=1)));max_edit=max(max_edit,edit)
            require(edit<=cfg['thresholds']['max_derived_vertex_edit_mm'],'DERIVED_EDIT_LIMIT '+key)
            if key in protected:require(edit<=.05,'PROTECTED_BODY_ARMHOLE_OR_SOURCE_EDGE_CHANGED '+key)
        lengths={k:arclength(p) for k,p in derived.items()};original_lengths={k:arclength(p) for k,p in raw.items()}
        total_ease=original_lengths['sleeve.cap.front']+original_lengths['sleeve.cap.back']-original_lengths['front.arm.left']-original_lengths['back.arm.left']
        require(0<=total_ease<=15,'SOURCE_SLEEVE_EASE_RANGE')
        residuals={}
        for side in ['left','right']:
            residuals['shoulder.'+side]=lengths['front.shoulder.'+side]-lengths['back.shoulder.'+side]
            residuals['side.'+side]=(lengths['front.side.'+side]-6)-(lengths['back.side.'+side]+10)
        residuals['sleeve.underarm']=lengths['sleeve.side.front']-lengths['sleeve.side.back']
        for half,share in [('front',.4),('back',.6)]:residuals['cap.'+half]=lengths['sleeve.cap.'+half]-lengths[half+'.arm.left']-total_ease*share
        for name,value in residuals.items():require(abs(value)*scale<=.05,'FLAT_LENGTH_RESIDUAL '+name)
        neck=sum(lengths[k] for k in lengths if '.neck.' in k);band=arclength(normalized[0])+arclength(normalized[1]);ratio=band/neck;require(.70<=ratio<=.95,'NECKBAND_RATIO_RANGE')
        original_residuals={}
        for side in ['left','right']:
            original_residuals['shoulder.'+side]=original_lengths['front.shoulder.'+side]-original_lengths['back.shoulder.'+side]
            original_residuals['side.'+side]=original_lengths['front.side.'+side]-6-original_lengths['back.side.'+side]-10
        original_residuals['sleeve.underarm']=original_lengths['sleeve.side.front']-original_lengths['sleeve.side.back']
        for half,share in [('front',.4),('back',.6)]:original_residuals['cap.'+half]=original_lengths['sleeve.cap.'+half]-original_lengths[half+'.arm.left']-total_ease*share
        original_status='FAIL' if any(abs(x)*scale>.05 for x in original_residuals.values()) else 'PASS'
        checks['flat_patterns']={'max_vertex_edit_mm':max_edit*scale,'max_processed_seam_residual_mm':max(abs(x) for x in residuals.values())*scale,'processed_residuals_mm':{k:x*scale for k,x in residuals.items()},'original_rest_lengths_mm':{k:x*scale for k,x in original_lengths.items()},'derived_rest_lengths_mm':{k:x*scale for k,x in lengths.items()},'sleeve_front_ease_mm':total_ease*.4*scale,'sleeve_back_ease_mm':total_ease*.6*scale,'neckband_body_ratio':ratio,'material_stretch_capacity':'NOT_RUN','original_pattern_connection':{'verdict':original_status,'processed_residuals_mm':{k:x*scale for k,x in original_residuals.items()},'evaluated_under_contract':cfg['id']}}
        expected_names=cfg['expected_patches'];require(sorted(manifest['patches'])==sorted(expected_names),'PATCH_SET_MISMATCH')
        ownership=np.full(len(f),-1,int);segment_boundary=defaultdict(set);patch_records={}
        segments=manifest['segments']
        for key,s in segments.items():
            local=np.asarray(s['local_vertices'],int);ids=np.asarray(s['vertices'],int);patch=manifest['patches'][s['patch']];xy=np.asarray(patch['flat_points'],dtype=np.float64);g=np.asarray(patch['global_vertices']);require(len(local)==len(ids)>=2,'EMPTY_SEGMENT '+key);require(np.array_equal(g[local],ids),'SEGMENT_VERTEX_ID_MISMATCH '+key)
            claimed=np.asarray(s['flat_points']);require(np.max(np.linalg.norm(xy[local]-claimed,axis=1))<=.002,'SEGMENT_UV_NOT_BOUNDARY '+key)
            segment_boundary[s['patch']].update(tuple(sorted([int(a),int(b)])) for a,b in zip(local[:-1],local[1:]))
            if key.startswith('band.'):
                rest=arclength(claimed);window=[0,1] if '.neck.' in key else [.1,.7]
                if '.neck.' in key:body_key=key[len('band.'):];process=lengths[body_key]-rest
                else:process=0.
                # Source strip is an actual rectangle, outer half between stitch and fold.
                xs=[float(normalized[i][0,0]) for i in [0,10,11,8,1]];yb=float(normalized[0][0,1]);yt=float(normalized[9][0,1]);require(xs[0]-1e-3<=claimed[:,0].min()<=claimed[:,0].max()<=xs[-1]+1e-3,'BAND_SOURCE_X_RANGE')
                if '.neck.' in key:
                    order=['back.neck.left','back.neck.right','front.neck.right','front.neck.left'];i=order.index(body_key);require(np.linalg.norm(claimed[0]-[xs[i],yb])<.002 and np.linalg.norm(claimed[-1]-[xs[i+1],yb])<.002,'BAND_NOTCH_ORIENTATION '+key)
                else:require(yb-1e-3<=claimed[:,1].min()<=claimed[:,1].max()<=yt+1e-3,'BAND_SOURCE_Y_RANGE')
            else:
                base=key.replace('sleeve.left.','sleeve.').replace('sleeve.right.','sleeve.');curve=derived[base];distance,positions=point_positions(claimed,curve);rest=lengths[base];require(np.max(distance)<=.002,'SEGMENT_NOT_ON_DERIVED_LINE '+key);require(positions[0]<.002 and abs(positions[-1]-rest)<.002 and np.all(np.diff(positions)>=-1e-3),'SEGMENT_REVERSED_OR_NOT_COVERED '+key)
                process=0.;window=[.1,.7]
                if '.side.' in key and key.startswith('front.'):process=-6.;window=[.04,.22]
                if '.side.' in key and key.startswith('back.'):process=10.;window=[.24,.75]
                if '.cap.' in key:half=key.split('.')[-1];process=-total_ease*(.4 if half=='front' else .6);window=[.1,.7]
                a,b=np.array(window)*rest;processed=positions+process*np.clip((positions-a)/(b-a),0,1);require(np.max(np.abs(processed/(rest+process)-s['parameter']))<3e-5,'LOCAL_EASE_OR_NOTCH_MAPPING '+key)
            require(abs(s['process_mm']-process)<.003,'UNDECLARED_SEWING_PROCESS '+key);require(np.allclose(s['process_window'],window,atol=1e-12),'EASE_WINDOW_CHANGED '+key)
        for number,name in enumerate(expected_names):
            p=manifest['patches'][name];xy=np.asarray(p['flat_points'],dtype=np.float64);ids=np.asarray(p['global_vertices'],int);t=np.asarray(p['local_faces'],int);start,count=p['face_start'],p['face_count'];require(count==len(t) and 0<=start<=start+count<=len(f),'INVALID_FACE_RANGE '+name);require(np.all(ownership[start:start+count]==-1),'OVERLAPPING_FACE_RANGES');ownership[start:start+count]=number
            require(np.array_equal(ids[t],f[start:start+count]),'SOURCE_FACES_NOT_THE_EXPORTED_FACES '+name)
            nb=p['boundary_count'];boundary=xy[:nb];edges=np.sort(np.concatenate([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]]),axis=1);e,c=np.unique(edges,axis=0,return_counts=True);actual={tuple(a) for a in e[c==1]};expected={tuple(sorted([i,(i+1)%nb])) for i in range(nb)}
            require(actual==expected==segment_boundary[name],'FLAT_BOUNDARY_NOT_FULLY_COVERED '+name)
            delta=xy[t[:,1]]-xy[t[:,0]];other=xy[t[:,2]]-xy[t[:,0]];signed=delta[:,0]*other[:,1]-delta[:,1]*other[:,0];require(np.all(signed>1e-6) or np.all(signed<-1e-6),'DEGENERATE_OR_FOLDED_SOURCE_TRIANGLES '+name)
            actual_area=float(np.abs(signed).sum()/2);expected_area=polygon_area(boundary);require(abs(actual_area-expected_area)<=max(.1,expected_area*1e-6),'SOURCE_PANEL_AREA_NOT_COVERED '+name)
            require(within_polygon(xy[t].mean(1),boundary).all(),'SOURCE_TRIANGLE_OUTSIDE_PAPER '+name)
            patch_records[name]={'flat_area_mm2':expected_area*scale**2,'triangle_area_mm2':actual_area*scale**2,'triangles':len(t),'all_source_boundary_segments_preserved':actual==expected}
        require(np.all(ownership>=0),'EXPORTED_FACES_WITHOUT_SOURCE_PATCH')
        edge_faces=defaultdict(list)
        for i,face in enumerate(f):
            for a,b in zip(face,np.roll(face,-1)):edge_faces[tuple(sorted([int(a),int(b)]))].append(i)
        require(manifest['seams']==cfg['seams'],'SEWING_PAIR_SET_OR_LABEL_CHANGED')
        sewn=set();seam_reports=[];max_gap=0.;max_length_error=0.
        for pair in cfg['seams']:
            a,b=segments[pair['a']],segments[pair['b']];aa=np.asarray(a['vertices'],int);bb=np.asarray(b['vertices'],int);require(len(aa)==len(bb) and np.array_equal(aa,bb),'UNWELDED_OR_REVERSED_SEAM '+pair['name']);gap=float(np.linalg.norm(v[aa]-v[bb],axis=1).max()*1000);max_gap=max(max_gap,gap);require(gap<=2.,'SEAM_GAP '+pair['name'])
            owners={expected_names.index(a['patch']),expected_names.index(b['patch'])};edges=[tuple(sorted([int(x),int(y)])) for x,y in zip(aa[:-1],aa[1:])]
            for edge in edges:
                incidences=edge_faces.get(edge,[]);require(len(incidences)==2,'SEAM_NOT_TWO_FACES '+pair['name']);require({int(ownership[i]) for i in incidences}==owners,'SEAM_WRONG_PATCH '+pair['name'])
            sewn.update(edges);la=(arclength(a['flat_points'])+a['process_mm'])*scale;lb=(arclength(b['flat_points'])+b['process_mm'])*scale;actual=arclength(v[aa])*1000;error=abs(actual-(la+lb)/2);max_length_error=max(max_length_error,error);require(abs(la-lb)<=.05,'SAMPLED_FLAT_LENGTH_MISMATCH '+pair['name']);require(error<=2.,'3D_SEAM_LENGTH_CHANGED '+pair['name'])
            seam_reports.append({'name':pair['name'],'pieces':[a['patch'],b['patch']],'samples':len(aa),'max_gap_mm':gap,'rest_a_mm':arclength(a['flat_points'])*scale,'rest_b_mm':arclength(b['flat_points'])*scale,'process_a_mm':a['process_mm']*scale,'process_b_mm':b['process_mm']*scale,'processed_residual_mm':abs(la-lb),'sewn_3d_length_mm':actual,'length_error_mm':error,'welded_shared_vertex_ids':bool(np.array_equal(aa,bb))})
        boundary_expected=set()
        require(manifest['openings']==cfg['openings'],'OPENING_SET_CHANGED')
        for key in cfg['openings']:
            ids=segments[key]['vertices'];boundary_expected.update(tuple(sorted([int(a),int(b)])) for a,b in zip(ids[:-1],ids[1:]))
        boundary_actual={e for e,fs in edge_faces.items() if len(fs)==1};require(boundary_actual==boundary_expected,'UNDECLARED_HOLE_OR_CLOSED_REQUIRED_OPENING')
        topo=mesh_audit(v,f);require(topo['connected_components']==1,'DISCONNECTED_GARMENT');require(topo['boundary_cycles']==4 and topo['boundary_components']==4,'WRONG_OPENING_COUNT');require(topo['euler_characteristic']==-2,'WRONG_GARMENT_TOPOLOGY')
        for key in ['nonmanifold_edges','boundary_branch_vertices','winding_conflicts','degenerate_triangles','duplicate_faces','orphan_vertices']:require(topo[key]==0,'INVALID_TOPOLOGY '+key)
        links=vertex_link_failures(f);require(not links,'PINCHED_OR_BOW_TIE_VERTICES')
        capped_volume=capped_orientation_volume(v,f,boundary_actual);require(capped_volume>1e-10,'ENTIRE_GARMENT_INSIDE_OUT')
        intersections=intersect_pairs(v,f,epsilon_m=1e-6) if check_intersections else None
        if check_intersections:require(len(intersections)==0,'PROPER_SELF_INTERSECTIONS')
        checks.update(topology=topo,vertex_link_failures=len(links),capped_orientation_volume_m3=capped_volume,outward_orientation=capped_volume>1e-10,patches=patch_records,seams=seam_reports,max_seam_gap_mm=max_gap,max_3d_seam_length_error_mm=max_length_error,proper_self_intersections=len(intersections) if intersections is not None else 'NOT_RUN',intersection_examples=intersections[:20] if intersections else [])
    except (ValueError,KeyError,IndexError,TypeError,AssertionError) as exc:errors.append('INVALID_OR_UNVERIFIABLE_ARTIFACT: '+str(exc))
    verdict='PASS' if not errors and check_intersections else 'FAIL' if errors else 'NOT_RUN'
    return {'verdict':verdict,'scope':cfg['scope'],'contract':cfg['id'],'checks':checks,'failures':list(dict.fromkeys(errors)),'physical_fit':'NOT_RUN','material_mechanics':'NOT_RUN','production_cutting_approval':'NOT_RUN','assumptions':cfg['assumptions']}

def audit_glb(blob,source,units):
    try:v,f,m,_=decode_glb(blob);return audit_arrays(v,f,m,source,units)
    except (ValueError,KeyError,IndexError,struct.error) as exc:return {'verdict':'FAIL','failures':['GLB_CERTIFICATE_REJECTED: '+str(exc)],'physical_fit':'NOT_RUN'}
