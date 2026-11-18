#!/usr/bin/env python3
"""Real WebGPU/WebGL standalone pixels, frozen physics and offline round trips.

No renderer, solver, adapter or device is substituted. The unavailable-adapter
control uses Chromium's own --disable-webgpu switch. Full legacy geometry,
constitutive, pressure, waist and 61-frame replay suites remain separate gates.
"""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import subprocess
import threading
import time
from urllib.parse import urlsplit

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from browser_runtime import (WEBGPU_FLAGS, assert_renderer, instrument_context,
                             launch_browser, renderer_url, wait_for_render)
from oracle import verify
from verify_browser import ROOT, save_json
from verify_fit import guard_avatar, pixels, pressure_colors
from verify_replay import INSTRUMENT, colors, compare_frame, counters, state


PHYSICAL_STATE = r'''() => {
  const p=clothLab.project(false), arrays={};
  const fields={positions:p.positions, previous:p.previous, pinPositions:p.pinPositions,
    contactFlags:p.contactFlags, restUV:p.restUV, triangleFields:p.triangleFields,
    bodyPositions:p.body.positions};
  const pack = (values,Type) => {
    const bytes=new Uint8Array(new Type(values).buffer); let binary='';
    for(let i=0;i<bytes.length;i+=16384)
      binary+=String.fromCharCode(...bytes.subarray(i,i+16384));
    return btoa(binary);
  };
  for(const [key,values] of Object.entries(fields)) arrays[key]=pack(values,Float32Array);
  arrays.triangles=pack(p.triangles,Int32Array);
  arrays.bodyTriangles=pack(p.body.triangles,Int32Array);
  return {arrays,parameters:p.parameters,material:p.material,pressureState:p.pressureState,
    fitPressure:p.fitPressure,pressureContacts:p.pressureContacts,seams:p.seams,
    frame:p.diagnostics.frame,time:p.diagnostics.simulationSeconds,
    bodyOffsetX:p.body.offsetX,bodySourceSha256:p.body.sourceSha256};
}'''


def same_physics(actual, expected):
    # Compare the bytes generated IN the page before JSON serialization can erase
    # a Float32 negative zero. Report the actual differing field, not all arrays.
    assert actual.keys() == expected.keys()
    for key in actual:
        if key == 'arrays':
            assert actual[key].keys() == expected[key].keys()
            for field in actual[key]:
                assert actual[key][field] == expected[key][field], f'Physical bytes changed: {field}'
        else:
            assert actual[key] == expected[key], f'Physical state changed: {key}'


def hashes(physical):
    return {key:hashlib.sha256(base64.b64decode(value,validate=True)).hexdigest()
            for key,value in physical['arrays'].items()}


def observe(page):
    result = {'pageErrors':[], 'consoleErrors':[], 'requests':[], 'badResponses':[]}
    page.on('pageerror', lambda e:result['pageErrors'].append(str(e)))
    page.on('console', lambda m:result['consoleErrors'].append(m.text) if m.type == 'error' else None)
    page.on('request', lambda r:result['requests'].append(r.url))
    page.on('response', lambda r:result['badResponses'].append({'url':r.url,'status':r.status}) if r.status >= 400 else None)
    return result


def healthy(events):
    assert not events['pageErrors'] and not events['consoleErrors'] and not events['badResponses'], events


def clothing_pixels(page, out, name):
    wait_for_render(page)
    result = pixels(page,out,name)
    for direction, data in result.items():
        image = np.array(Image.open(out/(name+'-'+direction+'.png')).convert('RGB')).astype(float)
        x0,y0,x1,y1 = data['hipROI']
        roi = image[y0:y1,x0:x1]
        brown = (roi[:,:,0] > roi[:,:,1]*1.1) & (roi[:,:,1] > roi[:,:,2]*1.02)
        data['fabricPixelFraction'] = float(brown.mean())
        # A black/blank canvas can have zero skin pixels. Require actual fabric
        # color in the same independent, projected anatomy rectangle as well.
        assert data['fabricPixelFraction'] > .85, (direction,data)
    return result


