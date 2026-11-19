import {readFile,writeFile} from 'node:fs/promises'
import {gzipSync} from 'node:zlib'
import {build} from 'esbuild'
const u=name=>new URL(name,import.meta.url)
const wasm=await readFile(u('rust/target/wasm32-unknown-unknown/release/cloth_lab_rust.wasm'))
const mesh=JSON.parse(await readFile(u('mesh.json'),'utf8'))
const payload=gzipSync(JSON.stringify({mesh,wasm:wasm.toString('base64')}),{level:9}).toString('base64')
const result=await build({entryPoints:[u('app.mjs').pathname],minify:true,bundle:true,platform:'browser',format:'iife',write:false})
const app=result.outputFiles[0].text.replace(/<\/script/gi,'<\\/script')
const [template,editor,panel,notices,art]=await Promise.all([
  readFile(u('template.html'),'utf8'),
  readFile(u('../page-carlton-inputs/fragment.template.html'),'utf8'),
  readFile(u('panel.html'),'utf8'),
  readFile(u('notices.txt'),'utf8'),
  readFile(u('line-art.png')),
])
const lineArt=art.toString('base64')
const combinedEditor=editor.split('<script>')[0]
  .replace('id="carlton-input-explorer"','id="carlton-input-explorer" data-physics')
  .replace('    <button class="btn" type="button" data-reset','    <div class="slider-grid" data-key-inputs></div>\n    <button class="btn" type="button" data-reset')
  .replace('  </div>\n</div>\n<style>',()=>panel.replace('__LINE_ART__',lineArt)+'  </div>\n</div>\n<style>')
const body=template.replace('__EDITOR__',()=>combinedEditor).replace('__PAYLOAD__',()=>payload)
  .replace('__APP__',()=>app).replace('__NOTICES__',()=>notices)
await writeFile(u('../../index.html'),body)
console.log('Unified offline preview bytes:',Buffer.byteLength(body))
