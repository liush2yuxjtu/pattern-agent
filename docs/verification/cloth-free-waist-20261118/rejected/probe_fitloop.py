import sys,json,gzip
from pathlib import Path
sys.path.insert(0,'scripts')
from verify_pages import local_site
from playwright.sync_api import sync_playwright
import os;os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:4])
out=Path('/workspace/work/free-waist-20261118/fit-loop');out.mkdir(exist_ok=True)
with local_site(out.parent) as base,sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader']);p=b.new_page(viewport={'width':1440,'height':1100});p.goto(base+'fit-loop.html',timeout=60000);p.wait_for_function('clothLab?.ready',timeout=60000)
 for target in [120,240,480]:
  if target>120:p.evaluate('(n)=>clothLab.step(n)',target-p.evaluate('clothLab.stats().steps'))
  r=p.evaluate('({support:clothLab.supportStats(),stats:clothLab.stats(),coverage:clothLab.coverageCheck()})');print(target,json.dumps(r),flush=True)
  with gzip.open(out/(f'state-{target}.json.gz'),'wt') as f:json.dump(p.evaluate('clothLab.project()'),f)
 p.get_by_role('button',name='Back',exact=True).click();p.screenshot(path=str(out/'back.png'),full_page=True);b.close()