def untouched_first_ready_pixels(page, out):
    """Observe the presented default view BEFORE any control can trigger a draw."""
    points = [[x,y,.14] for x in [-.06,.06] for y in [.80,.92]]
    projected = np.array([page.evaluate('(p)=>clothLab.pointToPixel(p)',p) for p in points])
    raw = page.locator('#viewport').screenshot(path=str(out/'first-ready-untouched.png'))
    image = np.array(Image.open(io.BytesIO(raw)).convert('RGB')).astype(float)
    x0,y0 = np.ceil(projected.min(axis=0)).astype(int)
    x1,y1 = np.floor(projected.max(axis=0)).astype(int)
    assert 0 <= x0 < x1 < image.shape[1] and 0 <= y0 < y1 < image.shape[0]
    roi = image[y0:y1,x0:x1]
    brown = (roi[:,:,0] > roi[:,:,1]*1.1) & (roi[:,:,1] > roi[:,:,2]*1.02)
    skin = (roi[:,:,0] > 70) & (roi[:,:,1]/np.maximum(roi[:,:,0],1) > .88) & (roi[:,:,2]/np.maximum(roi[:,:,1],1) > .80)
    result = {'sourcePoints':points,'hipROI':[int(x0),int(y0),int(x1),int(y1)],
              'fabricPixelFraction':float(brown.mean()),'skinPixels':int(skin.sum()),'pixels':int(brown.size)}
    assert result['fabricPixelFraction'] > .85 and result['skinPixels'] == 0, result
    return result


def secure_offline_page(browser, origin, html):
    context = browser.new_context(viewport={'width':1440,'height':1200},accept_downloads=True)
    instrument_context(context)
    context.add_init_script(INSTRUMENT)
    page = context.new_page()
    assert page.goto(origin,wait_until='load').status == 200
    assert page.evaluate('isSecureContext && !window.clothLab && actualWasmSteps===0')
    assert page.locator('script').count() == 0
    context.set_offline(True)
    events = observe(page)
    page.set_content(html,wait_until='load')
    page.wait_for_function('window.clothLab?.ready',timeout=60000)
    return context,page,events


