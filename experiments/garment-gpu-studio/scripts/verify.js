import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {createServer} from 'node:http';
import {verifyBrowser} from '../tests/browser-verification.js';
import {verifySavedGeometry} from '../tests/independent-geometry.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');process.chdir(root);
await import('./build.js');await import('../tests/unit.js');
const unit=JSON.parse(fs.readFileSync('evidence/unit-report.json'));if(unit.status!=='PASS')throw new Error('Module verification did not pass');
if(process.argv.includes('--unit-only')){console.log('MODULE VERIFICATION PASS',unit.count);process.exit(0);}
const server=createServer((req,res)=>{if(req.url!=='/garment-gpu-studio.html'){res.writeHead(404);res.end();return;}res.writeHead(200,{'content-type':'text/html; charset=utf-8','cache-control':'no-store'});res.end(fs.readFileSync('dist/garment-gpu-studio.html'));});
await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
let browser;try{browser=await verifyBrowser(root,{url:`http://127.0.0.1:${server.address().port}/garment-gpu-studio.html`});}finally{await new Promise(resolve=>server.close(resolve));}
const geometry=verifySavedGeometry(root);
const report={status:unit.status==='PASS'&&browser.status==='PASS'&&geometry.status==='PASS'?'PASS':'FAIL',htmlSha256:createHash('sha256').update(fs.readFileSync('dist/garment-gpu-studio.html')).digest('hex'),moduleChecks:unit.count,browserChecks:browser.checks.length,independentCases:geometry.results.map(r=>({label:r.label,status:r.status,p95:r.principalStrain.p95,max:r.principalStrain.max,bodyCrossings:r.bodyFaceCrossings,selfCrossings:r.selfFaceCrossings,seamGapMm:r.seamGapMm})),adapter:browser.adapter,scope:'Automated module, real-browser and independent discrete geometry assertions. No real-fabric calibration, physical GPU speed, continuous collision or human-fit claim.'};
fs.writeFileSync('evidence/verification-js.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));if(report.status!=='PASS')process.exitCode=1;
