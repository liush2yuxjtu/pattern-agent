#!/usr/bin/env node
// Drive the published skill workflow and reopen its actual download.
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,all)=>{if(v.startsWith('--'))a.push([v.slice(2),all[i+1]]);return a;},[]));
const base=args.url.replace(/\/$/,'')+'/',out=args.output||'work/human-skill/browser';
fs.mkdirSync(out,{recursive:true});
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 const errors=[],checks=[],badResponses=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 page.on('response',r=>{if(r.status()>=400)badResponses.push({url:r.url(),status:r.status()});});
 const check=(name,condition)=>{assert.ok(condition,name);checks.push(name);};
 try {
  const build=await (await page.request.get(base+'build.json')).json();
  if(args['expected-commit']) check('Hosted exact commit',build.commit===args['expected-commit']);
  await page.goto(base+'human-studio/',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.humanStudio?.ready);
  await page.getByRole('link',{name:'Skill & workflow'}).click();
  await page.waitForURL('**/garment-body/skill/');
  check('Editor opens current skill guide',await page.getByRole('heading',{name:'Reference photo → six views → verified body parameters'}).isVisible());
  check('12 cm controls and 163 bone contract',await page.locator('body').textContent().then(t=>t.includes('12 dimensions')&&t.includes('163 bones')));
  check('Units, camera and evidence limits visible',await page.locator('body').textContent().then(t=>t.includes('OBJ values are cm')&&t.includes('do not save the viewer camera')&&t.includes('not a detector result')));
  const manifest=await (await page.request.get(base+'garment-body/skill/manifest.json')).json();
  for(const [file,hash] of Object.entries(manifest.files)){
   const r=await page.request.get(base+'garment-body/skill/'+file);
   check('Published bytes: '+file,r.ok()&&sha(await r.body())===hash);
  }
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('link',{name:'Download .skill'}).click();
  const download=await downloadPromise;
  await download.saveAs(path.join(out,'garment-body-six-view.skill'));
  check('Actual .skill download hash',sha(fs.readFileSync(path.join(out,'garment-body-six-view.skill')))===manifest.files['garment-body-six-view.skill']);
  await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
  await page.setViewportSize({width:375,height:812});
  check('Mobile has no document overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  check('Mobile download reachable',await page.getByRole('link',{name:'Download .skill'}).isVisible());
  await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  await page.getByRole('link',{name:'Historical evaluations',exact:true}).click();
  await page.waitForURL('**/garment-body/eval.html');
  check('Historical evaluation retained',(await page.locator('body').innerText()).length>200);
  await page.goto(base+'garment-body/',{waitUntil:'networkidle'});
  await page.getByRole('link',{name:'Current six-view skill, workflow and download'}).click();
  await page.waitForURL('**/garment-body/skill/');
  await page.getByRole('link',{name:'Open Human Studio',exact:true}).click();
  await page.waitForFunction(()=>window.humanStudio?.ready);
  await page.setViewportSize({width:1440,height:1000});
  const initial=await page.evaluate(()=>window.humanStudio.getSnapshot().dimensions.height);
  const input=page.locator('#size-height');
  // Select the actual labelled dimension input from the rendered UI.
  const number=await input.count()?input:page.locator('input[type="number"]').first();
  await number.fill(String(initial===170?175:170));await number.press('Tab');
  check('Return to adjustable cm model',await page.evaluate(before=>window.humanStudio.getSnapshot().dimensions.height!==before,initial));
  await page.getByRole('tab',{name:'Pose & joints',exact:true}).click();
  await page.getByRole('button',{name:'Seated',exact:true}).click();
  check('Pose preset changes actual state',await page.evaluate(()=>Object.keys(window.humanStudio.getSnapshot().poseDegrees).length>0));
  await page.screenshot({path:path.join(out,'model-return.png')});
  check('No page/console/network errors',errors.length===0&&badResponses.length===0);
  fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2));
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({verdict:'PASS',url:base,build,checks,errors,badResponses},null,2));
  console.log(JSON.stringify({verdict:'PASS',checks:checks.length,commit:build.commit,output:out}));
 }catch(e){fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({verdict:'FAIL',error:String(e),checks,errors,badResponses},null,2));throw e;}
 finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
