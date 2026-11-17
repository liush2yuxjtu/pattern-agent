from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile

p=argparse.ArgumentParser(description='在全新目录从复现ZIP运行真实CLI及独立审计。')
p.add_argument('archive',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
commands=[]
with tempfile.TemporaryDirectory(prefix='intent-benchmark-zip-') as tmp:
    root=Path(tmp)
    with zipfile.ZipFile(a.archive) as z:
        for name in z.namelist():
            if not (root/name).resolve().is_relative_to(root):raise ValueError('非法归档路径')
        z.extractall(root);members=len(z.namelist())
    source=root/'experiments/intent-edit-benchmark'
    for command in [[sys.executable,str(source/'run_benchmark.py'),'--output',str(root/'fresh')],
                    [sys.executable,str(source/'audit_benchmark.py'),'--results',str(root/'fresh'),'--output',str(root/'fresh-audit')]]:
        r=subprocess.run(command,cwd=root,capture_output=True,text=True)
        commands.append({'command':[s.replace(str(root),'<isolated>') for s in command],'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    count=0
    for case in (source/'results').iterdir():
        if not (case/'new-spec.yaml').exists():continue
        for name in ['new-spec.yaml','output.dxf','spec-diff.json','geometry-patch.json']:
            if (case/name).read_bytes()!=(root/'fresh'/case.name/name).read_bytes():raise ValueError('归档重跑结果不同：'+case.name+'/'+name)
            count+=1
    audit=json.loads((root/'fresh-audit/independent-audit.json').read_text())
    if audit['verdict']!='PASS' or audit['positive_pass_count']!=4:raise ValueError('隔离独立审计未通过')
report={'verdict':'PASS','archive_sha256':hashlib.sha256(a.archive.read_bytes()).hexdigest(),'archive_members':members,
 'identical_artifacts':count,'positive_cases':4,'negative_cases':3,'commands':commands,'cleanup':'隔离目录自动删除。'}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='commands'},ensure_ascii=False))
