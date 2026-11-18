import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {build} from 'esbuild';
const result=await build({entryPoints:['sliders-ui.mjs'],bundle:true,write:false,platform:'browser',format:'iife',target:'es2022',minify:true,legalComments:'inline',metafile:true});
const code=result.outputFiles[0].text.replaceAll('</script','<\\/script');
const notices=new Map();
for(const input of Object.keys(result.metafile.inputs)){
 if(!input.includes('node_modules/'))continue;
 let dir=path.dirname(path.resolve(input));
 while(dir!==path.dirname(dir)&&!fs.existsSync(path.join(dir,'package.json')))dir=path.dirname(dir);
 for(const name of ['LICENSE','LICENSE.md','LICENSE-MIT','LICENSE.txt','license','license.md']){
  const p=path.join(dir,name);if(!fs.existsSync(p))continue;
  const text=fs.readFileSync(p,'utf8');const hash=createHash('sha256').update(text).digest('hex');
  if(!notices.has(hash))notices.set(hash,text);
 }
}
notices.set('freesewing',fs.readFileSync('LICENSE.FreeSewing','utf8'));
const html=fs.readFileSync('sliders-template.html','utf8').replace('/*BUNDLE*/',code).replace('<!--LICENSES-->','<!-- Bundled source licenses\n'+[...notices.values()].join('\n\n').replaceAll('-->','-- >')+'\n-->');
fs.writeFileSync('../../web/freesewing/brian/index.html',html);
fs.mkdirSync('work',{recursive:true});
fs.writeFileSync('work/sliders-metafile.json',JSON.stringify(result.metafile));
console.log(JSON.stringify({file:'web/freesewing/brian/index.html',bytes:Buffer.byteLength(html),bundledInputs:Object.keys(result.metafile.inputs).length,licenseNotices:notices.size}));
