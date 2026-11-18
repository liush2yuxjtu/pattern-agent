"""Native WebGPU draw/buffer proof, fallback, loss recovery and fenced timing."""
import argparse,gzip,hashlib,json,base64
from pathlib import Path
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from browser_launch import chromium_args
from verify_heatmap_gpu import expected_colors

HOOK=r'''(()=>{
 const ids=new WeakMap();let next=1;const id=o=>{if(!ids.has(o))ids.set(o,next++);return ids.get(o)};
 window.gpuProof={shaderModules:0,submits:0,draws:[],copies:[]};window.captureGPU=false;
 const shader=GPUDevice.prototype.createShaderModule;GPUDevice.prototype.createShaderModule=function(d){window.gpuProof.shaderModules++;return Reflect.apply(shader,this,[d]);};
 const submit=GPUQueue.prototype.submit;GPUQueue.prototype.submit=function(...a){window.gpuProof.submits++;return Reflect.apply(submit,this,a);};
 const bindings=new WeakMap(),set=GPURenderPassEncoder.prototype.setVertexBuffer;
 GPURenderPassEncoder.prototype.setVertexBuffer=function(slot,buffer,...rest){let m=bindings.get(this);if(!m){m=new Map();bindings.set(this,m)}m.set(slot,id(buffer));return Reflect.apply(set,this,[slot,buffer,...rest]);};
 for(const name of ['draw','drawIndexed']){const original=GPURenderPassEncoder.prototype[name];GPURenderPassEncoder.prototype[name]=function(...a){if(window.captureGPU)window.gpuProof.draws.push({count:a[0],buffers:[...(bindings.get(this)?.values()||[])]});return Reflect.apply(original,this,a);};}
 const copy=GPUCommandEncoder.prototype.copyBufferToBuffer;GPUCommandEncoder.prototype.copyBufferToBuffer=function(...a){if(window.captureGPU)window.gpuProof.copies.push({source:id(a[0]),bytes:a[4]});return Reflect.apply(copy,this,a);};
})();'''

