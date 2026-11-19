import {build} from 'esbuild';
await build({entryPoints:['scripts/verify-artifact-entry.js'],outfile:'dist/verify-garment.js',bundle:true,platform:'node',format:'esm',target:'node22',packages:'external',legalComments:'eof',banner:{js:'// Standalone artifact verifier. Requires Node.js 22+ and playwright@1.62.1.\n// Usage: node verify-garment.js garment-gpu-studio.html'}});
console.log('Built dist/verify-garment.js');
