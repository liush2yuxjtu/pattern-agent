#!/usr/bin/env python3
"""Independently re-open a saved GLB and its exact original DXF; exit 2 on FAIL."""
import argparse,json
from pathlib import Path
from verification.seams import audit_glb

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dxf',type=Path,required=True);p.add_argument('--glb',type=Path,required=True);p.add_argument('--units',choices=['mm','cm','inch'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    report=audit_glb(a.glb.read_bytes(),a.dxf.read_bytes(),a.units);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    c=report.get('checks',{});print(json.dumps({'verdict':report['verdict'],'seams':len(c.get('seams',[])),'max_seam_gap_mm':c.get('max_seam_gap_mm'),'proper_self_intersections':c.get('proper_self_intersections'),'failures':report.get('failures',[])},ensure_ascii=False));return 0 if report['verdict']=='PASS' else 2

if __name__=='__main__':raise SystemExit(main())
