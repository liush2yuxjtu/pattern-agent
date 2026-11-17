PYTHONPATH=/tmp/pattern-agent-prototype-331a27d/deps python3 - <<'PY'
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,time
root=Path('/tmp/pattern-agent-prototype-331a27d')
sha='331a27daf46f5debf3745834b478641f96ace06a'
def run(item):
 name,script=item
 cmd=['python3',str(root/'scripts'/script),'--base-url','https://liush2yuxjtu.github.io/pattern-agent/','--expected-commit',sha,'--browser','/usr/bin/google-chrome','--output',str(root/'evidence'/name)]
 started=time.monotonic()
 with (root/'evidence'/(name+'.log')).open('w') as stream:
  proc=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,timeout=52)
 return {'name':name,'command':cmd,'exit_code':proc.returncode,'elapsed_seconds':round(time.monotonic()-started,2)}
with ThreadPoolExecutor(max_workers=3) as executor:
 results=list(executor.map(run,[('prototype','verify_prototype_package.py'),('existing','verify_pages.py'),('fitted','verify_fitted_tshirt.py')]))
(root/'evidence'/'commands.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
for result in results:
 if result['exit_code']!=0:
  print((root/'evidence'/(result['name']+'.log')).read_text())
assert all(r['exit_code']==0 for r in results)
for name,file in [('prototype','report.json'),('existing','browser-report.json'),('fitted','report.json')]:
 data=json.loads((root/'evidence'/name/file).read_text())
 print(json.dumps({'name':name,'verdict':data['verdict'],'commit':data['commit'],'checks':len(data['checks']),'downloads':len(data['downloads'])}))
PY
