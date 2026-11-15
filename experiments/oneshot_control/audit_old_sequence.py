"""Run versioned independent oracle v2 on frozen old frames; no legacy import."""
import argparse,hashlib,importlib.util,json,time
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--source',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--frames',nargs='+',type=int);args=p.parse_args()
spec=importlib.util.spec_from_file_location('retained_incident_oracle_v2',args.source);oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
started=time.monotonic();tests=oracle.analytic_tests();source_hash=hashlib.sha256(args.source.read_bytes()).hexdigest();receipt=dict(implementation='independent_oracle_v2_retained_incident_pairs',source_sha256=source_hash,analytic_tests=tests)
args.out.with_name(args.out.stem+'-analytic-first.json').write_text(json.dumps(receipt,indent=2))
legacy=json.loads((args.run/'verification/verification.json').read_text());old={int(r['frame']):r for r in legacy['frames']};files=sorted((args.run/'frames').glob('frame-*.npz'))
if args.frames:files=[f for f in files if int(f.stem.rsplit('-',1)[-1]) in args.frames]
rows=[];progress=args.out.with_name(args.out.stem+'-progress.json');ledger=args.out.with_suffix('.ndjson')
with ledger.open('w') as stream:
 for f in files:
  tick=time.monotonic();frame=int(f.stem.rsplit('-',1)[-1])
  with np.load(f) as data:cv,ct,bv,bt=[data[k] for k in ['cloth_vertices','cloth_triangles','body_vertices','body_triangles']]
  cp=oracle.intersect_pairs(cv,ct);cb=oracle.intersect_pairs(cv,ct,bv,bt);bp=oracle.intersect_pairs(bv,bt)
  incident=[pair for pair in cp if set(map(int,ct[pair[0]]))&set(map(int,ct[pair[1]]))]
  body_incident=[pair for pair in bp if set(map(int,bt[pair[0]]))&set(map(int,bt[pair[1]]))]
  row=dict(frame=frame,input_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),garment_self_pairs=cp,garment_body_pairs=cb,body_self_pairs=bp,garment_self_count=len(cp),garment_body_count=len(cb),body_self_count=len(bp),incident_self_pairs=incident,incident_self_count=len(incident),body_incident_self_count=len(body_incident),nonincident_self_count=len(cp)-len(incident),legacy_self_count=old[frame]['self_intersection_pairs'],delta_from_legacy=len(cp)-old[frame]['self_intersection_pairs'],nonincident_delta_from_legacy=len(cp)-len(incident)-old[frame]['self_intersection_pairs'],triangle_gate_pass=not cp and not cb and not bp,elapsed_seconds=time.monotonic()-tick)
  rows.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
  status=dict(last_frame=frame,frames_completed=len(rows),elapsed_seconds=time.monotonic()-started,latest_self_count=len(cp),latest_incident_count=len(incident),running_sum_extra_pairs=sum(r['delta_from_legacy'] for r in rows))
  progress.write_text(json.dumps(status,indent=2));print(json.dumps(status),flush=True)
ids=[r['frame'] for r in rows];full=ids==list(range(1,242));peak=max(rows,key=lambda r:r['garment_self_count'])
receipt.update(complete_241_frames=full,frame_count=len(rows),frame_ids=ids,garment_self_fail_frames=sum(r['garment_self_count']>0 for r in rows),triangle_gate_fail_frames=sum(not r['triangle_gate_pass'] for r in rows),first_fail_frame=next((r['frame'] for r in rows if not r['triangle_gate_pass']),None),sum_garment_self_pairs=sum(r['garment_self_count'] for r in rows),sum_legacy_self_pairs=sum(r['legacy_self_count'] for r in rows),sum_extra_pairs=sum(r['delta_from_legacy'] for r in rows),sum_incident_pairs=sum(r['incident_self_count'] for r in rows),nonincident_count_disagreement_frames=[r['frame'] for r in rows if r['nonincident_delta_from_legacy']],peak_frame=peak['frame'],peak_garment_self_count=peak['garment_self_count'],peak_legacy_self_count=peak['legacy_self_count'],peak_incident_count=peak['incident_self_count'],sum_garment_body_pairs=sum(r['garment_body_count'] for r in rows),sum_body_self_pairs=sum(r['body_self_count'] for r in rows),elapsed_seconds=time.monotonic()-started,frames=rows,limits=['Independent triangle intersection audit only; no physics or physical-fit claim.','Pair totals sum repeated frame-pairs across time, not globally unique pairs.','Frozen v1 and legacy receipts are historical and incomplete under the retained-incident-pair definition.'])
tmp=args.out.with_suffix('.tmp');tmp.write_text(json.dumps(receipt,indent=2,allow_nan=False));tmp.replace(args.out)
print('FINAL',json.dumps({k:v for k,v in receipt.items() if k not in ['frames','frame_ids','analytic_tests']}),flush=True)
