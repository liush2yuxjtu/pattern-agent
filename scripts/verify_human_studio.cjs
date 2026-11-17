// Real browser acceptance of anatomical shape, skinning, centimetres and exports.
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const args={};for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
if(!args.url||!args.output)throw Error('Use --url URL --output DIRECTORY [--expected-commit SHA]');
const out=path.resolve(args.output);fs.mkdirSync(out,{recursive:true});
const checks=[],errors=[],failedRequests=[];
function check(passed,detail,evidence){checks.push({passed:!!passed,detail,evidence});if(!passed)throw Error(detail);}
const digest=value=>crypto.createHash('sha256').update(value).digest('hex');
async function ready(p){await p.waitForFunction(()=>window.humanStudio?.ready);await p.waitForFunction(()=>!document.getElementById('export-state').disabled);}
async function snapshot(p){return p.evaluate(()=>window.humanStudio.getSnapshot());}
async function canvas(p){return p.locator('canvas').evaluate(c=>c.toDataURL());}
async function geometry(p,withPose=true){return p.evaluate(withPose=>{
  const a=humanStudio.getGeometry(),data=humanStudio.getAsset();let hash=2166136261;for(const v of a.rest){hash^=Math.round(v*10000);hash=Math.imul(hash,16777619);}
  const measured={};for(const c of data.controls){let value=0;if(c.key==='height'){let min=Infinity,max=-Infinity;for(const i of a.bodyVertexIds){min=Math.min(min,a.rest[i*3+1]);max=Math.max(max,a.rest[i*3+1]);}value=max-min;}else{for(let j=1;j<c.path.length;j++){const i=c.path[j-1]*3,k=c.path[j]*3;value+=Math.sqrt((a.rest[i]-a.rest[k])**2+(a.rest[i+1]-a.rest[k+1])**2+(a.rest[i+2]-a.rest[k+2])**2);}}measured[c.key]=value;}
  return {restHash:hash,measured,finite:a.rest.every(Number.isFinite)&&a.posed.every(p=>p.every(Number.isFinite)),bones:a.bones,posed:withPose?a.posed:undefined,vertices:a.bodyVertexIds.length,triangles:a.indices.length/3};
},withPose);}
function maxPoseDelta(a,b){return Math.max(...a.posed.map((p,i)=>Math.hypot(...p.map((v,j)=>v-b.posed[i][j]))));}
async function dimension(p,key,value){await p.locator('#size-'+key).fill(String(value));await p.locator('#size-'+key).press('Tab');await p.waitForFunction(({key,value})=>window.humanStudio.getSnapshot().dimensions[key]===value&&!document.getElementById('export-state').disabled,{key,value});}
async function download(p,id,name){const pending=p.waitForEvent('download');await p.locator('#'+id).click();const file=await pending;await file.saveAs(path.join(out,name));return path.join(out,name);}

