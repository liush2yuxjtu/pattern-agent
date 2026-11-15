"""Keep confirmed mesh defects and cap-dependent route uncertainty separate."""
import argparse,json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--caps',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();audit=json.loads(a.audit.read_text());caps=json.loads(a.caps.read_text());uncertain=set(caps['cap_sensitive_frames']);rows=[]
    for r in audit['frames']:
        status='FAIL' if not r['independent_saved_mesh_pass'] else 'UNKNOWN' if r['frame'] in uncertain else 'PASS' if r['legacy_arm_path_pass'] else 'FAIL'
        rows.append({'frame':r['frame'],'saved_pose_verdict':status,'self_pairs':len(r['cloth_self_pairs']),
                     'legacy_route_pass':r['legacy_arm_path_pass'],'cap_sensitive':r['frame'] in uncertain})
    summary={'frames':len(rows),'PASS':sum(r['saved_pose_verdict']=='PASS' for r in rows),'FAIL':sum(r['saved_pose_verdict']=='FAIL' for r in rows),
             'UNKNOWN':sum(r['saved_pose_verdict']=='UNKNOWN' for r in rows),'overall':'FAIL' if any(r['saved_pose_verdict']=='FAIL' for r in rows) else 'UNKNOWN' if uncertain else 'PASS',
             'physical_fit':'NOT_RUN','scope':'Saved geometry and limited trusted-source paths only; cap ambiguity is not upgraded to wearing PASS.'}
    a.out.write_text(json.dumps({'summary':summary,'frames':rows},indent=2)+'\n');print(json.dumps(summary))


if __name__=='__main__':main()
