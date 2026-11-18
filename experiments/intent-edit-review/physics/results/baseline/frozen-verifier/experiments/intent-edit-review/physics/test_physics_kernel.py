#!/usr/bin/env python3
"""Reopen the actual extended WASM with independent NumPy/trimesh controls."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools/cloth_lab'))
from oracle import tensors
from exact_body_oracle import closest_body

def run(directory,output):
    data=json.loads((directory/'input.json').read_text());b=data['body']
    bv=np.frombuffer(base64.b64decode(b['positions']),'<f4').reshape(-1,3).astype(float)
    bf=np.frombuffer(base64.b64decode(b['indices']),'<i4').reshape(-1,3)
    body=trimesh.Trimesh(bv,bf,process=False);centers=body.triangles_center
    selected=np.flatnonzero((abs(centers[:,0])<.16)&(centers[:,1]>1.05)&(centers[:,1]<1.37))[::13]
    selected=selected[:30];points=[]
    for face in selected:
        for offset in [-.001,.01]:points.append((centers[face]+body.face_normals[face]*offset).tolist())
    # Exercise edge and vertex features as well as face interiors. Interpolated
    # vertex normals are not a valid signed-distance test for every feature.
    if 'edge_normals' in b:
        edge_normals=np.frombuffer(base64.b64decode(b['edge_normals']),'<f4').reshape(-1,3,3)
        vertex_normals=np.frombuffer(base64.b64decode(b['normals']),'<f4').reshape(-1,3)
        for face in np.linspace(0,len(bf)-1,40,dtype=int):
            a,c=bf[face,:2];mid=(bv[a]+bv[c])/2
            for sign in [-1,1]:points.append((mid+edge_normals[face,0]*.001*sign).tolist())
        for vertex in np.linspace(0,len(bv)-1,40,dtype=int):
            for sign in [-1,1]:points.append((bv[vertex]+vertex_normals[vertex]*.001*sign).tolist())
    coupons=[{'name':'rest','F':[1,0,0,0,1,0]},{'name':'rigid_rotation','F':[0,1,0,-1,0,0]},
             {'name':'warp_10pct','F':[1.1,0,0,0,1,0]},{'name':'weft_10pct','F':[1,0,0,0,1.1,0]},
             {'name':'shear','F':[1,0,0,.2,1,0]}]
    request={'input':data,'wasm':str((directory/'solver.wasm').resolve()),'coupons':coupons,'points':points,
             'contactPoint':[0,1.25,.2]}
    output.parent.mkdir(parents=True,exist_ok=True);request_file=output.with_suffix('.request.json');request_file.write_text(json.dumps(request))
    native=json.loads(subprocess.check_output(['node',str(Path(__file__).with_name('kernel_probes.mjs')),str(request_file)],text=True))
    results=[]
    for coupon,actual in zip(coupons,native['coupons']):
        F=np.array(coupon['F']).reshape(2,3);expected=tensors(np.vstack([[0,0,0],F]),np.array([[0,0],[1,0],[0,1]]),np.array([[0,1,2]]),data['material'])[0]
        error=np.max(abs(np.array(actual)-expected));assert np.allclose(actual,expected,rtol=3e-4,atol=np.array([2e-5,2e-5,2e-5,.15,.15,2e-5,2e-5,2e-5])),coupon['name']
        results.append({'coupon':coupon['name'],'maximum_absolute_error':float(error)})
    query=np.asarray(points,dtype=np.float32).astype(float);closest,distance,_=closest_body(body,query);inside=body.contains(query);signed=np.where(inside,-distance,distance)
    actual=np.asarray(native['collisions']);assert np.max(abs(actual[:,0]-signed))<2e-6
    # Validate a closest point without arbitrarily selecting one of several
    # equally close features on a medial set.
    surface_distance=closest_body(body,actual[:,1:4])[1]
    assert surface_distance.max()<2e-7
    exported_distance=np.linalg.norm(query-actual[:,1:4],axis=1)
    assert np.max(abs(exported_distance-distance))<2e-6
    expected_normal=(query-actual[:,1:4])/np.maximum(exported_distance[:,None],1e-15)*np.where(inside,-1,1)[:,None]
    differentiable=exported_distance>1e-8
    normal_error=np.max(np.linalg.norm(actual[differentiable,4:7]-expected_normal[differentiable],axis=1))
    assert normal_error<2e-3
    capacity=native['capacity'];assert capacity=={'seams':700,'bends':12000,'lastAliasExact':True}
    gravity=native['gravity'];x=np.asarray(gravity['initial'],dtype=float).reshape(-1,3);expected=x.copy();velocity=0.
    for _ in range(12):velocity=velocity*.993-9.81/120**2;expected[:,1]+=velocity
    assert np.max(abs(np.asarray(gravity['fallen']).reshape(-1,3)-expected))<2e-6
    actual_x=np.asarray(gravity['fallen']);expected_previous=actual_x-(actual_x-np.asarray(gravity['oldPrevious']))*.2
    assert np.array_equal(gravity['fallen'],gravity['dampedPositions'])
    assert np.max(abs(np.asarray(gravity['dampedPrevious'])-expected_previous))<1e-6
    contact=native['normalContact'];assert contact['beforeContact']==contact['afterContact']
    velocity=(np.asarray(contact['afterContact'])-np.asarray(contact['afterPrevious'])).reshape(-1,3)
    assert np.max(abs(velocity@np.asarray(contact['normal'])))<2e-7
    report={'verdict':'PASS','wasm_sha256':hashlib.sha256((directory/'solver.wasm').read_bytes()).hexdigest(),
            'coupons':results,'actual_body_queries':len(points),'max_body_signed_distance_error_m':float(np.max(abs(actual[:,0]-signed))),
            'max_closest_point_surface_distance_m':float(surface_distance.max()),'normal_consistency_error':float(normal_error),
            'reference':'f64 minimum over every body face; ray parity for sign; closest-point ties allowed',
            'capacity':capacity,'gravity_analytic_12_steps':'PASS','explicit_velocity_damping':'PASS','zero_restitution_contact_normal':'PASS',
            'scope':'Compiled engine controls only. Recorded garment acceptance, measured mechanics and real-person fit are separate.'}
    output.write_text(json.dumps(report,indent=2)+'\n');request_file.unlink();print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.directory,a.output)
