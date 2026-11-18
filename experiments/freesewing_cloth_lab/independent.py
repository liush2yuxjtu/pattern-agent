"""Reopen actual browser exports with NumPy and the repo's strict triangle oracle.
No rendering or application measurement code is imported here. Metres / mm.
"""
import argparse,copy,hashlib,importlib.util,json,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from independent_contact import run as contact_audit
from independent_fields import freesewing_reopen,folds_reopen,redraft

def load_oracle(root):
    path=root/'services/dxf-preview/verification/geometry.py'
    spec=importlib.util.spec_from_file_location('independent_geometry',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,path

def source_seams(data):
    nc,nr=data['parameters']['NC'],data['parameters']['NR'];per=nc//4
    assert len(data['panels'])==4 and len(data['seams'])==4
    points=np.array(data['positions']).reshape(-1,3)
    for k,s in enumerate(data['seams']):
        assert s['a']=={'panel':f'P{k+1}','edge':'right','direction':'waist-to-hem'}
        assert s['b']=={'panel':f'P{(k+1)%4+1}','edge':'left','direction':'waist-to-hem'}
        expected=[r*nc+((k+1)*per)%nc for r in range(nr+1)]
        assert np.array_equal(np.array(s['vertexPairs']),np.array([[i,i] for i in expected]))
        # A seam's source sides must have equal 2D lengths, in the correct order.
        p0=data['panels'][k]['polygon'];p1=data['panels'][(k+1)%4]['polygon']
        right=np.array([p0[64],p0[65]]);left=np.array([p1[0],p1[-1]])
        la=np.linalg.norm(right[1]-right[0]);lb=np.linalg.norm(left[1]-left[0])
        assert abs(la-lb)<1e-7 and abs(la-data['parameters']['slant_m']*1000)<1e-7
        assert s['notches']==[.25,.5,.75]
        assert max(np.linalg.norm(points[a]-points[b]) for a,b in s['vertexPairs'])<=.002
    return True

def tensor_reopen(data):
    p=np.array(data['positions']).reshape(-1,3);t=np.array(data['triangles']).reshape(-1,3)
    uv=np.array(data['materialCoordinates']).reshape(-1,3,2)
    Dm=np.stack([uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]],axis=-1)
    Ds=np.stack([p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]]],axis=-1)
    F=Ds@np.linalg.inv(Dm);C=F.transpose(0,2,1)@F
    principal=np.sqrt(np.linalg.eigvalsh(C)[:,1]);strain=(C-np.eye(2))/2
    E=data['material']['E'];nu=data['material']['nu'];sx=E/(1-nu**2)*(strain[:,0,0]+nu*strain[:,1,1]);sy=E/(1-nu**2)*(strain[:,1,1]+nu*strain[:,0,0]);shear=E/(1+nu)*strain[:,0,1]
    sigma=np.zeros_like(C);sigma[:,0,0]=sx;sigma[:,1,1]=sy;sigma[:,0,1]=sigma[:,1,0]=shear
    stress=np.maximum(0,np.linalg.eigvalsh(sigma)[:,1])/1000
    actual=data['triangleMeasures'];a=np.array([x['stretch'] for x in actual]);b=np.array([x['stress'] for x in actual])
    stretch_error=float(np.max(np.abs(principal-a)));stress_error=float(np.max(np.abs(stress-b)))
    assert stretch_error<1e-9 and stress_error<1e-8
    assert abs(principal.max()-data['simulation']['peakStretch'])<1e-9
    source=freesewing_reopen(data)
    return {'peak_stretch_percent':float(principal.max()*100),'peak_stress_kPa':float(stress.max()),'max_stretch_error':stretch_error,'max_stress_error_kPa':stress_error,'freesewing':source}

