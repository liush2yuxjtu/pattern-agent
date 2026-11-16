#!/usr/bin/env python3
"""Exercise the shipped public CLIs on independent analytical mask/mesh controls."""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
import cv2
import numpy as np
import vtk

ROOT=Path(__file__).resolve().parents[2]
SCRIPTS=ROOT/'.agents/skills/garment-body-six-view/scripts'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    a=np.zeros((32,32),np.uint8);b=a.copy();a[4:12,4:12]=255;b[6:14,6:14]=255
    for name,image in [('reference.png',a),('projected.png',b),('photo.png',np.zeros((32,32,3),np.uint8))]:assert cv2.imwrite(str(out/name),image)
    commands=[]
    def run(command,name):
        result=subprocess.run(command,capture_output=True,text=True,cwd=ROOT);commands.append({'argv':command,'exit_code':result.returncode});(out/(name+'.stdout')).write_text(result.stdout);(out/(name+'.stderr')).write_text(result.stderr)
        if result.returncode:raise RuntimeError(name+' CLI failed')
    run([sys.executable,str(SCRIPTS/'verify_masks.py'),'--reference',str(out/'reference.png'),'--projected',str(out/'projected.png'),'--photo',str(out/'photo.png'),'--out',str(out/'mask-result')],'masks')
    metrics=json.loads((out/'mask-result/metrics.json').read_text());assert abs(metrics['iou']-9/23)<1e-12
    assert cv2.imread(str(out/'mask-result/overlay.png')).shape==(32,32,3)
    cylinder=vtk.vtkCylinderSource();cylinder.SetRadius(10);cylinder.SetHeight(20);cylinder.SetResolution(360);cylinder.Update();writer=vtk.vtkOBJWriter();writer.SetFileName(str(out/'cylinder.obj'));writer.SetInputConnection(cylinder.GetOutputPort());writer.Write()
    (out/'sections.json').write_text(json.dumps([{'name':'analytical_circle','origin':[0,0,0],'normal':[0,1,0],'seed':[0,0,0]}]))
    run([sys.executable,str(SCRIPTS/'measure_mesh.py'),'--mesh',str(out/'cylinder.obj'),'--sections',str(out/'sections.json'),'--unit','cm','--out',str(out/'measurements.json')],'mesh')
    measure=json.loads((out/'measurements.json').read_text())['measurements'][0]
    assert abs(measure['mesh_girth']-20*math.pi)<.01;assert measure['anatomical_accuracy_verified'] is False
    summary={'verdict':'PASS','scope':'actual helper CLI/serialization/overlay boundaries on analytical controls; not a human-fit or native agent test','expected_iou':9/23,'observed_iou':metrics['iou'],'expected_circle_cm':20*math.pi,'observed_circle_cm':measure['mesh_girth'],'commands':commands}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
