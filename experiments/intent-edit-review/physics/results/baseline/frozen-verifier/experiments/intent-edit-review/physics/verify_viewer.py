#!/usr/bin/env python3
"""Real Chromium review of actual physics arrays, GPU fields and offline replay.

Browser plugin not available. The user explicitly permits Playwright. Numerical
garment acceptance remains the independent audit's verdict, even when UI passes.
"""
import argparse
import base64
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import sys
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from scripts.playwright_http import new_api_context

def unpack(value,width=1):
    a=np.frombuffer(base64.b64decode(value),dtype='<f4').astype(float)
    return a.reshape(-1,width) if width>1 else a

def expect_state(page,recording):
    actual=page.evaluate('physicsReview.state()'); info=page.evaluate('physicsReview.info()'); frame=recording['frames'][info['index']]
    for key in ['positions','previous','fields','contacts','folds']:
        assert np.array_equal(np.array(actual[key]),unpack(frame[key])),key
    assert actual['clock']==frame['time']
    assert info['integrationCallsDuringReplay']==0

def expect_colors(page,input,recording,mode):
    actual=page.evaluate('physicsReview.surface()');info=page.evaluate('physicsReview.info()')
    frame=recording['frames'][info['index']];fields=unpack(frame['fields'],8);faces=np.asarray(input['triangles']);nv=len(input['positions'])
    if mode=='contacts':
        expected=np.where(unpack(frame['contacts'])[:,None]>0,[.83,.28,.16],[.56,.69,.59])
    else:
        palette=np.array([[.16,.29,.65],[.20,.65,.68],[.85,.91,.78],[.94,.65,.25],[.76,.20,.18]])
        if mode=='strain':value=(fields[:,0]+.1)/.6
        elif mode=='stress':value=(fields[:,3]+20000)/120000
        elif mode=='fold':value=(unpack(frame['folds'],2)[:,0]+180)/360
        else:value=None
        colors=np.tile([.53,.71,.58],(len(faces),1))
        if value is not None:
            t=np.clip(value,0,1)*4;k=np.minimum(3,np.floor(t).astype(int));f=t-k
            colors=palette[k]*(1-f[:,None])+palette[k+1]*f[:,None]
        expected=np.zeros((nv,3));counts=np.zeros(nv)
        for j in range(3):np.add.at(expected,faces[:,j],colors);np.add.at(counts,faces[:,j],1)
        expected/=np.maximum(counts[:,None],1)
    assert np.max(abs(expected-np.asarray(actual['colors']).reshape(-1,3)))<2e-6