def run(args, base, baseline_url):
    out = args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    committed_baseline = subprocess.check_output(['git','show','aa3f497:web/cloth-lab/index.html'],cwd=ROOT)
    assert args.baseline_html.read_bytes() == committed_baseline, 'Baseline HTML must be the actual aa3f497 artifact'
    report = {'startedAtUnix':time.time(), 'baselineRef':'aa3f497',
              'htmlSha256':hashlib.sha256(args.html.read_bytes()).hexdigest(),
              'baselineHtmlSha256':hashlib.sha256(args.baseline_html.read_bytes()).hexdigest(),
              'launchFlags':WEBGPU_FLAGS, 'checks':{}, 'backends':{},
              'scope':'Real renderer/standalone refactor. Synthetic physical calibration and manufacturing fit NOT_RUN.'}
    with sync_playwright() as p:
        browser = launch_browser(p,args.browser)
        try:
            # Old committed app executes its real, unchanged WASM in this same
            # browser. Only current build fingerprints are intentionally new.
            baseline_context = browser.new_context(viewport={'width':1440,'height':1200})
            baseline_page = baseline_context.new_page()
            baseline_events = observe(baseline_page)
            assert baseline_page.goto(baseline_url,wait_until='networkidle').status == 200
            baseline_page.wait_for_function('window.clothLab?.ready',timeout=60000)
            baseline = []
            for count in [0,1,59]:
                if count:baseline_page.evaluate('(n)=>clothLab.advance(n)',count)
                baseline.append(baseline_page.evaluate(PHYSICAL_STATE))
            healthy(baseline_events)
            save_json(out/'baseline-native-float32.json',baseline)
            report['baselineArraySha256'] = [hashes(s) for s in baseline]
            baseline_context.close()

            for backend in ['webgpu','webgl']:
                directory = out/backend
                directory.mkdir(exist_ok=True)
                result = {'checks':{}}
                report['backends'][backend] = result
                context = browser.new_context(viewport={'width':1440,'height':1200},accept_downloads=True)
                instrument_context(context)
                context.add_init_script(INSTRUMENT)
                page = context.new_page()
                events = observe(page)
                assert page.goto(renderer_url(base,backend),wait_until='networkidle').status == 200
                page.wait_for_function('window.clothLab?.ready',timeout=60000)
                result['rendering'] = assert_renderer(page,backend)
                assert result['rendering']['diagnostics']['requested'] == backend
                result['untouchedFirstReadyPixels'] = untouched_first_ready_pixels(page,directory)
                initial = state(page)
                assert initial['diagnostics']['frame'] == 240 and counters(page) == {'actual':240,'reported':240}
                guard_avatar(page,initial)
                save_json(directory/'first-ready.json',initial)
                # This is the FIRST READY state, before any explicit user step.
                result['firstReadyGeometry'] = verify(initial,args.body_source)
                result['firstReadyPixels'] = clothing_pixels(page,directory,'first-ready')
                result['checks']['realFirstRenderAndFrontSideBackClothing'] = True
                actual_samples = []
                for index,count in enumerate([0,1,59]):
                    if count:page.evaluate('(n)=>clothLab.advance(n)',count)
                    actual = page.evaluate(PHYSICAL_STATE)
                    same_physics(actual,baseline[index])
                    actual_samples.append(hashes(actual))
                result['arraySha256'] = actual_samples
                result['checks']['defaultAndOneAnd60StepsMatchOldPhysicalBytes'] = True
                saved = state(page)
                image_bytes = {}
                for mode,column,scale in [('strain',0,.12),('stress',3,15000)]:
                    page.locator(f'[data-mode={mode}]').click()
                    colors(page,saved,column,scale)
                    wait_for_render(page)
                    image_bytes[mode] = page.locator('#viewport').screenshot(path=str(directory/(mode+'.png')))
                pressure_colors(page,saved)
                wait_for_render(page)
                image_bytes['pressure'] = page.locator('#viewport').screenshot(path=str(directory/'pressure.png'))
                assert len(set(image_bytes.values())) == 3
                result['checks']['trueTensorAndPressureColorsReachDistinctRenderedPixels'] = True

                # Small real recording exercises the new module handoff. The
                # original 61-frame numerical suite remains mandatory separately.
                page.locator('#record-start').click()
                page.evaluate('clothLab.advance(3)')
                page.locator('#record-stop').click()
                page.locator('#replay-timeline').fill('1')
                page.locator('#replay-timeline').dispatch_event('input')
                selected = state(page)
                # state() deliberately omits replay; the actual download below
                # must include all four frames and the selected cursor.
                selected_full = page.evaluate('clothLab.project()')
                assert len(selected_full['replay']['frames']) == 4 and selected_full['replay']['cursor'] == 1
                compare_frame(selected,selected_full['replay']['frames'][1])
                selected_bytes = page.evaluate(PHYSICAL_STATE)
                with page.expect_download() as event:page.locator('#save-html').click()
                snapshot = directory/'actual-downloaded.html'
                event.value.save_as(str(snapshot))
                blank = renderer_url(base.rsplit('/',1)[0]+'/origin.html',backend)
                offline,op,offline_events = secure_offline_page(browser,blank,snapshot.read_text())
                result['offlineRendering'] = assert_renderer(op,backend)
                assert counters(op) == {'actual':0,'reported':0}, 'Restoring a snapshot must not pre-drape again'
                same_physics(op.evaluate(PHYSICAL_STATE),selected_bytes)
                assert op.evaluate('clothLab.replay.info().frames') == 4
                assert op.evaluate('clothLab.replay.info().cursor') == 1
                compare_frame(state(op),selected_full['replay']['frames'][1])
                op.screenshot(path=str(directory/'offline-reopened.png'),full_page=True)
                page.evaluate('clothLab.advance(1)')
                op.evaluate('clothLab.advance(1)')
                next_state = op.evaluate(PHYSICAL_STATE)
                same_physics(next_state,page.evaluate(PHYSICAL_STATE))
                with op.expect_download() as event:op.locator('#save-html').click()
                second = directory/'recursive-downloaded.html'
                event.value.save_as(str(second))
                assert second.stat().st_size < snapshot.stat().st_size+16384
                assert not offline_events['requests'], offline_events
                healthy(offline_events)
                result['offlineEvents'] = offline_events
                offline.close()
                recursive,rp,recursive_events = secure_offline_page(browser,blank,second.read_text())
                result['recursiveRendering'] = assert_renderer(rp,backend)
                assert rp.locator('script#initial-state').count() == 1
                assert rp.locator('script#payload').count() == 1
                same_physics(rp.evaluate(PHYSICAL_STATE),next_state)
                assert not recursive_events['requests'], recursive_events
                healthy(recursive_events)
                recursive.close()
                result['checks']['zeroRequestSecureOriginOfflineActualBackendAndExactContinuation'] = True
                result['checks']['recursiveSnapshotAndRecordedSelectionSurviveModuleRefactor'] = True
                assert not [url for url in events['requests'] if url != renderer_url(base,backend)], events
                healthy(events)
                result['events'] = events
                result['performance'] = page.evaluate('clothLab.performanceLog()')
                result['finalRendering'] = assert_renderer(page,backend)
                context.close()
                save_json(out/'receipt.json',report)

            # Default auto must use the same actual GPU backend on this capable
            # browser, with a real native device and a presented first frame.
            context = browser.new_context(viewport={'width':1440,'height':1200})
            instrument_context(context)
            page = context.new_page()
            auto_events = observe(page)
            assert page.goto(base,wait_until='networkidle').status == 200
            page.wait_for_function('window.clothLab?.ready',timeout=60000)
            report['defaultAuto'] = assert_renderer(page,'webgpu')
            assert report['defaultAuto']['diagnostics']['requested'] == 'auto'
            healthy(auto_events)
            before_loss = page.evaluate(PHYSICAL_STATE)
            page.evaluate('__clothDestroyDevices()')
            page.wait_for_function("clothLab.ready && clothLab.rendererDiagnostics().api==='WebGL2'",timeout=30000)
            wait_for_render(page)
            lost = page.evaluate('({diagnostics:clothLab.rendererDiagnostics(),native:__clothNativeAudit})')
            assert lost['diagnostics']['isWebGLRenderer'] and lost['diagnostics']['firstRenderComplete'], lost
            assert lost['diagnostics']['fallbackReason'] and lost['diagnostics']['deviceErrors'], lost
            assert any(c['type'] == 'webgl2' for c in lost['native']['canvasContexts']), lost
            same_physics(page.evaluate(PHYSICAL_STATE),before_loss)
            page.locator('[data-camera=front]').click()
            before_pointer = page.locator('#viewport').screenshot()
            canvas = page.locator('#viewport canvas').bounding_box()
            page.mouse.move(canvas['x']+canvas['width']/2,canvas['y']+canvas['height']/2)
            page.mouse.down()
            page.mouse.move(canvas['x']+canvas['width']/2+90,canvas['y']+canvas['height']/2+25,steps=5)
            page.mouse.up()
            wait_for_render(page)
            assert page.locator('#viewport').screenshot() != before_pointer
            before_resize = page.locator('#viewport canvas').evaluate('(c)=>({width:c.width,height:c.height})')
            page.set_viewport_size({'width':1230,'height':1100})
            page.wait_for_function('''before=>{
              const c=document.querySelector('#viewport canvas');
              return c.width!==before.width || c.height!==before.height;
            }''',arg=before_resize)
            wait_for_render(page)
            after_resize = page.locator('#viewport canvas').evaluate('(c)=>({width:c.width,height:c.height})')
            assert after_resize != before_resize
            assert page.evaluate('clothLab.rendererDiagnostics().isWebGLRenderer')
            page.screenshot(path=str(out/'active-device-loss-auto-fallback.png'),full_page=True)
            same_physics(page.evaluate(PHYSICAL_STATE),before_loss)
            report['activeDeviceLossAuto'] = {**lost,'canvasBeforeResize':before_resize,'canvasAfterResize':after_resize}
            healthy(auto_events)
            context.close()
            report['checks']['defaultAutoActuallySelectsWebGPU'] = True
            report['checks']['actualDeviceLossAutoFallbackPreservesPhysicsPointerAndResize'] = True

            context = browser.new_context(viewport={'width':1440,'height':1200})
            instrument_context(context)
            context.add_init_script(INSTRUMENT)
            page = context.new_page()
            loss_events = observe(page)
            assert page.goto(renderer_url(base,'webgpu'),wait_until='networkidle').status == 200
            page.wait_for_function('window.clothLab?.ready',timeout=60000)
            assert_renderer(page,'webgpu')
            before_loss = page.evaluate(PHYSICAL_STATE)
            before_loss_project = page.evaluate('clothLab.project()')
            before_loss_calls = counters(page)
            page.evaluate('__clothDestroyDevices()')
            page.wait_for_function('window.clothLabError && !clothLab.ready',timeout=30000)
            forced = page.evaluate('({diagnostics:clothLab.rendererDiagnostics(),native:__clothNativeAudit})')
            assert forced['diagnostics']['blocked'] and not forced['diagnostics']['firstRenderComplete'], forced
            assert forced['diagnostics']['deviceErrors'], forced
            assert not any(c['type'] in ['webgl','webgl2'] for c in forced['native']['canvasContexts']), forced
            controls = ['width','length','material','fault','body-shift','collision','wind',
                        'record-start','run','single-step','settle','reset','replay-timeline','import-replay']
            locked = {name:page.locator('#'+name).is_disabled() for name in controls}
            assert all(locked.values()), locked
            page.locator('#reset').click(force=True)
            page.locator('#single-step').click(force=True)
            calls = page.evaluate('''async saved=>{
              const rejected={};
              for(const [name,call] of Object.entries({advance:()=>clothLab.advance(1),
                reset:()=>clothLab.reset(),run:()=>clothLab.setRunning(true),
                record:()=>clothLab.replay.start(),restore:()=>clothLab.restore(saved),
                inject:()=>clothLab.injectVertex(100,[.5,1,.5])})) {
                try {await call();rejected[name]=false;} catch(error) {rejected[name]=String(error);}
              }
              return rejected;
            }''',before_loss_project)
            assert all(calls.values()), calls
            page.wait_for_timeout(100)
            assert counters(page) == before_loss_calls, (before_loss_calls,counters(page),calls)
            assert not page.evaluate('clothLab.ready')
            assert page.locator('#verdict').inner_text().startswith('BLOCKED')
            same_physics(page.evaluate(PHYSICAL_STATE),before_loss)
            page.evaluate('clothLab.performanceLog()')
            assert page.locator('#verdict').inner_text().startswith('BLOCKED')
            assert not page.evaluate('clothLab.ready')
            report['activeDeviceLossForced'] = {**forced,'lockedControls':locked,'publicMutators':calls}
            page.screenshot(path=str(out/'active-device-loss-forced-blocked.png'),full_page=True)
            healthy(loss_events)
            context.close()
            report['checks']['actualDeviceLossForcedWebGPUBlocksWithoutFallbackOrFalseReady'] = True
        except Exception as error:
            report['verdict'] = 'FAIL'
            report['error'] = str(error)
            raise
        finally:
            browser.close()
            save_json(out/'receipt.json',report)

        unavailable = launch_browser(p,args.browser,webgpu=False)
        try:
            context = unavailable.new_context(viewport={'width':1440,'height':1200})
            instrument_context(context)
            page = context.new_page()
            events = observe(page)
            assert page.goto(renderer_url(base,'auto'),wait_until='networkidle').status == 200
            page.wait_for_function('window.clothLab?.ready',timeout=60000)
            report['unavailableAuto'] = assert_renderer(page,'webgl')
            fallback = report['unavailableAuto']['diagnostics']
            assert fallback['requested'] == 'auto' and fallback['fallbackReason']
            assert report['unavailableAuto']['native']['adapters'] == 0
            assert report['unavailableAuto']['native']['devices'] == 0
            assert 'WebGPU' in page.locator('#renderer-info').inner_text()
            assert 'WebGL2' in page.locator('#renderer-info').inner_text()
            report['unavailableAutoPixels'] = clothing_pixels(page,out,'fallback-first-ready')
            healthy(events)
            report['unavailableAutoEvents'] = events
            context.close()

            context = unavailable.new_context()
            instrument_context(context)
            page = context.new_page()
            strict_events = observe(page)
            assert page.goto(renderer_url(base,'webgpu'),wait_until='networkidle').status == 200
            page.wait_for_function('window.clothLabError || /BLOCKED|FAIL/.test(document.querySelector("#verdict").textContent)',timeout=30000)
            assert not page.evaluate('Boolean(window.clothLab?.ready)')
            assert 'WebGPU' in page.evaluate('window.clothLabError')
            native = page.evaluate('__clothNativeAudit')
            assert not any(c['type'] in ['webgl','webgl2'] for c in native['canvasContexts']), native
            report['strictUnavailable'] = {'native':native, 'message':page.locator('#verdict').inner_text(),
                                           'events':strict_events}
            page.screenshot(path=str(out/'strict-unavailable.png'),full_page=True)
            context.close()
            report['checks']['nativeUnavailableAdapterAutoFallbackAndStrictWebGPUFailure'] = True
            report['verdict'] = 'PASS'
        except Exception as error:
            report['verdict'] = 'FAIL'
            report['error'] = str(error)
            raise
        finally:
            unavailable.close()
            report['finishedAtUnix'] = time.time()
            save_json(out/'receipt.json',report)
    print(json.dumps({'verdict':report['verdict'],'checks':report['checks'],
                      'backends':{key:value['checks'] for key,value in report['backends'].items()}},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html',type=Path,default=ROOT/'web/cloth-lab/index.html')
    parser.add_argument('--baseline-html',type=Path,default=ROOT/'work/cloth-modular/baseline/index.html')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser',default='/usr/bin/chromium')
    parser.add_argument('--body-source',type=Path,default=ROOT/'web/human-studio/assets/human.json')
    args = parser.parse_args()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            name = urlsplit(self.path).path
            if name == '/candidate.html':raw = args.html.read_bytes()
            elif name == '/baseline.html':raw = args.baseline_html.read_bytes()
            elif name == '/origin.html':raw = b'<!doctype html><title>Empty secure origin for offline verification</title>'
            else:
                self.send_response(404);self.end_headers();return
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(raw)
        def log_message(self,*args):pass
    server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        base = f'http://127.0.0.1:{server.server_port}'
        run(args,base+'/candidate.html',base+'/baseline.html')
    finally:
        server.shutdown();server.server_close();thread.join()
