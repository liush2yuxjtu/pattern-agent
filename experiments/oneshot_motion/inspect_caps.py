"""Diagnose sensitivity to artificial cap construction; never repair a mesh.

Both fans span the same ordered cuff boundary. A disagreement is UNKNOWN for
the physical-passage claim, rather than permission to choose a favorable fan.
This is a legacy-stage diagnostic, not an independent collision implementation.
"""
import argparse,importlib.util,json,sys
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--legacy-report',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);source=Path(__file__).resolve().parents[1]/'full_arm/verification/geometry.py'
    spec=importlib.util.spec_from_file_location('legacy_cap_diagnostic',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    top=json.loads((args.run/'topology.json').read_text());saved=json.loads(args.legacy_report.read_text());rows=[]
    for row in saved['frames']:
        if row['arm_entry_pass']:continue
        with np.load(args.run/'frames'/f"frame-{row['frame']:04d}.npz") as f:
            v=f['cloth_vertices'];triangles=f['cloth_triangles']
            for side in ('L','R'):
                if row['sleeves'][side]['pass']:continue
                loop=v[np.asarray(top['cuffs'][side])];hole=v[np.asarray(top['armholes'][side])];axis=loop.mean(axis=0)-hole.mean(axis=0);axis/=np.linalg.norm(axis)
                center=m._cap(loop);corner=np.asarray([[loop[0],loop[i],loop[i+1]] for i in range(1,len(loop)-1)])
                a=m._path_hits(f['path_'+side],center,axis);b=m._path_hits(f['path_'+side],corner,axis)
                info=m._mesh_info(v,triangles[np.asarray(top['sleeve_triangles'][side])])
                oriented=m._orient_cap_from_sleeve(v,np.asarray(top['cuffs'][side]),info['edge_faces'])
                oriented_hits=m._path_hits(f['path_'+side],oriented,None)
                rows.append({'frame':row['frame'],'side':side,'same_boundary_vertex_indices':top['cuffs'][side],
                             'center_fan_hits':a,'corner_fan_hits':b,'legacy_axis_forced_sum':sum(h['direction'] for h in a),
                             'consistently_oriented_cap_hits':oriented_hits,'consistently_oriented_cap_sum':sum(h['direction'] for h in oriented_hits),
                             'sleeve_wall_crossings':row['sleeves'][side]['sleeve_wall_crossings'],
                             'cap_sensitive':len(a)!=len(b),'decision':'UNKNOWN if only artificial-cap construction changes the passage verdict'})
    report={'rows':rows,'cap_sensitive_frames':sorted(set(r['frame'] for r in rows if r['cap_sensitive'])),
            'scope':'Diagnostic sensitivity, not proof of physical passage. Preserve original strict flags.'}
    args.out.write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':main()