def run(args):
 out=args.output;out.mkdir(parents=True,exist_ok=True);base=args.url;gpu_url=base+('&' if '?' in base else '?')+'renderer=webgpu';r={'url':gpu_url,'checks':{},'errors':[],'views':{}}
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=chromium_args());ctx=b.new_context(viewport={'width':1440,'height':1100});ctx.add_init_script(HOOK);p=ctx.new_page();p.on('pageerror',lambda e:r['errors'].append(str(e)))
  response=p.goto(gpu_url,wait_until='networkidle');p.wait_for_function('window.clothLab?.ready',timeout=120000);r['htmlSHA256']=hashlib.sha256(response.body()).hexdigest();r['backend']=p.evaluate('clothLab.renderBackend()');assert r['backend']['api']=='WebGPU','A fallback is not WebGPU proof'
  r['checks']['nativeWebGPU']=p.evaluate('gpuProof.shaderModules>0 && gpuProof.submits>0');r['checks']['physicsClearlyCPU']=r['backend']['physics']=='WASM Float64 / CPU'
  state=p.evaluate('clothLab.project()')
  for view in ['strain','stress','fold','curvature','pressure']:
   p.get_by_role('button',name={'fold':'Fold · 折角','curvature':'Curvature · 曲率','pressure':'Pressure · 试衣压力'}.get(view,view.capitalize()),exact=True).click();p.evaluate('gpuProof.draws=[];gpuProof.copies=[];window.captureGPU=true');values=np.asarray(p.evaluate('clothLab.readColorBuffer()'));proof=p.evaluate('window.captureGPU=false;gpuProof');expected=expected_colors(state,view);error=float(np.max(abs(values-expected)));bound=any(c['bytes']==values.size*4 and any(d['count']==10752 and c['source'] in d['buffers'] for d in proof['draws']) for c in proof['copies']);r['views'][view]={'components':int(values.size),'maxLinearRGBError':error,'sameBufferBoundByClothDrawAndReadBack':bound,'verdict':'PASS' if error<2e-6 and values.size==32256 and bound else 'FAIL'}
   with gzip.open(out/(view+'-gpu-buffer.json.gz'),'wt') as f:json.dump({'values':values.tolist(),'proof':proof},f)
   p.screenshot(path=str(out/(view+'.png')),full_page=True);png=base64.b64decode(p.evaluate("async()=>{clothLab.drawFrame();await clothLab.gpuComplete();return document.getElementById('scene').toDataURL()}").split(',')[1]);(out/(view+'-canvas.png')).write_bytes(png);r['views'][view]['canvasSHA256']=hashlib.sha256(png).hexdigest()
  r['checks']['fiveDistinctActualCanvasImages']=len({x['canvasSHA256'] for x in r['views'].values()})==5;r['checks']['allFiveActualGPUColorBuffers']=all(x['verdict']=='PASS' for x in r['views'].values());p.evaluate("clothLab.setView('fabric')");p.get_by_role('button',name='Back',exact=True).click();p.screenshot(path=str(out/'back.png'),full_page=True);p.locator('#scene').screenshot(path=str(out/'canvas.png'));pixels=np.asarray(Image.open(out/'canvas.png').convert('RGB'));r['checks']['canvasNotBlank']=float(pixels.std())>15;r['canvasPixelStd']=float(pixels.std())
  # Actual saved file, zero network after document load, native GPU selected again.
  with p.expect_download() as d:p.get_by_role('button',name='Save single HTML',exact=True).click()
  saved=out/'saved.html';d.value.save_as(str(saved));offline=ctx.new_page();offline.route('**/*',lambda route:route.fulfill(body=saved.read_bytes(),content_type='text/html') if route.request.is_navigation_request() else route.abort());offline.goto(gpu_url);offline.wait_for_function('window.clothLab?.ready',timeout=120000);r['checks']['savedHTMLReopensOnGPU']=offline.evaluate('clothLab.renderBackend().api')=='WebGPU' and offline.evaluate('clothLab.project().positions')==state['positions'];offline.close()
  body=p.evaluate('clothLab.readBodyRenderBuffers()');r['checks']['GPUAndColliderUseIdenticalHuman']=np.array_equal(np.asarray(body['positions']),np.asarray(state['body']['vertices'],dtype=np.float32)) and body['indices']==body['colliderIndices']==state['body']['indices'] and body['colliderIndexType']=='Uint16Array';(out/'body-buffer-proof.json').write_text(json.dumps({'vertices':len(body['positions'])//3,'triangles':len(body['indices'])//3,'colliderIndexType':body['colliderIndexType'],'renderIndexType':body['renderIndexType'],'allValuesIdentical':bool(r['checks']['GPUAndColliderUseIdenticalHuman'])},indent=2)+'\n');r['checks']['GPUAndColliderUseIdenticalHuman']=bool(r['checks']['GPUAndColliderUseIdenticalHuman']);r['checks']['noGPUValidationErrors']=not p.evaluate('clothLab.renderBackend().errors')
  # Exercise an actual GPUDevice.destroy(), not a mocked loss notification.
  before=p.evaluate('clothLab.project().positions');p.evaluate('clothLab.destroyDeviceForTest()');p.wait_for_function('clothLab.renderBackend().deviceLost!==null');r['checks']['deviceLossPausesAndOffersRecovery']=p.locator('#gpuRecovery').is_visible() and p.locator('#run').is_disabled();p.get_by_role('button',name='Recover with WebGL2',exact=True).click();p.wait_for_function("window.clothLab?.ready && clothLab.renderBackend().api==='WebGL2'",timeout=120000);r['checks']['lossRecoveryPreservesExactState']=p.evaluate('clothLab.project().positions')==before;p.screenshot(path=str(out/'recovered-webgl.png'),full_page=True)
  auto=b.new_page();auto.goto(base);auto.wait_for_function('window.clothLab?.ready',timeout=120000);auto_status=auto.evaluate('clothLab.renderBackend()');r['checks']['softwareAdapterAutoCompatibility']=auto_status['api']=='WebGL2' and 'Software WebGPU' in auto_status['fallbackReason'] if r['backend']['adapter']['software'] else auto_status['api']=='WebGPU';auto.close()
  for name,script in [('missing',"Object.defineProperty(navigator,'gpu',{value:undefined})"),('no-adapter',"Object.defineProperty(navigator,'gpu',{value:{requestAdapter:async()=>null}})"),('denied',"Object.defineProperty(navigator,'gpu',{value:{requestAdapter:async()=>{throw new DOMException('Denied','NotAllowedError')}}})")]:
   c=b.new_context();c.add_init_script(script);page=c.new_page();page.goto(args.url);page.wait_for_function('window.clothLab?.ready',timeout=120000);status=page.evaluate('clothLab.renderBackend()');r['checks']['fallback-'+name]=status['api']=='WebGL2' and bool(status['fallbackReason']) and page.evaluate('clothLab.stats().render.triangles')>30000;c.close()
  r['checks']['pageExceptions']=not r['errors'];b.close()
 r['verdict']='PASS' if all(r['checks'].values()) else 'FAIL';(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));return r


def measure_timing(args):
 r={'timingScope':'Completed-frame latency including CPU submission and GPU fence; warm fixed scene; not GPU-only duration or hardware speedup'}
 r['timings']={}
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=chromium_args())
  for mode in ['webgpu','webgl']:
   page=b.new_page(viewport={'width':1440,'height':1100});url=args.url+('&' if '?' in args.url else '?')+'renderer='+mode;page.goto(url);page.wait_for_function('window.clothLab?.ready',timeout=120000)
   page.wait_for_function("(()=>{const c=document.getElementById('scene'),r=c.parentElement.getBoundingClientRect(),d=Math.min(devicePixelRatio,1.5);return c.width===Math.floor(r.width*d)&&c.height===Math.floor(r.height*d)&&c.width>500})()")
   assert page.evaluate('clothLab.renderBackend().api')==('WebGPU' if mode=='webgpu' else 'WebGL2')
   size=page.evaluate("({width:document.getElementById('scene').width,height:document.getElementById('scene').height})")
   page.locator('#scene').screenshot(path=str(args.output/(mode+'-timing-canvas.png')))
   samples=page.evaluate('''async()=>{const a=[];for(let i=0;i<35;i++){let t=performance.now();clothLab.drawFrame();await clothLab.gpuComplete();if(i>=5)a.push(performance.now()-t);}return a;}''');r['timings'][mode]={'canvasSize':size,'backend':page.evaluate('clothLab.renderBackend()'),'samples_ms':samples,'p50_ms':float(np.median(samples)),'p95_ms':float(np.percentile(samples,95))};page.close()
  b.close()
 (args.output/'timing.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));return r

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--timing-only',action='store_true');args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True);r=measure_timing(args) if args.timing_only else run(args);raise SystemExit(0 if args.timing_only or r['verdict']=='PASS' else 2)
