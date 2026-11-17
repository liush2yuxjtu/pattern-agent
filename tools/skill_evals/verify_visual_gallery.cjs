const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const args={};for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].slice(2)]=process.argv[i+1];
if(!args.url||!args.out)throw Error('--url URL --out DIR required');
fs.mkdirSync(args.out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});const checks=[],errors=[],bad=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('response',r=>{if(r.status()>=400)bad.push(r.url());});
 const check=(name,value)=>{assert.ok(value,name);checks.push(name);};
 try{
  await page.goto(args.url,{waitUntil:'networkidle'});
  check('Correct visual review page',await page.title()==='Eval Review');
  check('Quick section is first review content',await page.locator('#panel-outputs .main > :first-child').getAttribute('id')==='quick-review');
  const options=await page.locator('#gallery-case option').count();check('Case picker contains all runs',options>=2);
  let visualIndex;
  const stageKeys=['input','imagegen','simulation','overlay'];
  for(let i=0;i<options;i++){
   await page.locator('#gallery-case').selectOption(String(i));
   check('Case '+i+' updates main review too',await page.locator('#progress').innerText()===`${i+1} of ${options}`);
   check('Case '+i+' has four named evidence sections',JSON.stringify(await page.locator('.evidence-stage').evaluateAll(items=>items.map(e=>e.dataset.stage)))===JSON.stringify(stageKeys));
   check('Case '+i+' accurately marks Image Gen not run',(await page.locator('[data-stage="imagegen"]').innerText()).includes('NOT RUN')&&await page.locator('[data-stage="imagegen"] img').count()===0);
   const images=page.locator('#quick-review img');
   if(await images.count()){
    visualIndex??=i;await images.evaluateAll(items=>Promise.all(items.map(e=>e.decode())));
    check('Case '+i+' images all decode',await images.evaluateAll(items=>items.every(e=>e.naturalWidth>0)));
    check('Case '+i+' includes input, simulation and overlay',await page.locator('[data-stage="input"] img').count()>0&&await page.locator('[data-stage="simulation"] img').count()>=6&&await page.locator('[data-stage="overlay"] img').count()>0);
   }else check('State audit clearly reports absent image evidence',(await page.locator('#quick-review').innerText()).includes('No input image'));
  }
  check('At least one complete visual case',visualIndex!==undefined);
  await page.locator('#gallery-case').selectOption(String(visualIndex));
  await page.screenshot({path:path.join(args.out,'desktop.png')});
  const first=page.locator('[data-stage="input"] .evidence-image').first();await first.click();
  check('Image click opens accessible lightbox',await page.getByRole('dialog',{name:'Evidence image viewer'}).isVisible());
  const original=await page.locator('#lightbox-image').getAttribute('src');
  await page.locator('#lightbox-next').click();
  check('Next opens another image',(await page.locator('#lightbox-image').getAttribute('src'))!==original);
  await page.keyboard.press('ArrowLeft');check('Arrow key navigates within gallery',(await page.locator('#lightbox-image').getAttribute('src'))===original);
  check('Gallery arrows do not change evaluation case',await page.locator('#gallery-case').inputValue()===String(visualIndex));
  await page.screenshot({path:path.join(args.out,'lightbox.png')});
  const link=await page.locator('#lightbox-original').getAttribute('href');const response=await page.request.get(new URL(link,args.url).href);check('Original image link opens real bytes',response.ok()&&(await response.body()).length>100);
  await page.keyboard.press('Escape');check('Escape closes lightbox',!await page.getByRole('dialog').isVisible());
  check('Focus returns to clicked image',await first.evaluate(e=>e===document.activeElement));
  await page.setViewportSize({width:390,height:844});await page.locator('#quick-review').scrollIntoViewIfNeeded();
  check('Mobile has no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(args.out,'mobile.png'),fullPage:true});
  await page.locator('[data-stage="simulation"] .evidence-image').first().click();check('Mobile image lightbox works',await page.getByRole('dialog').isVisible());await page.locator('#lightbox-close').click();
  const id=await page.evaluate(()=>EMBEDDED_DATA.runs[Number(document.querySelector('#gallery-case').value)].id);
  const evidence=await page.evaluate(id=>VISUAL_EVIDENCE[id],id);
  for(const stage of evidence.stages)for(const item of stage.images){const r=await page.request.get(new URL(item.src,args.url).href);check('Gallery image bytes match provenance: '+item.label,r.ok()&&crypto.createHash('sha256').update(await r.body()).digest('hex')===item.sha256);}
  check('No console, page or broken image requests',errors.length===0&&bad.length===0);
  fs.writeFileSync(path.join(args.out,'report.json'),JSON.stringify({verdict:'PASS',url:args.url,runs:options,checks,errors,bad},null,2));console.log(JSON.stringify({verdict:'PASS',runs:options,checks:checks.length}));
 }catch(e){fs.writeFileSync(path.join(args.out,'report.json'),JSON.stringify({verdict:'FAIL',error:String(e),checks,errors,bad},null,2));throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
