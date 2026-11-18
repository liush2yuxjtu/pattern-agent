// Actual local-browser verification; no writes beyond local feedback/downloads.
const {chromium,request}=require('playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict'),same=require('util').isDeepStrictEqual;
const args={};for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].slice(2)]=process.argv[i+1];
if(!args.url||!args.out)throw Error('--url URL --out DIRECTORY [--allow-pending true]');
fs.mkdirSync(args.out,{recursive:true});const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1536,height:1100},acceptDownloads:true});
 const proxyEnvironment=process.env.HTTPS_PROXY||process.env.HTTP_PROXY;
 let externalRequest=null;
 if(proxyEnvironment){const u=new URL(proxyEnvironment);const proxy={server:u.protocol+'//'+u.host};if(u.username)proxy.username=decodeURIComponent(u.username);if(u.password)proxy.password=decodeURIComponent(u.password);externalRequest=await request.newContext({proxy});}
 const page=await context.newPage(),checks=[],errors=[],broken=[],writes=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('response',r=>{if(r.status()>=400)broken.push(r.url());});page.on('request',r=>{if(r.method()!=='GET')writes.push(r.method()+' '+r.url());});
 const check=(name,value)=>{assert.ok(value,name);checks.push(name);};
 try{
  check('Actual review HTTP200',(await page.goto(args.url,{waitUntil:'networkidle'})).status()===200);
  const manifest=await(await page.request.get(new URL('manifest.json',args.url).href)).json();
  check('Single actual candidate acceptance, no fabricated paired comparison',await page.evaluate(()=>EMBEDDED_DATA.runs.length===1)&&manifest.scope==='full workflow single-candidate acceptance');
  check('Official header remains primary first element',await page.locator('body > #app > :first-child').getAttribute('class')==='header');
  check('Native Prompt visible',await page.locator('#prompt-text').isVisible());
  check('Gallery only inside native Output',await page.locator('#official-case-gallery').evaluate(e=>!!e.closest('#outputs-body'))&&await page.locator('.full-e2e-context').evaluate(e=>!!e.closest('#outputs-body')));
  check('No custom shell or case navigation',await page.locator('.quick-raw,.quick-prompt,select').count()===0&&await page.locator('#outputs-nav').count()===1);
  check('Native grades and feedback section parents preserved',await page.locator('#grades-section').evaluate(e=>e.parentElement.matches('#panel-outputs > .main'))&&await page.locator('#feedback').evaluate(e=>e.closest('.section').parentElement.matches('#panel-outputs > .main')));
  const data=await page.evaluate(()=>FULL_E2E);
  check('Historical Previous Output is genuinely loaded by pinned upstream',await page.evaluate(()=>{const run=EMBEDDED_DATA.runs[0];const previous=EMBEDDED_DATA.previous_outputs?.[run.id];return previous?.length>=4&&previous.some(item=>(item.content||'').includes('REUSED HISTORY'));}));
  check('Previous context is explicitly reused, not fabricated new baseline',manifest.previous_output?.status==='REUSED_HISTORY'&&(await page.locator('.full-e2e-context').innerText()).includes('REUSED_HISTORY'));
  await page.locator('#prev-outputs-section .grades-toggle').click();
  check('Native Previous Output opens historical evidence',await page.locator('#prev-outputs-content').isVisible()&&(await page.locator('#prev-outputs-content').innerText()).includes('REUSED HISTORY'));
  await page.locator('#prev-outputs-content img').evaluateAll(es=>Promise.all(es.map(e=>e.decode())));
  check('Three frozen historical visual artifacts actually render',await page.locator('#prev-outputs-content img').count()===3&&await page.locator('#prev-outputs-content img').evaluateAll(es=>es.every(e=>e.naturalWidth>0)));
  await page.locator('#prev-outputs-content').screenshot({path:path.join(args.out,'previous-output-history.png')});
  await page.locator('#prev-outputs-section .grades-toggle').click();
  check('Native Previous Output collapses without replacing current Output',!await page.locator('#prev-outputs-content').isVisible()&&await page.locator('#official-case-gallery').isVisible());


  check('Four exact full-workflow stages',JSON.stringify(data.stages.map(x=>x.key))===JSON.stringify(['input','imagegen','simulation','overlay']));
  if(data.stages[2].images.length||data.stages[3].images.length)check('Actual current model and overlays both populate four-stage review',data.stages[2].images.length>=3&&data.stages[3].images.length>=2);
  if(manifest.imagegen_count===6){
   check('Six hero images use actual selected immutable paths',manifest.generation.every(g=>data.stages[1].images.some(x=>x.label===g.view&&x.src==='artifacts/'+g.relative_path&&x.sha256===g.sha256)));
  }
  if(args['expect-acceptance']){
   check('Expected scoped independent acceptance actually holds',manifest.overall_acceptance===args['expect-acceptance']);
   if(args['expect-acceptance']==='PASS')check('All original semantic and prospective numeric gates pass, hidden truth still unverified',manifest.grading.passed===13&&manifest.grading.failed===0&&manifest.quantitative_gates.length>0&&manifest.quantitative_gates.every(x=>x.passed===true)&&manifest.hidden_structure_accuracy==='NOT_VERIFIED');
  }
  if(manifest.visible_projection_evidence?.length){
   check('Selected generated images have actual independent visible-projection gallery',await page.locator('.visible-projection-gallery').evaluate(e=>!!e.closest('#outputs-body'))&&await page.locator('.visible-projection-gallery [data-retake-image]').count()===manifest.visible_projection_evidence.length);
   check('Projection evidence SHA matches selected native images, no refit',manifest.visible_projection_evidence.every(x=>manifest.generation.some(g=>g.view===x.view&&g.sha256===x.selected_image_sha256)&&x.registration_refit===false));
   await page.locator('.visible-projection-gallery [data-retake-image]').first().click();check('Independent generated-versus-model overlay opens evidence gallery',await page.getByRole('dialog',{name:'Iteration evidence viewer'}).isVisible());
   await page.screenshot({path:path.join(args.out,'generated-model-consistency-lightbox.png')});await page.keyboard.press('Escape');
  }
  if(manifest.generation_selection?.attempts?.length){
   check('Retained attempts remain in native Output',await page.locator('.retake-history').evaluate(e=>!!e.closest('#outputs-body')));
   await page.locator('.retake-history').evaluate(e=>e.open=true);
   const attemptButtons=page.locator('.retake-history [data-retake-image]');
   check('Every retained attempt displayed with source image',await attemptButtons.count()===manifest.generation_selection.attempts.length);
   await attemptButtons.first().click();check('Actual rejected attempt opens iteration gallery',await page.getByRole('dialog',{name:'Iteration evidence viewer'}).isVisible());
   const prior=await page.locator('#retake-image').getAttribute('src');await page.locator('#retake-next').click();check('Attempt gallery navigates distinct actual bytes',(await page.locator('#retake-image').getAttribute('src'))!==prior);
   await page.screenshot({path:path.join(args.out,'attempt-history-lightbox.png')});await page.keyboard.press('Escape');
  }

  check('Actual raw image visible',data.stages[0].images.length>=1&&await page.locator('[data-stage="input"] img').first().isVisible());
  await page.locator('#official-case-gallery img').evaluateAll(es=>Promise.all(es.map(e=>e.decode())));
  check('All actual gallery images decode',await page.locator('#official-case-gallery img').evaluateAll(es=>es.every(e=>e.naturalWidth>0&&e.naturalHeight>0)));
  if(!args['allow-pending']){
   check('Independently graded frozen end-to-end acceptance',manifest.complete&&manifest.grading.total===13);
   check('Six actual generated gallery outputs',manifest.imagegen_count===6&&data.stages[1].images.length===6&&new Set(data.stages[1].images.map(x=>x.sha256)).size===6);
   check('All native receipt pixels and source-bound SHA',manifest.generation.every(g=>g.receipt.status==='GENERATED'&&g.receipt.native===true&&g.receipt.sha256===g.sha256&&g.width===g.receipt.width&&g.height===g.receipt.height));
   check('Real simulation and actual overlays present',data.stages[2].images.length>=3&&data.stages[3].images.length>=2);
   check('Measured model dimensions visible',await page.locator('.full-e2e-context tbody tr').count()===12);
   check('Final overlay is quick-verification hero',(data.stages[3].images[0].src.includes('final-frozen-camera-overlay')||data.stages[3].images[0].src.includes('comparison/final/')));
   if(manifest.overall_acceptance==='FAIL')check('Overall failure is explicit before gallery',await page.locator('.full-e2e-quick-verdict').isVisible()&&(await page.locator('.full-e2e-quick-verdict').innerText()).includes('FAIL')); 
   await page.locator('#grades-section .grades-toggle').click();check('All13 real independent formal grades',await page.locator('#grades-content .assertion-item').count()===13);
  }else check('Pending explicitly visible',manifest.complete||(await page.locator('.full-e2e-context').innerText()).includes('NOT_GRADED'));
  check('Scope truth and native trigger limitation visible',(await page.locator('.full-e2e-context').innerText()).includes('native Claude trigger BLOCKED')&&manifest.real_person_accuracy==='NOT_VALIDATED'&&manifest.physical_fit==='NOT_RUN');
  await page.locator('#official-case-gallery .evidence-grid').evaluate(e=>{e.scrollIntoView({block:'start'});let p=e.parentElement;while(p){if(p.scrollHeight>p.clientHeight+2&&/auto|scroll/.test(getComputedStyle(p).overflowY)){p.scrollTop-=200;return;}p=p.parentElement;}window.scrollBy(0,-200);});const gridRect=await page.locator('#official-case-gallery .evidence-grid').boundingBox();check('Four-stage screenshot actually contains gallery top',gridRect.y>=100&&gridRect.y<600&&gridRect.width>1000);if(data.stages[3].images.length)check('Final overlay screenshot hero loaded',await page.locator('[data-stage="overlay"] .evidence-image img').evaluate(e=>e.complete&&e.naturalWidth>0));else check('Pending overlay is honestly absent',!!args['allow-pending']&&await page.locator('[data-stage="overlay"] .evidence-empty').isVisible());await page.screenshot({path:path.join(args.out,'four-stage-gallery-verified.png')});
  if(manifest.external_images?.length){
   check('Only four rejected history images external; selected six stay local',manifest.external_images.length===4&&manifest.generation.every(g=>data.stages[1].images.find(x=>x.label===g.view).src==='artifacts/'+g.relative_path)&&manifest.external_images.every(x=>!manifest.generation.some(g=>'artifacts/'+g.relative_path===x.original_logical_path)));
   for(const entry of manifest.external_images){
    const response=await (externalRequest||page.request).get(entry.url);check('Actual external rejected image HTTP200 and original SHA '+entry.original_logical_path,response.ok()&&sha(await response.body())===entry.sha256);
    check('Actual external history image decodes at native resolution '+entry.original_logical_path,await page.locator('.retake-history img').evaluateAll((imgs,entry)=>imgs.some(e=>e.src===entry.url&&e.complete&&e.naturalWidth===entry.native_pixels[0]&&e.naturalHeight===entry.native_pixels[1]),entry));
   }
  }
  for(const [file,digest] of Object.entries(manifest.files)){
   const response=await page.request.get(new URL(file,args.url).href);check('HTTP exact file '+file,response.ok()&&sha(await response.body())===digest);
  }
  if(data.stages[1].images.length){await page.locator('[data-stage="imagegen"] .evidence-image').click();check('Actual ImageGen opens image gallery',await page.getByRole('dialog',{name:'Evidence image viewer'}).isVisible());const original=await page.locator('#lightbox-image').getAttribute('src');await page.keyboard.press('ArrowRight');check('Image gallery navigates distinct actual output',(await page.locator('#lightbox-image').getAttribute('src'))!==original);await page.screenshot({path:path.join(args.out,'imagegen-lightbox.png')});await page.keyboard.press('Escape');}
  const fixture='Automated browser verification fixture; not human acceptance.';await page.locator('#feedback').fill(fixture);await page.locator('#feedback-status').filter({hasText:'Saved in this browser'}).waitFor();await page.reload({waitUntil:'networkidle'});check('Feedback survives actual reload',await page.locator('#feedback').inputValue()===fixture);
  const dw=page.waitForEvent('download');await page.locator('[onclick="showDoneDialog()"]').click();const dl=await dw;await dl.saveAs(path.join(args.out,'feedback.browser-test.json'));const payload=JSON.parse(fs.readFileSync(path.join(args.out,'feedback.browser-test.json')));check('Submit All Reviews reopened feedback JSON',payload.status==='complete'&&payload.reviews.length===1&&payload.reviews[0].feedback===fixture);await page.locator('[onclick="closeDoneDialog()"]').click();
  if(manifest.external_archives?.length)check('Every external ZIP is content addressed in the same GitHub repository',manifest.external_archives.every(x=>x.url==='https://raw.githubusercontent.com/liush2yuxjtu/pattern-agent/main/'+x.repo_path&&x.repo_path.startsWith('eval-artifacts/full-imagegen-hillclimb-20261118/')&&x.repo_path.includes(x.sha256.slice(0,16)+'-')&&x.bytes>0));
  const zipLink=page.locator('.full-e2e-context a[data-kind="run-archive"]').first();const zw=page.waitForEvent('download');await zipLink.click();const zd=await zw;const downloadDirectory=path.resolve(args['download-out']||path.join('work/full-imagegen-hillclimb-20261118/browser-downloads',path.basename(args.out)));fs.mkdirSync(downloadDirectory,{recursive:true});const archiveDownload=path.join(downloadDirectory,'downloaded-full-run.zip');await zd.saveAs(archiveDownload);const downloadedHash=sha(fs.readFileSync(archiveDownload));check('Actual full run download exact bytes',downloadedHash===manifest.reproduction_archives[0].sha256);fs.writeFileSync(path.join(args.out,'archive-download-receipt.json'),JSON.stringify({actual_browser_download:archiveDownload,sha256:downloadedHash,bytes:fs.statSync(archiveDownload).size,source:manifest.reproduction_archives[0].href},null,2));
  if(manifest.selected_six_archive){
   const wait=page.waitForEvent('download');await page.locator('a[data-kind="selected-six-archive"]').click();const item=await wait;const file=path.join(downloadDirectory,'downloaded-selected-six.zip');await item.saveAs(file);
   check('Actual final six-image ZIP downloads original exact bytes',sha(fs.readFileSync(file))===manifest.selected_six_archive.sha256);
   const python="import sys,json,zipfile,hashlib; z=zipfile.ZipFile(sys.argv[1]); expected=json.loads(sys.argv[2]); assert z.testzip() is None; assert all(hashlib.sha256(z.read(k+'.png')).hexdigest()==v['sha256'] for k,v in expected.items()); assert len([n for n in z.namelist() if n.endswith('.png')])==6; print('six native entries+CRC verified')";
   require('child_process').execFileSync('python',['-c',python,file,JSON.stringify(manifest.selected_six_archive.source_selection.images)]);
   check('Downloaded final-six ZIP reopens with six canonical native SHA entries and CRC',true);
   fs.writeFileSync(path.join(args.out,'selected-six-download-receipt.json'),JSON.stringify({actual_browser_download:file,source:manifest.selected_six_archive.href,sha256:sha(fs.readFileSync(file)),bytes:fs.statSync(file).size,zip_entry_sha_crc_verified:true},null,2));
  }
  if(manifest.complete){for(const kind of ['measurement_json','measurement_csv']){const link=page.getByRole('link',{name:kind,exact:true});const href=await link.getAttribute('href');const waiting=page.waitForEvent('download');await link.click();const item=await waiting;const destination=path.join(args.out,kind==='measurement_json'?'downloaded-measurements.json':'downloaded-measurements.csv');await item.saveAs(destination);const buffer=fs.readFileSync(destination);check('Actual '+kind+' download exact reopened bytes',sha(buffer)===manifest.files[href]);if(kind==='measurement_json')check('Downloaded12 mesh primary values',Object.keys(JSON.parse(buffer.toString()).measured_values_cm).length===12);else check('DownloadedCSV12 rows and source definition columns',buffer.toString().trim().split(/\r?\n/).length===13&&buffer.toString().startsWith('name,label,value_cm,unit,basis,method'));}}
  if(manifest.complete){await page.locator('[onclick="switchView(\'benchmark\')"]').click();check('Native Benchmark hides all Output enhancements',!await page.locator('#official-case-gallery').isVisible()&&!await page.locator('.full-e2e-context').isVisible());await page.screenshot({path:path.join(args.out,'benchmark.png')});await page.locator('[onclick="switchView(\'outputs\')"]').click();}else check('No fabricated benchmark in pending preview',await page.evaluate(()=>!EMBEDDED_DATA.benchmark));
  const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const mp=await mobile.newPage();await mp.goto(args.url,{waitUntil:'networkidle'});await mp.locator('[data-stage="imagegen"]').scrollIntoViewIfNeeded();check('Mobile gallery visible',await mp.locator('[data-stage="imagegen"]').isVisible());await mp.screenshot({path:path.join(args.out,'mobile.png'),fullPage:true});check('Mobile no page overflow',await mp.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));await mobile.close();
  const assetResponse=await page.request.get(new URL(manifest.runtime_source.external_asset.href,args.url).href);check('Actual human asset exact independent SHA',assetResponse.ok()&&sha(await assetResponse.body())===manifest.runtime_source.external_asset.sha256);
  if(manifest.complete){const href=await page.locator('.human-studio-handoff').getAttribute('href');const handoff=new URL(href,args.url);const stateUrl=new URL(handoff.searchParams.get('model'),handoff);const stateResponse=await page.request.get(stateUrl.href);const expected=await stateResponse.json();const modelPage=await context.newPage();await modelPage.goto(handoff.href);await modelPage.waitForFunction(()=>window.humanStudio?.ready);await modelPage.locator('#model-source[data-state=loaded]').waitFor();const snapshot=await modelPage.evaluate(()=>humanStudio.getSnapshot());check('Actual Human Studio handoff loads same final dimensions and full pose',same(snapshot.dimensions,expected.dimensions)&&same(snapshot.poseDegrees,expected.poseDegrees));await modelPage.screenshot({path:path.join(args.out,'final-human-studio-handoff.png')});await modelPage.close();}
  check('No browser/HTTP errors',errors.length===0&&broken.length===0);check('No external feedback writes',writes.length===0);
  fs.writeFileSync(path.join(args.out,'browser-report.json'),JSON.stringify({verdict:'PASS',url:args.url,complete:manifest.complete,imagegen_count:manifest.imagegen_count,checks,errors,broken,writes},null,2));console.log(JSON.stringify({verdict:'PASS',complete:manifest.complete,imagegen_count:manifest.imagegen_count,checks:checks.length}));
 }catch(e){fs.writeFileSync(path.join(args.out,'browser-report.json'),JSON.stringify({verdict:'FAIL',error:e.stack,checks,errors,broken,writes},null,2));throw e;}finally{if(externalRequest)await externalRequest.dispose();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
