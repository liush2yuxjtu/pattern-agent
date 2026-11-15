"""Create an inspectable diagnostic figure from measured per-frame geometry."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);args=p.parse_args()
    run=Path(args.run)
    report=json.loads((run/'verification/verification.json').read_text())
    rows=report['frames'];x=np.array([r['frame'] for r in rows])
    fig,axes=plt.subplots(4,1,figsize=(11,10),sharex=True,layout='constrained')
    fig.suptitle('Measured Blender Cloth diagnostics — synthetic fixture',fontsize=15)
    for key,label,color in [('self_intersection_pairs','Cloth self crossings','#c43e4b'),
                            ('cloth_body_intersection_pairs','Cloth / body crossings','#dd8b24'),
                            ('body_self_intersection_pairs','Body self crossings','#7856a8')]:
        axes[0].plot(x,[r.get(key,0) for r in rows],label=label,color=color)
    axes[0].set_ylabel('Triangle pairs');axes[0].legend(loc='upper right',ncols=3,fontsize=8)
    axes[1].plot(x,[r.get('seam_max_gap_mm',np.nan) for r in rows],color='#177879',label='Welded assembly seam gap')
    axes[1].axhline(2,color='#ba4545',ls='--',lw=1,label='Strict limit <2 mm')
    axes[1].set_ylabel('Gap (mm)');axes[1].legend(loc='upper right',fontsize=8)
    axes[2].plot(x,[r.get('strain_abs_p95_pct',np.nan) for r in rows],color='#177879',label='Absolute strain P95')
    axes[2].plot(x,[r.get('strain_abs_max_pct',np.nan) for r in rows],color='#8e7137',alpha=.8,label='Maximum local absolute strain')
    axes[2].set_ylabel('Strain (%)');axes[2].legend(loc='upper right',fontsize=8)
    axes[2].set_title('Against the assembled rest mesh; material is not calibrated',fontsize=9,loc='left')
    axes[3].step(x,[int(r.get('arm_entry_pass',False)) for r in rows],where='mid',label='Both arms enter correctly',color='#177879')
    axes[3].step(x,[int(r.get('cloth_sim_pass',False))-.04 for r in rows],where='mid',label='Full geometry gate',color='#355f9d')
    axes[3].set_yticks([0,1],['FAIL','PASS']);axes[3].set_ylim(-.15,1.15)
    axes[3].set_xlabel('Saved simulation frame at 24 fps');axes[3].legend(loc='lower right',fontsize=8)
    for ax in axes:
        ax.grid(axis='y',alpha=.2);ax.spines[['top','right']].set_visible(False)
        for frame,label in [(21,'A'),(81,'T'),(141,'Raised'),(221,'A')]:
            if frame<=max(x):ax.axvline(frame,color='#5a6570',lw=.6,alpha=.4)
    fig.savefig(run/'diagnostics.png',dpi=150)
    fig.savefig(run/'diagnostics.svg')


if __name__=='__main__':main()
