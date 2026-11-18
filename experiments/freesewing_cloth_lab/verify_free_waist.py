"""Actual no-pin gravity/contact tests on the shipped single HTML."""
import argparse,gzip,hashlib,json,time
from pathlib import Path
import numpy as np
from browser_launch import chromium_args
from playwright.sync_api import sync_playwright
from independent import run as independent
from independent_support import audit
ROOT=Path(__file__).resolve().parents[2]

def run(args):
 out=args.output;out.mkdir(parents=True,exist_ok=True);r={'url':args.url,'checks':{},'states':{},'errors':[]}
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=chromium_args());p=b.new_page(viewport={'width':1440,'height':1100});p.on('pageerror',lambda e:r['errors'].append(str(e)));response=p.goto(args.url,wait_until='networkidle',timeout=60000);p.wait_for_function('window.clothLab?.ready',timeout=60000);r['htmlSHA256']=hashlib.sha256(response.body()).hexdigest()
  r['checks']['noPinsAtStartup']=p.evaluate('clothLab.supportStats().fixed')==0
  centers=[]
  for target in [1440,1800]:
   p.evaluate('(n)=>clothLab.step(n)',target-p.evaluate('clothLab.stats().steps'));own=p.evaluate('clothLab.verify()');state=p.evaluate('clothLab.project()');s=audit(state);check=independent(state,ROOT,negative=False);key=f'step-{target}'
   with gzip.open(out/(key+'.json.gz'),'wt') as f:json.dump(state,f)
   r['states'][key]={'support':s,'independent':check,'appVerdict':own['verdict']};r['checks'][key]=own['verdict']==check['verdict']=='PASS' and s['fixedVertices']==0 and .9<=s['upwardToWeight']<=1.1 and s['comSpeed_m_s']<=.012;centers.append(s['com_m'])
   p.get_by_role('button',name='Back',exact=True).click();p.screenshot(path=str(out/(key+'-back.png')),full_page=True);(out/'progress.json').write_text(json.dumps(r,indent=2)+'\n')
  r['steadyCOMDisplacement_m']=float(np.linalg.norm(np.asarray(centers[1])-centers[0]));r['checks']['steadyOverAdditional3Seconds']=r['steadyCOMDisplacement_m']<.01
  p.evaluate('clothLab.reset();clothLab.setBodyEnabled(false)');start=p.evaluate('clothLab.project()');p.evaluate('clothLab.step(12)');fall=p.evaluate('clothLab.project()');weights=1/np.asarray(start['inverseMass']);a=np.asarray(start['positions']).reshape(-1,3);z=np.asarray(fall['positions']).reshape(-1,3);delta=np.sum((z-a)*weights[:,None],axis=0)/weights.sum();velocity=displacement=0.
  for _ in range(12):velocity=.98*velocity-9.81/120**2;displacement+=velocity
  error=float(np.max(abs(delta-np.array([0,displacement,0]))));support=audit(fall);r['freeFall']={'deltaCOM_m':delta.tolist(),'expectedGravityDisplacement_m':displacement,'error_m':error,'support':support,'bodyEnabled':fall['support']['bodyEnabled']};r['checks']['bodyRemovalCausesActualFreeFall']=bool(not fall['support']['bodyEnabled'] and error<1e-10 and delta[1]<-.03 and np.linalg.norm(support['normal_N'])<1e-12 and np.linalg.norm(support['friction_N'])<1e-12)
  with gzip.open(out/'body-removed-12.json.gz','wt') as f:json.dump(fall,f)
  p.screenshot(path=str(out/'body-removed.png'),full_page=True)
  broken=json.loads(json.dumps(fall));broken['inverseMass'][0]=0
  try:audit(broken);r['checks']['forgedPinRejected']=False
  except AssertionError:r['checks']['forgedPinRejected']=True
  p.evaluate('clothLab.reset();clothLab.step(120)');r['checks']['restoreHumanStillUnpinned']=p.evaluate('clothLab.supportStats().fixed')==0 and p.evaluate('clothLab.project().support.bodyEnabled');r['checks']['consoleHealthy']=not r['errors'];b.close()
 r['verdict']='PASS' if all(r['checks'].values()) else 'FAIL';(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'verdict':r['verdict'],'checks':r['checks'],'freeFallError_m':error,'states':{k:v['support'] for k,v in r['states'].items()}},indent=2));return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True);r=run(p.parse_args());raise SystemExit(0 if r['verdict']=='PASS' else 2)
