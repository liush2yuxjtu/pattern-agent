#!/usr/bin/env python3
"""Drive the actual inline-WASM app with Playwright, then reopen its exports.

Local: --html web/cloth-lab/index.html. Live: --base-url .../cloth-lab/.
The same assertions apply to both. No mocked solver, body or network dependency.
"""
import argparse
import colorsys
import copy
import hashlib
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import statistics
import sys
import threading
import time
import xml.etree.ElementTree as ET

import numpy as np
from playwright.sync_api import sync_playwright
import trimesh

from oracle import ROOT, tensors, verify, seam_audit
sys.path.insert(0,str(ROOT/'scripts'))
from playwright_http import new_api_context


def save_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def expect_rejection(call):
    try:call()
    except (AssertionError,ValueError,np.linalg.LinAlgError) as e:return str(e)[:300]
    raise AssertionError('Invalid negative control incorrectly accepted')


def run(args,base):
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    report={'base':base,'startedAtUnix':time.time(),'checks':{},'faults':{},'negativeControls':{},'pageErrors':[],'consoleErrors':[],'badResponses':[]}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        context=browser.new_context(viewport={'width':1440,'height':1050},accept_downloads=True)
        api=new_api_context(p,base)
        page=context.new_page()
        page.on('pageerror',lambda e:report['pageErrors'].append(str(e)))
        page.on('console',lambda m:report['consoleErrors'].append(m.text) if m.type=='error' else None)
        page.on('response',lambda r:report['badResponses'].append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        res=page.goto(base,wait_until='networkidle');assert res.status==200
        page.wait_for_function('window.clothLab?.ready',timeout=30000)
        report['source']=page.evaluate('clothLab.source')
        actual_html=api.get(base).body()
        report['htmlSha256']=hashlib.sha256(actual_html).hexdigest()
        if args.expected_html_sha:assert report['htmlSha256']==args.expected_html_sha
        if args.expected_commit:
            from urllib.parse import urljoin
            build=api.get(urljoin(base,'../build.json')).json()
            assert build['commit']==args.expected_commit,(build['commit'],args.expected_commit)
            report['deployedCommit']=build['commit']
        # One real button press must advance one actual 1/120 s physics step.
        initial=page.evaluate('clothLab.project()');initial_frame=initial['diagnostics']['frame'];initial_time=initial['diagnostics']['simulationSeconds'];save_json(out/'step-000.json',initial)
        page.screenshot(path=str(out/'step-000.png'),full_page=True)
        page.locator('#single-step').click();page.wait_for_function('(n)=>clothLab.stats().frame===n',arg=initial_frame+1)
        assert abs(page.evaluate('clothLab.stats().simulationSeconds')-initial_time-1/120)<1e-6
        page.screenshot(path=str(out/'step-001.png'),full_page=True)
        page.evaluate('clothLab.advance(59)');page.screenshot(path=str(out/'step-060.png'),full_page=True)
        page.locator('#settle').click();page.wait_for_function('(n)=>clothLab.stats().frame===n',arg=initial_frame+300,timeout=60000)
        settled=page.evaluate('clothLab.project()');save_json(out/'settled-project.json',settled)
        page.screenshot(path=str(out/'step-300-fabric.png'),full_page=True)
        (out/'desktop-snapshot.yml').write_text(page.locator('body').aria_snapshot())
        report['settled']=verify(settled,args.body_source)
        report['checks']['stepwiseSimulationAndIndependentGeometry']=True
        # Tests of the constitutive law independent of the cloth's appearance.
        mat=settled['material'];coupons=[]
        for name,u,v in [('rest',[1,0,0],[0,1,0]),('rigid-rotation',[0,1,0],[-1,0,0]),('warp-10-percent',[1.1,0,0],[0,1,0]),('weft-10-percent',[1,0,0],[0,1.1,0]),('shear',[1,0,0],[.2,1,0])]:
            observed=page.evaluate('([u,v])=>clothLab.materialProbe(u,v)',[u,v])
            expected=tensors(np.array([[0,0,0],u,v]),np.array([[0,0],[1,0],[0,1]]),np.array([[0,1,2]]),mat)[0]
            assert np.allclose(observed,expected,rtol=3e-4,atol=[2e-5,2e-5,2e-5,.15,.15,2e-5,2e-5,2e-5]),(name,observed,expected)
            coupons.append({'name':name,'observed':observed,'expected':expected.tolist()})
        report['coupons']=coupons;report['checks']['materialRestRotationStretchShear']=True
        # The actual GPU color buffer must be driven by those physical fields.
        images={}
        for mode,column,scale in [('strain',0,.12),('stress',3,15000),('contact',None,None)]:
            page.locator(f'[data-mode={mode}]').click()
            page.screenshot(path=str(out/(mode+'.png')),full_page=True)
            images[mode]=page.locator('#viewport').screenshot()
            surface=page.evaluate('clothLab.surface()');assert surface['mode']==mode
            assert np.allclose(surface['positions'],settled['positions'],atol=1e-7)
            if column is not None:
                faces=np.array(settled['triangles']).reshape(-1,3);values=np.array(settled['triangleFields']).reshape(-1,8)[:,column]
                sums=np.zeros(len(settled['positions'])//3);counts=sums.copy()
                for j in range(3):np.add.at(sums,faces[:,j],values);np.add.at(counts,faces[:,j],1)
                scalar=sums/counts/scale
                colors=[colorsys.hls_to_rgb(.61*(1-np.clip(x,0,1)),.54,.64) for x in scalar]
                assert np.max(abs(np.array(surface['colors']).reshape(-1,3)-colors))<2e-6
        assert images['strain']!=images['stress'] and images['contact']!=images['stress']
        report['checks']['physicalFieldsReachRealRenderedColors']=True
        # Actual downloadable formats, rather than just calling export functions.
        for button in ['export-svg','export-obj','export-json','export-log','save-html']:
            with page.expect_download() as event:page.locator('#'+button).click()
            event.value.save_as(str(out/event.value.suggested_filename))
        svg=ET.parse(out/'cloth-patterns.svg').getroot()
        assert svg.attrib['width']=='1420mm' and svg.attrib['height']=='705mm'
        obj=trimesh.load(out/'cloth-body-scene.obj',force='mesh',process=False)
        assert len(obj.vertices)==850+13380 and len(obj.faces)==1536+26756
        report['checks']['physicalScaleSVGAndActualSceneOBJ']=True
        # Independently query the runtime BVH near known body surfaces.
        bm=trimesh.Trimesh(np.array(settled['body']['positions']).reshape(-1,3),np.array(settled['body']['triangles']).reshape(-1,3),process=False)
        ids=np.where((bm.vertices[:,1]>.6)&(bm.vertices[:,1]<.95))[0][::73]
        points=np.concatenate([bm.vertices[ids]+bm.vertex_normals[ids]*.01,bm.vertices[ids]-bm.vertex_normals[ids]*.01])
        actual_probe=page.evaluate('(points)=>points.map(p=>clothLab.collisionProbe(p)[0])',points.tolist())
        expected_probe=-trimesh.proximity.signed_distance(bm,points)
        assert np.max(abs(np.array(actual_probe)-expected_probe))<1e-5
        report['bodyProbes']={'count':len(points),'maxSignedDistanceErrorM':float(np.max(abs(np.array(actual_probe)-expected_probe)))}
        report['checks']['runtimeBVHMatchesIndependentBodyQueries']=True
        # Rerun adversarial sewing on the actual UI. The oracle must also reject.
        page.locator('[data-mode=strain]').click()
        for fault in ['mismatch','open','reverse']:
            page.select_option('#fault',fault);page.evaluate('clothLab.advance(120)')
            data=page.evaluate('clothLab.project()');seam=seam_audit(data,np.array(data['restUV']).reshape(-1,2))
            assert page.locator('#verdict').inner_text().startswith('FAIL')
            assert seam['mismatchMm']>1 if fault=='mismatch' else seam['missing'] if fault=='open' else seam['reversed']
            report['faults'][fault]={'diagnostics':data['diagnostics'],'independentSeamAudit':seam}
            report['negativeControls'][fault]=expect_rejection(lambda d=data:verify(d,args.body_source,intersections=False))
            page.screenshot(path=str(out/('fault-'+fault+'.png')),full_page=True)
        page.select_option('#fault','good');page.evaluate('clothLab.advance(240)')
        # A real penetration, not a fake status flag. Disabled contact must fail.
        page.uncheck('#collision');page.evaluate('clothLab.injectVertex(150,[.10,.82,.08])')
        inside=page.evaluate('clothLab.project()');assert inside['diagnostics']['maxBodyPenetrationMm']>1
        report['negativeControls']['collisionDisabledActualPenetration']=expect_rejection(lambda:verify(inside,args.body_source,intersections=False))
        page.screenshot(path=str(out/'collision-disabled.png'),full_page=True)
        page.check('#collision');page.evaluate('clothLab.advance(240)')
        recovered=page.evaluate('clothLab.project()');report['collisionRecovery']=verify(recovered,args.body_source)
        save_json(out/'collision-recovered-project.json',recovered)
        page.screenshot(path=str(out/'collision-recovered.png'),full_page=True)
        report['checks']['actualPenetrationDetectedAndRecovered']=True
        # Change the actual body transform, then independently reopen both meshes.
        page.locator('#body-shift').fill('40');page.locator('#body-shift').dispatch_event('input')
        page.evaluate('clothLab.advance(240)');moved=page.evaluate('clothLab.project()');assert moved['body']['offsetX']==.04
        report['movedBody']=verify(moved,args.body_source);save_json(out/'body-moved-project.json',moved)
        page.screenshot(path=str(out/'body-moved.png'),full_page=True)
        report['checks']['movingActualBodyCollision']=True
        page.evaluate('clothLab.advance(1)');moved_next=page.evaluate('clothLab.project().positions')
        # The oracle must not bless fabricated strain/stress arrays or substitute bodies.
        bad=copy.deepcopy(settled);bad['triangleFields'][3]+=10000
        report['negativeControls']['fabricatedStress']=expect_rejection(lambda:verify(bad,args.body_source,intersections=False))
        bad=copy.deepcopy(settled);bad['body']['positions'][0]+=.01
        report['negativeControls']['substituteBody']=expect_rejection(lambda:verify(bad,args.body_source,intersections=False))
        # Parameter propagation to the actual pattern and rest mesh.
        page.locator('#width').fill('750');page.locator('#width').dispatch_event('input');page.locator('#length').fill('500');page.locator('#length').dispatch_event('input')
        changed=page.evaluate('clothLab.project()');assert changed['parameters']['bottomMm']==750 and changed['parameters']['lengthsMm']==[500,500]
        alpha=(750-420)/500;outer=420/alpha+500;assert abs(np.ptp(np.array(changed['restUV']).reshape(-1,2)[:,1])-2*outer*np.sin(alpha/2)/1000)<1e-6
        assert '420 / 750 × 500' in page.locator('#patterns').inner_html()
        report['checks']['sameParametersDrivePatternAndRestMesh']=True
        # Memory/resource counters across repeated real reset clicks.
        logs=[]
        for _ in range(10):page.locator('#reset').click();logs.append(page.evaluate('clothLab.performanceLog()'))
        assert len({l['geometries'] for l in logs})==1 and len({l['textures'] for l in logs})==1
        assert len({l['wasmMemoryBytes'] for l in logs})==1
        report['checks']['resetGPUResourcesAndWASMMemoryStable']=True
        # Restore known default via actual UI before performance and screenshots.
        page.locator('#width').fill('650');page.locator('#width').dispatch_event('input');page.locator('#length').fill('600');page.locator('#length').dispatch_event('input')
        page.locator('#body-shift').fill('0');page.locator('#body-shift').dispatch_event('input');page.evaluate('clothLab.advance(240)');page.locator('[data-mode=fabric]').click()
        # Material-axis presets must also affect the real simulated/exported model.
        page.select_option('#material','soft');page.evaluate('clothLab.advance(240)')
        soft=page.evaluate('clothLab.project()');assert soft['material']['Eu']==45000
        report['softMaterial']=verify(soft,args.body_source)
        page.screenshot(path=str(out/'soft-material.png'),full_page=True)
        page.select_option('#material','woven');page.evaluate('clothLab.advance(240)')
        report['checks']['bothMaterialPresetsAndVerticalGrain']=True
        page.evaluate('clothLab.clearPerformance()');page.locator('#run').click();page.wait_for_timeout(5000);page.locator('#run').click()
        before=page.evaluate('clothLab.stats().frame');page.wait_for_timeout(250);assert page.evaluate('clothLab.stats().frame')==before
        log=page.evaluate('clothLab.performanceLog()');times=log['frameTimesMs'][2:];assert len(times)>=10
        report['performance']={**log,'medianFrameMs':statistics.median(times),'p95FrameMs':float(np.percentile(times,95)),'sampleFrames':len(times)}
        report['checks']['realRunPauseAndPerformanceSample']=True
        page.screenshot(path=str(out/'performance.png'),full_page=True)
        for angle in ['front','side','back']:
            page.locator(f'[data-camera={angle}]').click();page.screenshot(path=str(out/(angle+'.png')),full_page=True)
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(500);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(out/'mobile.png'),full_page=True);(out/'mobile-snapshot.yml').write_text(page.locator('body').aria_snapshot())
        report['checks']['mobileWithoutOverflow']=True
        # Reopen the actual downloaded snapshot, fully offline, and compare arrays.
        saved=json.loads((out/'cloth-project.json').read_text())
        offline=browser.new_context(offline=True,viewport={'width':1280,'height':1000});op=offline.new_page();requests=[];offline_errors=[]
        op.on('request',lambda r:requests.append(r.url));op.on('pageerror',lambda e:offline_errors.append(str(e)))
        op.set_content((out/'cloth-lab-snapshot.html').read_text(),wait_until='load');op.wait_for_function('window.clothLab?.ready')
        restored=op.evaluate('clothLab.project()');assert np.array_equal(saved['positions'],restored['positions']) and np.array_equal(saved['previous'],restored['previous'])
        op.screenshot(path=str(out/'offline-restored.png'),full_page=True)
        assert not requests and not offline_errors,(requests,offline_errors)
        # Restored velocity/clock state must reproduce the next time step too.
        reference=offline.new_page();reference.set_content(actual_html.decode(),wait_until='load');reference.wait_for_function('window.clothLab?.ready');reference.evaluate('(s)=>clothLab.restore(s)',saved)
        op.evaluate('clothLab.advance(1)');reference.evaluate('clothLab.advance(1)');assert np.array_equal(op.evaluate('clothLab.project().positions'),reference.evaluate('clothLab.project().positions'))
        # The reopened snapshot must save its NEW state, not its original embedded one.
        second_state=op.evaluate('clothLab.project()')
        with op.expect_download() as second:op.locator('#save-html').click()
        second.value.save_as(str(out/'second-generation-snapshot.html'))
        third=offline.new_page();third.set_content((out/'second-generation-snapshot.html').read_text(),wait_until='load');third.wait_for_function('window.clothLab?.ready')
        assert np.array_equal(second_state['positions'],third.evaluate('clothLab.project().positions'))
        third.close()
        op.evaluate('(s)=>clothLab.restore(s)',moved);op.evaluate('clothLab.advance(1)')
        assert np.array_equal(moved_next,op.evaluate('clothLab.project().positions'))
        report['checks']['recursiveSaveAndMovedPinContinuation']=True
        report['checks']['offlineSnapshotExactStateAndContinuation']=True
        # Controlled performance experiment: same solver, state, renderer and steps.
        # Only the distance-bound broad phase changes; final vertex bits must match.
        op.evaluate('(s)=>clothLab.restore(s)',saved);reference.evaluate('(s)=>clothLab.restore(s)',saved)
        op.evaluate('clothLab.setCollisionCache(true)');reference.evaluate('clothLab.setCollisionCache(false)')
        cached=op.evaluate('clothLab.advance(20)');uncached=reference.evaluate('clothLab.advance(20)')
        assert np.array_equal(op.evaluate('clothLab.project().positions'),reference.evaluate('clothLab.project().positions'))
        report['cacheAB']={'cachedStepMs':cached['stepMs'],'uncachedStepMs':uncached['stepMs'],'steps':20,'positionArraysBitIdentical':True}
        report['checks']['collisionBroadPhaseMatchesFullQueriesBitForBit']=True
        report['offline']={'requests':requests,'errors':offline_errors,'snapshotBytes':(out/'cloth-lab-snapshot.html').stat().st_size}
        assert not report['pageErrors'] and not report['consoleErrors'] and not report['badResponses'],report
        api.dispose()
        browser.close()
    report['verdict']='PASS';report['finishedAtUnix']=time.time();report['scope']='WASM runtime, stated synthetic tensor model, sewing and discrete actual-body collision. Physical fit/calibration NOT_RUN.'
    save_json(out/'receipt.json',report)
    print(json.dumps({'verdict':report['verdict'],'checks':report['checks'],'settled':report['settled'],'performance':{k:report['performance'][k] for k in ['medianFrameMs','p95FrameMs','sampleFrames','rendererClass','stepMs'] if k in report['performance']}},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url')
    parser.add_argument('--html',type=Path,default=ROOT/'web/cloth-lab/index.html')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser',default='/usr/bin/chromium')
    parser.add_argument('--body-source',type=Path,default=ROOT/'web/human-studio/assets/human.json')
    parser.add_argument('--expected-html-sha')
    parser.add_argument('--expected-commit')
    args=parser.parse_args()
    if args.base_url:run(args,args.base_url)
    else:
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self,*a,**k):super().__init__(*a,directory=str(args.html.parent),**k)
            def log_message(self,*a):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:run(args,f'http://127.0.0.1:{server.server_port}/')
        finally:server.shutdown();server.server_close();thread.join()
