"""Build one offline HTML with exact design files and source-bound views."""
from pathlib import Path
from collections import defaultdict,deque
import argparse
import base64
import hashlib
import html
import json
import sys
import yaml

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
BENCH=REPO/'experiments/intent-edit-benchmark'
sys.path.insert(0,str(BENCH))
import engine
import model_reader

CASES=['01_sleeve_length','02_body_length','03_cuff_width','04_front_neck']
LABELS={'01_sleeve_length':'袖子加长 20U','02_body_length':'前后衣身缩短 15U','03_cuff_width':'袖口展开宽增加 10U','04_front_neck':'前领加深 10U，领条联动'}
METRICS={'01_sleeve_length':['袖片纵线'],'02_body_length':['前中纵线','后中纵线'],'03_cuff_width':['袖口展开线长'],'04_front_neck':['前片领深','领条长边']}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_record(path,name=None,mime='application/octet-stream'):
    raw=path.read_bytes()
    return {'name':name or path.name,'path':str(path.relative_to(REPO)),'mime':mime,'byte_length':len(raw),'sha256':sha(raw),'base64':base64.b64encode(raw).decode('ascii')}
def make_entry(cid):
    directory=REPO/'patterns/fitted-tshirt' if cid=='baseline' else BENCH/'results'/cid
    spec_path=directory/('input-spec.yaml' if cid=='baseline' else 'new-spec.yaml')
    dxf_path=directory/('input.dxf' if cid=='baseline' else 'output.dxf')
    spec=yaml.safe_load(spec_path.read_text());model_reader.validate(spec)
    files={'yaml':file_record(spec_path,'input-spec.yaml' if cid=='baseline' else cid+'-spec.yaml','application/yaml;charset=utf-8'),
      'dxf':file_record(dxf_path,'input.dxf' if cid=='baseline' else cid+'-output.dxf','application/dxf')}
    if cid!='baseline':
        files['spec_diff']=file_record(directory/'spec-diff.json',cid+'-spec-diff.json','application/json')
        files['geometry_patch']=file_record(directory/'geometry-patch.json',cid+'-geometry-patch.json','application/json')
    _,entities=engine.source_entities(dxf_path.read_bytes());lookup=defaultdict(deque)
    for row in model_reader.drawables(spec):
        kind={'折线':'POLYLINE','直线':'LINE','文字':'TEXT'}[row['线型']]
        points=row.get('点位',[row.get('位置')]);key=engine.key_for(kind,points,row.get('内容'))
        lookup[key].append({'piece':row['裁片'],'name':row.get('名称','文字')})
    primitives=[]
    contour_lines={s['线条'] for p in spec['完整二维几何'].values() for c in p['轮廓'].values() for s in c['组成']}
    for e in entities:
        key=engine.key_for(e['kind'],e['points'],e['text'])
        if not lookup[key]:raise ValueError('二维数据无法对应当前规格')
        label=lookup[key].popleft()
        primitives.append({'kind':e['kind'],'points':e['points'],'text':e['text'],'closed':False,**label,'contour':label['name'] in contour_lines})
    if any(lookup.values()):raise ValueError('规格几何没有完全显示')
    mesh_path=ROOT/'geometry'/(cid+'.mesh.json');raw=mesh_path.read_bytes();mesh=json.loads(raw)
    if mesh['source_dxf_sha256']!=files['dxf']['sha256'] or mesh['source_spec_sha256']!=files['yaml']['sha256']:raise ValueError('三维模型来源版次错误')
    entry={'id':cid,'files':files,'twoD':{'source_dxf_sha256':files['dxf']['sha256'],'source_yaml_sha256':files['yaml']['sha256'],'primitives':primitives},
      'threeD':{'artifact_base64':base64.b64encode(raw).decode('ascii'),'artifact_sha256':sha(raw),'byte_length':len(raw),
        'source_dxf_sha256':files['dxf']['sha256'],'source_yaml_sha256':files['yaml']['sha256'],'units':'U','mode':'static_geometric_assembly'}}
    if cid!='baseline':
        entry.update(label=LABELS[cid],intent=(directory/'intent.txt').read_text().strip())
    return entry,spec

def svg(primitives,box,label):
    x,y,w,h=box
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:.6f} {y:.6f} {w:.6f} {h:.6f}" role="img" aria-label="{html.escape(label)}"><title>{html.escape(label)}</title>']
    for i,p in enumerate(primitives):
        if p['kind']=='TEXT':
            px,py=p['points'][0]
            parts.append(f'<text x="{px:.6f}" y="{-py:.6f}" font-size="6" fill="#5e786b" font-family="sans-serif">{html.escape(p["text"] or "")}</text>')
        else:
            pts=' '.join(f'{px:.6f},{-py:.6f}' for px,py in p['points'])
            color='#285347' if p['contour'] else '#8da497';width=1 if p['contour'] else .55
            parts.append(f'<polyline data-entity="{i}" points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" vector-effect="non-scaling-stroke"/>')
    return ''.join(parts)+('</svg>')

def summary(model,names):
    rows=['品类: '+model['款式特征']['品类'],'图形单位: U']
    for name in names:rows.append(name+': '+format(model['关键尺寸']['项目'][name]['数值'],'.6f'))
    return rows+['生产状态: 待确认']

def build(output):
    base,base_model=make_entry('baseline');cases=[];models={}
    for cid in CASES:
        entry,m=make_entry(cid);cases.append(entry);models[cid]=m
    all_entries=[base]+cases
    points=[p for entry in all_entries for item in entry['twoD']['primitives'] for p in item['points']]
    x0,x1=min(p[0] for p in points),max(p[0] for p in points);y0,y1=min(p[1] for p in points),max(p[1] for p in points)
    box=[x0-25,-y1-25,x1-x0+50,y1-y0+50]
    for entry in all_entries:
        entry['twoD']['svg']=svg(entry['twoD']['primitives'],box,'输入二维纸样' if entry['id']=='baseline' else entry['label']+'输出二维纸样')
    base['summary_lines']=summary(base_model,METRICS[CASES[0]])
    for entry in cases:
        model=models[entry['id']];entry['summary_lines']=summary(model,METRICS[entry['id']]);entry['input_summary_lines']=summary(base_model,METRICS[entry['id']])
        entry['changes']=[{'name':name,'before':item['数值'],'after':model['关键尺寸']['项目'][name]['数值']} for name,item in base_model['关键尺寸']['项目'].items() if item['数值']!=model['关键尺寸']['项目'][name]['数值']]
    data={'schema_version':'intent-edit-review/1','baseline':base,'cases':cases,'scope':'静态几何示意；U未标定，布料仿真、生产缝合与试穿未验收。'}
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    page=(ROOT/'template.html').read_text()
    for tag,value in [('__STYLE__',(ROOT/'style.css').read_text()),('__DATA__',encoded),('__VIEWER__',(ROOT/'viewer.js').read_text()),('__APP__',(ROOT/'app.js').read_text())]:
        if page.count(tag)!=1:raise ValueError('模板占位符异常')
        page=page.replace(tag,value)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(page,encoding='utf-8')
    print(json.dumps({'html':str(output),'bytes':output.stat().st_size,'sha256':sha(output.read_bytes()),'cases':len(cases),'complete_design_files':sum(len(e['files']) for e in all_entries),'meshes':len(all_entries)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=REPO/'web/intent-edit-review/index.html');a=p.parse_args();build(a.output)
