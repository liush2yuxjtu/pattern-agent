import json,pathlib,hashlib
from playwright.sync_api import sync_playwright
root=pathlib.Path(__file__).resolve().parents[1];checks=[]
def check(name,value):checks.append({'name':name,'status':'PASS' if value else 'FAIL'})
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/lib/chromium/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-webgpu','--use-angle=vulkan','--use-vulkan=swiftshader','--enable-features=Vulkan','--disable-vulkan-surface'])
 page=b.new_page(viewport={'width':1440,'height':1050});page.goto('http://127.0.0.1:8047/garment-gpu-studio.html');page.wait_for_function('window.garmentState && !window.garmentState.busy',timeout=60000)
 page.locator('#run').click();page.wait_for_function('window.garmentState.running',timeout=60000)
 check('pause control remains enabled during integration',page.locator('#run').is_enabled());page.locator('#run').click();page.wait_for_function('!window.garmentState.running && !window.garmentState.busy',timeout=60000);check('pause actually stops simulation',not page.evaluate('window.garmentState.running'))
 check('live hybrid step finite',page.evaluate('window.garmentState.metrics.finite'))
 page.evaluate('async()=>{window.garmentAPI.getSolver().step=async()=>{throw new Error("controlled verification failure")};await window.garmentAPI.advance(1)}')
 check('failure marks data stale',page.evaluate('window.garmentState.stale'));check('failure disables exports',not page.locator('#obj').is_enabled());check('failure removes stale PASS labels','STALE' in page.locator('#diagnostics').inner_text() and 'PASS' not in page.locator('#diagnostics').inner_text())
 b.close()
old=json.loads((root/'evidence/browser-report.json').read_text())['physicalCoreSha256'];core={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'src').glob('*.js') if p.name not in ['app.js','viewer.js','exports.js']};check('physical core unchanged since full two-size run',old==core)
r={'status':'PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL','htmlSha256':hashlib.sha256((root/'dist/garment-gpu-studio.html').read_bytes()).hexdigest(),'checks':checks};(root/'evidence/ui-smoke-report.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
