"""Independent fit checks: original MakeHuman skin weights, real ray occlusion,
normal multipliers, current/rest area and unilateral contact equations.
Never imports renderer, solver, JS raster or pressure implementation.
"""
import json
from pathlib import Path
import numpy as np
import trimesh


def wear(data,source):
    """Independent actual-skin fitting test; no renderer profile/anchors imported.

    Rebuild the selected high-waist plane from original MakeHuman tape IDs and
    intersect raw triangles with that plane in float64. Then measure the exported
    upper cloth edge against the unchanged actual skin, not a circular proxy.
    """
    raw=json.loads(Path(source).read_text());original=np.array(raw['vertices']).reshape(-1,3)/100
    source_faces=np.array(raw['indices']).reshape(-1,3);original[:,1]-=original[np.unique(source_faces),1].min()
    ids=next(c['path'] for c in raw['controls'] if c['key']=='waist')
    height=round((float(original[ids[:-1],1].mean())+.035)/.005)*.005
    tri=original[source_faces];intersections=[]
    for a,b in [(0,1),(1,2),(2,0)]:
        p,q=tri[:,a],tri[:,b];cross=((p[:,1]<=height)&(q[:,1]>height))|((q[:,1]<=height)&(p[:,1]>height))
        part=np.full_like(p,np.nan);part[cross]=p[cross]+(q[cross]-p[cross])*((height-p[cross,1])/(q[cross,1]-p[cross,1]))[:,None];intersections.append(part)
    intersections=np.stack(intersections,axis=1);segments=[]
    for points in intersections:
        points=points[np.isfinite(points[:,0])]
        if len(points)==2 and np.all(abs(points[:,0])<.24):segments.append(points)
    segments=np.array(segments);assert len(segments)>=3
    # Resolution is an asset property; require a single closed contour instead
    # of inventing a minimum number of intersected triangles.
    vertices,inverse,degree=np.unique(np.round(segments.reshape(-1,3),7),axis=0,return_inverse=True,return_counts=True)
    assert np.all(degree==2),'Open anatomical section'
    adjacency={i:set() for i in range(len(vertices))}
    for a,b in inverse.reshape(-1,2):adjacency[a].add(b);adjacency[b].add(a)
    seen=set();todo=[0]
    while todo:
        a=todo.pop()
        if a not in seen:seen.add(a);todo.extend(adjacency[a]-seen)
    assert len(seen)==len(vertices),'Multiple anatomical section components'
    circumference=np.linalg.norm(segments[:,1]-segments[:,0],axis=1).sum()*1000
    x=np.array(data['positions']).reshape(-1,3);n,m=data['grid'];k=(n+1)*(m+1)
    edges=[x[p*k+np.arange(n+1)] for p in range(2)];points=np.vstack(edges)
    bv=np.array(data['body']['positions']).reshape(-1,3);bv[:,0]+=data['body']['offsetX']
    body=trimesh.Trimesh(bv,np.array(data['body']['triangles']).reshape(-1,3),process=False)
    closest,distance,_=body.nearest.on_surface(points);gap=distance*1000
    assert gap.max()<=10,f'Waist detachment {gap.max()} mm > 10 mm'
    assert gap.min()>=3,f'Waist skin clearance {gap.min()} mm < 3 mm'
    height_error=np.max(abs(closest[:,1]-height))*1000
    assert height_error<=2,f'Wrong anatomical waist level {height_error} mm'
    lengths=np.array([np.linalg.norm(np.diff(e,axis=0),axis=1).sum()*1000 for e in edges])
    mismatch=float(np.max(abs(lengths-data['parameters']['topsMm'])))
    assert mismatch<=1,f'Waist edge/pattern discrepancy {mismatch} mm'
    center=(segments.min((0,1))+segments.max((0,1)))/2;loop=np.r_[edges[0][:-1],edges[1]];loop[:,0]-=data['body']['offsetX']
    angles=np.unwrap(np.arctan2(loop[:,2]-center[2],loop[:,0]-center[0]));assert np.all(np.diff(angles)>0) and abs(angles[-1]-angles[0]-2*np.pi)<1e-7,'Waist does not wind once around torso'
    reported=data['diagnostics']['wear'];assert abs(reported['bodySectionGirthMm']-circumference)<1e-4
    assert abs(reported['maxWaistGapMm']-gap.max())<.005
    assert abs(reported['waistPatternMismatchMm']-mismatch)<.001
    return {'verdict':'PASS','bodySectionGirthMm':float(circumference),'waistEdgeLengthsMm':lengths.tolist(),'garmentWaistMm':float(lengths.sum()),'minWaistGapMm':float(gap.min()),'maxWaistGapMm':float(gap.max()),'maxSkinWaistHeightErrorMm':float(height_error),'patternMismatchMm':mismatch,'sectionHeightM':height}


