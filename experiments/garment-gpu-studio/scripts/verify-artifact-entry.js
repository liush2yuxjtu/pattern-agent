// Portable companion: bundle this file to dist/verify-garment.js.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createServer} from 'node:http';
import {createHash} from 'node:crypto';
import {verifyBrowser} from '../tests/browser-verification.js';
import {verifySavedGeometry} from '../tests/independent-geometry.js';
async function main(){
 const input=process.argv[2];if(!input){console.error('Usage: node verify-garment.js /path/to/garment-gpu-studio.html');process.exitCode=2;return;}
 const html=path.resolve(input);if(!fs.statSync(html).isFile())throw new Error('HTML file required');
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'garment-verification-'));fs.mkdirSync(path.join(root,'dist'));fs.mkdirSync(path.join(root,'evidence'));fs.copyFileSync(html,path.join(root,'dist/garment-gpu-studio.html'));
 const server=createServer((req,res)=>{if(req.url!=='/garment-gpu-studio.html'){res.writeHead(404);res.end();return;}res.writeHead(200,{'content-type':'text/html; charset=utf-8','cache-control':'no-store'});res.end(fs.readFileSync(html));});
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});let browser;
 try{browser=await verifyBrowser(root,{url:`http://127.0.0.1:${server.address().port}/garment-gpu-studio.html`});}finally{await new Promise(resolve=>server.close(resolve));}
 const geometry=verifySavedGeometry(root),report={status:browser.status==='PASS'&&geometry.status==='PASS'?'PASS':'FAIL',htmlSha256:createHash('sha256').update(fs.readFileSync(html)).digest('hex'),browserChecks:browser.checks.length,independentCases:geometry.results.map(r=>({label:r.label,status:r.status,p95:r.principalStrain.p95,max:r.principalStrain.max,bodyCrossings:r.bodyFaceCrossings,selfCrossings:r.selfFaceCrossings,seamGapMm:r.seamGapMm})),adapter:browser.adapter,evidenceDirectory:path.join(root,'evidence')};
 fs.writeFileSync(path.join(root,'verification-artifact.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));if(report.status!=='PASS')process.exitCode=1;
}
main().catch(e=>{console.error(e.stack||String(e));process.exitCode=1;});
