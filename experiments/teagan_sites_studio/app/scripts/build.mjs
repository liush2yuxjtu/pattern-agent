import {build} from 'esbuild';import wabtFactory from 'wabt';import fs from 'node:fs';
const wabt=await wabtFactory();const text=fs.readFileSync('dist/pattern-kernel.wat','utf8');fs.writeFileSync('dist/pattern-kernel.wasm',wabt.parseWat('pattern-kernel.wat',text).toBinary({}).buffer);
await build({entryPoints:['src/main.js'],outfile:'dist/studio.js',bundle:true,format:'esm',target:'es2022',external:['three'],minify:true,legalComments:'eof'});
await build({entryPoints:['src/wear-worker.js'],outfile:'dist/wear-worker.js',bundle:true,format:'esm',target:'es2022',minify:true,legalComments:'eof'});
await build({entryPoints:['src/sleeve-debugger.mjs'],outfile:'dist/sleeve-debugger.js',bundle:true,format:'esm',target:'es2022',external:['three'],minify:true,legalComments:'eof'});
console.log('Built real Teagan pattern engine and shared 2D/3D studio.');
