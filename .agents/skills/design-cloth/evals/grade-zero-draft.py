#!/usr/bin/env python3
"""Grade actual CAD/PDF artifacts and compare clean rebuild timings."""

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

import ezdxf
import fitz
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon


HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE/'zero-draft-cases.json').read_text())['cases']
CHECKS = [
    '运行真实工具并生成两版 CAD 与打印产物',
    '两版 DXF 毫米单位、净线与裁剪线闭合且无自交',
    '两版净尺寸、配缝或对称、缝份符合简报',
    '参数修改只改变指定净尺寸，其他目标尺寸保持',
    '整幅 PDF 的校准方框和裁片矢量比例正确',
    '分幅 PDF 的纸幅、校准框与拼页格完整，页码连续',
    '三次干净重建的 CAD 与打印几何证据一致',
]
MM = 72 / 25.4


def require(ok, context):
    if not ok:
        raise ValueError(context)


def close(a, b, tol=.15):
    return abs(a-b) <= tol


def read_dxf(file, names):
    doc = ezdxf.readfile(file)
    require(doc.units == 4, f'{file.name} 单位不是毫米')
    expected = {f'{name}_{suffix}' for name in names for suffix in ['NET','CUT']}
    layers = {}
    for entity in doc.modelspace().query('LWPOLYLINE'):
        layer = entity.dxf.layer.upper()
        if layer not in expected:
            continue
        require(layer not in layers, f'{layer} 存在重复轮廓')
        points = entity.get_points('xyb')
        require(entity.closed and len(points) >= 3 and all(abs(p[2]) < 1e-9 for p in points),
                f'{layer} 必须是闭合的折线路径')
        polygon = Polygon([(x,y) for x,y,_ in points])
        require(polygon.is_valid and polygon.area > 0, f'{layer} 轮廓无效或自交')
        layers[layer] = polygon
    require(set(layers) == expected, f'缺图层：{sorted(expected-set(layers))}')
    return layers


def profile(poly, spec):
    lo, bottom, hi, top = poly.bounds
    def width(y):
        return round(poly.intersection(LineString([(lo-1,y),(hi+1,y)])).length, 4)
    return {'top_mm':width(top), 'hem_mm':width(bottom), 'length_mm':round(top-bottom,4),
            **({'transition_width_mm':width(top-spec['transition_mm'])} if 'transition_mm' in spec else {})}


def dims_and_allowance(layers, spec, names):
    result = {}
    normalized = []
    for name in names:
        net, cut = layers[f'{name}_NET'], layers[f'{name}_CUT']
        dims = profile(net,spec)
        for key, value in dims.items():
            expected = spec['hem_mm' if key=='transition_width_mm' else key]
            require(close(value, expected), f'{name} {key}: {value}，目标 {expected}')
        require(cut.covers(net), f'{name} 裁剪线未包住净线')
        coords = list(net.exterior.coords)
        gaps = [cut.exterior.distance(Point((x1+x2)/2,(y1+y2)/2))
                for (x1,y1),(x2,y2) in zip(coords,coords[1:]) if math.hypot(x2-x1,y2-y1)>5]
        require(gaps and all(close(g,spec['allowance_mm'],.25) for g in gaps), f'{name} 缝份实测 {gaps}')
        lo, ymin, hi, _ = net.bounds
        part = affinity.translate(net,-(lo+hi)/2,-ymin)
        require(part.symmetric_difference(affinity.scale(part, xfact=-1, yfact=1, origin=(0,0))).area < 1,
                f'{name} 左右失去对称')
        normalized.append(part)
        result[name] = {**dims,'allowance_range_mm':[round(min(gaps),4),round(max(gaps),4)]}
    if len(normalized) == 2:
        require(normalized[0].symmetric_difference(normalized[1]).area < 1,
                '本例要求前后片可配对的相同侧缝')
    return result