def expect_source_tools(page,output):
    package=page.evaluate('physicsReview.sources()');files=package['files']
    page.locator('#view-2d').click();assert page.locator('#pattern-2d').is_visible()
    original=ET.fromstring(package['twoD']['svg']);namespace='{http://www.w3.org/2000/svg}'
    for tag in ['polyline','text']:
        expected=original.findall(namespace+tag);actual=page.locator('#pattern-svg-host svg '+tag)
        assert actual.count()==len(expected),tag
        for i,node in enumerate(expected):
            if tag=='polyline':assert actual.nth(i).get_attribute('points')==node.get('points')
            else:assert actual.nth(i).text_content()==''.join(node.itertext())
    svg=page.locator('#pattern-svg-host svg');initial=svg.get_attribute('viewBox')
    page.locator('#pattern-zoom-in').click();zoomed=svg.get_attribute('viewBox');assert zoomed!=initial
    page.locator('#pattern-reset').click();assert svg.get_attribute('viewBox')==initial
    page.locator('#open-spec').click();assert page.locator('#spec-dialog').evaluate('(d)=>d.open')
    expected_yaml=base64.b64decode(files['yaml']['base64']).decode('utf8')
    assert page.locator('#spec-content').text_content()==expected_yaml
    font=page.locator('#spec-content').evaluate('(e)=>({size:parseFloat(getComputedStyle(e).fontSize),line:parseFloat(getComputedStyle(e).lineHeight)})')
    assert font['size']>=12 and font['line']>=font['size']*1.4,'Readable full YAML font and line height'
    assert any('\u4e00'<=c<='\u9fff' for c in expected_yaml[:1500]),'Chinese specification prose is present'
    page.locator('#spec-content').hover();page.mouse.wheel(0,900);page.wait_for_timeout(100)
    page.locator('#spec-top').click();assert page.locator('#spec-content').evaluate('(e)=>e.scrollTop')==0
    page.keyboard.press('Escape');assert not page.locator('#spec-dialog').evaluate('(d)=>d.open')
    assert page.evaluate('document.activeElement.id')=='open-spec'
    buttons={'yaml':'download-spec','dxf':'download-dxf','spec_diff':'download-spec-diff','geometry_patch':'download-geometry-patch'}
    for key,file in files.items():
        with page.expect_download() as pending:page.locator('#'+buttons[key]).click()
        destination=output/('source-'+key+'-'+file['name']);pending.value.save_as(destination)
        raw=destination.read_bytes();assert raw==base64.b64decode(file['base64'])
        assert hashlib.sha256(raw).hexdigest()==file['sha256']
    page.locator('#view-3d').click();assert page.locator('#canvas-host canvas').is_visible()
    return {'full_files':len(files),'complete_yaml_bytes':len(expected_yaml.encode()),
            'svg_polylines':len(original.findall(namespace+'polyline')),'svg_text':len(original.findall(namespace+'text'))}

