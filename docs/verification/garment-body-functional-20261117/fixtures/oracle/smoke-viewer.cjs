const { chromium } = require('playwright');
const fs = require('fs');
(async()=>{
 const server=require('http').createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(fs.readFileSync('/workspace/work/skill-authoring/garment-body-six-view-workspace/fixtures/viewer-sync/index.html'))});await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1100,height:800}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:'+server.address().port);
 const initial=await page.evaluate(()=>({label:document.getElementById('chestValue').value,cache:JSON.parse(localStorage.getItem('synthetic-body-viewer')),pixels:document.querySelector('canvas').toDataURL(),vertices:mesh.vertices.length,triangles:mesh.faces.length}));
 await page.screenshot({path:'/workspace/work/skill-authoring/garment-body-six-view-workspace/fixtures/oracle/viewer-initial-smoke.png'});
 await page.locator('#chest').evaluate(el=>{el.value='110';el.dispatchEvent(new Event('input',{bubbles:true}))});
 const after=await page.evaluate(()=>({label:document.getElementById('chestValue').value,pixels:document.querySelector('canvas').toDataURL()}));
 await page.getByRole('button',{name:'Side',exact:true}).click();
 const side=await page.locator('canvas').evaluate(el=>el.toDataURL());
 fs.writeFileSync('/workspace/work/skill-authoring/garment-body-six-view-workspace/fixtures/oracle/viewer-smoke.json',JSON.stringify({browser:'Chromium /usr/bin/chromium',page_errors:errors,initial_cache:initial.cache,initial_label:initial.label,after_chest_label:after.label,vertices:initial.vertices,triangles:initial.triangles,bug_reproduced_label_changes_without_canvas_change:initial.pixels===after.pixels,side_camera_changes_canvas:side!==after.pixels},null,2)+'\n');
 await browser.close();server.close();
})();
