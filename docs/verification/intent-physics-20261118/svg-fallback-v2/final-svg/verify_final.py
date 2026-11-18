from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
import base64,gzip,hashlib,importlib.util,json,re,subprocess,sys,traceback
import numpy as np
from playwright.sync_api import sync_playwright
ROOT=Path.cwd();HERE=ROOT/'experiments/intent-edit-review/physics';OUT=ROOT/'work/intent-physics/svg-fallback-final';HTML=ROOT/'web/intent-edit-review/physics/index.html'
sys.path.insert(0,str(ROOT))
from scripts.playwright_http import new_api_context
spec=importlib.util.spec_from_file_location('svg_verify',HERE/'verify_svg_fallback.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
def sha(raw):return hashlib.sha256(raw).hexdigest()
raw=HTML.read_bytes();expected='80ccaf68114ad1d650ccfec248c812cc77d31ab5c9383e56d4904f18f617c872';assert sha(raw)==expected
text=raw.decode();encoded=re.search(r'<script id="physics-payload"[^>]*>(.*?)</script>',text,re.S)[1];payload=json.loads(gzip.decompress(base64.b64decode(encoded)))
actual_js=re.search(r'<script type="module">(.*?)</script>',text,re.S)[1]
subprocess.run([str(ROOT/'experiments/freesewing_cloth_lab/node_modules/.bin/esbuild'),str(HERE/'viewer.mjs'),'--bundle','--format=esm','--target=es2022','--minify','--legal-comments=inline','--outfile='+str(OUT/'expected-viewer.js')],check=True,capture_output=True)
rebuilt_js=(OUT/'expected-viewer.js').read_text().replace('</script','<\\/script');assert rebuilt_js==actual_js,'Final inline bundle differs from actual current entrypoint/dependencies'
rebuilt=(HERE/'viewer.template.html').read_text().replace('__STYLE__',(HERE/'viewer.css').read_text()).replace('__PAYLOAD__',encoded).replace('__BUNDLE__',rebuilt_js);assert rebuilt==text
expected_sources={name:sha((HERE/name).read_bytes()) for name in ['viewer.mjs','viewer.css','viewer.template.html','recording-codec.mjs']};assert payload['viewer_sources']==expected_sources
v3=json.loads((ROOT/'work/intent-physics/svg-fallback-v3/full/receipt.json').read_text());assert v3['verdict']=='PASS' and v3['viewer_sources']==expected_sources
report={'verdict':'FAIL','html_sha256':expected,'bytes':len(raw),'viewer_sources':expected_sources,'inline_bundle_sha256':sha(actual_js.encode()),'exact_current_source_bundle_template_css':True,'all_frames_payload_bytes':{},'browser_cases':[],'page_errors':[],'console_errors':[]}
sources={};recordings={}
for case in payload['cases']:
 id=case['input']['case'];directory=ROOT/'work/intent-physics'/('baseline-run37' if id=='baseline' else 'cuff-run37');source=json.loads((directory/'input.json').read_bytes());recording=json.loads((directory/'trajectory.json').read_bytes());audit=json.loads((directory/'audit.json').read_bytes());assert case['input']==source and case['audit']==audit
 assert {k:x for k,x in case['recording'].items() if k!='frames'}=={k:x for k,x in recording.items() if k!='frames'}
 all_arrays={}
 for key in v.ARRAYS:
  block=case['recording_blocks'][key];n,width=block['frames'],block['width'];assert n==len(recording['frames'])==61
  planes=np.frombuffer(base64.b64decode(block['base64']),dtype=np.uint8).reshape(4,n,width)
  deltas=planes.transpose(1,2,0).copy().view('<u4').reshape(n,width)
  words=np.bitwise_xor.accumulate(deltas,axis=0);assert words.dtype.itemsize==4
  for i,frame in enumerate(recording['frames']):
   assert case['recording']['frames'][i][key]=={'block':key,'frame':i}
   assert words[i].astype('<u4',copy=False).tobytes()==base64.b64decode(frame[key]),(id,key,i)
  all_arrays[key]={'frames':n,'decoded_sha256':sha(words.astype('<u4',copy=False).tobytes())}
 for i,frame in enumerate(recording['frames']):assert {k:x for k,x in case['recording']['frames'][i].items() if k not in v.ARRAYS}=={k:x for k,x in frame.items() if k not in v.ARRAYS}
 report['all_frames_payload_bytes'][id]={'input_sha256':sha((directory/'input.json').read_bytes()),'recording_sha256':sha((directory/'trajectory.json').read_bytes()),'audit_sha256':sha((directory/'audit.json').read_bytes()),'arrays':all_arrays};sources[id]=source;recordings[id]=recording
class Q(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Q,directory=str(HTML.parent)));Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/index.html'
try:
 with sync_playwright() as p:
  api=new_api_context(p,url);r=api.get(url);assert r.status==200 and sha(r.body())==expected;api.dispose()
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);context=browser.new_context(viewport={'width':1440,'height':1080},accept_downloads=True);context.add_init_script(v.NO_WEBGL);page=context.new_page();page.on('pageerror',lambda e:report['page_errors'].append(str(e)));page.on('console',lambda m:report['console_errors'].append(m.text) if m.type=='error' else None)
  page.goto(url,wait_until='load');page.wait_for_function('window.physicsReview && physicsReview.renderer().backend==="svg" && physicsReview.renderer().svgFaces>100',timeout=90000);assert page.evaluate('physicsReview.info().viewerSources')==expected_sources
  for id in ['baseline','03_cuff_width']:
   source,recording=sources[id],recordings[id];page.locator('#case').select_option(id);v.idle_svg(page);info=page.evaluate('physicsReview.info()');renderer=page.evaluate('physicsReview.renderer()');assert info['frames']==61 and info['verdict']=='PASS' and renderer['backend']=='svg' and not renderer['gpu'] and renderer['sourceTriangles']==len(source['triangles'])
   endpoints=[]
   for i in [0,60]:
    v.seek(page,i);state=page.evaluate(v.STATE_HASHES);assert state['hashes']=={key:sha(base64.b64decode(recording['frames'][i][key])) for key in v.ARRAYS};assert state['clock']==recording['frames'][i]['time'] and state['info']['index']==i and state['info']['integrationCallsDuringReplay']==0;endpoints.append(i)
   v.idle_svg(page);assert page.locator('#canvas-host>svg[data-renderer-backend="svg"] path').count()>100
   page.screenshot(path=str(OUT/f'{id}-actual-svg.png'))
   page.locator('#view-2d').click();assert page.locator('#canvas-host>svg[data-renderer-backend="svg"]').is_hidden();assert page.locator('#pattern-svg-host polyline').count()==204 and page.locator('#pattern-svg-host text').count()==27
   files=page.evaluate('physicsReview.sources().files');yaml_raw=(ROOT/files['yaml']['path']).read_bytes();page.locator('#open-spec').click();assert page.locator('#spec-content').text_content().encode()==yaml_raw
   with page.expect_download() as saved:page.locator('#spec-download').click()
   target=OUT/f'{id}.yaml';saved.value.save_as(target);assert target.read_bytes()==yaml_raw
   page.keyboard.press('Escape');assert page.evaluate('document.activeElement.id')=='open-spec';page.locator('#view-3d').click();assert page.locator('#canvas-host>svg[data-renderer-backend="svg"]').is_visible()
   report['browser_cases'].append({'case':id,'backend':renderer['backend'],'frames':61,'verified_endpoints':endpoints,'yaml_sha256':sha(yaml_raw),'exact_download':True,'source_triangles':renderer['sourceTriangles']})
  page.set_viewport_size({'width':375,'height':900});page.locator('#open-spec').click();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(OUT/'mobile-full-yaml.png'));page.keyboard.press('Escape');assert not report['page_errors'] and not report['console_errors'];browser.close()
 assert sha(HTML.read_bytes())==expected;report['verdict']='PASS'
except Exception as e:
 report['failure']=str(e);report['traceback']=traceback.format_exc();raise
finally:
 server.shutdown();server.server_close();(OUT/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report.get(k) for k in ['verdict','html_sha256','exact_current_source_bundle_template_css','failure']},ensure_ascii=False))
