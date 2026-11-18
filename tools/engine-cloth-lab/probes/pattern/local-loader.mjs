import { registerHooks } from 'node:module'
const officialLocalTransform = new URL('./vendor/plugin-transform/src/index.mjs',import.meta.url).href
registerHooks({resolve(specifier,context,nextResolve){
 try{return nextResolve(specifier,context)}catch(error){
  if(error.code==='ERR_MODULE_NOT_FOUND' && specifier==='@freesewing/plugin-transform')return {url:officialLocalTransform,shortCircuit:true}
  throw error
 }
}})