def verify_tiles(pages, names):
    texts=[row['text'] for row in pages]
    number_pattern=re.compile(r'(?i)\bPage\s+(\d+)(?:\s*/\s*|\s+of\s+)(\d+)|(?m:^\s*(\d+)\s*\|)')
    matches=[number_pattern.search(text) for text in texts]
    require(all(matches), '校准页或拼页缺可读页码')
    require(all(int(match[1] or match[3])==i for i,match in enumerate(matches,1)), '页码跳号、重复或乱序')
    require(all(not match[2] or int(match[2])==len(texts) for match in matches), '声明总页数与实际不符')
    rows_pattern=re.compile(r'(?i)\bR(?:OW\s*)?(\d+)(?:\s*/\s*(\d+))?\s+C(?:OL(?:UMN)?\s*)?(\d+)(?:\s*/\s*(\d+))?')
    grids={name:[] for name in names}
    declared=None
    for pat, order in [(r'(?i)(\d+)[ -]+rows?\s*[x×]\s*(\d+)[ -]+columns?', (1,2)),
                       (r'(?i)(\d+)[ -]+columns?\s+by\s+(\d+)[ -]+rows?', (2,1))]:
        match=re.search(pat,texts[0])
        if match:
            declared=tuple(int(match[i]) for i in order)
            break
    for text in texts[1:]:
        match=rows_pattern.search(text)
        named=[name for name in names if re.search(rf'\b{name}\b',text,re.I)]
        require(match and len(named)==1, '拼页缺唯一裁片名与行列位置')
        row,row_count,col,col_count=match.groups()
        grid=re.search(r'(?i)\bgrid\s*(\d+)\s*[x×]\s*(\d+)',text)
        limits=(int(row_count),int(col_count)) if row_count and col_count else tuple(map(int,grid.groups())) if grid else declared
        require(limits, f'{named[0]} 未声明拼页行列总数')
        grids[named[0]].append((int(row),int(col),limits))
    for name, tiles in grids.items():
        require(tiles, f'{name} 无拼页')
        limits=tiles[0][2]
        expected={(r,c) for r in range(1,limits[0]+1) for c in range(1,limits[1]+1)}
        coords=[(r,c) for r,c,_ in tiles]
        require(all(item[2]==limits for item in tiles) and set(coords)==expected and len(coords)==len(expected),
                f'{name} 拼页缺失或重复')
    return {name:len(tiles) for name,tiles in grids.items()}


