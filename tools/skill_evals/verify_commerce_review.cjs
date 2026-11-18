const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const {chromium}=require('playwright');
const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,x)=>{if(v.startsWith('--'))a.push([v.slice(2),x[i+1]]);return a;},[]));
if(!args.url||!args.out)throw Error('Use --url URL --out DIR [--allow-pending true]');fs.mkdirSync(args.out,{recursive:true});
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});const checks=[],errors=[],broken=[];const check=(name,value)=>{assert.ok(value,name);checks.push(name);};const context=await browser.newContext({viewport:{width:1600,height:1100},acceptDownloads:true});const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)broken.push(r.url())});
try{
check('Official review HTTP200',(await page.goto(args.url,{waitUntil:'networkidle'})).ok());
const base=new URL('./',args.url),historical=/^iteration-(\d+)\.html$/.exec(path.posix.basename(new URL(args.url).pathname)),manifestName=historical?'manifest-iteration-'+historical[1]+'.json':'manifest.json',manifest=await(await page.request.get(new URL(manifestName,base).href)).json();
if(!args['allow-pending'])check('All expected actual runs have strict independent grading',manifest.complete===true&&manifest.runs.every(r=>r.graded));
check('Official native shell is primary, not hidden below a custom page',await page.locator('body>#app>.header').isVisible()&&await page.locator('#pose-review,#pr-history').count()===0);
const data=await page.evaluate(()=>EMBEDDED_DATA),galleries=await page.evaluate(()=>OUTPUT_GALLERIES);
const assetResponse=await page.request.get(new URL('../../human-studio/assets/human.json',base).href),assetBytes=await assetResponse.body(),asset=JSON.parse(assetBytes);check('Measurement definition asset is available',assetResponse.ok());
const compact=new Map(asset.bodyVertexIds.map((id,i)=>[id,i]));
check('Official Prompt/Output/Feedback remain unchanged components',await page.locator('#prompt-text').isVisible()&&await page.locator('#outputs-body>#official-case-gallery').count()===1&&await page.locator('#feedback').count()===1&&await page.locator('#done-btn').innerText()==='Submit All Reviews');
check('Run count matches actual inventory',data.runs.length===manifest.runs.length&&data.runs.every(r=>galleries[r.id]));
for(const [file,expected]of Object.entries(manifest.files)){const response=await page.request.get(new URL(file,base).href);check('Published bytes '+file,response.ok()&&sha(await response.body())===expected);}
for(let i=0;i<data.runs.length;i++){
 await page.evaluate(i=>{saveCurrentFeedback();showRun(i)},i);const g=galleries[data.runs[i].id];
 check('Four real-evidence stages '+data.runs[i].id,await page.locator('.og-grid>section').count()===4);
 check('Current run overall is visible '+data.runs[i].id,(await page.locator('#official-case-gallery .output-file-header').innerText()).includes(g.overall));
 for(const stage of g.stages)for(const image of stage.images){const response=await page.request.get(new URL(image.src,base).href);check('Gallery source hash '+data.runs[i].id+' '+image.label,response.ok()&&sha(await response.body())===image.sha256);}
 const m=g.model_measurements;
 if(!args['allow-pending'])check('Primary model measurements exist '+data.runs[i].id,!!m);
 if(m){
  const mr=await page.request.get(new URL(m.json_href,base).href),mb=await mr.body(),report=JSON.parse(mb);
  const csv=await page.request.get(new URL(m.csv_href,base).href),cb=await csv.body();
  check('Model JSON/CSV actual bytes '+data.runs[i].id,mr.ok()&&csv.ok()&&sha(mb)===m.json_sha256&&sha(cb)===m.csv_sha256);
  const neutral=g.downloads.find(d=>d.label==='neutral.obj'),nr=await page.request.get(new URL(neutral.href,base).href),nb=await nr.body();
  const vertices=nb.toString().split('\n').filter(l=>l.startsWith('v ')).map(l=>l.trim().split(/\s+/).slice(1).map(Number));
  check('Actual neutral geometry identity '+data.runs[i].id,nr.ok()&&sha(nb)===report.model_fingerprints.neutral_mesh_sha256&&vertices.length===asset.bodyVertexIds.length&&sha(assetBytes)===report.model_fingerprints.asset_sha256&&report.model_fingerprints.state_sha256===g.source_fingerprints.state_sha256);
  const actual={};for(const control of asset.controls){if(control.key==='height'){const ys=vertices.map(v=>v[1]);actual.height=Math.max(...ys)-Math.min(...ys);}else{let length=0;for(let j=1;j<control.path.length;j++){const a=vertices[compact.get(control.path[j-1])],b=vertices[compact.get(control.path[j])];length+=Math.hypot(...a.map((v,k)=>v-b[k]));}actual[control.key]=length;}}
  check('Independent actual OBJ measurements match all12 primary output values '+data.runs[i].id,report.measurement_source==='neutral_mesh'&&Object.keys(actual).length===12&&Object.keys(actual).every(k=>Math.abs(actual[k]-report.measured_values_cm[k])<1e-9)&&report.measurements.every(r=>r.basis==='mesh_measurement'&&r.person_accuracy_verified===false));
  check('All12 primary dimensions displayed separately from targets '+data.runs[i].id,await page.locator('.og-measurements tbody tr').count()===12);
  for(const row of report.measurements)check('Displayed mesh value '+data.runs[i].id+' '+row.name,await page.locator('.og-measurements tr[data-measurement="'+row.name+'"]').locator('td').nth(1).innerText()===row.value_cm.toFixed(4));
  if(i===0){for(const [index,name,expected]of [[0,'model-measurements.json',m.json_sha256],[1,'model-measurements.csv',m.csv_sha256]]){const waiting=page.waitForEvent('download');await page.locator('.og-measurements a').nth(index).click();const file=path.join(args.out,name);await(await waiting).saveAs(file);check('Actual primary measurement download '+name,sha(fs.readFileSync(file))===expected);}
   await page.locator('.og-measurements').screenshot({path:path.join(args.out,'measurement-table.png')});
  }
 }
 if(data.runs[i].grading){await page.locator('#grades-section .grades-toggle').click();check('Native Formal Grades contain actual assertions '+data.runs[i].id,await page.locator('#grades-content .assertion-item').count()===data.runs[i].grading.expectations.length);await page.locator('#grades-section .grades-toggle').click();}
 else check('Ungraded run not displayed as a pass '+data.runs[i].id,g.overall.includes('NOT_GRADED')||g.overall.includes('RUNNING'));
}
await page.evaluate(()=>showRun(0));await page.locator('#official-case-gallery img').evaluateAll(es=>Promise.all(es.map(e=>e.decode())));await page.screenshot({path:path.join(args.out,'desktop.png')});
if(await page.locator('.og-image').count()){await page.locator('.og-image').first().click();const i=await page.evaluate(()=>currentIndex);await page.keyboard.press('ArrowRight');check('Image navigation cannot accidentally navigate official case',await page.locator('#official-image-dialog').isVisible()&&await page.evaluate(()=>currentIndex)===i);await page.keyboard.press('Escape');}
const fixture='自动化官方格式核验，不代表人工验收。';await page.locator('#feedback').fill(fixture);await page.locator('#feedback-status').filter({hasText:'Saved in this browser'}).waitFor();await page.reload({waitUntil:'networkidle'});check('Native feedback survives reload',await page.locator('#feedback').inputValue()===fixture);
if(data.runs.length>1){await page.locator('#next-btn').click();check('Official case navigation keeps feedback independent',await page.locator('#feedback').inputValue()==='');await page.locator('#prev-btn').click();check('Official navigation restores first-case feedback',await page.locator('#feedback').inputValue()===fixture);}
if(data.benchmark){await page.getByRole('button',{name:'Benchmark',exact:true}).click();check('Native Benchmark tab renders real supplied data',(await page.locator('#benchmark-content').innerText()).includes('Benchmark Results'));await page.screenshot({path:path.join(args.out,'benchmark.png')});await page.getByRole('button',{name:'Outputs',exact:true}).click();}
else check('Pending preview has no fabricated benchmark',await page.locator('#view-tabs').isHidden());
const wait=page.waitForEvent('download');await page.locator('#done-btn').click();const file=path.join(args.out,'feedback.json');await(await wait).saveAs(file);const feedback=JSON.parse(fs.readFileSync(file));check('Official submit downloads real feedback schema',feedback.status==='complete'&&feedback.reviews.length===data.runs.length&&feedback.reviews.some(r=>r.feedback===fixture));await page.locator('#done-overlay button').click();
for(const g of Object.values(galleries)){if(!g.model)continue;const state=g.downloads.find(d=>d.label==='final-state.json');check('Current model link targets corresponding state',new URL(g.model,args.url).searchParams.get('model').endsWith(state.href));const response=await page.request.get(new URL(state.href,base).href);check('Linked model state exact saved bytes',response.ok()&&sha(await response.body())===g.source_fingerprints.state_sha256);}
await page.setViewportSize({width:390,height:844});check('Official review has no mobile horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(args.out,'mobile.png'),fullPage:true});
check('No browser runtime or missing-asset errors',errors.length===0&&broken.length===0);fs.writeFileSync(path.join(args.out,'report.json'),JSON.stringify({verdict:'PASS',scope:'Official viewer format and asset/feedback integrity, not garment/person-fit acceptance',url:args.url,iteration:manifest.iteration,complete:manifest.complete,runs:manifest.runs.length,checks,errors,broken},null,2));console.log(JSON.stringify({verdict:'PASS',checks:checks.length,runs:manifest.runs.length,complete:manifest.complete}));
}catch(e){fs.writeFileSync(path.join(args.out,'report.json'),JSON.stringify({verdict:'FAIL',error:String(e),checks,errors,broken},null,2));throw e;}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
