#!/usr/bin/env python3
"""Extract original DXF polylines and text; never infer a units declaration."""
import argparse,json
from pathlib import Path

def extract(path):
    lines=Path(path).read_bytes().decode('gb18030').splitlines()
    if len(lines)%2:raise ValueError('Incomplete DXF group-code pair')
    entities=[]
    for i in range(0,len(lines),2):
        code,value=int(lines[i]),lines[i+1].strip()
        if code==0:entities.append([value,{}])
        elif entities:entities[-1][1][code]=value
    polylines=[];points=[];texts=[]
    for kind,a in entities:
        if kind=='POLYLINE':points=[]
        elif kind=='VERTEX':points.append([float(a[10]),float(a[20])])
        elif kind=='SEQEND' and len(points)>1:polylines.append(points)
        elif kind=='TEXT':texts.append({'text':a[1],'x':float(a[10]),'y':float(a[20])})
    return polylines,{'source':Path(path).name,'units':'UNDECLARED','unit_assumption':'millimetres for this visual reconstruction only','sizes_explicit':['M'],'polylines':len(polylines),'texts':texts,'physical_fit':'NOT_RUN','prj_decode':'UNRESOLVED'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=Path('source/女紧身款T恤.dxf'));p.add_argument('--output',type=Path,default=Path('data/polylines.json'));p.add_argument('--summary',type=Path,default=Path('data/source-summary.json'));a=p.parse_args()
    polylines,summary=extract(a.input);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(polylines));a.summary.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'polylines':len(polylines),'texts':len(summary['texts'])}))