def reopen_exports(folder,data):
    """Check actual independently parsed OBJ/SVG/DXF downloads against material data."""
    lines=(folder/'garment.obj').read_text().splitlines()
    vertices=np.array([[float(x) for x in l.split()[1:4]] for l in lines if l.startswith('v ')])
    faces=np.array([[int(x.split('/')[0])-1 for x in l.split()[1:4]] for l in lines if l.startswith('f ')])
    body=np.array(data['body']['vertices']).reshape(-1,3);cloth=np.array(data['positions']).reshape(-1,3)
    assert np.array_equal(vertices,np.concatenate([body,cloth]))
    expected_faces=np.concatenate([np.array(data['body']['indices']).reshape(-1,3),np.array(data['triangles']).reshape(-1,3)+len(body)])
    assert np.array_equal(faces,expected_faces)
    root=ET.fromstring((folder/'pattern.svg').read_text());ns={'s':'http://www.w3.org/2000/svg'}
    groups=root.findall("s:g[@data-panel]",ns);assert len(groups)==4
    for panel,group in zip(data['panels'],groups):
        assert group.attrib['data-panel']==panel['id']
        pp=group.findall('s:polygon',ns);assert len(pp)==2
        cut=np.array([[float(n) for n in pair.split(',')] for pair in pp[0].attrib['points'].split()])
        stitch=np.array([[float(n) for n in pair.split(',')] for pair in pp[1].attrib['points'].split()])
        assert np.array_equal(stitch,np.array(panel['polygon'])) and np.array_equal(cut,np.array(panel['cutOutline']))
        e=np.roll(stitch,-1,axis=0)-stitch
        delta=(cut+np.roll(cut,-1,axis=0)-stitch-np.roll(stitch,-1,axis=0))/2
        offset=np.abs(e[:,0]*delta[:,1]-e[:,1]*delta[:,0])/np.linalg.norm(e,axis=1)
        assert np.max(np.abs(offset-10))<1e-7
    # DXF entity groups are parsed here rather than trusting the app's unit label.
    raw=(folder/'pattern.dxf').read_text().splitlines();pairs=list(zip(raw[::2],raw[1::2]));assert ('9','$INSUNITS') in pairs
    polylines=[];current=None;pending=None
    for code,value in pairs:
        if code=='0':
            if current is not None:polylines.append(current)
            current={'points':[]} if value=='LWPOLYLINE' else None
        elif current is not None:
            if code=='8':current['layer']=value
            elif code=='10':pending=float(value)
            elif code=='20':current['points'].append([pending,-float(value)])
    for panel in data['panels']:
        for suffix,key in [('STITCH','polygon'),('CUT','cutOutline')]:
            item=next(x for x in polylines if x['layer']==panel['id']+'_'+suffix);actual=np.array(item['points']);expected=np.array(panel[key]);assert actual.shape==expected.shape
            assert np.max(np.abs((actual-actual[0])-(expected-expected[0])))<2e-6
    native=(folder/'freesewing-native.svg').read_text();assert native==redraft(data)['nativeSVG']
    return {'native_FreeSewing_SVG':'byte-exact independent upstream re-draft','OBJ_vertices_and_faces':'exact match','SVG_panels':'exact match','SVG_cut_offset_mm':10,'DXF_panels':'match within 0.000002 mm'}

