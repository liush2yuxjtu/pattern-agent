// Real local upstream review UI interaction. Fixture edits are not approved labels.
const {chromium}=require('playwright');const fs=require('fs'),path=require('path'),http=require('http');
(async()=>{
 const root=path.resolve(__dirname,'../..'),out=path.join(root,'work/skill-evals/browser');fs.mkdirSync(out,{recursive:true});
 const html=fs.readFileSync(path.join(root,'work/skill-evals/review/review.html'));
 const server=http.createServer((req,res)=>{if(req.url!=='/review.html'){res.writeHead(404);return res.end();}res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(html);});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));let browser;
 try{
  browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});const page=await browser.newPage({viewport:{width:1100,height:900},acceptDownloads:true});let errors=[];page.on('pageerror',e=>errors.push(e.message));
  const url='http://127.0.0.1:'+server.address().port+'/review.html';const response=await page.goto(url);if(response.status()!==200)throw Error('Review HTTP readiness failed');const inputs=page.locator('.query-input');if(await inputs.count()!==20)throw Error('Expected 20 queries');
  const text='fixture edit — not approved evaluation label';await inputs.first().fill(text);await inputs.first().blur();const toggle=page.locator('#eval-body label.toggle').first();const checked=await toggle.locator('input').isChecked();if(checked)await toggle.locator('.slider').click();const downloading=page.waitForEvent('download');await page.locator('.btn-export').click();const download=await downloading;const file=path.join(out,'edited-fixture-eval.json');await download.saveAs(file);const exported=JSON.parse(fs.readFileSync(file));if(exported.length!==20||!exported.some(x=>x.query===text&&x.should_trigger===false))throw Error('Export did not preserve editing');
  await page.screenshot({path:path.join(out,'review.png'),fullPage:false});if(errors.length)throw Error(errors.join(';'));fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify({verdict:'PASS',scope:'upstream review UI only; edited data is a fixture, not approved labels or model results',http_status:200,queries:20,edit_and_export_verified:true,page_errors:errors,transport:'localhost HTTP; managed Chromium blocks file:// navigation'},null,2));console.log('PASS: HTTP 200, 20 queries, label/query edit, export/reopen, no page errors');
 }finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
})();
