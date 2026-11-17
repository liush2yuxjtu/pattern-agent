// Actual same-origin model handoff, editing and exported-state roundtrip.
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const args={};for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
if(!args.url||!args['model-url']||!args.output)throw Error('Use --url STUDIO_URL --model-url MODEL_JSON_URL --output DIRECTORY');
const out=path.resolve(args.output);fs.mkdirSync(out,{recursive:true});const checks=[],errors=[];
function check(pass,detail,evidence){checks.push({passed:!!pass,detail,evidence});if(!pass)throw Error(detail);}
const hash=v=>crypto.createHash('sha256').update(JSON.stringify(v)).digest('hex');
const poseDelta=(a,b)=>Math.max(...a.posed.map((v,i)=>Math.hypot(...v.map((x,j)=>x-b.posed[i][j]))));
async function ready(p){await p.waitForFunction(()=>window.humanStudio?.ready);}
async function state(p){return p.evaluate(()=>humanStudio.getSnapshot());}
async function geometry(p){return p.evaluate(()=>humanStudio.getGeometry());}
(async()=>{let browser;try{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));
 const modelUrl=new URL(args['model-url'],args.url),response=await context.request.get(modelUrl.href);check(response.ok(),'Actual linked JSON responds HTTP 200');const modelBytes=await response.body(),expected=JSON.parse(modelBytes.toString('utf8'));
 const linked=new URL(args.url);linked.searchParams.set('model',modelUrl.href);await p.goto(linked.href);await ready(p);
 const initial=await state(p),g0=await geometry(p);check(await p.locator('#model-source').getAttribute('data-state')==='loaded','Visible linked-model success state');
 check(JSON.stringify(initial.dimensions)===JSON.stringify(expected.dimensions),'Actual linked cm dimensions loaded',{dimensions:initial.dimensions});
 const posed=Object.entries(expected.poseDegrees).every(([name,angles])=>angles.every((v,i)=>Math.abs((initial.poseDegrees[name]?.[i]??Infinity)-Math.round(v*10)/10)<1e-9));check(posed,'Actual linked bone angles loaded');
 check(g0.posed.every(v=>v.every(Number.isFinite))&&g0.posed.length===13380&&g0.bones.length===163,'Loaded state deforms the actual anatomical mesh and full rig');
 await p.screenshot({path:path.join(out,'linked-model.png')});
 const bust=initial.dimensions.bust+1;await p.locator('#size-bust').fill(String(bust));await p.locator('#size-bust').press('Tab');await p.waitForFunction(v=>humanStudio.getSnapshot().dimensions.bust===v&&!document.getElementById('export-state').disabled,bust);
 const g1=await geometry(p),s1=await state(p);check(hash(g1.rest)!==hash(g0.rest)&&Math.abs(s1.measuredNeutral.bust-bust)<.2,'Cm input edits real vertices with measured target agreement');
 await p.locator('#tab-pose').click();await p.locator('#mirror-pose').uncheck();await p.locator('#joint-select').selectOption('lowerarm01.L');await p.locator('#angle-0').fill('55');await p.locator('#angle-0').press('Tab');
 const edited=await state(p),g2=await geometry(p);check(edited.poseDegrees['lowerarm01.L'][0]===55&&hash(g2.posed)!==hash(g1.posed),'Degree input edits actual articulated mesh');
 check(JSON.stringify(edited.measuredNeutral)===JSON.stringify(s1.measuredNeutral),'Pose editing preserves neutral cm measurements');
 await p.screenshot({path:path.join(out,'edited-model.png')});
 const download=p.waitForEvent('download');await p.locator('#export-state').click();await(await download).saveAs(path.join(out,'edited-model.json'));const saved=JSON.parse(fs.readFileSync(path.join(out,'edited-model.json')));
 check(hash(saved)===hash(edited),'Downloaded JSON contains actual current cm/pose state');
 await p.locator('#reset-pose').click();await p.locator('#state-file').setInputFiles(path.join(out,'edited-model.json'));await p.waitForFunction(()=>document.getElementById('toast').textContent.includes('restored'));
 const importDelta=poseDelta(await geometry(p),g2);check(importDelta<1e-5,'Manual import restores skinned geometry within 0.00001 cm',{maximumVertexDeltaCm:importDelta});
 // After choosing an explicit saved state, a plain studio URL reopens that local state.
 await p.goto(args.url);await ready(p);const reloadDelta=poseDelta(await geometry(p),g2);check(reloadDelta<1e-5,'Plain editor URL reopens saved geometry within 0.00001 cm',{maximumVertexDeltaCm:reloadDelta});
 await p.goto(linked.href);await ready(p);check(hash((await state(p)).dimensions)===hash(initial.dimensions),'Explicit review link deliberately reloads the published case rather than stale cache');
 // Negative controls must not fetch cross-origin or silently substitute dimensions.
 const probe=new URL('handoff-probe.json',args.url),bad=[
  ['wrong-version',{...expected,version:'other-model'}],['wrong-asset',{...expected,asset:'other-asset'}],['wrong-units',{...expected,units:'m'}],
  ['invalid-cm',{...expected,dimensions:{...expected.dimensions,bust:'90'}}],['missing-cm',{...expected,dimensions:{height:170}}],
  ['invalid-pose',{...expected,poseDegrees:{'lowerarm01.L':[null,0,0]}}],['invalid-morph',{...expected,morphWeights:[null]}],
  ['invalid-json','{broken JSON']
 ];
 for(const [name,body] of bad){await context.route(probe.href,r=>r.fulfill({status:200,contentType:'application/json',body:typeof body==='string'?body:JSON.stringify(body)}));const u=new URL(args.url);u.searchParams.set('model',probe.href);await p.goto(u.href);await ready(p);check(await p.locator('#model-source').getAttribute('data-state')==='error',name+' rejected visibly');check(hash((await state(p)).dimensions)===hash(initial.dimensions),name+' preserves current editable state');await context.unroute(probe.href);}
 let outbound=0;p.on('request',r=>{if(new URL(r.url()).hostname==='example.invalid')outbound++;});const external=new URL(args.url);external.searchParams.set('model','https://example.invalid/private.json');await p.goto(external.href);await ready(p);check(await p.locator('#model-source').getAttribute('data-state')==='error'&&outbound===0,'Cross-origin model is rejected before any outbound request');
 await p.screenshot({path:path.join(out,'rejected-model.png')});check(errors.length===0,'No uncaught application errors',{errors});
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({verdict:'PASS',url:args.url,modelUrl:modelUrl.href,modelSha256:crypto.createHash('sha256').update(modelBytes).digest('hex'),checks,scope:'Linked configurable model and saved-state handoff. No photographed-body recovery or cloth physics claim.'},null,2));console.log(JSON.stringify({verdict:'PASS',checks:checks.length,output:out}));
 }catch(e){fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({verdict:'FAIL',checks,errors,error:String(e)},null,2));console.error(e);process.exitCode=1;}finally{if(browser)await browser.close();}})();
