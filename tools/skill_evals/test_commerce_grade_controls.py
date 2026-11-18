#!/usr/bin/env python3
"""Reproduce five frozen commerce-grader v1.1 fault/invariance controls.

Run against a completed pose-fit output and its frozen private case protocol:
  python tools/skill_evals/test_commerce_grade_controls.py \
    --candidate /absolute/completed/run-1/outputs \
    --case /absolute/protocol/cases/everlane-blue-shirt/case.json \
    --out /absolute/isolated/control-evidence

The CLI copies writable fault files into isolated candidates; originals are
read-only symlinks. Output must be an empty/new directory. It never refits the
human or updates actual run grading. Full grader execution checks three faults;
two deterministic crossing fixtures check incomplete/disconnected intervals.
"""
import argparse,pathlib,json,sys,shutil,concurrent.futures,subprocess,hashlib,cv2,numpy as np
def main():
    root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/skill_evals'))
    import commerce_grade as grader
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--candidate',required=True,type=pathlib.Path)
    parser.add_argument('--case',required=True,type=pathlib.Path)
    parser.add_argument('--out',required=True,type=pathlib.Path)
    args=parser.parse_args();source=args.candidate.resolve();case=args.case.resolve();dest=args.out.resolve()
    expected='e2908f7a4da8ab9eeb79cb05283e5fdc048e47e5604bee28fa73682ec0ed1757'
    if grader.sha(pathlib.Path(grader.__file__))!=expected:raise SystemExit('Frozen grader v1.1 implementation SHA differs; version new controls explicitly.')
    if not source.is_dir() or not case.is_file():raise SystemExit('Completed output directory and frozen case file required.')
    if source==dest or source in dest.parents or dest in source.parents:raise SystemExit('Control evidence must be isolated from actual outputs.')
    if dest.exists() and any(dest.iterdir()):raise SystemExit('Use an empty/new --out; previous control evidence is never removed.')
    dest.mkdir(parents=True,exist_ok=True)
    original_hashes=grader.output_hashes(source)
    controls=[]
    assert grader.paired_intervals([0,0.0001,2,5,7])==[(0.0,2.0),(5.0,7.0)]
    assert not any(lo<3<hi for lo,hi in grader.paired_intervals([0,2,5,7]))
    assert grader.paired_intervals([0,2,5]) is None
    controls.extend([dict(name='disjoint_skin_air_gap',passed=True,evidence='Crossings0,2,5,7 yield two intervals; point3 in air is not inside despite minmax hull.'),dict(name='odd_open_ray_unknown',passed=True,evidence='Three unique crossings return UNKNOWN, not collision-free.')])
    for name in ['pixel_view_tamper','posed_obj_translation','camera_parameter_alias']:
     d=dest/name/'candidate'
     if d.exists():shutil.rmtree(d)
     d.mkdir(parents=True,exist_ok=True)
     for p in source.iterdir():
      q=d/p.name
      if q.is_symlink():q.unlink()
      if not q.exists():q.symlink_to(p,target_is_directory=p.is_dir())
     if name=='pixel_view_tamper':
      (d/'views').unlink();(d/'views').mkdir()
      for p in (source/'views').iterdir():(d/'views'/p.name).symlink_to(p)
      path=d/'views/side.png';im=cv2.imread(str(path));path.unlink();im[:100,:100]=[255,0,255];cv2.imwrite(str(path),im)
     elif name=='posed_obj_translation':
      p=d/'posed.obj';text=p.read_text();p.unlink();lines=[]
      for line in text.splitlines():
       if line.startswith('v '):v=list(map(float,line.split()[1:]));v[0]+=15;line='v '+' '.join(map(str,v))
       lines.append(line)
      p.write_text('\n'.join(lines)+'\n')
     else:
      p=d/'camera.json';data=json.loads(p.read_text());p.unlink();data['final']=[999,-999,888,777,666,555];data['final_definition']='Deliberately nonsensical non-authoritative alias; original authoritative 3x4 matrix preserved.';p.write_text(json.dumps(data))
    def run(name):
     r=subprocess.run([sys.executable,str(root/'tools/skill_evals/commerce_grade.py'),'--candidate',str(dest/name/'candidate'),'--case',str(case),'--out',str(dest/name/'result')],capture_output=True,text=True)
     if r.returncode:raise RuntimeError(r.stderr[-1000:])
     d=json.loads((dest/name/'result/grading.json').read_text())
     if name=='pixel_view_tamper':passed=d['view_integrity']['checks']['side']['verdict']=='FAIL';evidence=d['view_integrity']['checks']['side']
     elif name=='posed_obj_translation':passed=d['source_reconstruction']['posed_max_error_cm']>14.99 and not d['expectations'][1]['passed'];evidence=d['source_reconstruction']
     else:passed=d['view_integrity']['checks']['photo']['verdict']=='PASS';evidence=d['view_integrity']['checks']['photo']
     return dict(name=name,passed=passed,evidence=evidence,grading_sha256=grader.sha(dest/name/'result/grading.json'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:controls.extend(pool.map(run,['pixel_view_tamper','posed_obj_translation','camera_parameter_alias']))
    if grader.output_hashes(source)!=original_hashes:raise RuntimeError('Actual source artifacts changed during controls; discard control run.')
    report=dict(grader_sha256=grader.sha(pathlib.Path(grader.__file__)),actual_source_state_sha256=grader.sha(source/'final-state.json'),controls=controls,all_passed=all(x['passed'] for x in controls),limits='These controls verify specific checker failure detection/invariance, not fitting quality. The real paired outcomes are independently graded and remain FAIL.')
    (dest/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    if not report['all_passed']:raise SystemExit(1)


if __name__ == "__main__":
    main()
