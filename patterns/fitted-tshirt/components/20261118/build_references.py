#!/usr/bin/env python3
"""Keep supplementary CAD as data; export readable self-contained geometry YAML."""
from collections import Counter
import hashlib
import html
import io
import json
from pathlib import Path
import tempfile
import ezdxf
from ezdxf import recover
import yaml

HERE=Path(__file__).resolve().parent

def read(path):
    raw=path.read_bytes()
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError:text=raw.decode('gb18030')
    # These uploads are an ENTITIES-only R12 stream. Give the native reader an
    # explicit container/GBK declaration; never change the archived source.
    wrapped=raw
    if '$ACADVER' not in text:
        wrapped=b'0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n9\n$DWGCODEPAGE\n3\nANSI_936\n0\nENDSEC\n'+raw
    doc,auditor=recover.read(io.BytesIO(wrapped));assert not auditor.errors
    entities=[];counts=Counter()
    for entity in doc.modelspace():
        kind=entity.dxftype();counts[kind]+=1
        row={'名称':f'{kind}-{counts[kind]:03d}','类型':kind,'图层':entity.dxf.layer,'颜色索引':entity.dxf.get('color',256)}
        if kind=='POLYLINE':
            row.update(闭合=entity.is_closed,点位=[{'横':float(v.dxf.location.x),'高':float(v.dxf.location.y),'弧凸度':v.dxf.get('bulge',0.)} for v in entity.vertices])
            assert not any(v.dxf.get('start_width',0) or v.dxf.get('end_width',0) for v in entity.vertices),'Variable-width source requires an extended exporter'
        elif kind=='LINE':row['点位']=[{'横':float(p.x),'高':float(p.y)} for p in [entity.dxf.start,entity.dxf.end]]
        elif kind=='TEXT':row.update(文字=entity.dxf.text,位置={'横':float(entity.dxf.insert.x),'高':float(entity.dxf.insert.y)},字高=float(entity.dxf.height),旋转角=float(entity.dxf.get('rotation',0.)))
        else:raise ValueError('Unimplemented CAD entity '+kind)
        entities.append(row)
    assert counts['POLYLINE']>0 and counts['LINE']>0,'Native CAD reader returned an empty pattern'
    return raw,entities,dict(counts)

def reconstruct(model,path):
    doc=ezdxf.new('R12');doc.encoding='gbk';doc.header['$DWGCODEPAGE']='ANSI_936';doc.units=0;m=doc.modelspace()
    for row in model['完整二维图形']['实体']:
        attributes={'layer':row['图层'],'color':row['颜色索引']}
        if row['图层'] not in doc.layers:doc.layers.new(row['图层'])
        kind=row['类型']
        if kind in ['LINE','POLYLINE']:
            points=[(p['横'],p['高']) for p in row['点位']]
            if kind=='LINE':m.add_line(*points,dxfattribs=attributes)
            else:
                entity=m.add_polyline2d(points,close=row['闭合'],dxfattribs=attributes)
                for v,p in zip(entity.vertices,row['点位']):v.dxf.bulge=p['弧凸度']
        else:m.add_text(row['文字'],dxfattribs={**attributes,'insert':(row['位置']['横'],row['位置']['高']),'height':row['字高'],'rotation':row['旋转角']})
    doc.saveas(path,encoding='gbk')

def build(name,slug,quantity,notes):
    raw,entities,counts=read(HERE/(name+'.dxf'))
    model={'文件说明':{'名称':name+'部件候选规格','语言':'简体中文','用途':'供制版师复核、缝制人员查阅，并独立重建本部件二维图形',
        '状态':'补充候选，尚未替换整件原型','源文件':name+'.dxf','源文件摘要_SHA256':hashlib.sha256(raw).hexdigest(),
        '外部设计文件依赖':False,'说明':'源文件名与摘要用于溯源；下面已列出重建几何所需的全部实体，不需读取源DXF。'},
        '阅读顺序':['先看部件用途与缝制要点','核对单位、尺码和待确认项','需要重画时读取完整二维图形'],
        '部件概况':{'所属款式':'女士贴身长袖圆领T恤','部件':name,'CAD标注尺码':'M','CAD标注裁片数量':quantity,
            'CAD标注材料':'面料A；不是已确认的实际面料','部件要点':notes},
        '单位与坐标':{'坐标单位':'U','实际比例':'未标定；源DXF没有INSUNITS声明','每U毫米数':None,
            '坐标解释':'保留原CAD排版坐标，横为X、高为Y；图中总包围框不是成衣净尺寸'},
        '待确认项':['独立部件与整件原型是否属于同一版次','刀口、缝线、裁剪线与纱向的逐线语义','实际图形单位与缝份','两份不同的M码表采用哪份以及平量/围量口径','最终面料及力学标定'],
        '完整二维图形':{'实体数量':counts,'实体':entities}}
    path=HERE/(slug+'-spec.yaml');path.write_text(yaml.safe_dump(model,allow_unicode=True,sort_keys=False,width=110))
    reopened=yaml.safe_load(path.read_text())
    with tempfile.TemporaryDirectory() as temporary:
        target=Path(temporary)/'reconstructed.dxf';reconstruct(reopened,target)
        _,again,again_counts=read(target)
        assert again_counts==counts and again==entities,'YAML-only geometry reconstruction changed actual CAD entities'
    points=[(p['横'],p['高']) for e in entities for p in e.get('点位',[])];xs,ys=zip(*points);lo,hi=min(xs),max(xs);bottom,top=min(ys),max(ys);pad=max(hi-lo,top-bottom)*.04
    drawing=[]
    for e in entities:
        if '点位' in e:
            p=e['点位']+([e['点位'][0]] if e.get('闭合') else [])
            drawing.append('<polyline points="'+' '.join(f'{q["横"]},{-q["高"]}' for q in p)+'"/>')
        elif e['类型']=='TEXT':
            p=e['位置'];drawing.append(f'<text x="{p["横"]}" y="{-p["高"]}" font-size="{e["字高"]}" stroke="none" fill="#243a30">{html.escape(e["文字"])}</text>')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{lo-pad} {-top-pad} {hi-lo+2*pad} {top-bottom+2*pad}"><title>{name}原始CAD实体</title><g fill="none" stroke="#294b39" stroke-width="0.4">'+''.join(drawing)+'</g></svg>'
    (HERE/(slug+'.svg')).write_text(svg)
    return {'component':name,'source_sha256':hashlib.sha256(raw).hexdigest(),'yaml_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'entities':counts,'yaml_only_geometry_roundtrip':'PASS','exact_entity_fields_preserved':True,'semantic_sewing_and_production':'NOT_RUN'}

if __name__=='__main__':
    rows=[build('领子','collar',1,['参考图为窄圆领领条；实际折叠、内外层及缝份须按CAD逐线确认。','前中、后中和肩位标记以原CAD文字保留；未将全部标记自动配到整件接口。']),
          build('袖子','sleeve',2,['长袖袖片，保留袖山、袖侧、袖口及内部辅助线。','CAD数量为2；左右配对、正反面与前后袖山方向仍须逐线复核。'])]
    (HERE/'geometry-roundtrip.json').write_text(json.dumps({'verdict':'PASS','components':rows},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'verdict':'PASS','components':len(rows)},ensure_ascii=False))
