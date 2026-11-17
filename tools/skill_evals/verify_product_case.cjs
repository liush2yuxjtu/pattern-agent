// Real product review: images, byte provenance, official viewer and model handoff.
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const args={};for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].slice(2)]=process.argv[i+1];
if(!args.url||!args.out)throw Error('--url URL --out DIR [--require-model true] [--expected-commit SHA]');
fs.mkdirSync(args.out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1100},acceptDownloads:true});
 const page=await context.newPage();const checks=[],errors=[],bad=[],writes=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('response',r=>{if(r.status()>=400)bad.push(r.url());});page.on('request',r=>{if(r.method()!=='GET')writes.push(r.method()+' '+r.url());});
 const check=(name,value)=>{assert.ok(value,name);checks.push(name);};
 const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
 try{
  const home=new URL('../../',args.url).href;
  check('Real homepage HTTP200',(await page.goto(home,{waitUntil:'networkidle'})).status()===200);
  const entry=page.locator('a[href="garment-body/product-case/eval.html"]');
  check('Homepage exposes actual product evidence entry',await entry.count()===1);
  await page.setViewportSize({width:390,height:844});check('Homepage mobile entry has no overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.setViewportSize({width:1440,height:1100});await entry.click();await page.waitForLoadState('networkidle');
  check('Homepage navigation reaches real product review',page.url()===args.url);
  check('Real review HTTP200',(await page.request.get(args.url)).status()===200);
  if(args['expected-commit']){
   const buildResponse=await page.request.get(new URL('../../build.json',args.url).href);const build=await buildResponse.json();
   check('Published build matches exact expected commit',buildResponse.ok()&&build.commit===args['expected-commit']);
  }
  check('Pinned Anthropic viewer runs discovered',await page.locator('#progress').innerText()==='1 of 2');
  check('Four-stage gallery is first output content',await page.locator('#panel-outputs .main > :first-child').getAttribute('id')==='quick-review');
  const manifest=await (await page.request.get(new URL('manifest.json',args.url).href)).json();
  if(args['require-model']==='true')check('Current model included after input hash gate',manifest.model_included===true);
  check('Provenance distinguishes source S and M prior',manifest.official_model.height_cm===171&&manifest.official_model.size.includes('S')&&manifest.model_prior.height_cm===170);
  check('Unknown trigger, tokens and physical fit preserved',manifest.unknown.native_claude_trigger==='BLOCKED'&&manifest.unknown.physical_fit==='NOT_RUN'&&manifest.unknown.tokens===null);
  const expected=['input','imagegen','simulation','overlay'];
  let selected;
  for(let i=0;i<2;i++){
   await page.locator('#gallery-case').selectOption(String(i));
   check('Case '+i+' updates official run',await page.locator('#progress').innerText()===`${i+1} of 2`);
   check('Case '+i+' has four stages',JSON.stringify(await page.locator('.evidence-stage').evaluateAll(es=>es.map(e=>e.dataset.stage)))===JSON.stringify(expected));
   const data=await page.evaluate(()=>VISUAL_EVIDENCE[EMBEDDED_DATA.runs[currentIndex].id]);
   check('Case '+i+' does not misattribute corrected metrics to failed generation',await page.locator('.product-results').isVisible()===data.title.includes('第2轮'));
   const generated=data.stages.find(s=>s.key==='imagegen');
   const supplied=data.stages.find(s=>s.key==='input').images;
   check('Case '+i+' source screenshot is not mislabelled as generator input',supplied.some(im=>im.label.includes('来源核对')&&im.caption.includes('不是提交给 Image Gen')));
   check('Case '+i+' exposes actual generation conditioning',data.title.includes('第2轮')?supplied.filter(im=>im.label.startsWith('实际第2轮编辑锚点')).length===4:supplied.filter(im=>im.label.startsWith('实际首轮三维引导')).length===6);
   check('Case '+i+' has six separate executed Image Gen files',generated.images.length===6&&generated.status.includes('实际执行'));
   check('Case '+i+' uses native high resolution images',generated.images.every(im=>Math.min(...im.pixels)>1000)&&new Set(generated.images.map(im=>im.src)).size===6);
   check('Case '+i+' labels pose and depth as illustrative',generated.images.filter(im=>/示意/.test(im.label)).every(im=>im.caption.includes('不是检测器')));
   await page.locator('#quick-review img').evaluateAll(es=>Promise.all(es.map(e=>e.decode())));
   check('Case '+i+' every displayed image decodes',await page.locator('#quick-review img').evaluateAll(es=>es.every(e=>e.naturalWidth>0)));
   for(const stage of data.stages)for(const item of stage.images){const response=await page.request.get(new URL(item.src,args.url).href);check('File SHA256 '+i+' '+item.src,response.ok()&&hash(await response.body())===item.sha256);}
   if(data.title.includes('第2轮'))selected=i;
  }
  check('Corrected case found',selected!==undefined);
  await page.locator('#gallery-case').selectOption(String(selected));
  if(manifest.model_included){
   const simulations=await page.evaluate(()=>VISUAL_EVIDENCE[EMBEDDED_DATA.runs[currentIndex].id].stages.find(s=>s.key==='simulation').images);
   check('Actual model has six standard distinct renders',simulations.filter(im=>im.label.startsWith('真实人体渲染')).length===6);
   check('Actual OpenCV comparisons exist',await page.locator('[data-stage="overlay"] .thumb-strip button').count()>=6);
   check('Centimetre table and download present',await page.locator('.product-results table').count()>=2&&await page.locator('a[download][href="model/final-state.json"]').count()===1);
   const gate=await(await page.request.get(new URL('model/fit/input-hashes.json',args.url).href)).json();
   for(const view of ['front','side','back'])check('Model fit uses corrected '+view,gate.reference_image_sha256[view]===manifest.files['images/generation-2/'+view+'.png']);
   const stateResponse=await page.request.get(new URL('model/final-state.json',args.url).href);const state=await stateResponse.json();
   check('State has real editable dimensions and pose',state.units==='cm'&&Object.keys(state.dimensions).length===12&&Object.keys(state.poseDegrees).length>100);
   check('Adjustable editor uses actual model URL',(await page.locator('#adjust-model').getAttribute('href')).includes('?model=../garment-body/product-case/model/final-state.json'));
   for(const name of ['final-posed.obj','final-posed.glb','neutral-measurements.csv']){const r=await page.request.get(new URL('model/'+name,args.url).href);check('Download '+name+' matches manifest',r.ok()&&hash(await r.body())===manifest.files['model/'+name]);}
   const measurements=await(await page.request.get(new URL('measurements.json',args.url).href)).json();
   check('All twelve model dimensions and six unavailable fields survive',measurements.measurements.length===18&&measurements.measurements.filter(r=>r.basis==='unavailable').length===6&&measurements.measurements.filter(r=>r.basis==='unavailable').every(r=>r.mesh_cm===null&&r.target_cm===null));
   check('Dimensions retain original M versus conditional adjustment',measurements.measurements.find(r=>r.key==='waist').initial_prior_cm===72&&measurements.measurements.find(r=>r.key==='waist').target_cm===state.dimensions.waist);
   check('Independent geometry checker ran including render provenance',manifest.independent_model_check.verdict==='PASS'&&manifest.independent_model_check.render_provenance_checked===true);
   if(await page.locator('#pose-mode-specific').count()){
    await page.locator('#pose-mode-specific').click();check('Single-view diagnostic tab changes visible images',await page.locator('#pose-specific').isVisible()&&!await page.locator('#pose-shared').isVisible());
    await page.locator('#pose-specific img').evaluateAll(es=>Promise.all(es.map(e=>e.decode())));
    check('Single-view diagnostic images decode',await page.locator('#pose-specific img').evaluateAll(es=>es.every(e=>e.naturalWidth>0)));
    await page.screenshot({path:path.join(args.out,'view-specific.png')});await page.locator('#pose-mode-shared').click();
    check('Shared pose tab restores default diagnostic',await page.locator('#pose-shared').isVisible());
    await page.locator('#pose-mode-shared').focus();await page.keyboard.press('ArrowRight');
    check('Pose tab keyboard does not change evaluation case',await page.locator('#pose-specific').isVisible()&&await page.locator('#gallery-case').inputValue()===String(selected));
    await page.keyboard.press('ArrowLeft');
    check('Pose tab keyboard restores shared view',await page.locator('#pose-shared').isVisible());
    check('Pose tabs do not hide original product render',await page.locator('.original-solid').count()===0||await page.locator('.original-solid').isVisible());
   }
   if(await page.locator('.original-comparison').count()){
    await page.locator('.original-comparison img').evaluate(e=>e.decode());
    check('Original product image has its own visible before/after',await page.locator('.original-comparison img').evaluate(e=>e.naturalWidth>0));
    const originalState=await(await page.request.get(new URL('original-reference/state.json',args.url).href)).json();
    check('Original image diagnostic keeps the selected body shape',JSON.stringify(originalState.dimensions)===JSON.stringify(state.dimensions)&&JSON.stringify(originalState.morphWeights)===JSON.stringify(state.morphWeights));
    const originalMetrics=await(await page.request.get(new URL('original-reference/metrics.json',args.url).href)).json();
    check('Original and generated image metrics explicitly separate',originalMetrics.protocol.separate_from_generated_validation===true&&originalMetrics.protocol.same_shape_as_main_final===true);
    check('Unresolved original pose is not presented as accepted match',originalMetrics.protocol.pose_status==='POSE_FAIL'&&originalMetrics.protocol.accepted_matched_candidate===null&&(await page.locator('.product-intro').innerText()).includes('POSE_FAIL'));
    await page.locator('.original-solid img').evaluateAll(es=>Promise.all(es.map(e=>e.decode())));
    check('Original failed candidate front and side are shown together',await page.locator('.original-solid img').count()===2&&await page.locator('.original-solid img').evaluateAll(es=>es.every(e=>e.naturalWidth>0)));
    check('Original annotations and true render are public',(await page.request.get(new URL('original-reference/manual-landmarks.json',args.url).href)).ok()&&(await page.request.get(new URL('original-reference/renders/front.png',args.url).href)).ok());
    await page.locator('.original-comparison').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(args.out,'original-reference.png')});
   }
   const zipPromise=page.waitForEvent('download');await page.locator('a[download][href="reproduce.zip"]').click();const zipDownload=await zipPromise;const zipPath=path.join(args.out,'reproduce.zip');await zipDownload.saveAs(zipPath);
   check('Actual reproduction download matches public manifest',hash(fs.readFileSync(zipPath))===manifest.files['reproduce.zip']);
   const audit=require('child_process').spawnSync(process.env.PYTHON_BIN||'python3',['-c',`import sys,zipfile,json,hashlib,tempfile,pathlib,subprocess
with zipfile.ZipFile(sys.argv[1]) as z:
 assert z.testzip() is None
 manifest=json.loads(z.read('REPRODUCE-MANIFEST.json'));m=manifest['files'];aliases=manifest['aliases']
 assert all(hashlib.sha256(z.read(aliases.get(n,n))).hexdigest()==h for n,h in m.items())
 assert any(n.endswith('/final-renders/rawdepth.npy') for n in m)
 assert any(n.endswith('/fit-generated.py') for n in m)
 assert any(n.endswith('/render_mesh.py') for n in m)
 assert any(n.endswith('/generation-1/front.png') for n in m)
 assert any(n.endswith('/generation-2/front.png') for n in m)
 assert any(n.endswith('/final-posed.glb') for n in m)
 assert not any('__pycache__' in n or n.endswith('.b64') for n in m)
 with tempfile.TemporaryDirectory(prefix='product-repro-check-') as d:
  root=pathlib.Path(d).resolve()
  assert all(root in (root/n).resolve().parents for n in z.namelist())
  z.extractall(root)
  result=subprocess.run([sys.executable,str(root/'REPRODUCE-RESTORE.py')],cwd=root,check=True,capture_output=True,text=True)
  report=json.loads(result.stdout);assert report['files']==len(m)
  print(json.dumps(report))`,zipPath],{encoding:'utf8',maxBuffer:1024*1024});
   check('Reproduction ZIP reopens with original source geometry raw depth and hashes',audit.status===0);
   fs.writeFileSync(path.join(args.out,'reproduce-audit.json'),audit.stdout);
  }
  await page.evaluate(async()=>{window.scrollTo(0,0);document.querySelector('#panel-outputs .main').scrollTop=0;await document.fonts.ready;await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));});
  await page.screenshot({path:path.join(args.out,'desktop.png')});
  const first=page.locator('[data-stage="imagegen"] .evidence-image');await first.click();
  check('Image opens lightbox',await page.getByRole('dialog',{name:'Evidence image viewer'}).isVisible());
  const src=await page.locator('#lightbox-image').getAttribute('src');
  await page.keyboard.press('ArrowRight');check('Arrow navigates separate image',(await page.locator('#lightbox-image').getAttribute('src'))!==src);
  await page.keyboard.press('ArrowLeft');check('Arrow returns to original image',(await page.locator('#lightbox-image').getAttribute('src'))===src);
  await page.screenshot({path:path.join(args.out,'lightbox.png')});
  await page.keyboard.press('Escape');check('Escape closes and restores focus',!await page.getByRole('dialog').isVisible()&&await first.evaluate(e=>e===document.activeElement));
  await page.locator('#grades-section .grades-toggle').click();check('Official formal grades open',await page.locator('#grades-content .assertion-item').count()>=2);
  const fixture='Product review browser fixture; not human acceptance.';
  await page.locator('#feedback').fill(fixture);await page.locator('#feedback-status').filter({hasText:'Saved in this browser'}).waitFor();
  await page.reload({waitUntil:'networkidle'});check('Official feedback persists after reload',await page.locator('#feedback').inputValue()===fixture);
  check('Gallery case persists after reload',await page.locator('#gallery-case').inputValue()===String(selected));
  await page.locator('[onclick="switchView(\'benchmark\')"]').click();check('Official Benchmark tab opens',await page.locator('#panel-benchmark').evaluate(e=>e.classList.contains('active')));
  check('Benchmark warns against skill causal gain',(await page.locator('#benchmark-content').innerText()).includes('不是新旧技能配对基准'));
  await page.screenshot({path:path.join(args.out,'benchmark.png')});
  await page.locator('[onclick="switchView(\'outputs\')"]').click();
  const promise=page.waitForEvent('download');await page.locator('#done-btn').click();const download=await promise;const saved=path.join(args.out,'feedback-fixture.json');await download.saveAs(saved);
  const feedback=JSON.parse(fs.readFileSync(saved));check('Official feedback download reopens',feedback.status==='complete'&&feedback.reviews.length===2&&feedback.reviews[selected].feedback===fixture);
  await page.locator('#done-overlay button').click();
  await page.setViewportSize({width:390,height:844});await page.locator('#quick-review').scrollIntoViewIfNeeded();
  check('Mobile has no page overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(args.out,'mobile.png'),fullPage:true});
  await page.locator('[data-stage="imagegen"] .thumb-strip button').last().click();check('Mobile image opens',(await page.locator('#lightbox-title').innerText()).includes('深度'));await page.keyboard.press('Escape');
  check('No errors broken assets or API writes',errors.length===0&&bad.length===0&&writes.length===0);
  fs.writeFileSync(path.join(args.out,'report.json'),JSON.stringify({verdict:'PASS',url:args.url,model_included:manifest.model_included,checks,errors,bad,writes},null,2));console.log(JSON.stringify({verdict:'PASS',checks:checks.length,model_included:manifest.model_included}));
 }catch(e){fs.writeFileSync(path.join(args.out,'report.json'),JSON.stringify({verdict:'FAIL',error:String(e),checks,errors,bad,writes},null,2));throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
