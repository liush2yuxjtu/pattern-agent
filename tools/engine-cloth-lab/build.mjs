import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {build} from 'esbuild';
const root=process.cwd(),raw=fs.readFileSync('inputs/golden-garment-1.1.yaml','utf8');
const sha=crypto.createHash('sha256').update(raw).digest('hex');
if(sha!=='88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e')throw Error('Canonical byte hash mismatch');
const sourceFiles=['build.mjs','package-lock.json','index.template.html','styles.css','inputs/golden-garment-1.1.yaml','probes/pattern/adapter.mjs','probes/pattern/mesh.mjs','probes/pattern/official-model.json','probes/rapier/engine.mjs','probes/rapier/native-seam.mjs','reference/assets/makehuman.json','reference/assets/README.md','reference/src/mesh-collider.js','reference/src/software-renderer.js','reference/benchmarks/collision/surface-audit.mjs','licenses/FreeSewing-MIT.txt',...fs.readdirSync('src').sort().map(f=>'src/'+f)];
const sourceHashes=Object.fromEntries(sourceFiles.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')]));
const sourceSha256=crypto.createHash('sha256').update(JSON.stringify(sourceHashes)).digest('hex');
const licenses=[];for(const name of ['@dimforge/rapier3d-compat','@freesewing/core','@freesewing/teagan','@freesewing/models','three','cdt2d','jspdf','yaml']){
  const base=path.join(root,'node_modules',name);let text='';
  for(const f of ['LICENSE','LICENSE.txt','LICENSE.md','license','LICENSE-MIT'])if(fs.existsSync(path.join(base,f))){text=fs.readFileSync(path.join(base,f),'utf8');break;}
  if(!text&&name.startsWith('@freesewing/'))text=fs.readFileSync('licenses/FreeSewing-MIT.txt','utf8');
  if(!text&&name==='@freesewing/models')text='Official model source: @freesewing/models@4.10.2; FreeSewing MIT license applies.';
  licenses.push(name+'\n'+text);
}
licenses.push('MakeHuman asset: CC0-1.0\nSource: https://github.com/makehumancommunity/makehuman/blob/master/makehuman/data/3dobjs/base.obj\n'+fs.readFileSync('reference/assets/README.md','utf8'));
const common={bundle:true,write:false,minify:true,platform:'browser',format:'iife',target:'es2022',legalComments:'inline'};
const worker=await build({...common,entryPoints:['src/solver-worker.mjs']});
const app=await build({...common,entryPoints:['src/app.mjs'],define:{__BUILD_ID__:JSON.stringify(sourceSha256),__GOLDEN_YAML__:JSON.stringify(raw),__WORKER__:JSON.stringify(worker.outputFiles[0].text),__LICENSES__:JSON.stringify(licenses.join('\n\n'))}});
// Base64 avoids HTML raw-text parser states triggered by dependency strings such as <!-- and <script.
const encoded=Buffer.from(app.outputFiles[0].text).toString('base64');
const loader=`(()=>{const s=document.createElement('script');s.textContent=new TextDecoder().decode(Uint8Array.from(atob('${encoded}'),c=>c.charCodeAt(0)));document.head.append(s)})();`;
const html=fs.readFileSync('index.template.html','utf8').replace('__CSS__',fs.readFileSync('styles.css','utf8')).replace('__APP__',()=>loader);
fs.mkdirSync('dist',{recursive:true});fs.writeFileSync('dist/index.html',html);fs.writeFileSync('dist/engine-cloth-lab.html',html);
fs.mkdirSync('.openai',{recursive:true});fs.writeFileSync('.openai/hosting.json',JSON.stringify({static:{directory:'dist'}}));
const manifest={schema:'engine-cloth-build-1',sourceSha256,sourceHashes,canonicalSha256:sha,htmlSha256:crypto.createHash('sha256').update(html).digest('hex'),htmlBytes:Buffer.byteLength(html),runtimeExternalAssets:0,versions:JSON.parse(fs.readFileSync('package.json')).dependencies};fs.writeFileSync('dist/build-manifest.json',JSON.stringify(manifest,null,2));console.log(JSON.stringify({...manifest,sourceHashes:undefined},null,2));
