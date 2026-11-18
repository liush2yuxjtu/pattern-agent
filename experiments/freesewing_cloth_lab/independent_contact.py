"""Independent posterior visibility rays and PBD reaction arithmetic.

No runtime raycaster/BVH is imported. Pressure checks validate the declared
projection-reaction estimate, not measured wearer pressure or a fabric law.
"""
import copy,gzip,json
from pathlib import Path
import numpy as np


def coverage(data, positions=None):
    body=np.asarray(data['body']['vertices']).reshape(-1,3)
    faces=np.asarray(data['body']['indices']).reshape(-1,3)
    normal=np.zeros_like(body)
    area_normal=np.cross(body[faces[:,1]]-body[faces[:,0]],body[faces[:,2]]-body[faces[:,0]])
    for k in range(3):np.add.at(normal,faces[:,k],area_normal)
    normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-30)
    ids=np.flatnonzero((body[:,1]>.83)&(body[:,1]<1.025)&(abs(body[:,0])<.18)&(normal[:,2]<-.35))
    # Include interior surface samples as well as the runtime's body vertices.
    centroids=body[faces].mean(axis=1)
    fn=area_normal/np.maximum(np.linalg.norm(area_normal,axis=1)[:,None],1e-30)
    select=(centroids[:,1]>.83)&(centroids[:,1]<1.025)&(abs(centroids[:,0])<.18)&(fn[:,2]<-.35)
    samples=np.concatenate([body[ids],centroids[select]])
    t=np.asarray(data['positions'] if positions is None else positions).reshape(-1,3)[np.asarray(data['triangles'],dtype=int).reshape(-1,3)]
    a=t[:,0];u=t[:,1]-a;v=t[:,2]-a;det=u[:,0]*v[:,1]-u[:,1]*v[:,0];valid=abs(det)>1e-12
    exposed=[]
    for i,point in enumerate(samples):
        q=point-a
        with np.errstate(divide='ignore',invalid='ignore'):
            s=(q[:,0]*v[:,1]-q[:,1]*v[:,0])/det;r=(u[:,0]*q[:,1]-u[:,1]*q[:,0])/det
            z=a[:,2]+s*u[:,2]+r*v[:,2]
        hit=valid&(s>=-1e-8)&(r>=-1e-8)&(s+r<=1+1e-8)&(z<point[2]-.0001)
        if not np.any(hit):exposed.append(i)
    return {'verdict':'PASS' if len(ids)>100 and not exposed else 'FAIL','bodyVertexSamples':len(ids),'triangleCentroidSamples':int(select.sum()),'totalSamples':len(samples),'exposed':len(exposed),'exposedSampleIndices':exposed,'scope':'Posterior pelvic region, outward -Z visibility; sampled coverage, not universal camera/garment certification'}


def pressure(data):
    cp=data['contactPressure'];inv=np.asarray(data['inverseMass']);correction=np.asarray(cp['correction_m']);dt=cp['dt_s']
    uv=np.asarray(data['materialCoordinates']).reshape(-1,3,2);tri=np.asarray(data['triangles'],dtype=int).reshape(-1,3)
    u=uv[:,1]-uv[:,0];v=uv[:,2]-uv[:,0];area=np.abs(u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
    lumped=np.zeros(len(inv))
    for k in range(3):np.add.at(lumped,tri[:,k],area/3)
    active=inv>0;mass=lumped*data['material']['density'];expected_area=np.where(active,lumped,0)
    expected_force=np.where(active,mass*correction/dt**2,0)
    expected_pressure=np.divide(expected_force,expected_area*1000,out=np.zeros_like(inv),where=expected_area>0)
    assert dt>0 and np.all(np.isfinite(correction)) and np.all(correction>=0)
    errors={name:float(np.max(abs(np.asarray(cp[name])-expected))) for name,expected in [('area_m2',expected_area),('force_N',expected_force),('pressure_kPa',expected_pressure)]}
    assert errors['area_m2']<1e-12 and errors['force_N']<1e-9 and errors['pressure_kPa']<1e-9
    assert cp['calibration']=='NOT_VALIDATED'
    return {'verdict':'PASS','maxErrors':errors,'peak_kPa':float(expected_pressure.max()),'contactVertices':int(np.count_nonzero(expected_pressure)),'calibration':'NOT_VALIDATED','scope':'Independent UV-lumped area/mass and m*normalProjection/dt²/area; timestep-dependent contact-reaction estimate'}


def run(data,negative=False):
    cov=coverage(data);pr=pressure(data);result={'coverage':cov,'pressure':pr,'verdict':cov['verdict']}
    if negative:
        raw_positions=data['initialPositions']
        if data.get('support',{}).get('mode')=='free-waist':
            # Keep the actual historical exposure fault even if a new fuller
            # draft already covers the pelvis before gravity. Do not weaken it.
            with gzip.open(Path(__file__).resolve().parents[2]/'docs/verification/cloth-coverage-pressure-20261118/local/dynamics/step-120.json.gz','rt') as f:raw_positions=json.load(f)['initialPositions']
        raw=coverage(data,raw_positions)
        broken=copy.deepcopy(data);broken['contactPressure']['pressure_kPa'][100]+=.001
        detected=False
        try:pressure(broken)
        except AssertionError:detected=True
        missing=copy.deepcopy(data);missing['triangles']=[]
        removed=coverage(missing)
        result['negativeControls']={'unrelaxedArrangement':raw,'missingCloth':removed,'forgedPressureDetected':detected}
        if raw['verdict']!='FAIL' or removed['verdict']!='FAIL' or not detected:result['verdict']='FAIL'
    return result