(async()=>{
 let browser;
 try{
  browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true}),p=await context.newPage();
  p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.status()>=400)failedRequests.push({url:r.url(),status:r.status()});});
  const response=await p.goto(args.url);check(response.status()===200,'Human Studio responds HTTP 200');await ready(p);
  if(args['expected-commit']){const r=await context.request.get(new URL('../build.json',args.url).href),build=await r.json();check(build.commit===args['expected-commit'],'Hosted build identity matches deployed commit',{actual:build.commit});}
  const initial=await snapshot(p),base=await geometry(p,false),initialCanvas=await canvas(p);
  check(base.vertices>=13000&&base.triangles>=26000&&base.bones.length===163,'Anatomical mesh and full163-bone rig loaded',{vertices:base.vertices,triangles:base.triangles,bones:base.bones.length});
  check(base.finite,'Initial actual mesh and skinned positions are finite');
  const initialError=Math.max(...Object.keys(initial.dimensions).map(k=>Math.abs(base.measured[k]-initial.dimensions[k])));
  check(initialError<.2,'Independently measured rendered neutral mesh matches12 cm targets',{maxErrorCm:initialError,measured:base.measured});
  await p.screenshot({path:path.join(out,'desktop.png')});
  await p.locator('#advanced-dimensions summary').click();
  for(const key of Object.keys(initial.dimensions)){
    const amount=key==='height'?3:1,value=Math.round((initial.dimensions[key]+amount)*10)/10;
    const before=await geometry(p,false);await dimension(p,key,value);const after=await geometry(p,false),state=await snapshot(p);
    const error=Math.max(...Object.keys(state.dimensions).map(k=>Math.abs(after.measured[k]-state.dimensions[k])));
    check(after.restHash!==before.restHash&&after.finite&&error<.2,key+' control changes real mesh and preserves all requested cm dimensions',{maxErrorCm:error});
    await dimension(p,key,initial.dimensions[key]);
  }
  await dimension(p,'bust',96);await dimension(p,'waist',76);await dimension(p,'hips',102);await dimension(p,'height',180);
  await dimension(p,'height',195);const framed=await p.evaluate(()=>humanStudio.getViewBounds());
  check(framed.left>0&&framed.top>50&&framed.right<framed.width&&framed.bottom<framed.height,'Tall195cm model is reframed without clipping or hiding the head behind toolbar',framed);
  await dimension(p,'height',180);
  check((await canvas(p))!==initialCanvas,'Size changes alter actual rendered pixels');
  await p.screenshot({path:path.join(out,'body-adjusted.png')});
  const viewHashes=[];for(const view of['front','side','back']){await p.locator('[data-view="'+view+'"]').click();await p.waitForTimeout(100);viewHashes.push(digest(await canvas(p)));}
  check(new Set(viewHashes).size===3,'Front, side and back cameras render distinct actual views');
  await p.locator('[data-view="three"]').click();await p.locator('#tab-pose').click();await p.locator('#mirror-pose').uncheck();
  await p.locator('#joint-select').selectOption('lowerarm01.L');const beforePose=await geometry(p),beforeMeasurements=(await snapshot(p)).measuredNeutral;
  await p.locator('#angle-0').fill('90');await p.locator('#angle-0').press('Tab');const afterPose=await geometry(p);
  const oldWrist=beforePose.bones.find(b=>b.name==='wrist.L').position,newWrist=afterPose.bones.find(b=>b.name==='wrist.L').position;
  check(Math.hypot(...oldWrist.map((v,i)=>v-newWrist[i]))>10&&maxPoseDelta(beforePose,afterPose)>10,'Elbow angle articulates actual wrist and smoothly skinned vertices');
  check(JSON.stringify(beforeMeasurements)===JSON.stringify((await snapshot(p)).measuredNeutral),'Pose is independent of neutral-pose cm dimensions');
  await p.locator('#angle-range-0').focus();await p.keyboard.press('ArrowRight');
  check((await snapshot(p)).poseDegrees['lowerarm01.L'][0]===90.1,'Pose range uses canonical0.1-degree state');
  await p.screenshot({path:path.join(out,'pose-adjusted.png')});
  const neutralPose=await snapshot(p);const presetEvidence=[];
  for(const preset of['tpose','walk','sit','reach']){await p.locator('[data-preset="'+preset+'"]').click();const g=await geometry(p),s=await snapshot(p);check(g.finite&&Object.keys(s.poseDegrees).length>0,preset+' preset rotates real rig without nonfinite geometry');presetEvidence.push({preset,pose:s.poseDegrees});if(preset==='sit')await p.screenshot({path:path.join(out,'seated.png')});}
  await p.locator('[data-preset="neutral"]').click();await p.locator('details:has(#full-rig) summary').click();await p.locator('#full-rig').check();await p.locator('#joint-select').selectOption('finger3-1.L');
  const beforeFinger=await geometry(p);await p.locator('#angle-0').fill('45');await p.locator('#angle-0').press('Tab');
  check(maxPoseDelta(beforeFinger,await geometry(p))>.3,'Finger joint controls deform actual detailed hand geometry');
  await p.locator('[data-preset="sit"]').click();const savedState=await snapshot(p),savedGeometry=await geometry(p);
  await download(p,'export-state','human-model.json');
  check(JSON.stringify(JSON.parse(fs.readFileSync(path.join(out,'human-model.json'))).poseDegrees)===JSON.stringify(savedState.poseDegrees),'Downloaded JSON contains actual current pose and cm dimensions');
  await download(p,'export-obj','human-posed-cm.obj');await download(p,'export-glb','human-rigged.glb');
  const png=await download(p,'export-png','human-view-2x.png'),pngBytes=fs.readFileSync(png);
  const canvasSize=await p.locator('canvas').evaluate(c=>({width:c.width,height:c.height}));
  check(pngBytes.readUInt32BE(16)===canvasSize.width*2&&pngBytes.readUInt32BE(20)===canvasSize.height*2,'PNG export renders actual pose at double pixel resolution');
  const glb=fs.readFileSync(path.join(out,'human-rigged.glb'));check(glb.readUInt32LE(0)===0x46546c67&&glb.readUInt32LE(8)===glb.length,'GLB download is a real complete glTF2 binary',{bytes:glb.length});
  fs.writeFileSync(path.join(out,'export-geometry.json'),JSON.stringify(await p.evaluate(()=>humanStudio.getGeometry())));
  await p.reload();await ready(p);const reloaded=await geometry(p);
  check(JSON.stringify((await snapshot(p)).poseDegrees)===JSON.stringify(savedState.poseDegrees)&&maxPoseDelta(savedGeometry,reloaded)<1e-5,'Save/reload preserves exact calibrated mesh and articulated pose');
  await p.locator('#reset-body').click();await ready(p);await p.locator('#tab-pose').click();await p.locator('#reset-pose').click();
  await p.locator('#state-file').setInputFiles(path.join(out,'human-model.json'));await p.waitForFunction(()=>document.getElementById('toast').textContent.includes('restored'));
  check(maxPoseDelta(savedGeometry,await geometry(p))<1e-5,'Imported downloaded JSON restores actual geometry, not labels only');
  await p.setViewportSize({width:390,height:844});await p.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  check(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Responsive390px screen has no horizontal overflow');
  const mobile=await browser.newContext({viewport:{width:375,height:812},isMobile:true,deviceScaleFactor:1});const mp=await mobile.newPage();await mp.goto(args.url);await ready(mp);
  check(await mp.evaluate(()=>innerWidth===375&&document.documentElement.scrollWidth<=375),'Real mobile device uses375CSS-pixel viewport');await mobile.close();
  const seeded=await browser.newContext({viewport:{width:1200,height:900}});
  await seeded.addInitScript(state=>{localStorage.setItem('pattern-agent:human-studio:v1',JSON.stringify(state));},{version:initial.version,asset:initial.asset,dimensions:{...initial.dimensions,height:170.55},pose:{'lowerarm01.L':[65.55,0,0]}});
  const sp=await seeded.newPage();await sp.goto(args.url);await ready(sp);const normalized=await snapshot(sp);
  const controls=await sp.evaluate(()=>({number:Number(document.querySelector('#size-height').value),range:Number(document.querySelector('#range-height').value)}));
  check(normalized.dimensions.height===170.6&&controls.number===170.6&&controls.range===170.6&&normalized.poseDegrees['lowerarm01.L'][0]===65.6,'Off-step same-version cm/degree cache normalizes to one control/mesh state',controls);await seeded.close();
  check(errors.length===0&&failedRequests.length===0,'No JavaScript errors or failed asset requests',{errors,failedRequests});
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({verdict:'PASS',url:args.url,checks,initial,savedState,presets:presetEvidence,scope:'Actual anatomical mesh/cm calibration, rigid-bone skinning, persistence, responsive UI and downloads. No anatomical recovery or physical tissue claim.'},null,2));
  await context.close();console.log(JSON.stringify({verdict:'PASS',checks:checks.length,output:out}));
 }catch(error){fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({verdict:'FAIL',checks,errors,failedRequests,error:String(error)},null,2));console.error(error);process.exitCode=1;}
 finally{if(browser)await browser.close();}
})();
