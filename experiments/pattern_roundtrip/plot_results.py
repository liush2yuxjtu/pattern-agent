"""Plot measured physical output controls; no illustration or fit inference."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser();p.add_argument('--metric',type=Path,required=True);a=p.parse_args()
    c=json.loads((a.metric/'control-comparison.json').read_text());rows=c['rows'];x=[r['frame'] for r in rows]
    fig,axes=plt.subplots(2,1,figsize=(9,7),sharex=True,layout='constrained')
    ax=axes[0];ax.plot(x,[r['atlas_max_vertex_delta_m']*1000 for r in rows],color='#2166ac',label='Rigid atlas vs baseline');ax.plot(x,[r['short_max_vertex_delta_m']*1000 for r in rows],color='#b2182b',label='Left sleeve90% vs baseline');ax.axhline(1,color='black',ls='--',lw=1,label='Predeclared1mm invariance limit');ax.set_ylabel('Max physical vertex difference (mm)');ax.legend(fontsize=9);ax.set_title('Full garment causal controls FAIL: atlas layout changes output')
    ax=axes[1]
    for name,color,label in [('baseline','#333333','Baseline'),('atlas_rigid','#2166ac','Rigid atlas'),('left_sleeve_90','#b2182b','Left sleeve90%')]:
        r=json.loads((a.metric/name/'drape-report.json').read_text())['frames'];ax.plot([i['frame'] for i in r],[i['sewing_max_gap_mm'] for i in r],color=color,label=label)
    ax.axhline(2,color='black',ls='--',lw=1,label='Historical3D gap limit2mm');ax.set_ylabel('Max matched sewing-point gap (mm)');ax.set_xlabel('Saved frame (24fps; frozen A-pose body)');ax.legend(fontsize=9)
    for ax in axes:ax.grid(alpha=.2)
    fig.savefig(a.metric/'measured-controls.png',dpi=170);svg=a.metric/'measured-controls.svg';fig.savefig(svg);plt.close(fig)
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')


if __name__=='__main__':main()
