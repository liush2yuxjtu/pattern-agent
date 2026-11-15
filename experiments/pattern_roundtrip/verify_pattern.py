"""Independent audit of flattened panels, source correspondence and seam mapping.

No flattening code is imported. External frozen rest mesh/topology are required;
the pattern's own embedded source cannot establish its provenance. Mapping to
stored 3D coordinates is assembly identity, never a simulated 2D sewing result.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import numpy as np

EPS_M=1e-9
AREA_M2=1e-12
PANEL_IDS=('front','back','left_sleeve','right_sleeve')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def cycles(face):return min(tuple(np.roll(face,k)) for k in range(3))
def edge(a,b):return tuple(sorted((int(a),int(b))))
def cross(a,b):return float(a[0]*b[1]-a[1]*b[0])


def overlap_area(a,b):
    """Independent 2D convex clipping, counting area rather than edge contact."""
    polygon=[p.copy() for p in a]
    orientation=1 if cross(b[1]-b[0],b[2]-b[0])>0 else -1
    for start,end in zip(b,np.roll(b,-1,axis=0)):
        if not polygon:return 0.
        result=[]
        for p,q in zip(polygon,polygon[1:]+polygon[:1]):
            dp=orientation*cross(end-start,p-start);dq=orientation*cross(end-start,q-start)
            inp=dp>=-1e-13;inq=dq>=-1e-13
            if inp:result.append(p)
            if inp!=inq and abs(dp-dq)>1e-30:result.append(p+(q-p)*dp/(dp-dq))
        polygon=result
    if len(polygon)<3:return 0.
    origin=polygon[0]
    return abs(sum(cross(polygon[i]-origin,polygon[i+1]-origin) for i in range(1,len(polygon)-1)))/2


def self_overlaps(vertices,faces):
    triangles=vertices[faces];lo=triangles.min(axis=1);hi=triangles.max(axis=1);pairs=[]
    for i,a in enumerate(triangles):
        candidate=np.flatnonzero(np.all(np.maximum(lo[i],lo[i+1:])<=np.minimum(hi[i],hi[i+1:])+EPS_M,axis=1))+i+1
        for j in candidate:
            area=overlap_area(a,triangles[j])
            if area>AREA_M2:pairs.append({'faces':[i,int(j)],'overlap_mm2':area*1e6})
    return pairs


def panel_topology(faces,vertex_count):
    incidence=defaultdict(list)
    for fi,t in enumerate(faces):
        for a,b in zip(t,np.roll(t,-1)):incidence[edge(a,b)].append((int(a),int(b),fi))
    parents=list(range(vertex_count))
    def root(x):
        while parents[x]!=x:parents[x]=parents[parents[x]];x=parents[x]
        return x
    for a,b in incidence:
        x,y=root(a),root(b)
        if x!=y:parents[x]=y
    boundary={e:v[0] for e,v in incidence.items() if len(v)==1};graph=defaultdict(list)
    for a,b in boundary:graph[a].append(b);graph[b].append(a)
    unseen=set(graph);loops=0
    while unseen:
        stack=[unseen.pop()];group=[]
        while stack:
            x=stack.pop();group.append(x)
            for y in graph[x]:
                if y in unseen:unseen.remove(y);stack.append(y)
        loops+=int(all(len(graph[x])==2 for x in group))
    used=set(map(int,faces.ravel()));components=len({root(i) for i in used})
    euler=len(used)-len(incidence)+len(faces)
    nonmanifold=sum(len(x)>2 for x in incidence.values())
    winding=sum(len(x)==2 and x[0][:2]==x[1][:2] for x in incidence.values())
    return {'vertices':vertex_count,'used_vertices':len(used),'faces':len(faces),'edges':len(incidence),
            'components':components,'euler_characteristic':euler,'boundary_cycles':loops,
            'boundary_branch_vertices':sum(len(x)!=2 for x in graph.values()),'nonmanifold_edges':nonmanifold,
            'winding_conflicts':winding,'disk':bool(components==1 and euler==1 and loops==1 and not nonmanifold and not winding
                                                  and all(len(x)==2 for x in graph.values()) and len(used)==vertex_count)},boundary


def metric(vertices,faces,source_vertices,source_ids):
    uv=vertices[faces];xyz=source_vertices[source_ids[faces]];a=xyz[:,1]-xyz[:,0];b=xyz[:,2]-xyz[:,0]
    length=np.linalg.norm(a,axis=1);normal=np.cross(a,b);area3=np.linalg.norm(normal,axis=1)/2
    u=a/length[:,None];n=normal/np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-30);v=np.cross(n,u)
    x=np.stack([np.stack([length,np.zeros(len(a))],axis=1),np.stack([np.sum(b*u,axis=1),np.sum(b*v,axis=1)],axis=1)],axis=2)
    q=np.stack([uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]],axis=2)
    determinants=np.linalg.det(q);valid=(np.abs(determinants)>2*AREA_M2)&(area3>AREA_M2)
    sv=np.full((len(faces),2),np.nan)
    if valid.any():sv[valid]=np.linalg.svd(x[valid]@np.linalg.inv(q[valid]),compute_uv=False)
    strain=np.max(np.abs(sv[valid]-1),axis=1)*100
    unique=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
    l2=np.linalg.norm(vertices[unique[:,0]]-vertices[unique[:,1]],axis=1)
    l3=np.linalg.norm(source_vertices[source_ids[unique[:,0]]]-source_vertices[source_ids[unique[:,1]]],axis=1)
    relative=np.abs(l2/l3-1)
    return {'valid_metric_triangles':int(valid.sum()),'invalid_metric_triangles':int((~valid).sum()),
            'area_2d_m2':float(np.abs(determinants).sum()/2),'area_3d_m2':float(area3.sum()),
            'area_ratio_2d_to_source_3d':float(np.abs(determinants).sum()/2/area3.sum()),
            'principal_stretch_min':float(sv[valid].min()) if valid.any() else None,
            'principal_stretch_max':float(sv[valid].max()) if valid.any() else None,
            'absolute_principal_strain_p95_pct':float(np.percentile(strain,95)) if len(strain) else None,
            'absolute_principal_strain_max_pct':float(strain.max()) if len(strain) else None,
            'edge_relative_error_p95_pct':float(np.percentile(relative,95)*100),
            'edge_relative_error_max_pct':float(relative.max()*100),
            'meaning':'2D paper to source3D metric change; no calibrated allowable fabric strain or physical-fit claim.'}


def analytic_tests():
    a=np.array([[0.,0],[1.,0],[0.,1]])
    cases=[('disjoint',a,a+[2,0],0.),('valid_edge_contact',a,np.array([[1.,0],[1.,1],[0.,1]]),0.),
           ('valid_point_contact',a,a+[1,0],0.),('nested_overlap',a,np.array([[.1,.1],[.3,.1],[.1,.3]]),.02),
           ('shared_vertex_area_overlap',a,np.array([[0.,0],[.7,0],[0.,.7]]),.245)]
    rows=[]
    for name,x,y,expected in cases:
        observed=overlap_area(x,y);assert abs(observed-expected)<1e-12,(name,observed,expected)
        rows.append({'name':name,'expected_overlap_area_m2':expected,'observed_overlap_area_m2':observed,'passed':True})
    v=np.array([[0.,0],[1.,0],[1.,1],[0.,1]]);f=np.array([[0,1,2],[0,2,3]])
    topo,_=panel_topology(f,len(v));assert topo['disk'] and not self_overlaps(v,f)
    rows.append({'name':'two_triangle_disk_with_legitimate_shared_edge','passed':True})
    return {'test_count':len(rows),'all_passed':True,'tests':rows,'scope':'Known-answer2D clipping and topology tests, not a general accuracy benchmark.'}


def verify(pattern,source_vertices,source_triangles,topology):
    """Compute checks from geometry/provenance, ignoring generator result fields."""
    errors=[];panel_reports={};parsed={};face_owners=Counter();boundary_occurrences=defaultdict(list);notches=defaultdict(list)
    def fail(code,detail):errors.append({'code':code,'detail':detail})
    if pattern.get('units')!='metres':fail('UNITS','Pattern coordinates must explicitly use metres')
    embedded=pattern.get('source',{})
    try:
        er=np.asarray(embedded['rest_vertices_3d_m'],float);et=np.asarray(embedded['triangles'],int)
        if er.shape!=source_vertices.shape or not np.isfinite(er).all() or not np.allclose(er,source_vertices,rtol=0,atol=1e-12):fail('EMBEDDED_SOURCE_MISMATCH','Rest coordinates differ from external frozen source')
        if not np.array_equal(et,source_triangles):fail('EMBEDDED_SOURCE_MISMATCH','Triangle topology differs from external frozen source')
    except Exception as exc:fail('EMBEDDED_SOURCE_MISMATCH',str(exc))
    panels=pattern.get('panels',{})
    if set(panels)!=set(PANEL_IDS):fail('PANEL_SET',f'Expected{PANEL_IDS}, observed{list(panels)}')
    sleeve_sets={s:set(map(int,topology['sleeve_triangles'][s])) for s in ('L','R')}
    expected={}
    torso=set(range(len(source_triangles)))-sleeve_sets['L']-sleeve_sets['R']
    expected['front']={i for i in torso if source_vertices[source_triangles[i],1].mean()<0}
    expected['back']=torso-expected['front'];expected['left_sleeve']=sleeve_sets['L'];expected['right_sleeve']=sleeve_sets['R']
    for name,panel in panels.items():
        try:
            uv=np.asarray(panel['vertices_2d_m'],float);ids=np.asarray(panel['source_vertex_ids'],int)
            faces=np.asarray(panel['faces'],int);source_faces=np.asarray(panel['source_face_ids'],int)
            if uv.ndim!=2 or uv.shape[1]!=2 or len(ids)!=len(uv) or not np.isfinite(uv).all():raise ValueError('invalid finite2D coordinate arrays')
            if faces.ndim!=2 or faces.shape[1]!=3 or len(faces)!=len(source_faces) or faces.min()<0 or faces.max()>=len(uv):raise ValueError('invalid triangle index arrays')
            if ids.min()<0 or ids.max()>=len(source_vertices) or source_faces.min()<0 or source_faces.max()>=len(source_triangles):raise ValueError('source indices out of range')
            parsed[name]=(uv,ids,faces,source_faces)
            if name not in expected or set(map(int,source_faces))!=expected[name]:fail('SOURCE_PANEL_ROLE',name+' source faces disagree with frozen front/back/L/R assignment')
            for local,original in zip(faces,source_faces):
                face_owners[int(original)]+=1
                if cycles(ids[local])!=cycles(source_triangles[original]):fail('SOURCE_TRIANGLE_MAPPING',f'{name} face{int(original)} inconsistent source vertices or orientation')
            info,boundary=panel_topology(faces,len(uv));tri=uv[faces]
            d1,d2=tri[:,1]-tri[:,0],tri[:,2]-tri[:,0];signed=(d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0])/2
            overlaps=self_overlaps(uv,faces)
            if not info['disk']:fail('PANEL_NOT_DISK',name)
            chart_sign=1 if np.sum(signed)>0 else -1
            if not np.all(chart_sign*signed>AREA_M2):fail('PANEL_FLIP_OR_COLLAPSE',name)
            if overlaps:fail('PANEL_SELF_OVERLAP',f'{name}:{len(overlaps)}positive-area pairs')
            declared=panel.get('boundary_vertex_ids',[])
            if len(declared)!=len(boundary) or {edge(a,b) for a,b in zip(declared,declared[1:]+declared[:1])}!=set(boundary):fail('DECLARED_BOUNDARY_MISMATCH',name)
            for e,(a,b,fi) in boundary.items():boundary_occurrences[edge(ids[a],ids[b])].append((name,e,(a,b)))
            for mark in panel.get('boundary_marks',[]):
                i=int(mark['vertex_id']);gid=int(mark['source_vertex_id'])
                if i<0 or i>=len(uv) or int(ids[i])!=gid:fail('MARK_SOURCE_MISMATCH',name+':'+str(mark.get('label')));continue
                if i not in {x for e in boundary for x in e}:fail('MARK_NOT_BOUNDARY',name+':'+str(mark.get('label')))
                if mark.get('kind')=='notch':notches[str(mark['label'])].append((name,i,gid))
            grain=panel.get('grainline')
            if not grain:fail('GRAINLINE_MISSING',name)
            else:
                direction=np.asarray(grain.get('direction_2d',[]),float);ref=np.asarray(grain.get('reference_3d',[]),float)
                if direction.shape!=(2,) or not np.isfinite(direction).all() or np.linalg.norm(direction)<1e-12:fail('GRAINLINE_INVALID',name)
                else:
                    anchors=grain.get('anchor_vertex_ids')
                    if anchors is None:fail('GRAINLINE_ANCHOR_MISSING',name)
                    else:
                        i,j=map(int,anchors);mapped=uv[j]-uv[i]
                        cosine=abs(float(np.dot(mapped,direction)/(np.linalg.norm(mapped)*np.linalg.norm(direction))))
                        if not np.isfinite(cosine) or cosine<np.cos(np.deg2rad(1)):fail('GRAINLINE_MAPPED_DIRECTION',name)
                if ref.shape!=(3,) or not np.isfinite(ref).all() or np.linalg.norm(ref)<1e-12:fail('GRAINLINE_REFERENCE_INVALID',name)
                else:
                    if name in ('front','back'):axis=np.array([0.,0,1])
                    else:
                        side='L' if name=='left_sleeve' else 'R';axis=source_vertices[topology['cuffs'][side]].mean(axis=0)-source_vertices[topology['armholes'][side]].mean(axis=0)
                    cosine=abs(float(np.dot(axis,ref)/(np.linalg.norm(axis)*np.linalg.norm(ref))))
                    if cosine<np.cos(np.deg2rad(1)):fail('GRAINLINE_SOURCE_ROLE',name)
            # Face+barycentric identity is required: XYZ alone may be ambiguous.
            weights=np.array([.2,.3,.5]);roundtrip_errors=[]
            for local in faces:
                q2=uv[local];x3=source_vertices[ids[local]];world=weights@x3
                recovered=np.linalg.lstsq(np.vstack([x3.T,np.ones(3)]),np.r_[world,1.],rcond=None)[0]
                roundtrip_errors.append(float(np.linalg.norm(recovered@q2-weights@q2)))
            report={'topology':info,'positive_triangle_count':int((signed>AREA_M2).sum()),'negative_triangle_count':int((signed<-AREA_M2).sum()),
                    'chart_orientation_sign':chart_sign,'flipped_or_collapsed_triangles':int((chart_sign*signed<=AREA_M2).sum()),
                    'barycentric_roundtrip_max_error_m':max(roundtrip_errors),
                    'self_overlap_pairs':overlaps,'metric':metric(uv,faces,source_vertices,ids)}
            panel_reports[name]=report
        except Exception as exc:fail('PANEL_INPUT_INVALID',name+':'+str(exc))
    if face_owners!=Counter({i:1 for i in range(len(source_triangles))}):fail('SOURCE_FACE_COVERAGE','Frozen source faces must occur exactly once, with no omissions or duplicates')
    source_edges=Counter(edge(a,b) for t in source_triangles for a,b in zip(t,np.roll(t,-1)))
    expected_sewn={};open_edges={}
    for e,occurrences in boundary_occurrences.items():
        if source_edges[e]==2:
            if len(occurrences)!=2:fail('CUT_EDGE_MULTIPLICITY',str(e))
            for name,local,_ in occurrences:expected_sewn[(name,local)]=e
        elif source_edges[e]==1:
            if len(occurrences)!=1:fail('OPEN_EDGE_MULTIPLICITY',str(e))
            open_edges[e]=occurrences
        else:fail('UNRECOGNIZED_SOURCE_BOUNDARY',str(e))
    notch_reports=[]
    for label,marks in notches.items():
        gids={x[2] for x in marks}
        if len(gids)!=1:fail('NOTCH_SOURCE_DISAGREEMENT',label)
        elif len(marks)<2:fail('NOTCH_UNPAIRED',label)
        notch_reports.append({'label':label,'marks':marks,'same_source_vertex':len(gids)==1,'paired':len(marks)>=2})
    if not notches:fail('NOTCHES_MISSING','No paired registration notches were declared')
    used_occurrences=Counter();seam_reports=[]
    for seam in pattern.get('seams',[]):
        name=str(seam.get('id',seam.get('label','unnamed')))
        try:
            ea,eb=seam['a'],seam['b'];an,bn=ea['panel'],eb['panel'];av,ai,af,_=parsed[an];bv,bi,bf,_=parsed[bn]
            aa=np.asarray(ea['vertices'],int);bb=np.asarray(eb['vertices'],int)
            if len(aa)<2 or len(aa)!=len(bb):raise ValueError('seam paths require equal,ordered vertices')
            ga,gb=ai[aa],bi[bb]
            if not np.array_equal(ga,gb):fail('SEAM_SOURCE_ORDER',name)
            if 'source_vertex_ids' not in seam or not np.array_equal(ga,seam['source_vertex_ids']):fail('SEAM_DECLARED_SOURCE_CHAIN',name)
            a_lengths=np.linalg.norm(np.diff(av[aa],axis=0),axis=1);b_lengths=np.linalg.norm(np.diff(bv[bb],axis=0),axis=1)
            for local_a,local_b in zip(zip(aa[:-1],aa[1:]),zip(bb[:-1],bb[1:])):
                ka=(an,edge(*local_a));kb=(bn,edge(*local_b));used_occurrences[ka]+=1;used_occurrences[kb]+=1
                if ka not in expected_sewn or kb not in expected_sewn:fail('SEAM_NOT_A_CUT_BOUNDARY',name)
                elif expected_sewn[ka]!=expected_sewn[kb]:fail('SEAM_WRONG_SOURCE_EDGE',name)
            delta=float(a_lengths.sum()-b_lengths.sum());target=float(seam.get('intentional_ease_a_minus_b_m',0.))
            total_tol=max(.002,.005*max(float(a_lengths.sum()),float(b_lengths.sum())))
            local_tol=np.maximum(.001,.02*np.maximum(a_lengths,b_lengths))
            local_delta=np.abs(a_lengths-b_lengths);total_ok=abs(delta-target)<=total_tol
            # Intentional ease must provide local distribution; a total scalar is insufficient.
            local_target=np.asarray(seam.get('intentional_ease_segments_a_minus_b_m',np.zeros(len(a_lengths))),float)
            if local_target.shape!=a_lengths.shape:raise ValueError('ease segment distribution shape mismatch')
            local_ok=bool(np.all(np.abs(a_lengths-b_lengths-local_target)<=local_tol))
            if abs(local_target.sum()-target)>1e-9:fail('EASE_DISTRIBUTION',name)
            if not total_ok:fail('SEAM_TOTAL_LENGTH',name)
            if not local_ok:fail('SEAM_LOCAL_LENGTH',name)
            source_chain=ga;kind='other_cut'
            for side in ('L','R'):
                ring=topology['armholes'][side];ring_edges={edge(a,b) for a,b in zip(ring,ring[1:]+ring[:1])}
                if all(edge(a,b) in ring_edges for a,b in zip(source_chain[:-1],source_chain[1:])):kind='armhole_'+side
            seam_reports.append({'id':name,'inferred_kind':kind,'a_panel':an,'b_panel':bn,'a_length_mm':float(a_lengths.sum()*1000),'b_length_mm':float(b_lengths.sum()*1000),
                                 'ease_assumption':'EXPLICIT_TARGET' if 'intentional_ease_a_minus_b_m' in seam else 'ZERO_ONLY_FOR_REVERSIBLE_TRANSFER_DIAGNOSTIC',
                                 'intentional_ease_a_minus_b_mm':target*1000,'total_difference_mm':delta*1000,'total_tolerance_mm':total_tol*1000,
                                 'max_segment_difference_mm':float(local_delta.max()*1000),'segment_count':len(a_lengths),'source_order_matches':bool(np.array_equal(ga,gb)),
                                 'total_length_pass':bool(total_ok),'local_length_pass':bool(local_ok)})
        except Exception as exc:fail('SEAM_INPUT_INVALID',name+':'+str(exc))
    missing=[{'panel':k[0],'local_edge':list(k[1]),'source_edge':list(e)} for k,e in expected_sewn.items() if used_occurrences[k]!=1]
    if missing:fail('CUT_EDGE_COVERAGE',f'{len(missing)}cut-side edges missing or repeated')
    if not seam_reports:fail('SEAMS_MISSING','No valid seam records')
    mapping_codes={'UNITS','EMBEDDED_SOURCE_MISMATCH','PANEL_SET','SOURCE_PANEL_ROLE','SOURCE_TRIANGLE_MAPPING','SOURCE_FACE_COVERAGE','PANEL_INPUT_INVALID','DECLARED_BOUNDARY_MISMATCH','CUT_EDGE_MULTIPLICITY','OPEN_EDGE_MULTIPLICITY','UNRECOGNIZED_SOURCE_BOUNDARY','MARK_SOURCE_MISMATCH','MARK_NOT_BOUNDARY','NOTCH_SOURCE_DISAGREEMENT','NOTCH_UNPAIRED','NOTCHES_MISSING','SEAM_SOURCE_ORDER','SEAM_DECLARED_SOURCE_CHAIN','SEAM_NOT_A_CUT_BOUNDARY','SEAM_WRONG_SOURCE_EDGE','SEAM_INPUT_INVALID','CUT_EDGE_COVERAGE','SEAMS_MISSING','GRAINLINE_MISSING','GRAINLINE_INVALID','GRAINLINE_ANCHOR_MISSING','GRAINLINE_MAPPED_DIRECTION','GRAINLINE_REFERENCE_INVALID','GRAINLINE_SOURCE_ROLE'}
    flat_codes={'PANEL_SET','PANEL_INPUT_INVALID','PANEL_NOT_DISK','PANEL_FLIP_OR_COLLAPSE','PANEL_SELF_OVERLAP'}
    seam_codes={'SEAM_TOTAL_LENGTH','SEAM_LOCAL_LENGTH','EASE_DISTRIBUTION'}|mapping_codes
    transfer=not any(e['code'] in mapping_codes for e in errors);flat=not any(e['code'] in flat_codes for e in errors)
    compatible=not any(e['code'] in seam_codes for e in errors)
    return {'schema_version':1,'verifier':'independent flat panel/source/seam audit','PATTERN_TRANSFER_PASS':transfer,'FLAT_PANEL_VALIDITY_PASS':flat,
            'SEAM_COMPATIBILITY_PASS':compatible,'SEAM_COMPATIBILITY_DECISION':'PASS_UNDER_DECLARED_OR_ZERO_EASE_TARGET' if compatible else 'CONDITIONAL_FAIL_UNDER_DECLARED_OR_ZERO_EASE_TARGET',
            'MANUFACTURING_COMPATIBILITY':'UNDETERMINED_EASE_AND_FABRIC','ASSEMBLY_IDENTITY_ONLY':'Stored source vertex/face identity checked; this is not2Dsewing orfit.',
            'TWO_D_SEW_SIM':'NOT_RUN','THREE_D_WEARING':'NOT_RUN','PHYSICAL_FIT':'NOT_RUN','material_allowable_strain':'UNKNOWN_UNCALIBRATED',
            'verdict':'PASS' if transfer and flat and compatible else 'FAIL','errors':errors,'panels':panel_reports,'seams':seam_reports,
            'notches':notch_reports,'missing_or_duplicate_cut_edges':missing,'source_face_count':len(source_triangles),'covered_source_faces':len(face_owners),
            'cut_edge_side_count':len(expected_sewn),'open_boundary_edge_count':len(open_edges),
            'threshold_policy':{'seam_total':'max(2mm,0.5% longer seam), around explicitly declared ease target','seam_segment':'max(1mm,2% corresponding segment), around declared local ease','scope':'Engineering transfer diagnostics, not universal sewing/fabric-fit tolerances.'}}


def metamorphic_controls(pattern,source_vertices,source_triangles,topology):
    baseline=verify(pattern,source_vertices,source_triangles,topology);base_seams={s['id']:s for s in baseline['seams']};rows=[]
    angle=.63;rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    for name,transform,offset in [('rigid_atlas_rotation_translation',rotation,np.array([1.2,-.7])),('uniform_chart_reflection',np.array([[-1.,0],[0,1.]]),np.zeros(2))]:
        p=deepcopy(pattern)
        for panel in p['panels'].values():
            panel['vertices_2d_m']=(np.asarray(panel['vertices_2d_m'])@transform.T+offset).tolist()
            panel['grainline']['direction_2d']=(transform@np.asarray(panel['grainline']['direction_2d'])).tolist()
        result=verify(p,source_vertices,source_triangles,topology)
        seam_error=max(abs(s[key]-base_seams[s['id']][key]) for s in result['seams'] for key in ['a_length_mm','b_length_mm','total_difference_mm','max_segment_difference_mm'])
        same_codes={e['code'] for e in result['errors']}=={e['code'] for e in baseline['errors']}
        passed=bool(result['PATTERN_TRANSFER_PASS']==baseline['PATTERN_TRANSFER_PASS'] and result['FLAT_PANEL_VALIDITY_PASS']==baseline['FLAT_PANEL_VALIDITY_PASS'] and same_codes and seam_error<1e-7)
        rows.append({'case':name,'passed':passed,'maximum_seam_metric_change_mm':seam_error,'same_failure_codes_as_baseline':same_codes,
                     'baseline_conditional_verdict':baseline['verdict'],'transformed_conditional_verdict':result['verdict']})
    return {'cases':rows,'all_invariants_passed':all(r['passed'] for r in rows),
            'meaning':'Whole-chart reflection changes orientation convention, not flattening validity; source roles and boundary correspondences remain fixed.'}


def negatives(pattern,source_vertices,source_triangles,topology):
    cases=[];baseline=verify(pattern,source_vertices,source_triangles,topology);base_codes={e['code'] for e in baseline['errors']}
    base_seams={s['id']:s for s in baseline['seams']}
    def add(name,change,expected_codes,effect=None):
        p=deepcopy(pattern);change(p);r=verify(p,source_vertices,source_triangles,topology);codes=sorted({e['code'] for e in r['errors']})
        new_codes=sorted(set(codes)-base_codes);witness=effect(r) if effect else None
        specific=bool(set(expected_codes)&set(new_codes)) if effect is None else bool(witness['injected_effect_detected'])
        cases.append({'case':name,'rejected':r['verdict']=='FAIL','expected_failure_codes':expected_codes,'observed_failure_codes':codes,
                      'new_failure_codes_vs_baseline':new_codes,'injected_effect_witness':witness,'expected_failure_detected':specific,
                      'summary':{k:r[k] for k in ['PATTERN_TRANSFER_PASS','FLAT_PANEL_VALIDITY_PASS','SEAM_COMPATIBILITY_PASS']}})
    def swap(p):p['panels']['left_sleeve'],p['panels']['right_sleeve']=p['panels']['right_sleeve'],p['panels']['left_sleeve']
    add('left_right_source_labels_swapped',swap,['SOURCE_PANEL_ROLE'])
    def scaled(p):p['panels']['left_sleeve']['vertices_2d_m']=(np.array(p['panels']['left_sleeve']['vertices_2d_m'])*1.20).tolist()
    def scale_effect(r):
        ratios=[];before=[];after=[]
        for s in r['seams']:
            old=base_seams[s['id']]
            if s['a_panel']=='left_sleeve':ratios.append(s['a_length_mm']/old['a_length_mm'])
            if s['b_panel']=='left_sleeve':ratios.append(s['b_length_mm']/old['b_length_mm'])
            if s['inferred_kind']=='armhole_L':before.append(abs(old['total_difference_mm']));after.append(abs(s['total_difference_mm']))
        return {'injected_effect_detected':bool(ratios and all(abs(x-1.2)<1e-10 for x in ratios) and max(after)>max(before)+10),
                'measured_sleeve_edge_scale_ratios':ratios,'baseline_max_left_armhole_gap_mm':max(before),'modified_max_left_armhole_gap_mm':max(after)}
    add('sleeve_scaled20percent',scaled,['SEAM_TOTAL_LENGTH','SEAM_LOCAL_LENGTH'],scale_effect)
    local_probe={}
    def local_without_total_change(p):
        seam=next(s for s in p['seams'] if s['id']=='armhole_L_back');end=seam['b'];name=end['panel'];chain=end['vertices'];k=len(chain)//2
        uv=np.array(p['panels'][name]['vertices_2d_m']);a,b=uv[chain[k-1]],uv[chain[k+1]];old=uv[chain[k]];center=(a+b)/2
        axis=(b-a)/np.linalg.norm(b-a);perp=np.array([-axis[1],axis[0]]);major=(np.linalg.norm(old-a)+np.linalg.norm(old-b))/2
        focal=np.linalg.norm(b-a)/2;minor=np.sqrt(max(0,major*major-focal*focal));theta=.45
        uv[chain[k]]=center+major*np.cos(theta)*axis+minor*np.sin(theta)*perp
        p['panels'][name]['vertices_2d_m']=uv.tolist();local_probe.update(seam_id=seam['id'],panel=name,edited_vertex=chain[k])
    def local_effect(r):
        s=next(s for s in r['seams'] if s['id']==local_probe['seam_id']);old=base_seams[s['id']]
        drift=abs(s['b_length_mm']-old['b_length_mm']);increase=s['max_segment_difference_mm']-old['max_segment_difference_mm']
        return {'injected_effect_detected':bool(drift<1e-6 and increase>3),
                'total_sleeve_chain_length_change_mm':drift,'baseline_local_mismatch_mm':old['max_segment_difference_mm'],
                'modified_local_mismatch_mm':s['max_segment_difference_mm'],'local_mismatch_increase_mm':increase,
                'meaning':'The complete seam arclength is unchanged; local matched-edge lengths changed.'}
    add('local_balance_changed_but_total_arclength_preserved',local_without_total_change,['SEAM_LOCAL_LENGTH'],local_effect)
    def missing(p):p['seams'].pop(0)
    add('missing_seam',missing,['CUT_EDGE_COVERAGE'])
    def reverse(p):p['seams'][0]['b']['vertices'].reverse()
    add('one_seam_reversed',reverse,['SEAM_SOURCE_ORDER','SEAM_WRONG_SOURCE_EDGE'])
    def notch(p):
        for panel in p['panels'].values():
            for mark in panel.get('boundary_marks',[]):
                if mark.get('kind')=='notch':mark['source_vertex_id']+=1;return
        raise ValueError('No notch available')
    add('notch_source_moved',notch,['MARK_SOURCE_MISMATCH'])
    def absent(p):p['panels']['front']['faces'].pop(0);p['panels']['front']['source_face_ids'].pop(0)
    add('source_triangle_missing',absent,['SOURCE_FACE_COVERAGE','SOURCE_PANEL_ROLE'])
    def grain(p):p['panels']['front']['grainline']['direction_2d']=[1.,0.]
    add('grainline_rotated90degrees',grain,['GRAINLINE_MAPPED_DIRECTION'])
    def no_grain(p):p['panels']['front'].pop('grainline',None)
    add('grainline_missing',no_grain,['GRAINLINE_MISSING'])
    return {'baseline_verdict':baseline['verdict'],'baseline_failure_codes':sorted(base_codes),'cases':cases,
            'all_faults_detected':all(r['rejected'] and r['expected_failure_detected'] for r in cases),
            'limits':'Baseline already has conditional seam-length FAIL, so rejection alone is not counted as fault detection. Each control needs a new specific code or a measured injected differential. Same-fixture injection is not a blind accuracy estimate. L/R checks declared source identity; symmetric physical sleeves may be interchangeable.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pattern',type=Path,required=True);p.add_argument('--source-topology',type=Path,required=True);p.add_argument('--source-frame',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--negative-controls',action='store_true')
    args=p.parse_args();started=time.monotonic();args.out.parent.mkdir(parents=True,exist_ok=True)
    tests=analytic_tests();args.out.with_name(args.out.stem+'-analytic-first.json').write_text(json.dumps(tests,indent=2)+'\n')
    pattern=json.loads(args.pattern.read_text());top=json.loads(args.source_topology.read_text());source=np.asarray(top['rest_vertices'],float)
    with np.load(args.source_frame) as f:tri=np.asarray(f['cloth_triangles'],int)
    result=verify(pattern,source,tri,top)
    result['analytic_tests']=tests
    result['inputs']={'pattern_sha256':sha(args.pattern),'source_topology_sha256':sha(args.source_topology),'source_frame_sha256':sha(args.source_frame),'verifier_sha256':sha(__file__)}
    if args.negative_controls:
        result['negative_controls']=negatives(pattern,source,tri,top)
        result['metamorphic_controls']=metamorphic_controls(pattern,source,tri,top)
    result['elapsed_seconds']=time.monotonic()-started;args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['panels','seams','notches','errors','missing_or_duplicate_cut_edges','negative_controls','metamorphic_controls']}));print(json.dumps({'errors':result['errors'],'negative_controls':result.get('negative_controls'),'metamorphic_controls':result.get('metamorphic_controls')}))
    if result['verdict']!='PASS':raise SystemExit(2)


if __name__=='__main__':main()
