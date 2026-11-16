import {makePatternSVG} from './pattern.mjs';
import {DEFAULTS} from './model.mjs';
import {build} from 'esbuild';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const result=await build({entryPoints:['app.mjs'],bundle:true,minify:true,format:'iife',target:'es2020',write:false,legalComments:'inline'});
const html=(await readFile('template.html','utf8')).replace('__CSS__',await readFile('style.css','utf8')).replace('__APP__',()=>result.outputFiles[0].text.replace(/<\/script/gi,'<\\/script'));
await mkdir('dist',{recursive:true});await writeFile('dist/index.html',html);await writeFile('dist/aster-studio.html',html);
await writeFile('dist/THREE-LICENSE.txt',await readFile('node_modules/three/LICENSE','utf8'));
console.log(`Built self-contained HTML: ${Buffer.byteLength(html)} bytes. Three.js bundled, no CDN.`);

await writeFile('dist/aster-pattern-1-to-1.svg',makePatternSVG(DEFAULTS,'',true));
await mkdir('dist/source',{recursive:true});
for(const f of ['app.mjs','model.mjs','pattern.mjs','style.css','template.html','build.mjs','verify.mjs','verify-dom.mjs','make-handoff.py','package.json','package-lock.json']) await writeFile('dist/source/'+f,await readFile(f));
