// Exercise the official review viewer, real evidence gallery and every saved body.
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const args={};for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].slice(2)]=process.argv[i+1];
if(!args.url||!args.out)throw Error('--url REVIEW_URL --out DIRECTORY [--expected-commit SHA]');
fs.mkdirSync(args.out,{recursive:true});
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:1440,height:1100},acceptDownloads:true});
 const page=await context.newPage(),checks=[],errors=[],broken=[],writes=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 page.on('response',r=>{if(r.status()>=400)broken.push(r.url());});page.on('request',r=>{if(r.method()!=='GET')writes.push(r.method()+' '+r.url());});
 const check=(name,pass)=>{assert.ok(pass,name);checks.push(name);};
 try{
  check('Actual review HTTP200',(await page.goto(args.url,{waitUntil:'networkidle'})).status()===200);
  const build=await(await page.request.get(new URL('../../build.json',args.url).href)).json();
  if(args['expected-commit'])check('Exact deployed revision',build.commit===args['expected-commit']);
  const manifest=await(await page.request.get(new URL('manifest.json',args.url).href)).json();
  check('All six independently graded executions published',manifest.complete===true&&manifest.runs.length===6&&manifest.runs.every(r=>r.grading&&r.grading.total>0));
  check('All six saved anatomical states present',manifest.models.length===6);
  check('Missing native routing and resource metrics honest',manifest.unknown.native_claude_trigger==='BLOCKED'&&manifest.unknown.tokens===null&&manifest.unknown.duration===null);
  check('Runtime fixture boundary visible',(await page.locator('#single-state-intro').innerText()).includes('不是 .skill 内置的优化器'));
  check('Official upstream six-run viewer active',await page.evaluate(()=>EMBEDDED_DATA.runs.length===6));
  check('Fresh review opens actual original-photo revised-skill case',await page.evaluate(()=>VISUAL_EVIDENCE[EMBEDDED_DATA.runs[currentIndex].id].title.includes('原始商品图')&&VISUAL_EVIDENCE[EMBEDDED_DATA.runs[currentIndex].id].title.includes('修订技能')));
  check('Quick gallery is first actual outputs content',await page.locator('#panel-outputs .main > :first-child').getAttribute('id')==='quick-review');
  const expectedStages=['input','imagegen','simulation','overlay'];const imageHashes=new Map();
  let photo=0;
  for(let i=0;i<6;i++){
   await page.locator('#gallery-case').selectOption(String(i));
   check('Selection '+i+' synchronizes official viewer',(await page.locator('#progress').innerText())===`${i+1} of 6`);
   const data=await page.evaluate(()=>VISUAL_EVIDENCE[EMBEDDED_DATA.runs[currentIndex].id]);
   check('Selection '+i+' has four real sections',JSON.stringify(await page.locator('.evidence-stage').evaluateAll(es=>es.map(e=>e.dataset.stage)))===JSON.stringify(expectedStages));
   check('Selection '+i+' does not invent fresh Image Gen',data.stages[1].status.includes('NOT_RUN')&&data.stages[1].images.every(im=>im.caption.includes('本轮未生成')));
   check('Selection '+i+' has actual source and at least three real views',data.stages[0].images.length>0&&data.stages[2].images.length>=3);
   await page.locator('#quick-review img').evaluateAll(es=>Promise.all(es.map(e=>e.decode())));
   check('Selection '+i+' every displayed image decodes',await page.locator('#quick-review img').evaluateAll(es=>es.every(e=>e.naturalWidth>0)));
   const runId=await page.evaluate(()=>EMBEDDED_DATA.runs[currentIndex].id);const model=manifest.models.find(m=>m.id===runId);
   check('Selection '+i+' only current model handoff visible',await page.locator('#model-handoffs [data-model-id]:visible').count()===1&&await page.locator('#model-handoffs [data-model-id]:visible').getAttribute('data-model-id')===model.id);
   if(model.eval_id===3){
    if(model.config==='with_skill')photo=i;
    check('Original photo selection '+i+' shows real residual metrics',await page.locator('.photo-metrics:visible table').count()===1&&(await page.locator('.photo-metrics:visible').innerText()).includes('流程达标不等于原图逐像素一致'));
    check('Original photo selection '+i+' leads with actual final overlay',data.stages[3].images[0].src.endsWith('/overlay-final-overlay.png'));
   }
   for(const stage of data.stages)for(const im of stage.images)imageHashes.set(im.src,im.sha256);
  }
  for(const [file,sha] of imageHashes){const response=await page.request.get(new URL(file,args.url).href);check('Actual evidence SHA '+file,response.ok()&&hash(await response.body())===sha);}
  await page.locator('#gallery-case').selectOption(String(photo));
  await page.evaluate(()=>{window.scrollTo(0,0);document.querySelector('#panel-outputs .main').scrollTop=0;});
  await page.screenshot({path:path.join(args.out,'desktop.png')});
  const opener=page.locator('[data-stage="simulation"] .evidence-image');await opener.click();
  check('Actual render opens accessible lightbox',await page.getByRole('dialog',{name:'Evidence image viewer'}).isVisible());
  const source=await page.locator('#lightbox-image').getAttribute('src');await page.keyboard.press('ArrowRight');check('Lightbox arrow changes image',(await page.locator('#lightbox-image').getAttribute('src'))!==source);
  await page.keyboard.press('ArrowLeft');check('Lightbox back restores exact original',(await page.locator('#lightbox-image').getAttribute('src'))===source);
  await page.screenshot({path:path.join(args.out,'lightbox.png')});await page.keyboard.press('Escape');
  check('Close restores keyboard focus',!await page.getByRole('dialog').isVisible()&&await opener.evaluate(e=>e===document.activeElement));
  await page.locator('#grades-section .grades-toggle').click();check('Formal grades render frozen assertions',await page.locator('#grades-content .assertion-item').count()===7);
  const fixture='Single-state browser test fixture, not human acceptance.';await page.locator('#feedback').fill(fixture);await page.locator('#feedback-status').filter({hasText:'Saved in this browser'}).waitFor();
  await page.reload({waitUntil:'networkidle'});check('Selected case and feedback persist',await page.locator('#gallery-case').inputValue()===String(photo)&&await page.locator('#feedback').inputValue()===fixture);
  await page.locator('[onclick="switchView(\'benchmark\')"]').click();check('Official quantitative Benchmark tab works',await page.locator('#panel-benchmark').evaluate(e=>e.classList.contains('active')));
  await page.screenshot({path:path.join(args.out,'benchmark.png')});await page.locator('[onclick="switchView(\'outputs\')"]').click();
  const feedbackDownload=page.waitForEvent('download');await page.locator('#done-btn').click();await(await feedbackDownload).saveAs(path.join(args.out,'feedback-fixture.json'));
  const reopened=JSON.parse(fs.readFileSync(path.join(args.out,'feedback-fixture.json')));check('Official feedback download reopens six runs',reopened.status==='complete'&&reopened.reviews.length===6&&reopened.reviews[photo].feedback===fixture);await page.locator('#done-overlay button').click();
  const selectedId=await page.evaluate(()=>EMBEDDED_DATA.runs[currentIndex].id);const selectedRun=manifest.runs.find(r=>r.id===selectedId);
  const archiveDownload=page.waitForEvent('download');await page.locator('#model-handoffs [data-model-id]:visible a[download][href$=".zip"]').click();const actualArchive=path.join(args.out,'actual-browser-run.zip');await(await archiveDownload).saveAs(actualArchive);check('Real browser archive download matches source hash',hash(fs.readFileSync(actualArchive))===selectedRun.sha256);
  for(const run of manifest.runs){
   const response=await page.request.get(new URL(run.archive,args.url).href);const bytes=await response.body();check('Complete run archive bytes '+run.id,response.ok()&&hash(bytes)===run.sha256);
   const filename=path.join(args.out,run.id+'.zip');fs.writeFileSync(filename,bytes);
   const audit=require('child_process').spawnSync(process.env.PYTHON_BIN||'python3',['-c',`import zipfile,sys,json\nwith zipfile.ZipFile(sys.argv[1]) as z:\n assert z.testzip() is None\n names=z.namelist();assert 'grading.json' in names and 'eval_metadata.json' in names\n assert any(n.endswith('.obj') for n in names) and any(n.endswith('TRACE.md') for n in names)\n assert not any('__pycache__' in n for n in names)\n print(json.dumps({'files':len(names)}))`,filename],{encoding:'utf8'});
   check('Archive independently reopens '+run.id,audit.status===0);
  }
  const modelPage=await context.newPage();modelPage.on('pageerror',e=>errors.push(e.message));
  for(const model of manifest.models){
   const response=await modelPage.request.get(new URL(model.state,args.url).href);const bytes=await response.body(),expected=JSON.parse(bytes.toString());check('Saved state hash '+model.id,response.ok()&&hash(bytes)===model.sha256);
   await modelPage.goto(new URL(model.href,args.url).href,{waitUntil:'networkidle'});await modelPage.waitForFunction(()=>window.humanStudio?.ready);
   const actual=await modelPage.evaluate(()=>humanStudio.getSnapshot());
   check('Actual linked model loads '+model.id,await modelPage.locator('#model-source').getAttribute('data-state')==='loaded'&&Object.keys(expected.dimensions).every(k=>Math.abs(actual.dimensions[k]-Math.round(expected.dimensions[k]*10)/10)<1e-8));
   check('All pose angles preserved at supported step '+model.id,Object.entries(expected.poseDegrees).every(([k,a])=>a.every((v,j)=>Math.abs((actual.poseDegrees[k]?.[j]??0)-Math.round(v*10)/10)<1e-8)));
   check('Real finite anatomical mesh loaded '+model.id,await modelPage.evaluate(()=>{const g=humanStudio.getGeometry();return g.posed.length===13380&&g.bones.length===163&&g.posed.every(v=>v.every(Number.isFinite));}));
  }
  const before=await modelPage.evaluate(()=>({vertices:humanStudio.getGeometry().posed,pose:humanStudio.getSnapshot().poseDegrees,bust:humanStudio.getSnapshot().dimensions.bust}));
  await modelPage.screenshot({path:path.join(args.out,'linked-model.png')});
  await modelPage.locator('#size-bust').fill(String(before.bust+1));await modelPage.locator('#size-bust').press('Tab');await modelPage.waitForFunction(v=>humanStudio.getSnapshot().dimensions.bust===v,before.bust+1);
  const after=await modelPage.evaluate(()=>({vertices:humanStudio.getGeometry().posed,pose:humanStudio.getSnapshot().poseDegrees}));
  check('Actual served model cm edit deforms mesh and keeps pose',JSON.stringify(before.vertices)!==JSON.stringify(after.vertices)&&JSON.stringify(before.pose)===JSON.stringify(after.pose));
  await modelPage.screenshot({path:path.join(args.out,'editable-model.png')});await modelPage.close();
  await page.setViewportSize({width:375,height:812});await page.locator('#quick-review').scrollIntoViewIfNeeded();check('375px review has no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(args.out,'mobile.png'),fullPage:true});await page.locator('[data-stage="input"] .evidence-image').click();check('Mobile image interaction works',await page.getByRole('dialog').isVisible());await page.keyboard.press('Escape');
  check('No runtime errors broken assets or API writes',errors.length===0&&broken.length===0&&writes.length===0);
  fs.writeFileSync(path.join(args.out,'report.json'),JSON.stringify({verdict:'PASS',url:args.url,commit:build.commit,checks,errors,broken,writes,runs:6,model_links:6,evidence_images:imageHashes.size},null,2));console.log(JSON.stringify({verdict:'PASS',checks:checks.length,runs:6,model_links:6}));
 }catch(e){fs.writeFileSync(path.join(args.out,'report.json'),JSON.stringify({verdict:'FAIL',error:String(e),checks,errors,broken,writes},null,2));throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
