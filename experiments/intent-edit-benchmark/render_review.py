"""Plot the actual input/output DXFs for visual review; no image editing."""
from pathlib import Path
import argparse
import json
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/intent-benchmark-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import ezdxf
import yaml

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
FONT=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc')
def curves(doc):
    result=[]
    for e in doc.modelspace():
        if e.dxftype()=='POLYLINE':result.append([(p.dxf.location.x,p.dxf.location.y) for p in e.vertices])
        elif e.dxftype()=='LINE':result.append([(e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y)])
    return result
def render(results,output):
    source=ezdxf.readfile(REPO/'patterns/fitted-tshirt/input.dxf',encoding='gb18030');before=curves(source)
    base=yaml.safe_load((REPO/'patterns/fitted-tshirt/input-spec.yaml').read_text());records=[]
    fig,axes=plt.subplots(2,2,figsize=(14,14),dpi=150)
    for ax,d in zip(axes.flat,sorted(p for p in results.iterdir() if (p/'new-spec.yaml').exists()),strict=True):
        model=yaml.safe_load((d/'new-spec.yaml').read_text());case=json.loads((d/'case.json').read_text())
        doc=ezdxf.readfile(d/'output.dxf',encoding='gb18030');audit=doc.audit()
        if audit.errors or audit.fixes:raise ValueError((d.name,audit.errors,audit.fixes))
        declared='$INSUNITS' in (d/'output.dxf').read_bytes().decode('gb18030')
        records.append({'case':d.name,'ezdxf_reopen':'PASS','errors':len(audit.errors),'fixes':len(audit.fixes),'entities':len(doc.modelspace()),
          'raw_INSUNITS_declared':declared,'reader_default_INSUNITS':doc.units,'unit_interpretation':'原容器无HEADER；软件默认不是文件声明或真实标定，本测试按YAML图形单位U。'})
        affected=case['affected_pieces'];points=[]
        for m in [base,model]:
            for name in affected:
                piece=m['完整二维几何'][name];o=piece['排版放置点']
                points.extend((p['横']+o['横'],p['高']+o['高']) for line in piece['线条'] for p in line['点位'])
        left,right=min(p[0] for p in points),max(p[0] for p in points);bottom,top=min(p[1] for p in points),max(p[1] for p in points)
        for lines,color,label in [(before,'#879487','修改前'),(curves(doc),'#a3402d','修改后')]:
            for i,line in enumerate(lines):ax.plot([p[0] for p in line],[p[1] for p in line],color=color,lw=.75,alpha=.85,label=label if i==0 else None)
        margin=max(right-left,top-bottom)*.08
        ax.set_xlim(left-margin,right+margin);ax.set_ylim(bottom-margin,top+margin);ax.set_aspect('equal')
        ax.set_title(case['title'],fontproperties=FONT,fontsize=15)
        ax.set_xlabel('横向 / U',fontproperties=FONT);ax.set_ylabel('高度 / U',fontproperties=FONT)
        ax.legend(prop=FONT,loc='best');ax.grid(alpha=.12)
    fig.suptitle('四个明确意图：真实DXF修改前后叠加',fontproperties=FONT,fontsize=21,y=.98)
    fig.text(.5,.015,'图形单位U，毫米比例未标定；几何测试不等于生产或试穿验收',ha='center',fontproperties=FONT,fontsize=12)
    fig.tight_layout(rect=(0,.04,1,.96));output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(output);plt.close(fig)
    (output.parent/'third-party-dxf-reopen.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(records,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();render(a.results,a.output)
