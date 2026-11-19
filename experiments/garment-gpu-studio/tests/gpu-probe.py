import json,pathlib
from playwright.sync_api import sync_playwright
root=pathlib.Path(__file__).resolve().parents[1]
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/lib/chromium/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-webgpu','--use-angle=vulkan','--use-vulkan=swiftshader','--enable-features=Vulkan','--disable-vulkan-surface'])
 page=b.new_page();page.goto('http://127.0.0.1:8047/garment-gpu-studio.html');page.wait_for_function('window.garmentState && !window.garmentState.busy',timeout=60000)
 r=page.evaluate('''async()=>{const st=window.garmentAPI.getState(),s=window.garmentAPI.getSolver();let planes=st.contact.planes(st.model.initial),normalMax=0;for(let i=0;i<planes.length;i+=8)normalMax=Math.max(normalMax,Math.hypot(...planes.slice(i,i+3)));const out={normalMax,planeLength:planes.length,nodes:st.model.nodeCount,tests:[]};for(const iterations of [1,2,16,128]){s.p=st.model.initial.slice();s.device.queue.writeBuffer(s.pos,0,s.p);s.device.queue.writeBuffer(s.prev,0,s.p);s.options.iterations=iterations;try{const p=await s.step();out.tests.push({iterations,max:Math.max(...p.map(Math.abs)),first:Array.from(p.slice(0,3))});}catch(e){out.tests.push({iterations,error:e.message,max:Math.max(...s.p.map(Math.abs))});}}return out;}''')
 (root/'evidence/gpu-probe.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True);b.close()
