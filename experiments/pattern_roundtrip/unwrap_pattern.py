"""Cut a frozen one-shot garment into four disks and flatten its actual rest metric.

Python CLI: --topology TOPOLOGY.json --source-frame FRAME.npz --out FRESH_DIR
The UV coordinates are solved by LSCM followed by local/global ARAP. No body,
legacy checker, Blender parameterization, or cloth solver is imported. These
are reverse-engineered seam-line panels; no manufacturing/physical-fit PASS.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib,heapq,json,math
from pathlib import Path
import time
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import lsqr,factorized


def edges_of(face):
    return [(int(face[i]),int(face[(i+1)%3])) for i in range(3)]


def cut_panel(vertices,triangles,face_ids,cut_edges):
    selected=triangles[face_ids];parents=list(range(3*len(selected)))
    def root(x):
        while parents[x]!=x:parents[x]=parents[parents[x]];x=parents[x]
        return x
    def union(a,b):
        a,b=root(a),root(b)
        if a!=b:parents[b]=a
    incidence=defaultdict(list)
    for f,tri in enumerate(selected):
        for i in range(3):
            a,b=int(tri[i]),int(tri[(i+1)%3]);incidence[tuple(sorted((a,b)))].append((f,i))
    for edge,entries in incidence.items():
        if len(entries)==2 and edge not in cut_edges:
            (a,_),(b,_)=entries
            for vertex in edge:
                ia=int(np.flatnonzero(selected[a]==vertex)[0]);ib=int(np.flatnonzero(selected[b]==vertex)[0])
                union(3*a+ia,3*b+ib)
    local={};source=[];faces=[]
    for f,tri in enumerate(selected):
        face=[]
        for i,vertex in enumerate(tri):
            k=root(3*f+i)
            if k not in local:local[k]=len(source);source.append(int(vertex))
            face.append(local[k])
        faces.append(face)
    return np.asarray(source,int),np.asarray(faces,int)


def boundary_data(faces,n):
    counts=Counter(tuple(sorted(e)) for tri in faces for e in edges_of(tri))
    graph=defaultdict(list)
    for (a,b),count in counts.items():
        if count==1:graph[a].append(b);graph[b].append(a)
    if any(len(x)!=2 for x in graph.values()):raise ValueError('Cut has branching or open boundary')
    loops=[];unseen=set(graph)
    while unseen:
        start=min(unseen);loop=[start];previous=None;current=start
        while True:
            choices=[x for x in graph[current] if x!=previous]
            nxt=min(choices) if previous is None else choices[0]
            if nxt==start:break
            if nxt in loop:raise ValueError('Boundary repeats before closing')
            loop.append(nxt);previous,current=current,nxt
        unseen-=set(loop);loops.append(loop)
    adjacency=[set() for _ in range(n)]
    for a,b in counts:adjacency[a].add(b);adjacency[b].add(a)
    visited=set();components=0
    for start in range(n):
        if start in visited:continue
        components+=1;stack=[start];visited.add(start)
        while stack:
            i=stack.pop()
            for j in adjacency[i]:
                if j not in visited:visited.add(j);stack.append(j)
    report={'vertices':n,'edges':len(counts),'faces':len(faces),'components':components,
            'boundary_loops':len(loops),'euler':n-len(counts)+len(faces),'nonmanifold_edges':sum(c>2 for c in counts.values())}
    report['disk']=components==1 and len(loops)==1 and report['euler']==1 and not report['nonmanifold_edges']
    return loops,counts,report


def underarm_path(v,t,ids,armhole,cuff):
    boundary=np.asarray(armhole,int);ring=v[boundary]
    # The source's bottom armhole arc contains a unique central y=0 underarm point.
    lowest=ring[:,2].min();eligible=np.flatnonzero(abs(ring[:,2]-lowest)<1e-6)
    start=int(boundary[eligible[np.argmin(abs(ring[eligible,1]))]])
    cuff=np.asarray(cuff,int);end=int(cuff[np.argmin(v[cuff,2])])
    graph=defaultdict(dict)
    for tri in t[ids]:
        for a,b in edges_of(tri):
            length=float(np.linalg.norm(v[a]-v[b]));graph[a][b]=length;graph[b][a]=length
    distance={start:0.};previous={};queue=[(0.,start)]
    while queue:
        cost,i=heapq.heappop(queue)
        if cost!=distance[i]:continue
        if i==end:break
        for j,w in graph[i].items():
            new=cost+w
            if new<distance.get(j,float('inf'))-1e-12:distance[j]=new;previous[j]=i;heapq.heappush(queue,(new,j))
    if end not in distance:raise ValueError('No underarm path')
    path=[end]
    while path[-1]!=start:path.append(previous[path[-1]])
    return path[::-1]


def intrinsic(v,t):
    x=v[t];e1=x[:,1]-x[:,0];e2=x[:,2]-x[:,0];length=np.linalg.norm(e1,axis=1)
    xx=np.einsum('ij,ij->i',e1,e2)/length;yy=np.linalg.norm(np.cross(e1,e2),axis=1)/length
    if np.any(yy<1e-10):raise ValueError('Degenerate source triangle')
    dm=np.zeros((len(t),2,2));dm[:,0,0]=length;dm[:,0,1]=xx;dm[:,1,1]=yy
    inverse=np.linalg.inv(dm);grad=np.concatenate([-inverse.sum(axis=1)[:,None,:],inverse],axis=1)
    return dm,inverse,grad,length*yy/2


def flatten(v,t,boundary):
    dm,inverse,grad,area=intrinsic(v,t);n=len(v);f=len(t)
    rows=[];cols=[];data=[]
    for fi,tri in enumerate(t):
        weight=math.sqrt(area[fi])
        for k,vertex in enumerate(tri):
            gx,gy=grad[fi,k]*weight
            rows.extend([2*fi,2*fi,2*fi+1,2*fi+1]);cols.extend([vertex,n+vertex,vertex,n+vertex]);data.extend([gx,-gy,gy,gx])
    cr=sparse.coo_matrix((data,(rows,cols)),shape=(2*f,2*n)).tocsr()
    first=int(boundary[0]);second=int(boundary[np.argmax(np.linalg.norm(v[boundary]-v[first],axis=1))])
    pin=[first,n+first,second,n+second];values=np.array([0.,0.,np.linalg.norm(v[second]-v[first]),0.]);free=np.setdiff1d(np.arange(2*n),pin)
    solution=np.zeros(2*n);solution[pin]=values
    solve=lsqr(cr[:,free],-cr[:,pin]@values,atol=1e-12,btol=1e-12,iter_lim=15000);solution[free]=solve[0]
    uv=np.column_stack([solution[:n],solution[n:]])
    def jacobian(uv):return np.einsum('fij,fjk->fik',np.stack([uv[t[:,1]]-uv[t[:,0]],uv[t[:,2]]-uv[t[:,0]]],axis=2),inverse)
    # Global scale is arbitrary in LSCM. Fit it once to the intrinsic metric.
    s=np.linalg.svd(jacobian(uv),compute_uv=False);scale=float(np.sum(area[:,None]*s)/np.sum(area[:,None]*s*s));uv*=scale
    grow=np.repeat(np.arange(2*f),3);gcol=np.tile(t[:,None,:],(1,2,1)).reshape(-1);gdata=grad.transpose(0,2,1).reshape(-1)
    G=sparse.coo_matrix((gdata,(grow,gcol)),shape=(2*f,n)).tocsr();weights=np.repeat(area,2);K=(G.T@sparse.diags(weights)@G).tocsc()
    free=np.setdiff1d(np.arange(n),[first]);fixed=uv[first].copy();linear=factorized(K[free][:,free].tocsc());energies=[]
    for iteration in range(60):
        J=jacobian(uv);U,sv,Vt=np.linalg.svd(J);R=U@Vt;bad=np.linalg.det(R)<0
        if bad.any():U[bad,:,-1]*=-1;R=U@Vt
        energy=float(np.sum(area*np.sum((J-R)**2,axis=(1,2))));energies.append(energy)
        for d in range(2):
            rhs=G.T@(weights*R[:,d,:].reshape(-1));uv[free,d]=linear(rhs[free]-K[free,first].toarray().ravel()*fixed[d]);uv[first,d]=fixed[d]
        if len(energies)>3 and abs(energies[-1]-energies[-2])<1e-11*max(energies[0],1e-12):break
    return uv,{'method':'intrinsic LSCM followed by local/global area-weighted ARAP','lscm_solver_stop':int(solve[1]),'lscm_iterations':int(solve[2]),'arap_iterations':len(energies),'arap_energies':energies,'arbitrary_lscm_scale_fitted_to_metric':scale}


def cross2(a,b):return float(a[0]*b[1]-a[1]*b[0])


def overlap_area(a,b):
    if cross2(b[1]-b[0],b[2]-b[0])<0:b=b[::-1]
    polygon=list(a)
    for start,end in zip(b,np.roll(b,-1,axis=0)):
        old=polygon;polygon=[]
        for p,q in zip(old,old[1:]+old[:1]):
            dp=cross2(end-start,p-start);dq=cross2(end-start,q-start);ip=dp>=-1e-14;iq=dq>=-1e-14
            if ip:polygon.append(p)
            if ip!=iq:polygon.append(p+(q-p)*(dp/(dp-dq)))
        if not polygon:return 0.
    origin=polygon[0]
    return abs(sum(cross2(polygon[i]-origin,polygon[i+1]-origin) for i in range(1,len(polygon)-1)))/2


def metrics(v,t,uv):
    dm,inverse,grad,area=intrinsic(v,t);dx=np.stack([uv[t[:,1]]-uv[t[:,0]],uv[t[:,2]]-uv[t[:,0]]],axis=2);J=dx@inverse
    sv=np.linalg.svd(J,compute_uv=False);det=np.linalg.det(J)
    edges=np.unique(np.sort(np.concatenate([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]]),axis=1),axis=0)
    ratio=np.linalg.norm(uv[edges[:,0]]-uv[edges[:,1]],axis=1)/np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)
    pts=uv[t];lo,hi=pts.min(axis=1),pts.max(axis=1);overlaps=[]
    for i in range(len(t)):
        candidates=np.flatnonzero(np.all(np.minimum(hi[i],hi[i+1:])-np.maximum(lo[i],lo[i+1:])>1e-12,axis=1))+i+1
        for j in candidates:
            a=overlap_area(pts[i],pts[j])
            if a>1e-12:overlaps.append({'faces':[int(i),int(j)],'area_m2':a})
    strain=np.abs(sv-1)*100
    return {'triangle_count':len(t),'source_area_m2':float(area.sum()),'flat_area_m2':float(np.sum(area*abs(det))),
            'signed_area_ratio_min':float(det.min()),'signed_area_ratio_max':float(det.max()),'flipped_triangles':int(np.sum(det<=0)),
            'principal_length_ratio_min':float(sv.min()),'principal_length_ratio_max':float(sv.max()),
            'principal_abs_strain_p95_pct':float(np.percentile(strain,95)),'principal_abs_strain_max_pct':float(strain.max()),
            'edge_abs_length_error_p95_pct':float(np.percentile(abs(ratio-1)*100,95)),
            'edge_abs_length_error_max_pct':float(np.max(abs(ratio-1)*100)),'positive_area_self_overlaps':overlaps}


def trace_paths(entries):
    graph=defaultdict(list)
    for k,entry in enumerate(entries):
        a,b=entry['global_edge'];graph[a].append((b,k));graph[b].append((a,k))
    remaining=set(range(len(entries)));paths=[]
    while remaining:
        active_vertices={v for k in remaining for v in entries[k]['global_edge']}
        endpoints=[v for v in active_vertices if sum(k in remaining for _,k in graph[v])==1]
        current=min(endpoints or active_vertices);vertices=[current];path=[]
        while True:
            options=[(v,k) for v,k in graph[current] if k in remaining]
            if not options:break
            v,k=min(options);remaining.remove(k);path.append(entries[k]);vertices.append(v);current=v
        paths.append((vertices,path))
    return paths


def make_seams(panels,source_v,source_t):
    original=Counter(tuple(sorted(e)) for tri in source_t for e in edges_of(tri));by_global=defaultdict(list)
    for name,p in panels.items():
        faces=np.array(p['faces']);counts=Counter(tuple(sorted(e)) for tri in faces for e in edges_of(tri));ids=p['source_vertex_ids']
        for edge,c in counts.items():
            if c==1:
                g=tuple(sorted((ids[edge[0]],ids[edge[1]])))
                by_global[g].append({'panel':name,'local_by_global':{ids[i]:i for i in edge},'edge':list(edge)})
    grouped=defaultdict(list);opened=defaultdict(list)
    for edge,items in by_global.items():
        centre=source_v[list(edge)].mean(axis=0)
        if original[edge]==1:
            item=items[0];kind='cuff' if 'sleeve' in item['panel'] else 'hem' if centre[2]<.9 else 'neck'
            opened[(item['panel'],kind)].append({'global_edge':edge,'a':item});continue
        if len(items)!=2:raise ValueError(f'Internal source edge {edge} has {len(items)} cut boundary copies')
        a,b=sorted(items,key=lambda x:x['panel']);names={a['panel'],b['panel']}
        side='L' if centre[0]>0 else 'R'
        if a['panel']==b['panel']:label='sleeve_underarm_'+side
        elif names=={'front','back'}:label=('bodice_shoulder_' if centre[2]>1.48 else 'bodice_side_')+side
        else:
            body='front' if 'front' in names else 'back';label='armhole_'+side+'_'+body
        grouped[(label,a['panel'],b['panel'])].append({'global_edge':edge,'a':a,'b':b})
    seams=[];open_paths=[]
    for (label,na,nb),entries in sorted(grouped.items()):
        for pi,(global_ids,path) in enumerate(trace_paths(entries)):
            local_a=[];local_b=[]
            for vertex in global_ids:
                choices=[entry for entry in path if vertex in entry['global_edge']]
                aa={entry['a']['local_by_global'][vertex] for entry in choices};bb={entry['b']['local_by_global'][vertex] for entry in choices}
                if len(aa)!=1 or len(bb)!=1:raise ValueError('Seam sides switch local cut-vertex copies')
                local_a.append(aa.pop());local_b.append(bb.pop())
            seam={'id':label+('_'+str(pi) if pi else ''),'label':label,'a':{'panel':na,'vertices':local_a},'b':{'panel':nb,'vertices':local_b},
                  'source_vertex_ids':global_ids,'correspondence':'same ordered source vertices; actual boundary winding is opposite on sewn sides'}
            ua=np.array(panels[na]['vertices_2d_m'])[local_a];ub=np.array(panels[nb]['vertices_2d_m'])[local_b]
            la=np.linalg.norm(np.diff(ua,axis=0),axis=1);lb=np.linalg.norm(np.diff(ub,axis=0),axis=1)
            seam['measurements']={'a_length_mm':float(la.sum()*1000),'b_length_mm':float(lb.sum()*1000),'signed_length_difference_mm':float((la.sum()-lb.sum())*1000),
                                  'max_corresponding_segment_mismatch_mm':float(np.max(abs(la-lb))*1000),
                                  'intended_sewing_ease':'UNSPECIFIED; reverse-engineered 3D shared edge is not measured sleeve-cap ease'}
            if label.startswith('armhole'):
                for suffix,index in [('start',0),('balance',len(global_ids)//2),('end',len(global_ids)-1)]:
                    notch=seam['id']+'_'+suffix
                    for name,local in [(na,local_a),(nb,local_b)]:
                        panels[name]['boundary_marks'].append({'kind':'notch','label':notch,'vertex_id':local[index],'source_vertex_id':global_ids[index],
                                                               'meaning':'topological match marker, not an independently measured anatomical balance point'})
            seams.append(seam)
    for (panel,kind),entries in sorted(opened.items()):
        for global_ids,path in trace_paths(entries):
            local=[]
            for vertex in global_ids:
                x=next(e for e in path if vertex in e['global_edge']);local.append(x['a']['local_by_global'][vertex])
            open_paths.append({'panel':panel,'kind':kind,'vertices':local,'source_vertex_ids':global_ids})
    return seams,open_paths


def grainline(v,uv,name,source_ids,top):
    if name in ('front','back'):
        ref=np.array([0.,0,1]);target_y=-.142 if name=='front' else .142
        a=int(np.argmin(np.linalg.norm(v-[0,target_y,1.0],axis=1)));b=int(np.argmin(np.linalg.norm(v-[0,target_y,1.225],axis=1)))
    else:
        side='L' if name=='left_sleeve' else 'R';all_v=np.array(top['rest_vertices']);ref=all_v[top['cuffs'][side]].mean(axis=0)-all_v[top['armholes'][side]].mean(axis=0);ref/=np.linalg.norm(ref)
        cap=[i for i,g in enumerate(source_ids) if g in top['armholes'][side]];cuff=[i for i,g in enumerate(source_ids) if g in top['cuffs'][side]]
        choices=[(float(np.dot(v[j]-v[i],ref)/np.linalg.norm(v[j]-v[i])),i,j) for i in cap for j in cuff]
        _,a,b=max(choices)
    delta=uv[b]-uv[a];angle=np.pi/2-np.arctan2(delta[1],delta[0]);R=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    uv=uv@R.T;uv-=uv.min(axis=0)
    return uv,{'direction_2d':[0.,1.],'reference_3d':ref.tolist(),'anchor_vertex_ids':[a,b],
               'method':'mapped source tangent; entire panel rotated so mapped anchors point upward',
               'meaning':'suggested construction direction, not measured material warp/weft calibration'}


def svg_pattern(pattern,path):
    panels=pattern['panels'];names=list(panels);boxes={n:np.max(p['vertices_2d_m'],axis=0)*1000 for n,p in panels.items()}
    widths=[max(boxes[n][0] for n in names[:2]),max(boxes[n][0] for n in names[2:])];height=max(boxes[n][1] for n in names[:2])+max(boxes[n][1] for n in names[2:])+210;width=max(sum(boxes[n][0] for n in names[:2]),sum(boxes[n][0] for n in names[2:]))+150
    x=35;y=75;positions={}
    for pair in [names[:2],names[2:]]:
        x=35
        for n in pair:positions[n]=(x,y);x+=boxes[n][0]+70
        y+=max(boxes[n][1] for n in pair)+65
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}mm" height="{height:.3f}mm" viewBox="0 0 {width:.3f} {height:.3f}">',
         '<rect width="100%" height="100%" fill="white"/>','<g font-family="Arial,sans-serif" fill="#172d36">',
         '<text x="25" y="20" font-size="9">Rest-mesh reverse-engineered seam-line panels</text>',
         '<text x="25" y="33" font-size="5">LSCM + ARAP flattening. Distortion and seam mismatch measured; fit/material NOT CALIBRATED.</text>',
         '<text x="25" y="43" font-size="5">NO seam allowance. NOT a manufacturing-approved pattern. Print at 100% only after dimensional checks.</text>']
    colors={'front':'#177f95','back':'#557c45','left_sleeve':'#a65c24','right_sleeve':'#765a9f'}
    for n,p in panels.items():
        points=np.array(p['vertices_2d_m'])*1000;ox,oy=positions[n];H=boxes[n][1]
        def xy(i):return (ox+points[i,0],oy+H-points[i,1])
        loop=p['boundary_vertex_ids'];coords=' '.join(f'{a:.4f},{b:.4f}' for a,b in map(xy,loop))
        out.append(f'<polygon points="{coords}" fill="{colors[n]}" fill-opacity=".08" stroke="{colors[n]}" stroke-width=".65"/>')
        for tri in p['faces']:
            coords=' '.join(f'{a:.4f},{b:.4f}' for a,b in map(xy,tri));out.append(f'<polygon points="{coords}" fill="none" stroke="#b8c5cc" stroke-width=".08"/>')
        out.append(f'<text x="{ox}" y="{oy-9}" font-size="7">{n}</text>')
        center=points.mean(axis=0);cx,cy=ox+center[0],oy+H-center[1]
        out.append(f'<path d="M {cx} {cy+35} V {cy-35} l -3 7 m 3 -7 l 3 7" fill="none" stroke="#172d36" stroke-width=".7"/>')
        out.append(f'<text x="{cx+5}" y="{cy}" font-size="4">suggested grain</text>')
        for mark in p['boundary_marks']:
            a,b=xy(mark['vertex_id']);out.append(f'<circle cx="{a}" cy="{b}" r="1.3" fill="#c23439"/>')
    by=height-28;out.extend([f'<path d="M 25 {by-3} V {by+3} M 25 {by} H 125 M 125 {by-3} V {by+3}" stroke="black" stroke-width=".6"/>',f'<text x="25" y="{by-7}" font-size="5">100 mm calibration</text>','</g></svg>'])
    path.write_text('\n'.join(out))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--topology',type=Path,required=True);p.add_argument('--source-frame',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if args.out.exists():raise FileExistsError('Use a fresh output directory')
    started=time.monotonic();top=json.loads(args.topology.read_text());v=np.asarray(top['rest_vertices'],float)
    with np.load(args.source_frame) as frame:t=np.asarray(frame['cloth_triangles'],int)
    sleeves={s:np.asarray(top['sleeve_triangles'][s],int) for s in ('L','R')};torso=np.setdiff1d(np.arange(len(t)),np.concatenate(list(sleeves.values())))
    ids={'front':torso[v[t[torso],1].mean(axis=1)<0],'back':torso[v[t[torso],1].mean(axis=1)>=0],'left_sleeve':sleeves['L'],'right_sleeve':sleeves['R']}
    panels={};paths={}
    for name,face_ids in ids.items():
        cuts=set()
        if 'sleeve' in name:
            side='L' if name=='left_sleeve' else 'R';path=underarm_path(v,t,face_ids,top['armholes'][side],top['cuffs'][side]);paths[side]=path;cuts={tuple(sorted((a,b))) for a,b in zip(path,path[1:])}
        source,faces=cut_panel(v,t,face_ids,cuts);local_v=v[source];loops,edges,report=boundary_data(faces,len(source))
        if not report['disk']:raise ValueError(f'{name} is not a disk: {report}')
        uv,solver=flatten(local_v,faces,loops[0]);uv,grain=grainline(local_v,uv,name,source,top);measure=metrics(local_v,faces,uv)
        panels[name]={'id':name,'side':'L' if name=='left_sleeve' else 'R' if name=='right_sleeve' else 'CENTER',
                      'vertices_2d_m':uv.tolist(),'source_vertex_ids':source.tolist(),'faces':faces.tolist(),'source_face_ids':face_ids.tolist(),
                      'boundary_vertex_ids':loops[0],'grainline':grain,'boundary_marks':[],'topology_audit':report,'flattening':solver,'metrics':measure}
        print(json.dumps({'panel':name,'disk':report['disk'],'principal_p95_pct':measure['principal_abs_strain_p95_pct'],'principal_max_pct':measure['principal_abs_strain_max_pct'],'flips':measure['flipped_triangles'],'overlap_pairs':len(measure['positive_area_self_overlaps'])}),flush=True)
    seams,open_paths=make_seams(panels,v,t)
    pattern={'schema_version':1,'units':'metres','source':{'topology_sha256':hashlib.sha256(args.topology.read_bytes()).hexdigest(),'frame_sha256':hashlib.sha256(args.source_frame.read_bytes()).hexdigest(),
             'rest_vertices_3d_m':v.tolist(),'triangles':t.tolist(),'state':'frozen generator rest mesh, not failed dynamic terminal frame'},
             'panels':panels,'seams':seams,'open_boundaries':open_paths,'source_underarm_paths':paths,
             'contract':{'seam_allowance_mm':0,'construction':'reverse-engineered 3D surface cut along bodice sides/shoulders and sleeve underarms',
                         'material':'NOT_CALIBRATED','physical_fit':'NOT_RUN','manufacturing_pattern':'NOT_APPROVED','no_body_fit_claim_from_unwrap':True}}
    report={'panel_count':len(panels),'all_disks':all(p['topology_audit']['disk'] for p in panels.values()),'source_faces':len(t),'seam_paths':len(seams),
            'total_flipped_triangles':sum(p['metrics']['flipped_triangles'] for p in panels.values()),'total_positive_area_overlap_pairs':sum(len(p['metrics']['positive_area_self_overlaps']) for p in panels.values()),
            'max_principal_abs_strain_pct':max(p['metrics']['principal_abs_strain_max_pct'] for p in panels.values()),
            'max_seam_length_difference_mm':max(abs(s['measurements']['signed_length_difference_mm']) for s in seams),
            'status':'MEASURED_REVERSE_ENGINEERING_ONLY','fit':'NOT_RUN','material':'NOT_CALIBRATED','seconds':time.monotonic()-started,
            'interpretation':'Flattening distortion is measured, not accepted as a material strain allowance. Seam matching/ease, anatomy and forward cloth simulation need independent validation.'}
    args.out.mkdir(parents=True);(args.out/'pattern.json').write_text(json.dumps(pattern,indent=2,allow_nan=False)+'\n');(args.out/'unwrap-report.json').write_text(json.dumps(report,indent=2)+'\n');svg_pattern(pattern,args.out/'pattern.svg');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
