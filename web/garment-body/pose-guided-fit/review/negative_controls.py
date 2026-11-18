#!/usr/bin/env python3
"""Real geometry faults plus metadata fraud; source runtime re-evaluates poses."""
import sys,json,shutil,copy
from pathlib import Path
REPO_ROOT=next(p for p in Path(__file__).resolve().parents if (p/'tools/human_fit/pose_guided/runtime.py').exists())
ARTIFACT_ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(REPO_ROOT/'tools/human_fit/pose_guided'))
sys.path.insert(0,str(REPO_ROOT/'tools/skill_evals'))
from runtime import Runtime
import grade_pose_guided_fit as critic
critic.ARTIFACT_ROOT=ARTIFACT_ROOT
from grade_pose_guided_fit import grade
src=Path(sys.argv[1]) if len(sys.argv)>1 else (ARTIFACT_ROOT/'model' if (ARTIFACT_ROOT/'model/final-state.json').exists() else ARTIFACT_ROOT/'iterations/round-8')
root=ARTIFACT_ROOT/'review/negative-controls';root.mkdir(exist_ok=True)
state=json.loads((src/'final-state.json').read_text());r=Runtime();report=[]
try:
 for name,kind in [('metadata_only_forged_pose','metadata'),('real_changed_right_arm','arm'),('real_changed_pelvis_spine','hip'),('tiny_body_containment_cheat','shrink')]:
  out=root/name;out.mkdir(exist_ok=True)
  for f in ['final-state.json','camera.json','posed.obj']:shutil.copy2(src/f,out/f)
  changed=copy.deepcopy(state)
  if kind in ['metadata','arm']:changed['poseDegrees']['upperarm01.R'][2]+=40
  elif kind=='hip':changed['poseDegrees']['spine05'][2]+=30
  (out/'final-state.json').write_text(json.dumps(changed,indent=2))
  if kind in ['arm','hip']:
   ev=r.evaluate(changed);v=ev['posed'][r.ids];lines=(src/'posed.obj').read_text().splitlines();i=0
   for n,l in enumerate(lines):
    if l.startswith('v '):lines[n]='v '+' '.join('%.9f'%x for x in v[i]);i+=1
   (out/'posed.obj').write_text('\n'.join(lines)+'\n')
  elif kind=='shrink':
   lines=(src/'posed.obj').read_text().splitlines()
   for n,l in enumerate(lines):
    if l.startswith('v '):
     xyz=list(map(float,l.split()[1:4]));xyz[0]*=.35;xyz[2]*=.35
     lines[n]='v '+' '.join(map(str,xyz))
   (out/'posed.obj').write_text('\n'.join(lines)+'\n')
  g=grade(out,str(ARTIFACT_ROOT/'review/acceptance.json'),out/'grade')
  fail=g['functional_integrity']['verdict']=='FAIL' or g['visual_alignment_2d']['verdict']=='FAIL'
  report.append({'name':name,'fault':kind,'functional_integrity':g['functional_integrity']['verdict'],'visual_alignment_2d':g['visual_alignment_2d']['verdict'],'action_alignment_2d':g.get('action_alignment_2d'),'left_arm_regional_verdict':g['visual_alignment_2d']['regions']['arm_left']['verdict'],'rejected':fail,'max_state_mesh_error_cm':g['functional_integrity'].get('independent_source_state_mesh_max_error_cm')})
finally:r.close()
(root/'summary.json').write_text(json.dumps({'source':str(src),'controls':report,'all_rejected':all(c['rejected'] for c in report)},indent=2));print(json.dumps(report,indent=2))
# A view-specific pose swap must fail even when all metadata still claims one pose.
if (src/'views/view-provenance.json').exists():
 from check_pose_guided_views import check
 for name,kind in [('view_specific_pose_swap','swap'),('view_provenance_mesh_fraud','metadata')]:
  out=root/name;out.mkdir(exist_ok=True)
  for f in ['final-state.json','posed.obj']:shutil.copy2(src/f,out/f)
  shutil.copytree(src/'views',out/'views',dirs_exist_ok=True)
  if kind=='swap':
   other=ARTIFACT_ROOT/'baseline'
   shutil.copy2(other/'side.png',out/'views/side.png')
  else:
   path=out/'views/view-provenance.json';pr=json.loads(path.read_text());pr['side']['posed_mesh_sha256']='0'*64;path.write_text(json.dumps(pr))
  result=check(out);(out/'view-integrity.json').write_text(json.dumps(result,indent=2))
  report.append({'name':name,'fault':kind,'view_integrity':result['verdict'],'rejected':result['verdict']=='FAIL'})
 (root/'summary.json').write_text(json.dumps({'source':str(src),'controls':report,'all_rejected':all(c['rejected'] for c in report)},indent=2))
