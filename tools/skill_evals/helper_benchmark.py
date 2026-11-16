#!/usr/bin/env python3
"""Real functional helper benchmark; not a Claude trigger or image-quality score."""
import argparse
import importlib.util
import json
import time
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def evaluate(module):
    a=np.zeros((10,10),bool);b=a.copy();a[2:6,2:6]=1;b[3:7,3:7]=1
    photo=np.zeros((10,10,3),np.uint8);allmask=np.ones((3,3))
    cases=[
        ('known_overlap',lambda:module.compare(a,b),lambda r:abs(r['iou']-9/23)<1e-12,False),
        ('identical_boundary_zero',lambda:module.compare(a,a),lambda r:r['iou']==1 and r['mean_symmetric_contour_distance_px']==0,False),
        ('empty_rejected',lambda:module.compare(np.zeros((3,3)),np.zeros((3,3))),None,True),
        ('shape_mismatch_rejected',lambda:module.compare(a,np.ones((3,3))),None,True),
        ('probability_mask_rejected',lambda:module.compare(np.full((3,3),.2),np.full((3,3),.9)),None,True),
        ('nan_mask_rejected',lambda:module.compare(np.full((3,3),np.nan),allmask),None,True),
        ('infinite_mask_rejected',lambda:module.compare(allmask,np.full((3,3),np.inf)),None,True),
        ('negative_photo_rejected',lambda:module.overlay(np.full((10,10,3),-1.),a,b),None,True),
        ('valid_overlay_colors',lambda:module.overlay(photo,a,a),lambda r:np.array_equal(r[3,3],[68,121,30]),False)
    ]
    rows=[];start=time.perf_counter()
    for name,call,check,reject in cases:
        try:
            value=call();passed=not reject and bool(check(value));observed='returned_result'
        except ValueError:
            passed=reject;observed='rejected_with_ValueError'
        except Exception as exc:
            passed=False;observed='unexpected_error:'+type(exc).__name__
        rows.append({'check':name,'passed':passed,'observation':observed})
    return {'passed':sum(r['passed'] for r in rows),'total':len(rows),'elapsed_seconds':time.perf_counter()-start,'checks':rows}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    old=load(Path(__file__).parent/'fixtures/v0/verify_masks.py','baseline_verify')
    new=load(ROOT/'.agents/skills/garment-body-six-view/scripts/verify_masks.py','current_verify')
    report={'scope':'binary-mask/overlay helper robustness on analytical controls; not native skill triggering, full workflow quality or body-measurement accuracy','baseline':evaluate(old),'current':evaluate(new),'timing_scope':'single in-process functional pass; no model latency/token comparison'}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if report['current']['passed']!=report['current']['total']:raise SystemExit(1)

if __name__=='__main__':main()