def pdf_detail(file, tiled, parts=(), names=()):
    with fitz.open(file) as doc:
        require(len(doc)>0, f'{file.name} 没有可读页面')
        squares = []
        contours = []
        pages = []
        for page in doc:
            w,h=[x/MM for x in (page.rect.width,page.rect.height)]
            drawings=page.get_drawings()
            page_text=page.get_text()
            pages.append({'size_mm':[round(w,3),round(h,3)], 'vectors':len(drawings), 'text':page_text})
            if tiled:
                require(all(close(a,b,.3) for a,b in zip(sorted([w,h]),[210,297])), f'{file.name} 页幅 {w:.2f}×{h:.2f}')
            for path in drawings:
                rect=path['rect']
                bounds=(rect.width/MM,rect.height/MM)
                items=[item[0] for item in path['items']]
                if all(close(d,100,.25) for d in bounds) and ('re' in items or items.count('l')>=3):
                    squares.append(list(bounds))
                if 'l' in items or 'c' in items or 'qu' in items or 're' in items:
                    if rect in page.rect:
                        contours.append((len(pages),bounds,tuple(rect)))
            # Also accept four separately stroked orthogonal edges for the calibration square.
            lines=[(item[1],item[2]) for path in drawings for item in path['items'] if item[0]=='l']
            for a,b in lines:
                if abs(a.y-b.y) > .25 or not close(abs(a.x-b.x)/MM,100,.25):
                    continue
                xa,xb=sorted([a.x,b.x]); y=a.y
                for sign in [-1,1]:
                    other=y+sign*100*MM
                    def matching(x1,y1,x2,y2):
                        return any((math.hypot(c.x-x1,c.y-y1)<.6 and math.hypot(d.x-x2,d.y-y2)<.6)
                                   or (math.hypot(d.x-x1,d.y-y1)<.6 and math.hypot(c.x-x2,c.y-y2)<.6) for c,d in lines)
                    if matching(xa,other,xb,other) and matching(xa,y,xa,other) and matching(xb,y,xb,other):
                        squares.append([abs(xb-xa)/MM,100.0]); break
        require(bool(squares), f'{file.name} 找不到实测一百毫米矢量方框')
        tile_counts={}
        if tiled:
            require(len(pages)>1 and all(row['vectors'] and row['text'].strip() for row in pages),
                    f'{file.name} 含空页或缺少文本定位标记')
            tile_counts=verify_tiles(pages,names)
        else:
            # Match each printed part to a separate paper region. Net and cut
            # outlines from the same position cannot stand in for a second equal-size piece.
            used=[]
            for net,cut in parts:
                sizes=[(p.bounds[2]-p.bounds[0],p.bounds[3]-p.bounds[1]) for p in (cut,net)]
                def distinct(candidate):
                    page,_,rect=candidate
                    x,y=(rect[0]+rect[2])/2,(rect[1]+rect[3])/2
                    return all(page!=n or abs(x-ox)>MM*15 or abs(y-oy)>MM*15 for n,ox,oy in used)
                matched=next((candidate for size in sizes for candidate in contours
                              if all(close(a,b,.5) for a,b in zip(sorted(candidate[1]),sorted(size)))
                              and distinct(candidate)),None)
                require(matched, f'{file.name} 缺独立摆放的完整裁片，目标外接尺寸 {sizes}')
                page,_,rect=matched
                used.append((page,(rect[0]+rect[2])/2,(rect[1]+rect[3])/2))
        return {'pages':len(pages),'square_mm':[round(x,5) for x in squares[0]],
                'vectors':sum(row['vectors'] for row in pages), **({'tiles':tile_counts} if tiled else {})}


def artifact_checks(out, case):
    values = {}; layers = {}
    for variant in ['base','revision']:
        folder=out/variant
        layers[variant]=read_dxf(folder/'pattern.dxf',case['pieces'])
        values[variant]=dims_and_allowance(layers[variant],case[variant],case['pieces'])
    return layers,values


def physical_signature(folder,case):
    layers,values=artifact_checks(folder,case)
    signature={}
    for variant in layers:
        group=layers[variant]
        parts=[(group[f'{p}_NET'],group[f'{p}_CUT']) for p in case['pieces']]
        signature[variant]={
            'measured':values[variant], 'full':pdf_detail(folder/variant/'full.pdf',False,parts),
            'a4':pdf_detail(folder/variant/'a4.pdf',True,names=case['pieces']),
            'outlines':{name:list(poly.exterior.coords) for name,poly in group.items()},
        }
    return signature


