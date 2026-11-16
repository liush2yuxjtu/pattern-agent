#!/usr/bin/env python3
"""Check delivered file bytes, native topology and actual PDF geometry."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import zipfile

import fitz

ROOT=Path(__file__).resolve().parents[1]


def require(condition,message):
    if not condition: raise AssertionError(message)


def verify(directory):
    directory=Path(directory)
    metadata=json.loads((directory/'build.json').read_text())
    for name,digest in metadata['files'].items():
        require(hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest,'File checksum mismatch: '+name)
    p=directory/'patterns/straight-skirt-eu40'
    native=json.loads((p/'straight-skirt-eu40.sloper').read_text())
    require(native['units']=='mm','Native units must be mm')
    measurements=p/native['measurementFile']
    require(measurements.is_file(),'Missing measurement sidecar')
    values={x['key']:x['value'] for x in json.loads(measurements.read_text())['measurements']}
    require(values=={'waist':740,'hip':980,'waist_to_hip':200,'skirt_length':600},'Reference body measurements changed')
    objects={o['id']:o for o in native['objects']}
    require(len(objects)==len(native['objects']),'Duplicate native IDs')
    pieces={o['name']:o for o in native['objects'] if o['type']=='piece'}
    require(set(pieces)=={'Back','Front','Waistband'},'Missing or unexpected pattern pieces')
    require(pieces['Back']['cut']=={'count':2,'mirrored':True},'Back must be cut twice mirrored')
    require(pieces['Front']['cut']['count']==1,'Front must be cut once on fold')
    require(pieces['Front']['foldEdge'] in [e['edge'] for e in pieces['Front']['path']],'Missing front fold edge')
    for name,piece in pieces.items():
        sequence=[]
        for ref in piece['path']:
            edge=objects[ref['edge']]
            require(edge['role']=='outline','Non-outline edge in '+name)
            start,end=edge['start'],edge['end']
            if ref.get('reversed'): start,end=end,start
            sequence.append((start,end))
        require(all(a[1]==b[0] for a,b in zip(sequence,sequence[1:]+sequence[:1])),'Disconnected native outline: '+name)
    for prefix in ['B','F']:
        legs=[o for o in native['objects'] if o.get('name','').startswith(prefix+'_Dart_leg_')]
        require(len(legs)==2 and all(o['role']=='stitch' for o in legs),'Darts must retain fabric with stitch marks')
        require(not any(o['id'] in [r['edge'] for r in pieces['Back' if prefix=='B' else 'Front']['path']] for o in legs),'A dart was cut out')
    a4=fitz.open(p/'print-a4.pdf')
    require(len(a4)==14,'A4 PDF must contain 1 cover plus 13 pattern sheets')
    for page in a4:
        require(abs(page.rect.width/72*25.4-210)<.02 and abs(page.rect.height/72*25.4-297)<.02,'A4 paper size changed')
    squares=[d['rect'] for d in a4[0].get_drawings() if abs(d['rect'].width/72*25.4-100)<.02 and abs(d['rect'].height/72*25.4-100)<.02]
    require(bool(squares),'No physical 100 x 100 mm calibration square')
    require('13 pages to print' in a4[0].get_text(),'Unexpected tile map')
    full=fitz.open(p/'print-fullsize.pdf')
    require(len(full)==1 and abs(full[0].rect.width/72*25.4-914)<.02 and abs(full[0].rect.height/72*25.4-925)<.02,'Full-size PDF dimensions changed')
    guide=fitz.open(p/'使用说明.pdf')
    require(len(guide)==2 and '基础直身裙' in guide[0].get_text(),'Chinese guide missing or unreadable')
    with zipfile.ZipFile(p.with_suffix('.zip')) as archive:
        require(archive.testzip() is None,'Archive failed CRC verification')
        expected={'straight-skirt-eu40/'+f.name:f for f in p.iterdir() if f.is_file()}
        require(set(archive.namelist())==set(expected),'Archive file set does not match site downloads')
        for name,file in expected.items(): require(archive.read(name)==file.read_bytes(),'Archive bytes differ: '+name)
    return {'verdict':'PASS','a4_pages':len(a4),'calibration_mm':[round(squares[0].width/72*25.4,4),round(squares[0].height/72*25.4,4)],'pieces':list(pieces),'guide_pages':len(guide),'checked_files':len(metadata['files'])}


def verify_native(cli,pattern):
    result=subprocess.run([cli,'check',str(pattern),'--json'],text=True,capture_output=True,timeout=30)
    require(result.returncode==0,'OpenSloper CLI check failed: '+result.stdout+result.stderr)
    # Read back current geometry through the public API; do not trust a stored report.
    requests=[{'jsonrpc':'2.0','id':1,'method':'open','params':{'path':str(pattern)}},
              {'jsonrpc':'2.0','id':2,'method':'list_objects','params':{}}]
    result=subprocess.run([cli,'serve'],input=''.join(json.dumps(r)+'\n' for r in requests),text=True,capture_output=True,timeout=30,check=True)
    replies=[json.loads(s) for s in result.stdout.splitlines()]
    require(all('error' not in r for r in replies),'Native read-back failed')
    objects={o['name']:o for o in replies[1]['result']['objects']}
    waist=2*sum(objects[n]['length'] for n in ['B_Waist_centre','B_Waist_outer','F_Waist_centre','F_Waist_outer'])
    require(abs(waist-750)<.01,'Sewn waist does not match 750 mm')
    sides=[sum(objects[f'{p}_{suffix}']['length'] for suffix in ['Side_curve','Side_lower']) for p in ['B','F']]
    require(abs(sides[0]-sides[1])<.01,'Side seams do not match')
    for prefix in ['B','F']:
        require(abs(objects[prefix+'_Dart_leg_1']['length']-objects[prefix+'_Dart_leg_2']['length'])<.01,'Unequal dart legs')
    return {'verdict':'PASS','waist_mm':waist,'side_lengths_mm':sides,'side_difference_mm':abs(sides[0]-sides[1])}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,default=ROOT/'dist')
    p.add_argument('--cli')
    args=p.parse_args()
    report=verify(args.directory)
    if args.cli: report['native']=verify_native(args.cli,(args.directory/'patterns/straight-skirt-eu40/straight-skirt-eu40.sloper').resolve())
    print(json.dumps(report,ensure_ascii=False,indent=2))
