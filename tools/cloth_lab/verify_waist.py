#!/usr/bin/env python3
"""Reopen a REAL exported garment and isolate each waist-fit rejection boundary."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from fit_oracle import wear


def run(project,source):
    raw=project.read_bytes();data=json.loads(raw);valid=wear(data,source)
    x=np.array(data['positions']).reshape(-1,3);n,m=data['grid'];k=(n+1)*(m+1)
    top=np.r_[np.arange(n+1),k+np.arange(n+1)]
    bv=np.array(data['body']['positions']).reshape(-1,3);bv[:,0]+=data['body']['offsetX']
    body=trimesh.Trimesh(bv,np.array(data['body']['triangles']).reshape(-1,3),process=False)
    results={'actualExport':valid}
    for name in ['detached','wrong-level-following-skin','wrong-pattern-length']:
        bad=copy.deepcopy(data)
        if name=='wrong-pattern-length':
            bad['parameters']['topsMm'][0]+=20
            expected='Waist edge/pattern discrepancy'
        else:
            points=x[top].copy()
            if name=='detached':
                center=np.array([data['body']['offsetX'],0,.06]);direction=points-center;direction[:,1]=0
                points+=direction/np.linalg.norm(direction,axis=1)[:,None]*.03
                expected='Waist detachment'
            else:
                points[:,1]+=.03
                closest,_,faces=body.nearest.on_surface(points)
                points=closest+body.face_normals[faces]*.007
                # This fault stays close to skin; only the anatomical level is wrong.
                _,dist,_=body.nearest.on_surface(points)
                assert dist.min()*1000>=3 and dist.max()*1000<=10
                expected='Wrong anatomical waist level'
            for field in ['positions','previous','pinPositions']:
                array=np.array(bad[field]).reshape(-1,3);array[top]=points;bad[field]=array.ravel().tolist()
        try:wear(bad,source)
        except AssertionError as error:
            message=str(error);assert expected in message,(name,message)
            results[name]={'verdict':'REJECTED','reason':message}
        else:raise AssertionError(f'{name} was accepted')
    return {'verdict':'PASS','project':str(project),'projectSha256':hashlib.sha256(raw).hexdigest(),
            'bodySourceSha256':data['body']['sourceSha256'],'sourceFingerprint':data['fingerprint'],
            'probes':results,'scope':'Actual exported mesh, independent anatomical section/skin queries; no solver substitution.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--body-source',type=Path,default=Path(__file__).resolve().parents[2]/'web/human-studio/assets/human.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=run(args.project,args.body_source);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