def pressure(data):
    x=np.array(data['positions']).reshape(-1,3);faces=np.array(data['triangles']).reshape(-1,3)
    uv=np.array(data['restUV']).reshape(-1,2);p=data['fitPressure'];d=data['diagnostics']['pressure']
    tri=x[faces];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
    nodal=np.bincount(faces.ravel(),np.repeat(area/3,3),minlength=len(x))
    flat=uv[faces];a=flat[:,1]-flat[:,0];b=flat[:,2]-flat[:,0]
    rest=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
    rest_nodal=np.bincount(faces.ravel(),np.repeat(rest/3,3),minlength=len(x))
    n,m=data['grid'];k=(n+1)*(m+1);pins=set(np.r_[np.arange(n+1),k+np.arange(n+1)].tolist())
    parent=np.arange(len(x))
    def root(i):
        while parent[i]!=i:i=parent[i]
        return i
    for s in data['seams']:
        if s['active']:parent[root(s['b'])]=root(s['a'])
    reps=np.array([root(i) for i in range(len(x))])
    dt=p['dtSeconds'];assert abs(dt-1/120)<1e-9
    reported=np.array(p['nominalClothAreaPressurePa']);assert np.isfinite(reported).all() and np.all(reported>=0)
    assert np.max(abs(nodal-p['nodalAreaM2']))<5e-9
    load=np.zeros(len(x));total=0;resultant=np.zeros(3);points=[];normals=[];envelope=[];compression=[]
    if d['ready']:
        assert d['frame']==data['diagnostics']['frame'] and data['parameters']['collision']
        for kind,rows in data['pressureContacts'].items():
            seen=set()
            for index,multiplier,*normal in rows:
                assert index not in seen and multiplier>0;seen.add(index)
                normal=np.array(normal);assert abs(np.linalg.norm(normal)-1)<1e-4
                force=multiplier/dt**2;total+=force;resultant+=force*normal;normals.append(normal)
                if kind=='vertex':
                    assert 0<=index<len(x) and reps[index]==index
                    attached=reps==index;assert not any(v in pins for v in np.flatnonzero(attached))
                    load[attached]+=force*nodal[attached]/nodal[attached].sum()
                    points.append(x[index]);envelope.append(p['nominalOffsetM']);compression.append(force/(p['referenceSpringPaPerM']*rest_nodal[attached].sum()))
                else:
                    assert kind=='centroid' and 0<=index<len(faces)
                    load[faces[index]]+=force/3;points.append(x[faces[index]].mean(axis=0));envelope.append(p['faceGuardOffsetM']);compression.append(0)
    else:
        assert data['pressureContacts'] is None
    assert np.allclose(reported,load/nodal,atol=.0005,rtol=1e-5)
    assert np.max(abs(np.array(p['nodalNormalForceN'])-load))<1e-7
    assert abs(np.sum(reported*nodal)-total)<max(1e-6,total*1e-6)
    assert abs(d['normalForceN']-total)<max(1e-6,total*1e-6)
    assert np.max(abs(resultant-d['resultantOnClothN']))<max(1e-6,total*1e-6)
    assert reported.max()==d['maxPressurePa']
    residual=0;alignment=1
    if points:
        bv=np.array(data['body']['positions']).reshape(-1,3);bv[:,0]+=data['body']['offsetX']
        body=trimesh.Trimesh(bv,np.array(data['body']['triangles']).reshape(-1,3),process=False)
        points=np.array(points);closest,distance,_=trimesh.proximity.closest_point(body,points)
        signed=-trimesh.proximity.signed_distance(body,points)
        assert signed.min()>0,'Pressure contact lies inside actual avatar'
        alignment=float(np.min(np.sum((points-closest)/distance[:,None]*np.array(normals),axis=1)))
        residual=float(np.max(abs(signed-np.array(envelope)+compression))*1000)
        assert alignment>.90,alignment
        assert residual<.25,f'Contact equation residual {residual} mm'
    return {'verdict':'PASS','samples':len(points),'forceN':total,'peakPa':float(reported.max()),'forceIntegralErrorN':float(abs(np.sum(reported*nodal)-total)),'maxContactResidualMm':residual,'minNormalAlignment':alignment}


