import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadPlaywright,launchSettings} from './playwright-runtime.js';
export async function verifyBrowser(root,{steps=180,url='http://127.0.0.1:8047/garment-gpu-studio.html'}={}){
 const dir=path.join(root,'evidence'),report={status:'RUNNING',checks:[],errors:[],cases:{},htmlSha256:createHash('sha256').update(fs.readFileSync(path.join(root,'dist/garment-gpu-studio.html'))).digest('hex')};
 const save=()=>fs.writeFileSync(path.join(dir,'browser-report-js.json'),JSON.stringify(report,null,2));
 const check=(name,value,detail=null)=>{report.checks.push({name,status:value?'PASS':'FAIL',detail});save();console.log(`${value?'PASS':'FAIL'} ${name}`,detail??'');};
 const snap=async(page,file)=>{const value=await page.evaluate(()=>({project:window.garmentAPI.getProject(),positions:window.garmentAPI.getPositions()}));fs.writeFileSync(path.join(dir,file),JSON.stringify(value));};
 save();const {chromium}=await loadPlaywright();let browser;
 try{
  browser=await chromium.launch(launchSettings());const context=await browser.newContext({viewport:{width:1440,height:1050},acceptDownloads:true}),page=await context.newPage(),requests=[];
  page.on('pageerror',e=>report.errors.push(e.message));page.on('request',r=>requests.push(r.url()));await page.goto(url,{waitUntil:'load'});
  await page.waitForFunction(()=>window.garmentState&&!window.garmentState.busy,{},{timeout:90000});
  const state=()=>page.evaluate(()=>window.garmentState);report.initial=await state();report.adapter=report.initial.backend;save();
  check('full anatomical mesh and real 3D canvas',report.initial.bodyVertices===4002&&report.initial.bodyFaces===8000&&await page.locator('canvas').count()===1);
  check('WASM f64 functions active',report.initial.wasm.active&&report.initial.wasm.exports.includes('principal_min'));
  check('WebGPU adapter/device available',!!report.adapter,report.adapter);if(!report.adapter)throw new Error('No compute device');
  const before=await page.evaluate(()=>window.garmentAPI.getPositions());await page.locator('#step').click();await page.waitForFunction(()=>window.garmentState.step===1&&!window.garmentState.busy,{},{timeout:90000});let st=await state();
  check('GPU queue dispatch and raw read-back candidate changes',st.dispatches>0&&st.gpuCandidateDeltaMm>0,{dispatches:st.dispatches,deltaMm:st.gpuCandidateDeltaMm});
  check('GPU predictor stays inside 1 mm trust region',st.gpuCandidateDeltaMm<=1.001,st.gpuCandidateDeltaMm);
  check('final hybrid state changes',JSON.stringify(before)!==JSON.stringify(await page.evaluate(()=>window.garmentAPI.getPositions())));
  check('GPU shader validation produces no errors',st.errors.length===0,st.errors);
  async function settle(label){for(let i=0;i<steps/30;i++){await page.evaluate(async()=>{await window.garmentAPI.advance(30)});const s=await state();if(s.stale)throw new Error('Solver stopped: '+s.errors.join('; '));console.log(label,'step',s.step);}
    await page.locator('#verify').click();const s=await state();check(`${label}: finite positions`,s.metrics.finite);check(`${label}: seam gap <= 2 mm`,s.metrics.seamGapMm<=2,s.metrics.seamGapMm);check(`${label}: no internal body vertices or samples`,s.metrics.penetratingVertices===0&&s.metrics.penetratingSamples===0);check(`${label}: no complete body-face crossing`,s.metrics.bodyFaceCrossings===0,s.metrics.bodyFaceCrossings);check(`${label}: no nonadjacent cloth-face crossing`,s.metrics.selfFaceCrossings===0,s.metrics.selfFaceCrossings);check(`${label}: p95 principal strain <= 10%`,s.metrics.strainP95<=.1,s.metrics.strainP95);check(`${label}: max principal strain <= 25%`,s.metrics.strainMax<=.25,s.metrics.strainMax);check(`${label}: full discrete geometry verdict`,s.verdict.geometry==='PASS',s.verdict.geometry);return s;}
  report.settled=await settle('baseline');await snap(page,'gpu-snapshot-js.json');save();
  for(const mode of ['pattern','strain','stress','folds','collision','debug','fabric']){await page.locator(`[data-mode="${mode}"]`).click();check('view '+mode,(await state()).mode===mode);}
  await page.locator('[data-view="front"]').click();const front=await page.locator('#viewport').screenshot();await page.locator('[data-view="back"]').click();const back=await page.locator('#viewport').screenshot();check('front/back cameras render distinct real images',!front.equals(back));await page.locator('[data-view="iso"]').click();
  const liveStep=(await state()).step;await page.evaluate(()=>window.garmentAPI.seek(0));check('replay seek does not integrate physics',(await state()).step===liveStep);check('replay exact recorded Float32 coordinates',await page.evaluate(()=>JSON.stringify(window.garmentAPI.getPositions())===JSON.stringify(Array.from(window.garmentAPI.getState().frames.frames[0].positions))));await page.locator('#next').click();check('next recorded frame control',(await state()).cursor===1);
  await page.locator('#chestMm').fill('935');check('size edit invalidates old mesh/physics/export',(await state()).stale&&!await page.locator('#obj').isEnabled());check('size edit removes old PASS labels',(await page.locator('#diagnostics').innerText()).includes('STALE'));
  await page.locator('#apply').click();await page.waitForFunction(()=>!window.garmentState.stale&&!window.garmentState.busy,{},{timeout:90000});st=await state();
  check('resized document has new version and clean timeline',st.version!==report.initial.version&&st.step===0&&st.frameCount===1);check('actual morphed chest remeasured within 1 mm',Math.abs(st.measurements.chest)<1,st.measurements);
  await page.locator('#step').click();await page.waitForFunction(()=>window.garmentState.step===1&&!window.garmentState.busy,{},{timeout:90000});report.wideSettled=await settle('wide');await snap(page,'gpu-snapshot-wide-js.json');save();
  await page.locator('#grade').click();await page.waitForFunction(()=>window.garmentState.grade&&!window.garmentState.busy,{},{timeout:90000});check('three independently redrafted grading sizes',(await state()).grade.length===3);await page.locator('[data-mode="fabric"]').click();
  const getDownload=async(id,name)=>{const promise=page.waitForEvent('download');await page.locator('#'+id).click();const download=await promise;await download.saveAs(path.join(dir,name));return fs.readFileSync(path.join(dir,name),'utf8');};
  const obj=await getDownload('obj','browser-export-js.obj'),positions=await page.evaluate(()=>window.garmentAPI.getPositions()),vertices=obj.split('\n').filter(s=>s.startsWith('v ')).flatMap(s=>s.split(' ').slice(1).map(Number));check('downloaded OBJ equals exact displayed frame',JSON.stringify(vertices)===JSON.stringify(positions));
  const svg=await getDownload('svg','browser-pattern-js.svg');check('downloaded metric SVG has actual 100 mm calibration box',svg.includes('width="100" height="100"')&&/width="[\d.]+mm"/.test(svg));
  await page.locator('#run').click();await page.waitForFunction(()=>window.garmentState.running,{},{timeout:90000});check('pause remains enabled during integration',await page.locator('#run').isEnabled());await page.locator('#run').click();await page.waitForFunction(()=>!window.garmentState.running&&!window.garmentState.busy,{},{timeout:90000});check('pause stops integration',!(await state()).running);
  const next=(await state()).step+1;await context.setOffline(true);await page.locator('#step').click();await page.waitForFunction(n=>window.garmentState.step===n&&!window.garmentState.busy,next,{timeout:90000});check('offline physical step really runs',(await state()).step===next);check('no remote runtime dependency requests',requests.every(u=>u.startsWith(new URL(url).origin+'/')),requests);
  await page.setViewportSize({width:390,height:844});check('mobile has no document horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.setViewportSize({width:1440,height:1050});report.final=await state();
  check('no uncaught browser exceptions',report.errors.length===0,report.errors);
  await page.evaluate(async()=>{window.garmentAPI.getSolver().step=async()=>{throw new Error('controlled verification failure')};await window.garmentAPI.advance(1)});st=await state();check('controlled solver error invalidates old results',st.stale&&!await page.locator('#obj').isEnabled()&&(await page.locator('#diagnostics').innerText()).includes('STALE'));
  report.status=report.checks.every(c=>c.status==='PASS')?'PASS':'FAIL';report.acceleration=report.adapter.isFallbackAdapter?'Real WebGPU API/WGSL via software adapter; hardware acceleration not asserted.':'Hardware adapter reported by browser; no performance guarantee.';save();await browser.close();return report;
 }catch(e){report.status='FAIL';report.exception=e.stack||String(e);save();if(browser)await browser.close();throw e;}
}
