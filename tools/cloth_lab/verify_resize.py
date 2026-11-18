#!/usr/bin/env python3
"""Real zero/subpixel/hidden viewport controls and WebGPU size recovery.

Native texture creation and queue methods are forwarded unchanged. CSS layout is
the negative input; no renderer, error or pixel is substituted or suppressed.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from browser_runtime import (assert_renderer, instrument_context, launch_browser,
                             renderer_url, wait_for_render)
from verify_browser import ROOT, save_json
from verify_replay import INSTRUMENT, counters
from verify_webgpu import (PHYSICAL_STATE, healthy, observe, same_physics,
                           untouched_first_ready_pixels)

CASES = {
    'zero-width':{'width':'0px','height':'490px'},
    'one-css-pixel-width':{'width':'1px','height':'490px'},
    'fractional-width':{'width':'.75px','height':'490px'},
    'zero-height':{'width':'640px','height':'0px'},
    'one-css-pixel-height':{'width':'640px','height':'1px'},
    'display-none':{'display':'none'},
}


def boot_hidden(browser,args,base,directory,default_state):
    """Boot the unchanged app while real CSS hides its viewport, then reveal it."""
    directory.mkdir(exist_ok=True)
    result={}
    context=browser.new_context(viewport={'width':1440,'height':1200})
    instrument_context(context);context.add_init_script(INSTRUMENT)
    context.add_init_script('''(() => {
      const style=document.createElement('style');
      style.textContent='#viewport{display:none!important}';
      window.__clothQAHiddenStyle=style;
      const insert=()=>{if(!document.documentElement)return false;document.documentElement.append(style);return true;};
      if(!insert()){
        const observer=new MutationObserver(()=>{if(insert())observer.disconnect();});
        observer.observe(document,{childList:true});
      }
    })();''')
    page=context.new_page();events=observe(page)
    try:
        assert page.goto(renderer_url(base,args.renderer),wait_until='networkidle').status==200
        page.wait_for_function('__clothNativeAudit.devices===1 && actualWasmSteps===240' if args.renderer=='webgpu' else 'actualWasmSteps===240')
        page.wait_for_timeout(100)
        assert not page.evaluate('Boolean(clothLab.ready)')
        assert page.locator('#viewport').evaluate('(v)=>v.getBoundingClientRect().width===0')
        result['hiddenNative']=page.evaluate('__clothNativeAudit')
        assert not result['hiddenNative']['invalidTextureSizes'] and not result['hiddenNative']['deviceErrors']
        assert result['hiddenNative']['queueSubmits']==0
        page.screenshot(path=str(directory/'boot-hidden-fullpage.png'),full_page=True)
        page.evaluate('__clothQAHiddenStyle.remove()')
        page.wait_for_function('window.clothLab?.ready',timeout=60000)
        result['restoredRenderer']=assert_renderer(page,args.renderer)
        assert counters(page)=={'actual':240,'reported':240}
        result['restoredPixels']=untouched_first_ready_pixels(page,directory)
        same_physics(page.evaluate(PHYSICAL_STATE),default_state)
        healthy(events)
        result['verdict']='PASS'
    except Exception as error:
        result['verdict']='FAIL';result['error']=str(error)
        try:result['failureRuntime']=page.evaluate('({native:__clothNativeAudit,error:window.clothLabError})')
        except Exception:pass
    finally:
        result['events']=events;save_json(directory/'receipt.json',result);context.close()
    return result


def run(args, base):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    report={'url':base,'htmlSha256':hashlib.sha256(args.html.read_bytes()).hexdigest(),
            'startedAtUnix':time.time(),'renderer':args.renderer,'cases':{},'checks':{}}
    with sync_playwright() as p:
        browser=launch_browser(p,args.browser)
        try:
            default_state=None
            for name,style in CASES.items():
                directory=out/name;directory.mkdir(exist_ok=True)
                result={'style':style}
                report['cases'][name]=result
                context=browser.new_context(viewport={'width':1440,'height':1200})
                instrument_context(context);context.add_init_script(INSTRUMENT)
                page=context.new_page();events=observe(page)
                try:
                    assert page.goto(renderer_url(base,args.renderer),wait_until='networkidle').status==200
                    page.wait_for_function('window.clothLab?.ready',timeout=60000)
                    result['initialRenderer']=assert_renderer(page,args.renderer)
                    physical=page.evaluate(PHYSICAL_STATE);steps=counters(page)
                    if default_state is None:default_state=physical
                    native_before=page.evaluate('__clothNativeAudit')
                    original_style=page.locator('#viewport').get_attribute('style')
                    page.evaluate('''style=>{
                      const viewport=document.querySelector('#viewport');
                      for(const [key,value] of Object.entries(style))viewport.style[key]=value;
                      // A draw requested synchronously must also consult layout;
                      // ResizeObserver has not necessarily delivered its update.
                      clothLab.setMode('stress');
                    }''',style)
                    page.wait_for_timeout(100)
                    page.screenshot(path=str(directory/'invalid-layout-fullpage.png'),full_page=True)
                    page.wait_for_timeout(100)
                    result['invalidPhase']=page.evaluate('({diagnostics:clothLab.rendererDiagnostics(),native:__clothNativeAudit})')
                    native=result['invalidPhase']['native'];d=result['invalidPhase']['diagnostics']
                    assert not native['invalidTextureSizes'] and not native['deviceErrors'] and not d['deviceErrors'], result['invalidPhase']
                    assert not d['blocked'] and page.evaluate('clothLab.ready'), result['invalidPhase']
                    if args.renderer=='webgpu':
                        assert native['queueSubmits']==native_before['queueSubmits'], 'Invalid layout submitted a GPU draw'
                        assert len(native['textureCreations'])==len(native_before['textureCreations']), 'Invalid layout allocated GPU textures'
                    assert counters(page)==steps
                    same_physics(page.evaluate(PHYSICAL_STATE),physical)
                    page.evaluate('''style=>{
                      const viewport=document.querySelector('#viewport');
                      if(style===null)viewport.removeAttribute('style');else viewport.setAttribute('style',style);
                      clothLab.setMode('fabric');
                    }''',original_style)
                    page.wait_for_function('''before=>{
                      const d=clothLab.rendererDiagnostics(),c=document.querySelector('#viewport canvas');
                      return d.renderedFrames>before && c.width>0 && c.height>0;
                    }''',arg=d['renderedFrames'])
                    result['restoredRenderer']=assert_renderer(page,args.renderer)
                    result['restoredPixels']=untouched_first_ready_pixels(page,directory)
                    page.screenshot(path=str(directory/'restored-fullpage.png'),full_page=True)
                    wait_for_render(page)
                    result['afterFullPageScreenshot']=assert_renderer(page,args.renderer)
                    assert counters(page)==steps
                    same_physics(page.evaluate(PHYSICAL_STATE),physical)
                    healthy(events)
                    result['verdict']='PASS'
                except Exception as error:
                    result['verdict']='FAIL';result['error']=str(error)
                    try:
                        result['failureRuntime']=page.evaluate('({diagnostics:clothLab?.rendererDiagnostics?.(),native:__clothNativeAudit})')
                        page.screenshot(path=str(directory/'failure.png'),full_page=True)
                    except Exception:pass
                finally:
                    result['events']=events
                    save_json(directory/'receipt.json',result)
                    context.close()
                    save_json(out/'receipt.json',report)
            report['cases']['boot-hidden']=boot_hidden(browser,args,base,out/'boot-hidden',default_state)
            assert all(result['verdict']=='PASS' for result in report['cases'].values()), {
                name:result.get('error') for name,result in report['cases'].items() if result['verdict']!='PASS'}
            report['checks']['allZeroSubpixelHiddenLayoutsPauseGPUWithoutInvalidTextures']=True
            report['checks']['allRestoredLayoutsRenderActualFabricWithoutPhysicsChanges']=True
            report['checks']['actualFullPageScreenshotsPreserveHealthyBackend']=True
            report['verdict']='PASS'
        except Exception as error:
            report['verdict']='FAIL';report['error']=str(error)
            raise
        finally:
            browser.close();report['finishedAtUnix']=time.time();save_json(out/'receipt.json',report)
    print(json.dumps({'verdict':report['verdict'],'checks':report['checks']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html',type=Path,default=ROOT/'web/cloth-lab/index.html')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--renderer',choices=['webgpu','webgl'],default='webgpu')
    parser.add_argument('--browser',default='/usr/bin/chromium')
    args=parser.parse_args()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if urlsplit(self.path).path!='/':self.send_response(404);self.end_headers();return
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(args.html.read_bytes())
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:run(args,f'http://127.0.0.1:{server.server_port}/')
    finally:server.shutdown();server.server_close();thread.join()
