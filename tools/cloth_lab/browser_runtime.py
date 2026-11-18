"""Real Chromium rendering, shared by the cloth-lab browser verifiers.

The extra Dawn/Vulkan flags select Chromium's real software WebGPU adapter on
this host. They do not change browser policy, origin security or TLS checking.
Native methods below are forwarded unchanged; instrumentation only counts calls.
"""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


WEBGL_FLAGS = [
    '--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader',
]
WEBGPU_FLAGS = WEBGL_FLAGS + [
    '--enable-unsafe-webgpu', '--enable-features=Vulkan',
    '--use-vulkan=swiftshader',
]

NATIVE_AUDIT = r'''(() => {
  const stats = {adapterRequests:0, adapters:0, deviceRequests:0, devices:0,
    canvasContexts:[], configurations:0, configurationUsesRequestedDevice:true,
    queueSubmits:0, commandBuffers:0, deviceErrors:[], deviceLosses:[],
    adapterInfo:[], deviceDetails:[], textureCreations:[], invalidTextureSizes:[],
    viewportSamples:[]};
  const devices = new Set(), queues = new Set();
  window.__clothNativeAudit = stats;
  // Explicit negative control: destroy the actual requested native device.
  // This does not replace adapters, devices, rendering or any physics output.
  window.__clothDestroyDevices = () => {
    for (const device of devices) device.destroy();
  };
  const recordViewport = reason => {
    const viewport=document.querySelector('#viewport');
    if(!viewport)return;
    const rect=viewport.getBoundingClientRect(),canvas=viewport.querySelector('canvas');
    const entry={reason,time:performance.now(),windowWidth:innerWidth,windowHeight:innerHeight,
      cssWidth:rect.width,cssHeight:rect.height,canvasWidth:canvas?.width,canvasHeight:canvas?.height};
    stats.viewportSamples.push(entry);
    if(stats.viewportSamples.length>1000)stats.viewportSamples.shift();
  };
  addEventListener('DOMContentLoaded',()=>{
    const viewport=document.querySelector('#viewport');
    if(viewport)new ResizeObserver(()=>recordViewport('ResizeObserver')).observe(viewport);
    recordViewport('DOMContentLoaded');
  },{once:true});
  addEventListener('resize',()=>recordViewport('window-resize'));
  window.__clothWaitForGPU = async () => {
    await Promise.all([...queues].map(queue => queue.onSubmittedWorkDone()));
    await new Promise(requestAnimationFrame);
    await new Promise(requestAnimationFrame);
  };
  const context = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type, ...args) {
    const result = context.call(this, type, ...args);
    if (result) stats.canvasContexts.push({type, nativeClass:result.constructor.name});
    return result;
  };
  if (typeof GPU !== 'undefined') {
    const requestAdapter = GPU.prototype.requestAdapter;
    GPU.prototype.requestAdapter = async function(...args) {
      stats.adapterRequests++;
      const adapter = await requestAdapter.apply(this, args);
      if (adapter) {
        stats.adapters++;
        const info = adapter.info;
        stats.adapterInfo.push(Object.fromEntries(
          ['vendor','architecture','device','description','isFallbackAdapter']
            .map(key => [key, info[key]])));
      }
      return adapter;
    };
  }
  if (typeof GPUAdapter !== 'undefined') {
    const requestDevice = GPUAdapter.prototype.requestDevice;
    GPUAdapter.prototype.requestDevice = async function(...args) {
      stats.deviceRequests++;
      const device = await requestDevice.apply(this, args);
      stats.devices++; devices.add(device); queues.add(device.queue);
      stats.deviceDetails.push({label:device.label,features:[...device.features].sort(),
        limits:Object.fromEntries(['maxTextureDimension2D','maxBufferSize',
          'maxStorageBufferBindingSize','maxBindGroups'].map(key => [key,device.limits[key]]))});
      device.lost.then(info => {
        queues.delete(device.queue);
        stats.deviceLosses.push({reason:info.reason, message:info.message});
      });
      device.addEventListener('uncapturederror', event =>
        stats.deviceErrors.push(event.error.message));
      return device;
    };
  }
  if (typeof GPUCanvasContext !== 'undefined') {
    const configure = GPUCanvasContext.prototype.configure;
    GPUCanvasContext.prototype.configure = function(descriptor) {
      const result = configure.call(this, descriptor);
      stats.configurations++;
      stats.configurationUsesRequestedDevice &&= devices.has(descriptor.device);
      return result;
    };
  }
  if (typeof GPUQueue !== 'undefined') {
    const submit = GPUQueue.prototype.submit;
    GPUQueue.prototype.submit = function(buffers) {
      const result = submit.call(this, buffers);
      if (queues.has(this)) {
        stats.queueSubmits++;
        stats.commandBuffers += buffers.length;
      }
      return result;
    };
  }
  if (typeof GPUDevice !== 'undefined') {
    const createTexture=GPUDevice.prototype.createTexture;
    GPUDevice.prototype.createTexture=function(descriptor) {
      const size=descriptor?.size;
      const dimensions=Array.isArray(size)?[size[0],size[1]??1,size[2]??1]:
        [size?.width,size?.height??1,size?.depthOrArrayLayers??1];
      const entry={label:descriptor?.label??'',size:dimensions,format:descriptor?.format};
      if(devices.has(this)) {
        if(stats.textureCreations.length<500)stats.textureCreations.push(entry);
        if(dimensions.some(value=>value<1))stats.invalidTextureSizes.push(entry);
      }
      return createTexture.call(this,descriptor);
    };
  }
})();'''


