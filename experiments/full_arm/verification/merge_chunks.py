"""Combine independently computed frame chunks, rejecting omissions/duplicates."""
import argparse,csv,json
from pathlib import Path


def merge(paths,expected):
    chunks=[json.loads(Path(p).read_text()) for p in paths]
    rows=sorted([row for chunk in chunks for row in chunk['frames']],key=lambda row:row['frame'])
    observed=[r['frame'] for r in rows]
    if observed!=list(range(1,expected+1)):
        raise ValueError(f'Frame coverage must be exactly1..{expected}; got {len(observed)} entries')
    result={'schema_version':1,'frame_count':len(rows),'all_arm_entry_pass':all(r['arm_entry_pass'] for r in rows),
            'all_cloth_sim_pass':all(r['cloth_sim_pass'] for r in rows),'frames':rows,
            'limitations':chunks[0].get('limitations',[]),'source_chunks':[str(p) for p in paths]}
    # geometry.py reads the preceding measured frame when a chunk starts in the
    # middle of a run. Preserve that measured boundary displacement.
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--expected',type=int,required=True)
    p.add_argument('--out',required=True);p.add_argument('chunks',nargs='+');args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    report=merge(args.chunks,args.expected)
    (out/'verification.json').write_text(json.dumps(report,indent=2))
    columns=['frame','frame_file','arm_entry_pass','cloth_sim_pass','seam_max_gap_mm','self_intersection_pairs',
             'cloth_body_intersection_pairs','body_self_intersection_pairs','body_inside_sample_count',
             'body_penetration_max_mm','strain_abs_p95_pct','strain_abs_max_pct','motion_rms_mm']
    with (out/'per-frame.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(report['frames'])
    print(json.dumps({k:v for k,v in report.items() if k not in ['frames','limitations','source_chunks']}))
