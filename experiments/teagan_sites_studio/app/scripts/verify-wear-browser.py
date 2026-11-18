from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import urlparse,unquote
import mimetypes,json,hashlib
root=(Path(__file__).resolve().parents[1]/'dist');work=Path('/tmp/pattern-wear-browser-qa');work.mkdir(parents=True,exist_ok=True);checks=[];errors=[];warnings=[]
def check(n,c):assert c,n;checks.append(n)
with sync_playwright()as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader']);ctx=b.new_context(viewport={'width':1500,'height':1000},accept_downloads=True)
 def route(r):
  f=root/(unquote(urlparse(r.request.url).path).lstrip('/')or'index.html')
  r.fulfill(status=200 if f.is_file()else 404,body=f.read_bytes()if f.is_file()else b'missing',content_type=mimetypes.guess_type(str(f))[0]or'application/octet-stream')
 ctx.route('http://pattern-studio.test/**',route);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text)if m.type=='error'else warnings.append(m.text)if m.type=='warning'else None)
 page.add_init_script('''window.__depthOnlyClearCount=0;for(const P of[WebGLRenderingContext.prototype,WebGL2RenderingContext.prototype]){const clear=P.clear;P.clear=function(mask){if(mask===256)window.__depthOnlyClearCount++;return clear.call(this,mask);};}''')
 try:
  page.goto('http://pattern-studio.test/',wait_until='networkidle');page.wait_for_function('window.patternStudio&&window.__atelier.fitReady',timeout=180000)
  check('Opaque human defaults to 100%',page.locator('#human-opacity').input_value()=='100')
  for key in['basic','relaxed','cropped']:
   page.locator('[data-preset="'+key+'"]').click();page.wait_for_function('(key)=>window.__atelier.preset===key&&window.__atelier.fitReady',arg=key,timeout=180000);r=page.evaluate('patternStudio.getWearReport()');check(key+' runtime geometry PASS',r['status']=='PASS'and r['report']['intersectingTriangles']==0 and r['report']['insideSamples']==0 and r['report']['seamMaxMm']<1 and all(r['report']['openings'].values()));page.locator('#frame-body').click();page.locator('#front').click();page.locator('#scene canvas').screenshot(path=str(work/(key+'-worn-front.png')));page.locator('#back').click();page.locator('#scene canvas').screenshot(path=str(work/(key+'-worn-back.png')))
  page.locator('[data-preset="basic"]').click();page.wait_for_function('window.__atelier.fitReady');page.locator('#front').click();page.locator('#frame-garment').click()
  with page.expect_download()as d:page.locator('#download-wear').click()
  d.value.save_as(str(work/'download-wear.json'));check('Wear download records actual checks and material limits',json.loads((work/'download-wear.json').read_text())['report']['materialPhysics']=='NOT_CALIBRATED')
  page.evaluate('patternStudio.setOption("lengthDelta",1)');check('Edits revoke PASS while solver runs',page.evaluate('patternStudio.getWearReport().status')=='SOLVING'and not page.evaluate('__atelier.fitReady'))
  page.evaluate('patternStudio.setOption("lengthDelta",2)');page.evaluate('patternStudio.setOption("lengthDelta",3)');check('2D is usable while worker solves',page.locator('#paper svg [data-part]').count()==3 and page.evaluate('patternStudio.getPattern().metrics.length')==680)
  page.wait_for_function('__atelier.fitReady',timeout=180000);r=page.evaluate('patternStudio.getWearReport()');check('Latest edit passes after cancelling stale workers',page.evaluate('__atelier.spec.lengthDelta')==3 and r['status']=='PASS');(work/'browser-latest.json').write_text(json.dumps(page.evaluate('patternStudio.getWearGeometry()')))
  page.locator('#reset').click();page.wait_for_function('__atelier.fitReady');page.locator('#back').click();page.locator('#scene canvas').screenshot(path=str(work/'final-back.png'));page.locator('#front').click();page.screenshot(path=str(work/'final-default.png'),full_page=False)
  check('Renderer never clears depth between body and cloth',page.evaluate('window.__depthOnlyClearCount')==0)
  with page.expect_popup()as popup:page.locator('a[href="./verification/wear-report.json"]').click()
  popup.value.wait_for_load_state();check('Independent verification report is accessible','PASS'in popup.value.locator('body').inner_text());popup.value.close()
  check('No console errors or buffer warnings',not errors and not warnings)
  result={'status':'PASS','testCount':len(checks),'tests':checks,'consoleErrors':errors,'warnings':warnings,'depthOnlyClears':page.evaluate('window.__depthOnlyClearCount'),'runner':'Installed Chromium + Playwright; actual dist artifacts with WebGL SwiftShader','artifactSha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest()for n in['index.html','studio.js','wear-worker.js','style.css','pattern-kernel.wasm','models/teagan-static-fits.json']}};(work/'wear-browser-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
 finally:b.close()