def renderer_url(base, renderer):
    parts = urlsplit(base)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != 'renderer']
    return urlunsplit(parts._replace(query=urlencode(query + [('renderer', renderer)])))


def launch_browser(playwright, executable, *, webgpu=True):
    return playwright.chromium.launch(
        executable_path=executable, headless=True,
        args=WEBGPU_FLAGS if webgpu else WEBGL_FLAGS + ['--disable-webgpu'])


def instrument_context(context):
    context.add_init_script(NATIVE_AUDIT)


def wait_for_render(page):
    page.evaluate('window.__clothWaitForGPU()')


def assert_renderer(page, expected='webgpu'):
    """Require actual native rendering as well as the app's public diagnostics."""
    wait_for_render(page)
    result = page.evaluate('({diagnostics:clothLab.rendererDiagnostics(),native:__clothNativeAudit})')
    d, native = result['diagnostics'], result['native']
    assert d['firstRenderComplete'] and d['renderedFrames'] > 0, result
    assert not d['deviceErrors'] and not native['deviceErrors'], result
    assert not native['invalidTextureSizes'], result
    assert d['rendererClass'] in ['software', 'hardware-or-unknown'], result
    if expected == 'webgpu':
        assert d['api'] == 'WebGPU' and d['backend'] == 'WebGPUBackend', result
        assert d['isWebGPURenderer'] and d['isWebGPUBackend'], result
        assert not d['isWebGLRenderer'] and not d['fallbackReason'], result
        assert native['devices'] > 0 and native['configurations'] > 0, result
        assert native['configurationUsesRequestedDevice'], result
        assert native['queueSubmits'] > 0 and native['commandBuffers'] > 0, result
        assert any(c == {'type':'webgpu', 'nativeClass':'GPUCanvasContext'}
                   for c in native['canvasContexts']), result
        assert isinstance(d['device'], dict) and d['device']['features'] is not None, result
        device = native['deviceDetails'][-1]
        for key in ['label', 'features', 'limits']:
            assert d['device'][key] == device[key], result
        for key, value in native['adapterInfo'][-1].items():
            assert d['device']['adapterInfo'].get(key) == value, result
        if 'swiftshader' in str(native['adapterInfo']).lower():
            assert d['rendererClass'] == 'software', result
    else:
        assert d['api'] == 'WebGL2' and d['backend'] == 'WebGLRenderer', result
        assert d['isWebGLRenderer'] and not d['isWebGPUBackend'], result
        assert any(c['type'] == 'webgl2' for c in native['canvasContexts']), result
        assert not any(c['type'] == 'webgpu' for c in native['canvasContexts']), result
    return result


def add_renderer_argument(parser):
    parser.add_argument('--renderer', choices=['webgpu', 'webgl'], default='webgpu',
                        help='Require this real backend (default: webgpu).')