def coverage(data,source,angles=16,allow_exposure=False):
    """Occlude anatomical pelvis/spine/upper-leg vertices AND face interiors.
    Angles differ from the four-view runtime raster; no image colors are used.
    """
    source=json.loads(Path(source).read_text());ids=np.unique(np.array(source['indices']))
    bones={i for i,b in enumerate(source['bones']) if b['name'].startswith(('pelvis','upperleg','spine'))}
    skin=np.array(source['skinIndices']).reshape(-1,4)[ids];weights=np.array(source['skinWeights']).reshape(-1,4)[ids]
    anatomical=np.where(np.isin(skin,list(bones)),weights,0).sum(axis=1)>.5
    v=np.array(data['body']['positions']).reshape(-1,3);v[:,0]+=data['body']['offsetX'];faces=np.array(data['body']['triangles']).reshape(-1,3)
    region=anatomical&(v[:,1]>=.70)&(v[:,1]<=.985)
    samples=np.concatenate([v[region],v[faces[np.all(region[faces],axis=1)]].mean(axis=1)])
    assert len(samples)>250
    cloth=trimesh.Trimesh(np.array(data['positions']).reshape(-1,3),np.array(data['triangles']).reshape(-1,3),process=False)
    results=[]
    for a in np.linspace(0,2*np.pi,angles,endpoint=False):
        outward=np.array([np.sin(a),0,np.cos(a)]);starts=samples+outward*2;directions=np.broadcast_to(-outward,starts.shape)
        loc,rays,_=cloth.ray.intersects_location(starts,directions,multiple_hits=True)
        distances=np.full(len(samples),np.inf)
        if len(rays):np.minimum.at(distances,rays,np.einsum('ij,j->i',loc-starts[rays],-outward))
        missing=distances>2-.0001
        results.append({'angleDegrees':float(np.degrees(a)),'exposed':int(missing.sum()),'rays':len(samples)})
    exposed=sum(r['exposed'] for r in results)
    if not allow_exposure:assert exposed==0,f'Anatomical hip exposure: {exposed} rays across {angles} views'
    return {'verdict':'PASS' if exposed==0 else 'FAIL','anatomicalSurfaceSamples':len(samples),'views':angles,'totalRays':len(samples)*angles,'exposedRays':exposed,'byView':results}


def arrays(points, faces):
    x = np.array(points).reshape(-1,3)
    f = np.array(faces).reshape(-1,3)
    tr = x[f]
    area = np.linalg.norm(np.cross(tr[:,1]-tr[:,0],tr[:,2]-tr[:,0]),axis=1)*.5
    nodeArea = np.bincount(f.ravel(), np.repeat(area/3,3), minlength=len(x))
    return x,f,area,nodeArea


