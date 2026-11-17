"""Reviewable corrected sewing-line artifacts; never overwrite the source DXF."""
import json
from html import escape
from verification.seams import decode_glb

def review_files(result,source):
    _,_,m,_=decode_glb(result.glb);p=m['pattern'];all_points=[q for curves in [p['original_edges'],p['derived_edges']] for points in curves.values() for q in points]
    x=[q[0] for q in all_points];y=[-q[1] for q in all_points];left,right=min(x)-35,max(x)+35;top,bottom=min(y)-65,max(y)+35
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left} {top} {right-left} {bottom-top}" role="img" aria-label="原始与修正缝合线对照"><rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" fill="#faf9f4"/>',f'<text x="{left+15}" y="{top+25}" font-size="15" fill="#213e34">灰虚线：原缝合线　彩色：修正缝合线</text>',f'<text x="{left+15}" y="{top+46}" font-size="11" fill="#68746b">供连接核查；原始文件未改动。不是含缝份的生产裁剪母版。</text>']
    for key,points in p['original_edges'].items():
        path=' '.join(f'{a:.6f},{-b:.6f}' for a,b in points);parts.append(f'<polyline points="{path}" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4 3"/>')
    for key,points in p['derived_edges'].items():
        colour='#3779a5' if key.startswith('front') else '#418466' if key.startswith('back') else '#a75a69';path=' '.join(f'{a:.6f},{-b:.6f}' for a,b in points);parts.append(f'<polyline points="{path}" fill="none" stroke="{colour}" stroke-width=".9"><title>{escape(key)}</title></polyline>')
    parts.append('</svg>')
    revision={'input_sha256':result.report['input_sha256'],'source_file':'original-input.dxf','coordinates':'canonical millimetres; apply physical_scale for this input geometry','physical_scale':m['physical_scale'],'source_profile':result.report['profile'],'contract':result.report['connection_verification']['contract'],'pattern':p,'production_cutting_approval':'NOT_RUN','hidden_neckband_inner_layer':'not part of the outer-shell certificate'}
    return {'original-input.dxf':source,'connection-verification.json':json.dumps(result.report['connection_verification'],ensure_ascii=False,indent=2).encode(),'pattern-revision.json':json.dumps(revision,ensure_ascii=False,indent=2).encode(),'corrected-seam-lines.svg':'\n'.join(parts).encode()}
