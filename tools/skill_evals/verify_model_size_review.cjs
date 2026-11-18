// Real browser verification of pinned official viewer and source-bound geometry gallery.
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const args={};for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].slice(2)]=process.argv[i+1];
if(!args.url||!args.out)throw Error('--url URL --out DIRECTORY [--allow-pending true]');
fs.mkdirSync(args.out,{recursive:true});
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1100},acceptDownloads:true});
 const page=await context.newPage(),checks=[],errors=[],broken=[],writes=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 page.on('response',r=>{if(r.status()>=400)broken.push(r.url());});page.on('request',r=>{if(r.method()!=='GET')writes.push(r.method()+' '+r.url());});
 const check=(name,pass)=>{assert.ok(pass,name);checks.push(name);};
 const selectRun=async i=>{let current=await page.evaluate(()=>currentIndex);while(current!==i){await page.locator(current<i?'#next-btn':'#prev-btn').click();current=await page.evaluate(()=>currentIndex);}};
 try{
  check('Actual official page HTTP200',(await page.goto(args.url,{waitUntil:'networkidle'})).status()===200);
  const manifest=await(await page.request.get(new URL('manifest.json',args.url).href)).json();
  check('Six real paired executions',manifest.runs.length===6);
  check('Unknown telemetry and routing honest',manifest.unknown.native_claude_trigger==='BLOCKED'&&manifest.unknown.tokens===null&&manifest.unknown.duration===null&&manifest.unknown.imagegen==='NOT_REQUESTED');
  if(!args['allow-pending'])check('All independently graded counts 7/7/5',manifest.complete&&manifest.runs.every(r=>r.grading?.total===({1:7,2:7,3:5})[r.eval_id]));
  else check('Pending status explicitly visible',manifest.complete||(await page.locator('.model-size-context').innerText()).includes('NOT_GRADED'));
  check('Official header remains first primary element',await page.locator('body > #app > :first-child').getAttribute('class')==='header');
  check('Prompt visible without custom folding',await page.locator('#prompt-text').isVisible());
  check('Gallery and context only inside official Output',await page.locator('#official-case-gallery').evaluate(e=>!!e.closest('#outputs-body'))&&await page.locator('.model-size-context').evaluate(e=>!!e.closest('#outputs-body')));
  check('No custom shell or case navigation',await page.locator('.quick-raw,.quick-prompt,#model-size-intro,#gallery-case,select').count()===0&&await page.locator('#outputs-nav').count()===1);
  check('Native output, grades and feedback retain original section parents',await page.locator('#outputs-body').evaluate(e=>e.parentElement.parentElement.matches('#panel-outputs > .main'))&&await page.locator('#grades-section').evaluate(e=>e.parentElement.matches('#panel-outputs > .main'))&&await page.locator('#feedback').evaluate(e=>e.closest('.section').parentElement.matches('#panel-outputs > .main')));
  check('Pinned official viewer active',await page.evaluate(()=>EMBEDDED_DATA.runs.length===6));
  await page.screenshot({path:path.join(args.out,'official-layout.png')});
  const prompts=await page.evaluate(()=>EMBEDDED_DATA.runs.map(r=>r.prompt));check('Same prompt for every configuration',new Set(prompts).size===1);
  for(let i=0;i<6;i++){
   await selectRun(i);
   check('Run '+i+' official navigation sync',(await page.locator('#progress').innerText())===`${i+1} of 6`);
   const data=await page.evaluate(()=>VISUAL_EVIDENCE[EMBEDDED_DATA.runs[currentIndex].id]);const id=await page.evaluate(()=>EMBEDDED_DATA.runs[currentIndex].id);const run=manifest.runs.find(r=>r.id===id);
   check('Run '+i+' four evidence stages',JSON.stringify(data.stages.map(s=>s.key))===JSON.stringify(['input','imagegen','simulation','overlay']));
   check('Run '+i+' ImageGen NOT_REQUESTED',data.stages[1].status==='NOT_REQUESTED'&&data.stages[1].images.length===0);
   check('Run '+i+' actual projections and overlay',data.stages[0].images.length===2&&data.stages[3].images.length===2&&data.stages[0].images.every(im=>im.caption.includes('review-derived')));
   await page.locator('#official-case-gallery img').evaluateAll(es=>Promise.all(es.map(e=>e.decode())));
   check('Run '+i+' images decode',await page.locator('#official-case-gallery img').evaluateAll(es=>es.every(e=>e.naturalWidth>0)));
   check('Run '+i+' measurement rows',await page.locator('#measurement-results tbody tr').count()===12);
   if(run.eval_id===2){const row=page.locator('#measurement-results tr').filter({hasText:'waist'});check('Residual actual 99.0831 separated from target108',(await row.innerText()).includes('99.083100')&&(await row.innerText()).includes('108.000000'));}
   if(run.eval_id===3)check('Rejected mesh never displayed as successful measurement',(await page.locator('#measurement-results').innerText()).includes('对应关系拒绝')&&Object.values(run.measurement_values).every(x=>x===null));
   if(manifest.complete){await page.locator('#grades-section .grades-toggle').click();check('Run '+i+' actual formal grades count',await page.locator('#grades-content .assertion-item').count()==={1:7,2:7,3:5}[run.eval_id]);}
  }
  // Every delivered byte is read from the running HTTP surface and hash-checked.
  for(const [file,sha] of Object.entries(manifest.files)){
   const r=await page.request.get(new URL(file,args.url).href);check('Published file SHA '+file,r.ok()&&hash(await r.body())===sha);
  }
  await selectRun(2);await page.locator('#official-case-gallery').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(args.out,'desktop-residual.png')});
  await page.locator('[data-stage="simulation"] .evidence-image').click();check('Source image opens lightbox',await page.getByRole('dialog',{name:'Evidence image viewer'}).isVisible());
  const first=await page.locator('#lightbox-image').getAttribute('src');await page.keyboard.press('ArrowRight');check('Lightbox navigates actual image',(await page.locator('#lightbox-image').getAttribute('src'))!==first);await page.screenshot({path:path.join(args.out,'gallery-lightbox.png')});await page.keyboard.press('Escape');
  const fixture='Browser verification fixture; not human approval.';await page.locator('#feedback').fill(fixture);await page.locator('#feedback-status').filter({hasText:'Saved in this browser'}).waitFor();
  await page.reload({waitUntil:'networkidle'});check('Feedback and selected run persist across reload',await page.evaluate(()=>currentIndex)===2&&await page.locator('#feedback').inputValue()===fixture);await page.locator('#feedback').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(args.out,'feedback-reloaded.png')});
  const downloadWait=page.waitForEvent('download');await page.locator('[onclick="showDoneDialog()"]').click();const download=await downloadWait;await download.saveAs(path.join(args.out,'feedback.browser-test.json'));const payload=JSON.parse(fs.readFileSync(path.join(args.out,'feedback.browser-test.json')));
  check('Submit All Reviews downloads real reopened JSON',payload.status==='complete'&&payload.reviews.length===6&&payload.reviews[2].feedback===fixture);await page.screenshot({path:path.join(args.out,'feedback-download.png')});await page.locator('[onclick="closeDoneDialog()"]').click();
  if(manifest.complete){
   await page.locator('[onclick="switchView(\'benchmark\')"]').click();check('Benchmark hides all case Output additions',!await page.locator('#measurement-results').isVisible()&&!await page.locator('.model-size-context').isVisible()&&!await page.locator('#official-case-gallery').isVisible());check('Official Benchmark works',await page.locator('#panel-benchmark').evaluate(e=>e.classList.contains('active')));const b=await page.evaluate(()=>EMBEDDED_DATA.benchmark);check('Unknown resource metrics remain null',b.runs.every(r=>r.result.tokens===null&&r.result.time_seconds===null));await page.screenshot({path:path.join(args.out,'benchmark.png')});await page.locator('[onclick="switchView(\'outputs\')"]').click();
  }
  await selectRun(4);await page.locator('#official-case-gallery').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(args.out,'consistency-rejection.png')});
  await page.locator('.claim-audit summary').click();const caveat=page.locator('.claim-audit p').filter({hasText:'Executor geometric audit is implementation-independent'});check('False implementation-independence claim visible',await caveat.isVisible()&&(await caveat.innerText()).includes('NOT VERIFIED'));await caveat.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(args.out,'claim-independence-caveat.png')});
  // Actual original JSON download through the visible browser link.
  const selected=manifest.runs.find(r=>r.eval_id===3&&r.config==='with_skill');const jsonLink=page.locator('#measurement-results a').filter({hasText:/measurements.*json/}).first();const artifactWait=page.waitForEvent('download');await jsonLink.click();const artifact=await artifactWait;await artifact.saveAs(path.join(args.out,'downloaded-original-measurements.json'));check('Original download exact bytes',hash(fs.readFileSync(path.join(args.out,'downloaded-original-measurements.json')))===manifest.files[selected.measurement_file]);
  const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const mp=await mobile.newPage();await mp.goto(args.url,{waitUntil:'networkidle'});await mp.locator('#next-btn').click();await mp.locator('#next-btn').click();await mp.locator('#official-case-gallery .evidence-grid').scrollIntoViewIfNeeded();check('Mobile evidence visible',await mp.locator('#official-case-gallery').isVisible());await mp.screenshot({path:path.join(args.out,'mobile.png'),fullPage:true});check('Mobile no document overflow',await mp.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));await mobile.close();
  check('No browser or HTTP errors',errors.length===0&&broken.length===0);check('No feedback API writes',writes.length===0);
  fs.writeFileSync(path.join(args.out,'browser-report.json'),JSON.stringify({verdict:'PASS',url:args.url,complete:manifest.complete,checks,errors,broken,writes},null,2));console.log(JSON.stringify({verdict:'PASS',checks:checks.length,complete:manifest.complete}));
 }catch(e){fs.writeFileSync(path.join(args.out,'browser-report.json'),JSON.stringify({verdict:'FAIL',error:e.stack,checks,errors,broken,writes},null,2));throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
