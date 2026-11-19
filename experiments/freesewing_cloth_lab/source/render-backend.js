import {WebGLRenderer} from 'three';
import {WebGPURenderer} from 'three/webgpu';

// No network modules: both backends are bundled into the delivered document.
export async function createRenderBackend(canvas) {
 const softwareDriver=/swiftshader|llvmpipe|lavapipe|software|basic render driver|warp/i;
 const requested=new URL(location.href).searchParams.get('renderer')||'auto';
 const status={requested,api:null,physics:'WASM Float64 / CPU',adapter:null,fallbackReason:null,deviceLost:null,errors:[]};
 let device;
 if(requested!=='webgl') {
  try {
   if(!isSecureContext||!navigator.gpu)throw new Error('WebGPU unavailable in this browser/context');
   const adapter=await navigator.gpu.requestAdapter({powerPreference:'high-performance'});
   if(!adapter)throw new Error('No WebGPU adapter available');
   const info=adapter.info;
   status.adapter={vendor:info?.vendor||'',architecture:info?.architecture||'',device:info?.device||'',description:info?.description||'',isFallbackAdapter:info?.isFallbackAdapter??null};
   const software=status.adapter.isFallbackAdapter===true||softwareDriver.test([info?.vendor,info?.architecture,info?.description].join(' '));
   status.adapter.software=software;
   if(software&&requested!=='webgpu')throw new Error('Software WebGPU adapter; using WebGL2 compatibility path');
   device=await adapter.requestDevice({});
   const renderer=new WebGPURenderer({canvas,device,antialias:true,trackTimestamp:false});
   await renderer.init();
   if(!renderer.backend.isWebGPUBackend)throw new Error('Requested WebGPU backend did not initialize');
   status.api='WebGPU';
   device.lost.then(info=>{status.deviceLost={reason:info.reason,message:info.message};});
   device.addEventListener('uncapturederror',e=>{status.errors.push(e.error.message);console.error('[WebGPU]',e.error.message);});
   return {renderer,status,device};
  } catch(error) {
   status.fallbackReason=String(error.message||error);
   device?.destroy();
   // A canvas that acquired a GPU context cannot acquire a WebGL context.
   const replacement=canvas.cloneNode(false);canvas.replaceWith(replacement);canvas=replacement;
  }
 } else status.fallbackReason='WebGL2 explicitly selected';
 status.api='WebGL2';
 const renderer=new WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance',preserveDrawingBuffer:true});
 const gl=renderer.getContext(),debug=gl.getExtension('WEBGL_debug_renderer_info');
 status.software=debug?softwareDriver.test(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)):status.adapter?.software===true;
 return {renderer,status,device:null};
}