def run(data,root,negative=True):
    oracle,path=load_oracle(root);v=np.array(data['positions']).reshape(-1,3);f=np.array(data['triangles']).reshape(-1,3);bv=np.array(data['body']['vertices']).reshape(-1,3);bf=np.array(data['body']['indices']).reshape(-1,3)
    analytic=oracle.analytic_tests();assert analytic['pass'] if 'pass' in analytic else all(x.get('pass',True) for x in analytic.values() if isinstance(x,dict))
    source=root/data['body']['provenance']['sourceFile'];assert hashlib.sha256(source.read_bytes()).hexdigest()==data['body']['provenance']['sourceSHA256']
    original=np.array([[float(x)/100 for x in l.split()[1:4]] for l in source.read_text().splitlines() if l.startswith('v ')])
    original_faces=np.array([[int(x.split('/')[0])-1 for x in l.split()[1:4]] for l in source.read_text().splitlines() if l.startswith('f ')])
    assert np.array_equal(original_faces,bf)
    original[:,1]-=original[:,1].min();original[:,0]-=(original[:,0].max()+original[:,0].min())/2
    assert np.max(np.abs(original-bv))<=5.1e-8
    source_seams(data);tensor=tensor_reopen(data);folds=folds_reopen(data);topology=oracle.mesh_audit(v,f);body_topology=oracle.mesh_audit(bv,bf)
    assert topology['connected_components']==1 and topology['boundary_cycles']==2 and topology['euler_characteristic']==0
    assert topology['nonmanifold_edges']==topology['winding_conflicts']==topology['degenerate_triangles']==topology['duplicate_faces']==0
    assert body_topology['closed_oriented_edge_manifold']
    body_pairs=oracle.intersect_pairs(v,f,bv,bf);self_pairs=oracle.intersect_pairs(v,f)
    # Independent solid-angle membership, deliberately unrelated to the app BVH.
    inside=np.flatnonzero(oracle.point_inside_mesh(bv,bf,v)).tolist()
    result={'verdict':'PASS' if not body_pairs and not self_pairs and not inside else 'FAIL','body_triangle_intersections':len(body_pairs),'body_pairs':body_pairs[:40],'cloth_self_intersections':len(self_pairs),'self_pairs':self_pairs[:40],'inside_body_vertices':inside,'topology':topology,'body_topology':body_topology,'tensor':tensor,'folds':folds,'source_hash':hashlib.sha256(source.read_bytes()).hexdigest(),'oracle_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'analytic_controls':analytic,'physical_calibration':'NOT_RUN','manufacturing':'NOT_RUN','dynamic_self_collision_solver':bool(data.get('selfContact',{}).get('enabled',False))}
    if 'contactPressure' in data:
        result['coverageAndPressure']=contact_audit(data,negative)
        if result['coverageAndPressure']['verdict']!='PASS':result['verdict']='FAIL'
    if negative:
        controls={}
        for fault in ['reverse-seam','swap-panel','gap','uv','fold-angle','curvature','freesewing-source']:
            d=copy.deepcopy(data)
            if fault=='reverse-seam':d['seams'][0]['b']['direction']='hem-to-waist'
            if fault=='swap-panel':d['seams'][0]['b']['panel']='P4'
            if fault=='gap':
                d['positions']+=list(v[d['seams'][0]['vertexPairs'][3][0]]+[.003,0,0]);d['seams'][0]['vertexPairs'][3][1]=len(v)
            if fault=='uv':d['materialCoordinates'][4]+=.02
            if fault=='fold-angle':d['folding']['angle_rad'][0]+=.1
            if fault=='curvature':d['folding']['curvature_per_m'][0]+=.1
            if fault=='freesewing-source':d['freesewing']['halfPanel']['inner'][0][0][0]+=1
            try:
                if fault in ['uv','freesewing-source']:tensor_reopen(d)
                elif fault in ['fold-angle','curvature']:folds_reopen(d)
                else:source_seams(d)
                controls[fault]=False
            except (AssertionError,ValueError,IndexError):controls[fault]=True
        broken=v.copy();broken[10*data['parameters']['NC']+5]=[0,.93,.05]
        controls['body-penetration']=len(oracle.intersect_pairs(broken,f,bv,bf))>0
        duplicated=np.concatenate([f,f[100:101]])
        controls['overlapping-face']=len(oracle.intersect_pairs(v,duplicated))>len(self_pairs)
        result['negative_controls']=controls
        if not all(controls.values()):result['verdict']='FAIL'
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('project',type=Path);parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--no-negative',action='store_true');args=parser.parse_args();start=time.time()
    data=json.loads(args.project.read_text());result=run(data,args.repo,not args.no_negative)
    if args.project.name=='simulation.json':result['downloaded_exports']=reopen_exports(args.project.parent,data)
    result['duration_s']=time.time()-start;result['export_sha256']=hashlib.sha256(args.project.read_bytes()).hexdigest();args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));sys.exit(0 if result['verdict']=='PASS' else 2)