def grade(folder, case, repeats):
    out=folder/'outputs'
    checks=[]
    values={}
    timings=[]
    def check(index, action):
        try:
            detail=action()
            checks.append({'text':CHECKS[index], 'passed':True, 'evidence':str(detail)})
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, ezdxf.DXFError) as exc:
            checks.append({'text':CHECKS[index], 'passed':False, 'evidence':str(exc)})

    command_items=[]
    for line in (folder/'events.jsonl').read_text().splitlines():
        try:
            event=json.loads(line)
        except json.JSONDecodeError:
            continue
        item=event.get('item',{})
        if event.get('type')=='item.completed' and item.get('type')=='command_execution':
            command_items.append(item)
    def tool_run():
        ok=[item for item in command_items if item.get('exit_code')==0]
        require(ok, '工具轨迹没有成功执行的命令')
        require(all((out/variant/name).is_file() for variant in ['base','revision'] for name in ['pattern.dxf','full.pdf','a4.pdf']), '两版产物不齐')
        return f'成功命令 {len(ok)} / {len(command_items)}，两版六个文件齐备'
    check(0,tool_run)
    check(1,lambda: {v:sorted(read_dxf(out/v/'pattern.dxf',case['pieces'])) for v in ['base','revision']})
    def geometry():
        _,measured=artifact_checks(out,case)
        values.update(measured)
        return measured
    check(2,geometry)
    def delta():
        _,measured=artifact_checks(out,case)
        key='length_mm' if case['id']==33 else 'top_mm'
        target=case['revision'][key]-case['base'][key]
        diffs={part:{k:round(measured['revision'][part][k]-v,4) for k,v in measured['base'][part].items() if isinstance(v,(float,int))} for part in case['pieces']}
        require(all(all(close(v,target if k==key else 0) for k,v in dims.items()) for dims in diffs.values()), str(diffs))
        values['delta']=diffs
        return diffs
    check(3,delta)
    def pdf(tiled):
        result={}
        for variant in ['base','revision']:
            layers=read_dxf(out/variant/'pattern.dxf',case['pieces'])
            parts=[(layers[f'{p}_NET'],layers[f'{p}_CUT']) for p in case['pieces']]
            result[variant]=pdf_detail(out/variant/('a4.pdf' if tiled else 'full.pdf'),tiled,parts,case['pieces'])
        values['a4' if tiled else 'full']=result
        return result
    check(4,lambda:pdf(False)); check(5,lambda:pdf(True))

    def rebuilds():
        script=out/'rebuild.sh'
        require(script.is_file(), '缺可执行重建入口')
        original=physical_signature(out,case)
        with tempfile.TemporaryDirectory(prefix='clean-',dir=folder) as temp:
            for i in range(repeats):
                work=Path(temp)/str(i)
                start=time.perf_counter()
                for variant in ['base','revision']:
                    env=dict(os.environ,PATTERN_EVAL_PYTHON=sys.executable)
                    process=subprocess.run(['sh',str(script),str(folder/f'{variant}.json'),str(work/variant)],cwd=folder,
                                           env=env,capture_output=True,text=True,timeout=45)
                    require(process.returncode==0, f'{variant} 重建失败：{process.stderr[-400:]}')
                timings.append(round(time.perf_counter()-start,4))
                require(physical_signature(work,case)==original, '干净重建的矢量坐标、版幅或校准证据改变')
        return f'{repeats} 次两版重建一致，耗时 {timings} 秒'
    check(6,rebuilds)
    passed=sum(x['passed'] for x in checks)
    summary={'passed':passed,'failed':len(checks)-passed,'total':len(checks),'pass_rate':passed/len(checks)}
    return {'expectations':checks,'summary':summary,'scope':'DIGITAL_ARTIFACTS_ONLY',
            'release_ready':False,'measurements':values,'rebuild_seconds':timings,
            'execution_metrics':{'tool_calls':dict(Counter(item['type'] for item in command_items)),
                                 'total_tool_calls':len(command_items),'errors_encountered':sum(item.get('exit_code')!=0 for item in command_items)}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace',type=Path)
    parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    for case in CASES:
        directory=args.workspace.resolve()/f'eval-{case["id"]}-{case["name"]}'
        metadata=json.loads((directory/'eval_metadata.json').read_text())
        metadata['assertions']=CHECKS
        (directory/'eval_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
        for kind in ['with_skill','old_skill']:
            folder=directory/kind
            result=grade(folder,case,args.repeats)
            (folder/'grading.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            print(f'{directory.name}/{kind}: {result["summary"]["passed"]}/{len(CHECKS)} DIGITAL_ONLY',flush=True)


if __name__=='__main__':
    main()