def verify_coupon(q):
    x, f, area, node_area = arrays(q['positionsM'],q['faces'])
    rest = np.array(q['restUV']).reshape(-1,2)[f]
    u,v=rest[:,1]-rest[:,0],rest[:,2]-rest[:,0]
    rest_area=abs(u[:,0]*v[:,1]-u[:,1]*v[:,0]).sum()/2
    assert abs(rest_area-.04)<1e-7
    p = np.array(q['pressurePa'])
    fn = np.array(q['nodalForceN'])
    dt = q['dtSeconds']
    l = np.r_[q['vertexLambdas'],q['centroidLambdas']]
    force = l.sum()/dt**2
    assert np.min(l)>=0 and np.min(p)>=0
    assert abs(force-q['totalNormalForceN']) < max(2e-6,1e-6*force)
    assert np.max(abs(node_area-np.array(q['nodalAreaM2']))) < 5e-9
    assert abs(np.sum(p*node_area)-force) < max(2e-6,1e-6*force)
    assert abs(fn.sum()-force) < max(2e-6,1e-6*force)
    expected = q['loadPa']*rest_area if q['collision'] and not q['detached'] else 0
    assert abs(force-expected) < max(2e-6,2e-5*expected)
    assert np.max(abs(np.array(q['resultantN'])-force*np.array(q['normal']))) < max(2e-6,2e-6*force)
    height = x@np.array(q['normal'])
    if expected == 0:
        assert np.all(p == 0) and np.all(l == 0)
        law_error = 0
    else:
        assert np.max(abs(p-q['loadPa'])) < max(.004,.0001*q['loadPa'])
        assert not any(q['centroidLambdas'])
        target = q['marginM'] - q['loadPa']/q['stiffnessPaPerM']
        law_error = float(np.max(abs(height-target))*1000)
        assert law_error < .00015, law_error
    return dict(inputPa=q['loadPa'], expectedN=expected, outputN=float(force), actualPa=float(force/area.sum()),
                cells=q['cells'], tiltDeg=q['tilt'], maxCompressionErrorMm=law_error)



def pattern_svg(svg,parameters):
    """Measure actual SVG arcs, straight sides, exact seam allowances and page fit."""
    import re
    import xml.etree.ElementTree as ET
    root=ET.fromstring(svg);assert root.attrib['width'].endswith('mm') and root.attrib['height'].endswith('mm')
    width=float(root.attrib['width'][:-2]);height=float(root.attrib['height'][:-2]);pieces=[]
    number=r'[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?'
    for i,g in enumerate(root.findall('{http://www.w3.org/2000/svg}g')):
        paths=g.findall('{http://www.w3.org/2000/svg}path');cut=np.array([float(x) for x in re.findall(number,paths[0].attrib['d'])]);seam=np.array([float(x) for x in re.findall(number,paths[1].attrib['d'])]);assert len(cut)==len(seam)==18
        r=seam[2];outer=seam[11];points=seam[[0,1,7,8,9,10,16,17]].reshape(4,2);cutpoints=cut[[0,1,7,8,9,10,16,17]].reshape(4,2)
        angles=np.arctan2(points[:,0],points[:,1]+r);top=r*(angles[1]-angles[0]);bottom=outer*(angles[2]-angles[3])
        expected_top=parameters.get('topsMm',[parameters['topMm']]*2)[i]
        assert abs(top-expected_top)<1e-6 and abs(bottom-parameters['bottomMm'])<1e-6
        L=parameters['lengthsMm'][i];assert abs(outer-r-L)<1e-6 and abs(np.linalg.norm(points[2]-points[1])-L)<1e-6
        assert abs((r-cut[2])-10)<1e-7 and abs((cut[11]-outer)-10)<1e-7
        v=points[2]-points[1]
        for q in cutpoints[1:3]:
            d=abs(v[0]*(q-points[1])[1]-v[1]*(q-points[1])[0])/np.linalg.norm(v);assert abs(d-10)<1e-6
        tx,ty=[float(x) for x in re.findall(number,g.attrib['transform'])]
        bounds=[tx+min(cutpoints[:,0]),ty+min(cutpoints[:,1]),tx+max(cutpoints[:,0]),ty+cut[11]-r]
        assert bounds[0]>=10 and bounds[1]>=10 and bounds[2]<=width-10 and bounds[3]<=height-35,('Cutting line clipped by page',bounds,width,height)
        pieces.append({'waistArcMm':top,'hemArcMm':bottom,'seamLengthMm':L,'allowanceMm':10,'cutBoundsMm':bounds})
    assert len(pieces)==2
    return {'verdict':'PASS','widthMm':width,'heightMm':height,'pieces':pieces}
