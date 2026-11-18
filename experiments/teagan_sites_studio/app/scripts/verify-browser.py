from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import urlparse,unquote
from PIL import Image
import mimetypes,json,math
root=(Path(__file__).resolve().parents[1]/'dist');work=Path('/tmp/pattern-browser-qa');work.mkdir(parents=True,exist_ok=True);tests=[];errors=[]
def check(name,condition):
 assert condition,name
 tests.append(name)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader'])
 context=browser.new_context(viewport={'width':1600,'height':1000},device_scale_factor=1,accept_downloads=True)
 def route(r):
  f=(root/(unquote(urlparse(r.request.url).path).lstrip('/') or 'index.html')).resolve()
  if root not in f.parents or not f.is_file():r.fulfill(status=404,body='missing');return
  r.fulfill(status=200,body=f.read_bytes(),content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream')
 context.route('http://pattern-studio.test/**',route);page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text)if m.type=='error'else None)
 def state():return page.evaluate('window.__atelier')
 def ready():page.wait_for_function('window.patternStudio&&window.__atelier.rendererReady&&window.__atelier.fitReady',timeout=180000)
 def select_views(names):
  v=state()['views']
  for k in names:
   if not v[k]:page.locator('[data-panel="'+k+'"]').click();v=state()['views']
  for k in list(v):
   if v[k]and k not in names:page.locator('[data-panel="'+k+'"]').click();v=state()['views']
  page.wait_for_timeout(150)
 def slider(selector,value):page.locator(selector).evaluate('(el,v)=>{el.value=v;el.dispatchEvent(new Event("input",{bubbles:true}));}',str(value))
 def red_pixels(selector,file):
  page.locator(selector).screenshot(path=str(work/file),animations='disabled');im=Image.open(work/file).convert('RGB');return sum(1 for r,g,b in im.get_flattened_data()if r>120 and r>g*1.3 and r>b*1.3)
 try:
  page.goto('http://pattern-studio.test/',wait_until='networkidle');ready();s=state()
  check('Initial static geometric wear is PASS',s['geometricWear']['status']=='PASS')
  (work/'browser-basic.json').write_text(json.dumps(page.evaluate('patternStudio.getWearGeometry()')))
  check('Page identity and nonblank source SVG / WebGL / WASM', 'Teagan' in page.title()and page.locator('#paper svg [data-part]').count()==3 and s['wasm'])
  check('Default is 2D plus plain 3D, with no heat renderer or field',s['views']=={'paper':True,'model':True,'heat':False,'crease':False} and s['mode']=='solid'and not s['heatRendererReady']and s['deformation']is None and page.locator('#heat-scene canvas').count()==0)
  check('No default 2D heat coloring, legend, or heat controls',page.locator('.heat-triangle').count()==0 and not page.locator('#heat-panel').is_visible()and not page.locator('#heat-options').is_visible())
  page.screenshot(path=str(work/'default.png'),full_page=True,animations='disabled')
  for names in [['paper'],['model'],['paper','model'],['heat'],['paper','heat'],['model','heat'],['paper','model','heat']]:
   select_views(names);s=state();check('Actual multiselect combination: '+','.join(names),[k for k in s['views']if s['views'][k]]==[k for k in ['paper','model','heat']if k in names]and page.locator('.stage>section:visible').count()==len(names))
   for k in ['paper','model','heat']:check('Visibility '+','.join(names)+' / '+k,page.locator('#'+{'paper':'paper-panel','model':'model-panel','heat':'heat-panel'}[k]).is_visible()==(k in names))
  check('Plain and heat 3D are separate live canvases',page.locator('#scene canvas').is_visible()and page.locator('#heat-scene canvas').is_visible()and state()['heatRendererReady'])
  n=red_pixels('#scene canvas','normal-canvas.png');h=red_pixels('#heat-scene canvas','heat-canvas.png');check('Rendered heat stays separate from plain material pixels',h>n+300)
  check('2D remains plain when 3D heat is opened',page.locator('.heat-triangle').count()==0)
  page.locator('#paper-heat').check();check('2D heat is independently opt-in',page.locator('.heat-triangle').count()>1000);page.locator('#paper-heat').uncheck()
  before=state()['deformation']['max'];slider('#heat-opacity',0);page.wait_for_timeout(150);zero=red_pixels('#heat-scene canvas','heat-zero.png');check('Heat overlay strength can be zero without changing data',zero<h and abs(state()['deformation']['max']-before)<1e-9);slider('#heat-opacity',100);page.wait_for_timeout(150);check('Heat overlay strength updates independently',state()['heatOpacity']==1 and page.locator('#heat-opacity-label').inner_text()=='100%');slider('#heat-opacity',85)
  page.locator('#heat-scene canvas').focus();before=state()['cameraViews'];page.keyboard.press('ArrowRight');after=state()['cameraViews'];check('Heat view rotates independently',math.dist(before['heat'],after['heat'])>.01 and math.dist(before['model'],after['model'])<1e-8)
  page.locator('#heat-front').click();page.locator('#scene canvas').focus();before=state()['cameraViews'];page.keyboard.press('ArrowLeft');after=state()['cameraViews'];check('Plain view rotates independently',math.dist(before['model'],after['model'])>.01 and math.dist(before['heat'],after['heat'])<1e-8);page.locator('#front').click()
  page.locator('#paper [data-part="sleeve"]').click();check('2D selection links both 3D views and the heat summary',state()['selected']=='sleeve'and state()['deformation']['selectedPart']=='sleeve');page.locator('#analysis-clear-selection').click()
  slider('#heat-unfold',100);check('Heat unfold control updates the shared geometry and both sliders',state()['geometricWear']['status']=='PREVIEW'and not state()['human']['visible']and state()['unfold']==1 and page.locator('#unfold').input_value()=='100'and abs(state()['deformation']['max'])<1e-6);slider('#unfold',0);check('Plain unfold control updates heat view',state()['unfold']==0 and page.locator('#heat-unfold').input_value()=='0')
  page.locator('#heat-metric').select_option('shear');check('Heat metric changes without switching plain 3D mode',state()['deformation']['metric']=='shear'and state()['mode']=='solid');page.locator('#heat-metric').select_option('maxStrain')
  page.locator('#locate-heat-peak').click();check('Extreme probe appears only in the heat pane',state()['probe']is not None and page.locator('#heat-scene #heat-probe').is_visible()and page.locator('#scene #heat-probe').count()==0);page.locator('#analysis-clear-selection').click()
  page.locator('[data-mode="wire"]').click();check('Plain wireframe does not replace heat overlay',state()['mode']=='wire'and state()['views']['heat']and red_pixels('#heat-scene canvas','heat-with-wire.png')>300);page.locator('[data-mode="solid"]').click()
  slider('#lengthDelta',5);page.wait_for_function('window.__atelier.spec.lengthDelta===5',timeout=180000);page.wait_for_function('window.__atelier.fitReady',timeout=180000);check('Edited garment also passes body and seam checks',state()['geometricWear']['status']=='PASS');(work/'browser-edited.json').write_text(json.dumps(page.evaluate('patternStudio.getWearGeometry()')));check('Source edits rebuild both selected 3D views',state()['metrics']['length']==700 and state()['views']=={'paper':True,'model':True,'heat':True,'crease':False}and state()['deformation']['invalidFaces']==0);page.locator('#undo-edit').click();page.wait_for_function('window.__atelier.spec.lengthDelta===0');check('Undo preserves the selected views',state()['views']['heat']and state()['metrics']['length']==650)
  with page.expect_download()as d:page.locator('#download-deformation').click()
  f=work/'deformation.json';d.value.save_as(str(f));j=json.loads(f.read_text());check('Real export retains the verified source and numeric field',len(j['pieces'])==4 and j['assemblyAlgorithm']=='static-contact-assembly-v3'and j['geometricWear']['status']=='PASS'and j['bodyCollision']=='RUN'and j['summary']['invalidFaces']==0)
  page.screenshot(path=str(work/'all.png'),full_page=True,animations='disabled')
  select_views(['heat']);page.locator('[data-panel="heat"]').click();check('Last view cannot be deselected into a blank workspace',state()['views']['heat']and page.locator('.stage>section:visible').count()==1 and '至少' in page.locator('#toast').inner_text())
  select_views(['paper','model']);check('Closing heat removes its legend and 2D coloring',not page.locator('#heat-panel').is_visible()and not page.locator('#heat-options').is_visible()and page.locator('.heat-triangle').count()==0 and state()['deformation']is None)
  page.reload(wait_until='networkidle');ready();check('Reload always starts without automatically restoring heat',state()['views']=={'paper':True,'model':True,'heat':False,'crease':False}and not state()['heatRendererReady']and state()['mode']=='solid')
  page.set_viewport_size({'width':390,'height':844});page.evaluate('window.scrollTo(0,0)');select_views(['paper','model','heat']);check('Mobile supports all three vertically stacked views',page.locator('.stage>section:visible').count()==3 and page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'))
  check('Mobile independent canvases have usable dimensions',page.locator('#scene canvas').bounding_box()['height']>300 and page.locator('#heat-scene canvas').bounding_box()['height']>280);page.locator('#scene canvas').scroll_into_view_if_needed();page.wait_for_timeout(150);page.locator('#scene canvas').screenshot(path=str(work/'mobile-model-canvas.png'),animations='disabled')
  im=Image.open(work/'mobile-model-canvas.png').convert('RGB');greens=[(i%im.width,i//im.width)for i,(r,g,b)in enumerate(im.get_flattened_data())if g>r+10 and g>b+10];check('Mobile plain 3D is framed with the garment fully visible',len(greens)>100 and max(x for x,y in greens)-min(x for x,y in greens)<im.width*.9)
  page.locator('#heat-scene canvas').scroll_into_view_if_needed();page.wait_for_timeout(150);page.locator('#heat-scene canvas').screenshot(path=str(work/'mobile-heat-canvas.png'),animations='disabled');page.screenshot(path=str(work/'mobile-all.png'),full_page=False,animations='disabled')
  select_views(['heat']);check('Mobile heat-only view keeps controls and numeric legend',page.locator('#heat-legend').is_visible()and page.locator('#heat-unfold').is_visible());select_views(['paper','model']);page.locator('#scene canvas').scroll_into_view_if_needed();page.wait_for_timeout(150);page.screenshot(path=str(work/'mobile-default.png'),full_page=False,animations='disabled')
  check('Zero page and console errors',not errors)
  result={'status':'PASS','tests':tests,'testCount':len(tests),'consoleErrors':errors,'viewports':[{'width':1600,'height':1000},{'width':390,'height':844}],'defaultViews':['paper','model'],'defaultHeat':False,'runner':'Installed Chromium + Playwright, exact dist bytes via file-backed routes','fallbackReason':'Native browser connector UNAVAILABLE / Connection failed; managed browser runtime absent'}
  (work/'browser-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'status':'PASS','testCount':len(tests),'consoleErrors':errors,'normalRedPixels':n,'heatRedPixels':h},ensure_ascii=False))
 except Exception:
  page.screenshot(path=str(work/'failure.png'),full_page=True,animations='disabled');raise
 finally:browser.close()
