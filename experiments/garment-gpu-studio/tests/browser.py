"""Real Chromium / WebGPU compute acceptance. Run with the app's local HTTP server.

The isolated test profile permits SwiftShader. It is a real WebGPU device/queue
and WGSL execution, but it is NOT evidence of physical GPU acceleration.
"""
import argparse, json, hashlib, pathlib, sys, time, traceback
from playwright.sync_api import sync_playwright
root=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8047/garment-gpu-studio.html');parser.add_argument('--steps',type=int,default=180);args=parser.parse_args()
out=root/'evidence';out.mkdir(exist_ok=True);checks=[];errors=[];report={'status':'RUNNING','checks':checks,'errors':errors,'snapshots':[]}
def save(): (out/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
def check(name,condition,detail=None):
 checks.append({'name':name,'status':'PASS' if condition else 'FAIL','detail':detail});save();print(checks[-1],flush=True)
save()
try:
 with sync_playwright() as pw:
  launch=['--no-sandbox','--enable-unsafe-webgpu','--use-angle=vulkan','--use-vulkan=swiftshader','--enable-features=Vulkan','--disable-vulkan-surface']
  browser=pw.chromium.launch(executable_path='/usr/lib/chromium/chromium',headless=True,args=launch)
  context=browser.new_context(viewport={'width':1440,'height':1050},device_scale_factor=1,accept_downloads=True)
  page=context.new_page();requests=[];page.on('request',lambda r:requests.append(r.url));page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(args.url,wait_until='load');page.wait_for_function('window.garmentAPI && window.garmentState && !window.garmentState.busy',timeout=60000)
  state=page.evaluate('window.garmentState');report['initial']=state;report['adapter']=state['backend'];report['render']=state['render'];save()
  check('App: real anatomical mesh displayed',state['bodyVertices']==4002 and state['bodyFaces']==8000 and page.locator('canvas').count()==1)
  check('WASM: active f64 diagnostic kernel',state['wasm']['active'] and 'principal_min' in state['wasm']['exports'])
  check('WebGPU: compute adapter and device',state['backend'] is not None,state['backend'])
  if state['backend'] is None: raise RuntimeError('No WebGPU adapter; cannot certify compute')
  before=page.evaluate('window.garmentAPI.getPositions()');page.locator('#step').click();page.wait_for_function('window.garmentState.step===1 && !window.garmentState.busy',timeout=60000)
  after=page.evaluate('window.garmentAPI.getPositions()');check('WebGPU: raw GPU predictor changes actual read-back positions',before!=after and page.evaluate('window.garmentState.gpuCandidateDeltaMm')>0,page.evaluate('({dispatches:window.garmentState.dispatches,rawPredictorDeltaMm:window.garmentState.gpuCandidateDeltaMm})'))
  check('WebGPU: shader validation error free',not page.evaluate('window.garmentState.errors'),page.evaluate('window.garmentState.errors'))
  for i in range(args.steps//30):
   page.evaluate('async()=>{await window.garmentAPI.advance(30)}');print('GPU steps',page.evaluate('window.garmentState.step'),flush=True)
  page.locator('#verify').click();state=page.evaluate('window.garmentState');report['settled']=state;save()
  check('WebGPU: finite stable simulation',state['metrics']['finite'])
  check('seams: real equality constraints, zero residual',state['seams']['maxGapMm']==0)
  check('collision: morphed mesh queried for current frame',state['metrics']['fullCollision'] and state['metrics']['contactQueries']>state['vertices'])
  check('settled geometry: no full-face body crossing',state['metrics']['bodyFaceCrossings']==0,state['metrics']['bodyFaceCrossings'])
  check('settled geometry: no cloth self crossing',state['metrics']['selfFaceCrossings']==0,state['metrics']['selfFaceCrossings'])
  check('settled geometry: principal strain p95 <= 10%',state['metrics']['strainP95']<=.1,state['metrics']['strainP95'])
  check('settled geometry: maximum principal strain <= 25%',state['metrics']['strainMax']<=.25,state['metrics']['strainMax'])
  snapshot=page.evaluate('({project:window.garmentAPI.getProject(),positions:window.garmentAPI.getPositions()})');(out/'gpu-snapshot.json').write_text(json.dumps(snapshot));report['snapshots'].append('gpu-snapshot.json');save()
  for name in ['pattern','strain','stress','folds','collision','debug','fabric']:
   page.locator('[data-mode="'+name+'"]').click();check('view: '+name,page.evaluate('window.garmentState.mode')==name)
  step=page.evaluate('window.garmentState.step');page.evaluate('window.garmentAPI.seek(0)');check('replay: seeking preserves live solver step',page.evaluate('window.garmentState.step')==step)
  check('replay: exact recorded coordinates',page.evaluate('JSON.stringify(window.garmentAPI.getPositions())===JSON.stringify(Array.from(window.garmentAPI.getState().frames.frames[0].positions))'))
  page.locator('#next').click();check('replay: next frame button',page.evaluate('window.garmentState.cursor')==1)
  page.locator('#chestMm').fill('935');check('edit: immediately invalidates old physics',page.evaluate('window.garmentState.stale') and not page.locator('#obj').is_enabled())
  check('edit: stale PASS removed from screen','STALE' in page.locator('#diagnostics').inner_text())
  page.locator('#apply').click();page.wait_for_function('!window.garmentState.stale && !window.garmentState.busy',timeout=90000)
  wide=page.evaluate('window.garmentState');check('edit: new version and reset replay',wide['version']!=state['version'] and wide['step']==0 and wide['frameCount']==1)
  check('body: new requested chest remeasured < 1 mm',abs(wide['measurements']['chest'])<1,wide['measurements'])
  page.locator('#step').click();page.wait_for_function('window.garmentState.step===1 && !window.garmentState.busy',timeout=60000)
  check('WebGPU: rebuilt size really simulates',page.evaluate('window.garmentState.dispatches')>0)
  for i in range(6):
   page.evaluate('async()=>{await window.garmentAPI.advance(30)}');print('WIDE GPU steps',page.evaluate('window.garmentState.step'),flush=True)
  page.locator('#verify').click();wide_state=page.evaluate('window.garmentState');report['wideSettled']=wide_state;save()
  check('resized body: complete discrete geometry acceptance',wide_state['verdict']['geometry']=='PASS',wide_state['metrics'])
  wide_snapshot=page.evaluate('({project:window.garmentAPI.getProject(),positions:window.garmentAPI.getPositions()})');(out/'gpu-snapshot-wide.json').write_text(json.dumps(wide_snapshot))
  offline_next=wide_state['step']+1
  page.locator('#grade').click();page.wait_for_function('window.garmentState.grade && !window.garmentState.busy',timeout=90000)
  check('grading: three independently redrafted patterns',len(page.evaluate('window.garmentState.grade'))==3)
  page.locator('[data-mode="fabric"]').click()
  with page.expect_download() as dl:page.locator('#obj').click()
  dp=dl.value;path=out/'browser-export.obj';dp.save_as(path)
  positions=page.evaluate('window.garmentAPI.getPositions()');obj_vertices=[list(map(float,s.split()[1:])) for s in path.read_text().splitlines() if s.startswith('v ')]
  check('export: downloaded OBJ equals displayed frame',sum(obj_vertices,[])==positions)
  with page.expect_download() as dl:page.locator('#svg').click()
  dl.value.save_as(out/'browser-pattern.svg')
  check('export: downloaded SVG has real 100 mm scale','width="100" height="100"' in (out/'browser-pattern.svg').read_text())
  context.set_offline(True);page.locator('#step').click();page.wait_for_function('(n)=>window.garmentState.step===n && !window.garmentState.busy',arg=offline_next,timeout=60000)
  check('offline: GPU continues with network disabled',page.evaluate('window.garmentState.step')==offline_next)
  check('standalone: no remote runtime requests',not [u for u in requests if not u.startswith('http://127.0.0.1:8047/')],requests)
  page.set_viewport_size({'width':390,'height':844});check('mobile: no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
  page.set_viewport_size({'width':1440,'height':1050});page.screenshot(path=str(out/'browser-preview.png'),full_page=True)
  check('runtime: no page exceptions',not errors,errors)
  report['final']=page.evaluate('window.garmentState');report['status']='FAIL' if any(c['status']=='FAIL' for c in checks) else 'PASS';report['acceleration']='Software Vulkan/SwiftShader WebGPU unless adapter states hardware; no physical GPU performance claim.';save();browser.close()
except Exception as e:
 report['status']='BLOCKED' if not any(c['name'].startswith('WebGPU: raw GPU') and c['status']=='PASS' for c in checks) else 'FAIL';report['exception']=str(e);report['trace']=traceback.format_exc();save();print(report['trace'],flush=True);sys.exit(1)
print('BROWSER',report['status'],len(checks),'checks',flush=True)