def run(args):
    args.output.mkdir(parents=True,exist_ok=True)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*a,**k):super().__init__(*a,directory=str(args.html.parent),**k)
        def log_message(self,*a):pass
    server=None
    if args.base_url:url=args.base_url
    else:
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}/{args.html.name}'
    receipt={'browserPath':'User-requested repository Playwright with actual Chromium, WebGL, downloads and reopen.',
        'url':url,'html_sha256':hashlib.sha256(args.html.read_bytes()).hexdigest(),'checks':{},'page_errors':[],'console_errors':[],
        'scope':'Actual reviewer interaction and exact saved array/color display. Garment verdict is independently reported and is not changed by UI PASS.'}
    source=json.loads((args.run/'input.json').read_text());recording=json.loads((args.run/'trajectory.json').read_text())
    receipt.update(case=source['case'],input_sha256=hashlib.sha256((args.run/'input.json').read_bytes()).hexdigest(),
                   recording_sha256=hashlib.sha256((args.run/'trajectory.json').read_bytes()).hexdigest())
    try:
        with sync_playwright() as p:
            api=new_api_context(p,url)
            served=api.get(url,timeout=90000);assert served.status==200
            assert hashlib.sha256(served.body()).hexdigest()==receipt['html_sha256'],'Served HTML differs from candidate'
            api.dispose()
            browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
            context=browser.new_context(viewport={'width':1440,'height':1080},accept_downloads=True)
            page=context.new_page();page.on('pageerror',lambda e:receipt['page_errors'].append(str(e)))
            page.on('console',lambda m:receipt['console_errors'].append(m.text) if m.type=='error' else None)
            response=page.goto(url,wait_until='load');assert response.status==200
            page.wait_for_function('Boolean(window.physicsReview)',timeout=90000)
            page.locator('#case').select_option(source['case'])
            info=page.evaluate('physicsReview.info()')
            if 'viewerSources' in info:
                expected={name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                          for name in ['viewer.mjs','viewer.css','viewer.template.html','recording-codec.mjs']}
                assert info['viewerSources']==expected,'Viewer source revision differs'
                receipt['viewer_sources']=expected
            assert page.title()=='物理实验台 · Pattern Agent';assert page.get_by_role('heading',name='让纸样接受真实计算。').is_visible()
            assert not receipt['page_errors'];expect_state(page,recording)
            receipt['checks']['identityMeaningfulRenderAndExactInitialState']='PASS'
            screenshot=args.output/'desktop.png';page.screenshot(path=str(screenshot),full_page=True)
            image=Image.open(screenshot).convert('RGB');colors=image.getcolors(image.width*image.height)
            assert len(colors)>500,'Actual shaded model must render';assert page.evaluate('physicsReview.renderer().triangles')>len(source['triangles'])
            receipt['checks']['realWebGLBodyAndClothPixels']='PASS'
            receipt['source_tools']=expect_source_tools(page,args.output)
            receipt['checks']['actual2DZoomFullReadableChineseYAMLAndExactSourceDownloads']='PASS'
            page.locator('#timeline').focus();page.keyboard.press('Home')
            for index in range(1,len(recording['frames'])):
                page.keyboard.press('ArrowRight');assert page.evaluate('physicsReview.info().index')==index;expect_state(page,recording)
            receipt['checks']['everyRecordedStateExactAndSeekingDoesNotIntegrate']='PASS'
            for mode in ['strain','stress','fold','contacts','seams','cloth']:
                page.locator(f'[data-mode="{mode}"]').click();expect_colors(page,source,recording,mode)
                assert page.evaluate('physicsReview.info().mode')==mode
            receipt['checks']['allActualFieldModesReachGPUColorBuffers']='PASS'
            page.locator('[data-mode="stress"]').click();page.screenshot(path=str(args.output/'stress.png'),full_page=True)
            for pair in source['source_sewing']['seams']:
                page.locator('#seam').select_option(pair['name']);assert page.evaluate('physicsReview.info().mode')=='seams'
                assert pair['name']==page.locator('#seam').input_value();assert '采样点' in page.locator('#seam-detail').inner_text()
            receipt['checks']['all15SewingConnectionsSelectable']='PASS'
            page.locator('#body').uncheck();page.wait_for_timeout(100);assert page.evaluate('physicsReview.renderer().triangles')==len(source['triangles'])
            page.locator('#body').check();page.locator('#wire').check();page.wait_for_timeout(100)
            assert page.evaluate('physicsReview.renderer().calls')>=3
            # A real pointer click on a projected front vertex must inspect an actual face.
            positions=np.asarray(page.evaluate('physicsReview.state().positions')).reshape(-1,3)
            candidates=np.flatnonzero((abs(positions[:,0])<.08)&(positions[:,1]>1.15)&(positions[:,1]<1.35))
            candidate=int(candidates[np.argmax(positions[candidates,2])]);point=page.evaluate('(v)=>physicsReview.projectPoint(v)',candidate)
            page.mouse.click(point['x'],point['y']);assert page.evaluate('physicsReview.info().selectedFace')>=0
            assert page.locator('#uv-preview polygon').count()==1
            receipt['checks']['bodyWireframeAndActualFacePointerInspector']='PASS'
            page.locator('#wire').uncheck()
            for speed in ['.25','2']:
                page.locator('#timeline').focus();page.keyboard.press('Home');page.locator('#speed').select_option(speed)
                page.locator('#play').click();page.wait_for_function('physicsReview.info().index>0',timeout=10000)
                page.wait_for_function('physicsReview.info().playing===false',timeout=15000)
                assert page.evaluate('physicsReview.info().index')==len(recording['frames'])-1
            receipt['checks']['quarterAndDoubleSpeedPlaybackWithoutIntegration']='PASS'
            page.locator('#timeline').focus();page.keyboard.press('Home');page.keyboard.press('ArrowRight')
            page.locator('[data-mode="fold"]').click();expect_state(page,recording)
            for button,name in [('download-record','actual-record.json'),('download-obj','actual-cloth.obj'),('download-html','saved.html')]:
                with page.expect_download() as pending:page.locator('#'+button).click()
                pending.value.save_as(args.output/name)
            downloaded=json.loads((args.output/'actual-record.json').read_text())
            assert downloaded['input']==source;assert downloaded['recording']==recording
            obj=(args.output/'actual-cloth.obj').read_text().splitlines();vertices=np.array([[float(v) for v in line[2:].split()] for line in obj if line.startswith('v ')])
            assert np.array_equal(vertices,unpack(recording['frames'][1]['positions'],3))
            assert sum(line.startswith('f ') for line in obj)==len(source['triangles'])
            receipt['checks']['realJSONAndOBJDownloadsReopened']='PASS'
            offline=browser.new_context(viewport={'width':1440,'height':1080},accept_downloads=True,offline=True);saved_page=offline.new_page()
            saved_page.on('pageerror',lambda e:receipt['page_errors'].append('offline: '+str(e)))
            offline_requests=[];saved_page.on('request',lambda r:offline_requests.append(r.url))
            # This managed Chromium blocks file:// by administrator policy. Keep
            # that limitation; independently render the actual downloaded bytes
            # with network disabled, as the repository's cloth verifier does.
            receipt['file_url_navigation']='BLOCKED by administrator policy; no policy changes attempted.'
            saved_page.set_content((args.output/'saved.html').read_text(),wait_until='load',timeout=90000);saved_page.wait_for_function('Boolean(window.physicsReview)',timeout=90000)
            assert saved_page.evaluate('physicsReview.info().index')==1;assert saved_page.evaluate('physicsReview.info().mode')=='fold';expect_state(saved_page,recording)
            saved_page.locator('#next').click();expect_state(saved_page,recording)
            with saved_page.expect_download() as pending:saved_page.locator('#download-html').click()
            pending.value.save_as(args.output/'recursive.html')
            saved_page=offline.new_page();saved_page.on('pageerror',lambda e:receipt['page_errors'].append('recursive: '+str(e)))
            saved_page.on('request',lambda r:offline_requests.append(r.url))
            saved_page.set_content((args.output/'recursive.html').read_text(),wait_until='load',timeout=90000);saved_page.wait_for_function('Boolean(window.physicsReview)',timeout=90000)
            assert saved_page.evaluate('physicsReview.info().index')==2;expect_state(saved_page,recording);assert saved_page.locator('canvas').count()==1
            assert (args.output/'recursive.html').stat().st_size<(args.output/'saved.html').stat().st_size*1.01
            assert not offline_requests,offline_requests
            saved_page.locator('#view-2d').click();assert saved_page.locator('#pattern-svg-host svg').count()==1
            saved_page.locator('#open-spec').click()
            offline_package=saved_page.evaluate('physicsReview.sources()')
            assert saved_page.locator('#spec-content').text_content()==base64.b64decode(offline_package['files']['yaml']['base64']).decode('utf8')
            saved_page.keyboard.press('Escape');saved_page.locator('#view-3d').click()
            receipt['checks']['offlineSavedFrameFieldsAndRecursiveHTMLReopen']='PASS'
            page.set_viewport_size({'width':390,'height':844});page.locator('#timeline').scroll_into_view_if_needed()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#prev').click();expect_state(page,recording)
            for selector in ['#play','#prev','#next','#view-2d','#view-3d','#open-spec','#download-spec','#download-dxf']:
                box=page.locator(selector).bounding_box();assert box and box['width']>=44 and box['height']>=44,selector
            page.locator('#open-spec').click();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.keyboard.press('Escape')
            page.screenshot(path=str(args.output/'mobile.png'),full_page=True)
            receipt['checks']['mobileWithoutOverflowAndActualReplayControls']='PASS'
            receipt['garment_verdict']=downloaded['audit']['verdict']
            assert not receipt['page_errors'] and not receipt['console_errors'],receipt
            receipt['verdict']='PASS';browser.close()
    except Exception as exc:
        receipt['verdict']='FAIL';receipt['failure']=str(exc);raise
    finally:
        if server:server.shutdown();server.server_close()
        receipt['cleanup']='Owned test server and browser contexts closed.'
        (args.output/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'verdict':receipt['verdict'],'checks':len(receipt['checks']),'garment_verdict':receipt['garment_verdict']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--html',type=Path,required=True);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--browser',default='/usr/bin/chromium');p.add_argument('--base-url');run(p.parse_args())
