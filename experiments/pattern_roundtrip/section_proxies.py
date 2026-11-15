"""Cautious actual-mesh upper-arm section proxies; never an anatomical-fit gate.

The known one-shot path starts0.10m inside its shoulder bone point. Planes at
0.12m/0.22m outside that proxy point are experimental sections, not armholes.
No unwrap, garment verifier, Blender or mathutils implementation is imported.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np

EPS=1e-7


def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]


def point_segment_distances(points,a,b):
    points=np.asarray(points,float);d=b-a;den=np.sum(d*d,axis=1)
    t=np.sum((points[:,None]-a[None])*d[None],axis=2)/np.maximum(den[None],1e-300)
    delta=points[:,None]-(a[None]+np.clip(t,0,1)[...,None]*d[None])
    return np.linalg.norm(delta,axis=2)


def segment_relations(a,b,c,d,eps=EPS):
    """All-pair proper crossing, touching and positive collinear overlap masks."""
    ab=b-a;cd=d-c
    s1=cross(ab[:,None],c[None]-a[:,None]);s2=cross(ab[:,None],d[None]-a[:,None])
    t1=cross(cd[None],a[:,None]-c[None]);t2=cross(cd[None],b[:,None]-c[None])
    at=eps*np.linalg.norm(ab,axis=1)[:,None];bt=eps*np.linalg.norm(cd,axis=1)[None]
    proper=(((s1>at)&(s2<-at))|((s1<-at)&(s2>at)))&(((t1>bt)&(t2<-bt))|((t1<-bt)&(t2>bt)))
    distances=np.minimum.reduce([point_segment_distances(a,c,d),point_segment_distances(b,c,d),
                                point_segment_distances(c,a,b).T,point_segment_distances(d,a,b).T])
    touching=distances<=eps
    collinear=(np.abs(s1)<=at)&(np.abs(s2)<=at)&(np.abs(t1)<=bt)&(np.abs(t2)<=bt)
    unit=ab/np.maximum(np.linalg.norm(ab,axis=1)[:,None],1e-300)
    p=np.sum((c[None]-a[:,None])*unit[:,None],axis=2);q=np.sum((d[None]-a[:,None])*unit[:,None],axis=2)
    overlap=np.minimum(np.linalg.norm(ab,axis=1)[:,None],np.maximum(p,q))-np.maximum(0,np.minimum(p,q))
    return proper,touching,collinear&(overlap>eps),distances


def classify_points(points,polygon,eps=EPS):
    """-1 outside,0 boundary,+1 interior; simple closed polygon required."""
    points=np.asarray(points,float);p=np.asarray(polygon,float);a=p;b=np.roll(p,-1,axis=0)
    boundary=point_segment_distances(points,a,b).min(axis=1)<=eps
    x,y=points[:,0,None],points[:,1,None];ay,by=a[None,:,1],b[None,:,1]
    active=(ay>y)!=(by>y)
    denominator=np.where(active,by-ay,1.)
    ix=a[None,:,0]+(y-ay)*(b[None,:,0]-a[None,:,0])/denominator
    inside=np.sum(active&(x<ix),axis=1)%2==1
    return np.where(boundary,0,np.where(inside,1,-1))


def simple_polygon(points):
    p=np.asarray(points,float);n=len(p)
    if n<3:return False,{'reason':'fewer than3vertices'}
    a=p;b=np.roll(p,-1,axis=0);proper,touch,overlap,_=segment_relations(a,b,a,b)
    mask=np.triu(np.ones((n,n),bool),1)
    for i in range(n):mask[i,(i+1)%n]=False;mask[(i+1)%n,i]=False
    bad=mask&(proper|touch|overlap)
    area=abs(float(np.sum(cross(p,np.roll(p,-1,axis=0)))/2))
    return bool(not bad.any() and area>EPS**2),{'nonadjacent_intersection_pairs':np.argwhere(bad).tolist(),'area_m2':area}


def plane_basis(normal):
    n=np.asarray(normal,float);n/=np.linalg.norm(n)
    helper=np.array([0.,1,0]) if abs(n[1])<.9 else np.array([1.,0,0])
    u=np.cross(n,helper);u/=np.linalg.norm(u);v=np.cross(n,u)
    return n,u,v


def mesh_section(vertices,triangles,origin,normal,eps=EPS):
    """Actual triangle/plane intersections, endpoint graph, all components."""
    vertices=np.asarray(vertices,float);triangles=np.asarray(triangles,int)
    if not np.isfinite(vertices).all():raise ValueError('Nonfinite mesh vertices')
    n,u,v=plane_basis(normal);tri=vertices[triangles];dist=(tri-origin)@n
    candidates=np.flatnonzero((dist.min(axis=1)<=eps)&(dist.max(axis=1)>=-eps))
    segments=[];coplanar=[];point_tangencies=0;ambiguous_triangles=[]
    for index in candidates:
        points=tri[index];ds=dist[index]
        if np.all(np.abs(ds)<=eps):coplanar.append(int(index));continue
        hits=[]
        for i,j in [(0,1),(1,2),(2,0)]:
            if abs(ds[i])<=eps:hits.append(points[i])
            if (ds[i]>eps and ds[j]<-eps) or (ds[i]<-eps and ds[j]>eps):hits.append(points[i]+ds[i]/(ds[i]-ds[j])*(points[j]-points[i]))
        unique=[]
        for point in hits:
            if not any(np.linalg.norm(point-q)<=eps for q in unique):unique.append(point)
        if len(unique)==2 and np.linalg.norm(unique[0]-unique[1])>eps:segments.append(unique)
        elif len(unique)==1:point_tangencies+=1
        elif len(unique)>2:ambiguous_triangles.append(int(index))
    points=[];bins={};edges=set();duplicate_segments=0
    def node(point):
        q=np.array([np.dot(point-origin,u),np.dot(point-origin,v)])
        key=tuple(np.floor(q/eps).astype(int))
        for dx in [-1,0,1]:
            for dy in [-1,0,1]:
                for i in bins.get((key[0]+dx,key[1]+dy),[]):
                    if np.linalg.norm(points[i]-q)<=eps:return i
        i=len(points);points.append(q);bins.setdefault(key,[]).append(i);return i
    for a,b in segments:
        i,j=node(a),node(b)
        if i==j:continue
        edge=tuple(sorted((i,j)))
        duplicate_segments+=int(edge in edges);edges.add(edge)
    graph={i:set() for edge in edges for i in edge}
    for i,j in edges:graph[i].add(j);graph[j].add(i)
    unseen=set(graph);components=[]
    while unseen:
        todo=[unseen.pop()];ids=[]
        while todo:
            i=todo.pop();ids.append(i)
            for j in graph[i]:
                if j in unseen:unseen.remove(j);todo.append(j)
        degrees={i:len(graph[i]) for i in ids};closed=all(d==2 for d in degrees.values()) and len(ids)>=3
        branch=any(d>2 for d in degrees.values());ends=[i for i,d in degrees.items() if d==1]
        ordered=[]
        if closed or (not branch and len(ends)==2):
            start=min(ids) if closed else min(ends);previous=None;current=start
            for _ in range(len(ids)+1):
                ordered.append(current);nxt=sorted(graph[current]-({previous} if previous is not None else set()))
                if not nxt:break
                following=nxt[0]
                if following==start:break
                previous,current=current,following
        else:ordered=sorted(ids)
        poly=np.asarray([points[i] for i in ordered]);simple,detail=simple_polygon(poly) if closed else (False,{'reason':'open or branching component'})
        index=len(components);contains=int(classify_points([[0,0]],poly)[0]) if closed and simple else None
        local_edges=[(i,j) for i,j in edges if i in degrees and j in degrees]
        perimeter=sum(np.linalg.norm(points[i]-points[j]) for i,j in local_edges)
        components.append({'index':index,'closed':closed,'branching':branch,'simple':simple,'node_count':len(ids),
            'degree_counts':{str(d):list(degrees.values()).count(d) for d in sorted(set(degrees.values()))},
            'perimeter_mm':float(perimeter*1000),'axis_point_classification':contains,
            'coordinates_plane_m':poly.tolist(),'coordinates_world_m':[(origin+q[0]*u+q[1]*v).tolist() for q in poly],
            'edges_local_component_node_ids':[[ordered.index(i),ordered.index(j)] for i,j in local_edges],
            'polygon_audit':detail})
    qualifying=[c['index'] for c in components if c['closed'] and c['simple'] and c['axis_point_classification']==1]
    boundary=[c['index'] for c in components if c['axis_point_classification']==0]
    unresolved=bool(coplanar or ambiguous_triangles or any(not c['closed'] or not c['simple'] for c in components))
    if len(qualifying)>1:status='AMBIGUOUS_MULTIPLE_CONTAINING_LOOPS'
    elif boundary:status='AMBIGUOUS_AXIS_ON_BOUNDARY'
    elif unresolved:status='AMBIGUOUS_OPEN_BRANCH_COPLANAR_OR_NONSIMPLE'
    elif not qualifying:status='UNRESOLVED_NO_CONTAINING_LOOP'
    else:status='DEFINED_LOCAL_SECTION_PROXY'
    return {'status':status,'selected_loop_index':qualifying[0] if status=='DEFINED_LOCAL_SECTION_PROXY' else None,
        'unique_local_candidate_for_diagnostics':qualifying[0] if len(qualifying)==1 else None,
        'containing_loop_indices':qualifying,'containing_loop_count':len(qualifying),'axis_on_boundary_loops':boundary,
        'closed_loop_count':sum(c['closed'] for c in components),'component_count':len(components),
        'open_or_branch_component_count':sum(not c['closed'] or c['branching'] for c in components),
        'coplanar_triangle_count':len(coplanar),'ambiguous_triangle_count':len(ambiguous_triangles),
        'point_tangent_triangle_count':point_tangencies,'raw_segment_count':len(segments),'duplicate_segments_deduplicated':duplicate_segments,
        'components':components,'selection_policy':'Unique simple closed loop strictly containing the unchanged projected bone-axis point; any global open/branch/coplanar uncertainty blocks a defined proxy.'}


def contour_comparison(body_poly,cloth_poly):
    b=np.asarray(body_poly,float);c=np.asarray(cloth_poly,float)
    proper,touch,overlap,distance=segment_relations(b,np.roll(b,-1,axis=0),c,np.roll(c,-1,axis=0))
    classification=classify_points(b,c)
    minimum=0. if proper.any() or touch.any() or overlap.any() else float(distance.min())
    strictly=bool(np.all(classification==1) and not (proper|touch|overlap).any())
    including_contact=bool(np.all(classification>=0) and not proper.any())
    return {'body_vertex_count':len(b),'body_vertices_inside_cloth':int(np.sum(classification==1)),
        'body_vertices_on_cloth_boundary':int(np.sum(classification==0)),'body_vertices_outside_cloth':int(np.sum(classification==-1)),
        'proper_segment_crossing_pairs':int(proper.sum()),'boundary_contact_pairs':int(touch.sum()),'collinear_overlap_pairs':int(overlap.sum()),
        'body_section_strictly_inside_cloth':strictly,'body_section_enclosed_or_touching':including_contact,
        'minimum_unsigned_boundary_distance_mm':minimum*1000,
        'signed_clearance_convention':'Positive only after strict enclosure; zero at boundary contact/crossing; negative for separated or outside contours. This sign is diagnostic, not a fitting tolerance.',
        'diagnostic_signed_boundary_distance_mm':minimum*1000 if strictly else 0. if minimum==0 else -minimum*1000}


def all_simple_loop_min_gap(body,cloth):
    values=[]
    for a in body['components']:
        if not a['closed'] or not a['simple']:continue
        for b in cloth['components']:
            if b['closed'] and b['simple']:values.append(contour_comparison(a['coordinates_plane_m'],b['coordinates_plane_m'])['minimum_unsigned_boundary_distance_mm'])
    return min(values) if values else None


def run_case(data,translation):
    bv=data['body_vertices']+translation;cv=data['cloth_vertices'];records=[]
    for side in ['L','R']:
        path=data['path_'+side];direction=path[-1]-path[0];direction/=np.linalg.norm(direction)
        deviation=float(np.linalg.norm(np.cross(path-path[0],direction),axis=1).max())
        if deviation>1e-6:raise ValueError('This proxy implementation requires the declared straight one-shot arm path')
        shoulder=path[0]+.10*direction
        for offset in [.12,.22]:
            origin=shoulder+offset*direction;body=mesh_section(bv,data['body_triangles'],origin,direction);cloth=mesh_section(cv,data['cloth_triangles'],origin,direction)
            bi=body['selected_loop_index'];ci=cloth['selected_loop_index'];comparison=None
            if bi is not None and ci is not None:comparison=contour_comparison(body['components'][bi]['coordinates_plane_m'],cloth['components'][ci]['coordinates_plane_m'])
            diagnostic=None;dbi=body['unique_local_candidate_for_diagnostics'];dci=cloth['unique_local_candidate_for_diagnostics']
            if comparison is None and dbi is not None and dci is not None:
                diagnostic=contour_comparison(body['components'][dbi]['coordinates_plane_m'],cloth['components'][dci]['coordinates_plane_m'])
            association=bool(body['containing_loop_count']==1 and body['status']=='DEFINED_LOCAL_SECTION_PROXY')
            records.append({'side':side,'shoulder_bone_proxy_m':shoulder.tolist(),'offset_outside_shoulder_proxy_m':offset,
                'plane_origin_m':origin.tolist(),'plane_normal':direction.tolist(),'path_collinearity_max_error_m':deviation,
                'body':body,'cloth':cloth,'body_axis_association':association,'defined_proxy_comparison':comparison,
                'conditional_local_candidate_diagnostic':diagnostic,'all_simple_loops_minimum_unsigned_gap_mm':all_simple_loop_min_gap(body,cloth),
                'geometric_enclosure_supported':bool(association and comparison is not None and comparison['body_section_enclosed_or_touching']),
                'fit_verdict':'UNKNOWN','interpretation':'Experimental local upper-arm cross-section only. Not a human armhole measurement, full shoulder/axilla envelope, or comfort test.'})
    return records


def self_tests():
    rows=[]
    def check(name,value):
        if not value:raise AssertionError(name)
        rows.append({'name':name,'passed':True})
    outer=np.array([[-1,-1],[1,-1],[1,1],[-1,1]],float);inner=outer*.5
    a=contour_comparison(inner,outer);check('nested_square_enclosure_and_half_metre_gap',a['body_section_strictly_inside_cloth'] and abs(a['minimum_unsigned_boundary_distance_mm']-500)<1e-8)
    a=contour_comparison(inner+[0,3],outer);check('separated_positive_unsigned_gap_is_not_enclosure',not a['body_section_enclosed_or_touching'] and a['minimum_unsigned_boundary_distance_mm']>0 and a['diagnostic_signed_boundary_distance_mm']<0)
    a=contour_comparison(inner+[1,0],outer);check('partly_outside_body_detected',not a['body_section_enclosed_or_touching'])
    concave=np.array([[-2,-2],[2,-2],[2,2],[1,2],[1,-1],[-1,-1],[-1,2],[-2,2]],float)
    bridge=np.array([[-1.5,-.5],[1.5,-.5],[1.5,.5],[-1.5,.5]],float)
    a=contour_comparison(bridge,concave);check('all_vertices_inside_is_insufficient_when_edges_cross_concavity',a['body_vertices_inside_cloth']==4 and a['proper_segment_crossing_pairs']>0 and not a['body_section_enclosed_or_touching'])
    check('bowtie_is_not_simple',not simple_polygon(np.array([[0,0],[1,1],[0,1],[1,0]],float))[0])
    v=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],float)
    t=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    s=mesh_section(v,t,np.zeros(3),[0,0,1]);check('actual_cube_triangle_plane_section_unique_closed',s['status']=='DEFINED_LOCAL_SECTION_PROXY' and s['closed_loop_count']==1)
    c=s['components'][s['selected_loop_index']];check('cube_section_area_and_perimeter',abs(c['perimeter_mm']-8000)<1e-6 and abs(c['polygon_audit']['area_m2']-4)<1e-10)
    s=mesh_section(v+[0,3,0],t,np.zeros(3),[0,0,1]);check('translated_cube_axis_association_rejected',s['containing_loop_count']==0 and s['selected_loop_index'] is None)
    both=np.concatenate([v,v*.5]);tri=np.concatenate([t,t+8]);s=mesh_section(both,tri,np.zeros(3),[0,0,1]);check('multiple_containing_loops_are_ambiguous',s['status']=='AMBIGUOUS_MULTIPLE_CONTAINING_LOOPS')
    s=mesh_section(v,t[:-2],np.zeros(3),[0,0,1]);check('open_mesh_section_not_closed_artificially',s['open_or_branch_component_count']>0 and s['selected_loop_index'] is None)
    return {'test_count':len(rows),'all_passed':True,'tests':rows}


def plot_case(records,path,title):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(12,10))
    for ax,row in zip(axes.flat,records):
        for label,section,color in [('body',row['body'],'#b56e3d'),('cloth',row['cloth'],'#087e8b')]:
            once=True
            for c in section['components']:
                q=np.array(c['coordinates_plane_m'])*1000
                if c['closed']:q=np.vstack([q,q[0]])
                ax.plot(q[:,0],q[:,1],color=color,linewidth=1.4,label=label if once else None);once=False
        ax.scatter([0],[0],c='#b00020',marker='+',s=65,label='unchanged bone-axis point')
        ax.set_title(f"{row['side']} / offset {row['offset_outside_shoulder_proxy_m']*1000:.0f}mm\nbody: {row['body']['status']}\ncloth: {row['cloth']['status']}",fontsize=8)
        ax.set_aspect('equal',adjustable='box');ax.set_xlabel('plane u (mm)');ax.set_ylabel('plane v (mm)');ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle(title+'\nLOCAL PROXIES ONLY — FIT UNKNOWN',fontsize=12);fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(path.with_suffix('.png'),dpi=160);fig.savefig(path.with_suffix('.svg'));plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pair',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);tests=self_tests();(a.out/'analytic-first.json').write_text(json.dumps(tests,indent=2)+'\n')
    with np.load(a.pair) as f:data={k:f[k].copy() for k in ['body_vertices','body_triangles','cloth_vertices','cloth_triangles','path_L','path_R']}
    baseline=run_case(data,np.zeros(3));negative=run_case(data,np.array([0.,2.,0.]))
    rejected=all(not r['body_axis_association'] and not r['geometric_enclosure_supported'] for r in negative)
    positive_distance=any(r['all_simple_loops_minimum_unsigned_gap_mm'] is not None and r['all_simple_loops_minimum_unsigned_gap_mm']>0 for r in negative)
    report={'schema_version':1,'units':'metres, report distances explicitly marked mm','epsilon_m':EPS,
        'source_pair_sha256':hashlib.sha256(a.pair.read_bytes()).hexdigest(),'source_python_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'path_contract':'One-shot generator stores path from shoulder-0.10m through shoulder+0.71m. Shoulder is reconstructed from the unchanged path, not measured anatomy.',
        'section_offsets_m':[.12,.22],'baseline':baseline,'negative_body_translation_m':[0,2,0],'negative_stale_paths':negative,
        'negative_control':{'all_four_body_associations_and_enclosures_rejected':rejected,'at_least_one_positive_unsigned_distance_exists':positive_distance,
                            'passed':bool(rejected and positive_distance),'explanation':'A positive unsigned gap between separated curves cannot establish wearing or fit.'},
        'fit_verdict':'UNKNOWN','physical_fit':'NOT_RUN','limits':['No anatomical acromion or axillary-fold landmarks supplied.','Local cross-sections do not represent the full shoulder/axillary motion envelope.','Seam/cap arc length is not a target upper-arm circumference.','Missing, open, branching, nonsimple or multiple containing contours remain unresolved.','No material calibration, style-specific clearance threshold or comfort claim.']}
    (a.out/'section-proxies.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');plot_case(baseline,a.out/'baseline','Actual body/cloth triangle-plane sections');plot_case(negative,a.out/'negative-stale-paths','Actual body translated2m; paths retained')
    compact={'tests':tests['test_count'],'negative_control':report['negative_control'],'sections':[{'side':r['side'],'offset_m':r['offset_outside_shoulder_proxy_m'],'body_status':r['body']['status'],'cloth_status':r['cloth']['status'],'comparison':r['defined_proxy_comparison'],'diagnostic':r['conditional_local_candidate_diagnostic']} for r in baseline]}
    print(json.dumps(compact),flush=True)
    if not report['negative_control']['passed']:raise SystemExit(2)


if __name__=='__main__':main()
