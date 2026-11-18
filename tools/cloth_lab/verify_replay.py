#!/usr/bin/env python3
"""Exercise real trajectory controls; independently reopen EVERY stable frame.

No simulation fixtures. Instrument the real WASM step export only to count calls.
The numerical oracle never imports the runtime or trajectory codec.
"""
import argparse
import base64
import colorsys
import copy
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import statistics
import threading
import time
from urllib.parse import urljoin

import numpy as np
from playwright.sync_api import sync_playwright

from verify_browser import ROOT, new_api_context, save_json, expect_rejection
from oracle import verify

INSTRUMENT = '''(() => {
  const original=WebAssembly.instantiate;
  window.actualWasmSteps=0;
  WebAssembly.instantiate=async function(...args){
    const result=await original.apply(this,args), e=result.instance.exports;
    return {...result,instance:{exports:{...e,step:(n,w)=>{window.actualWasmSteps+=n;return e.step(n,w);}}}};
  };
})();'''


def state(page):
    return page.evaluate('clothLab.project(false)')


def counters(page):
    return page.evaluate('({actual:actualWasmSteps,reported:clothLab.replay.info().integratedSteps})')


def compare_frame(project, frame):
    raw=base64.b64decode(frame['state'],validate=True)
    values=np.frombuffer(raw,dtype='<f4')
    assert len(values)==8500
    for key,a,b in [('positions',0,2550),('previous',2550,5100),('pinPositions',5100,7650),('contactFlags',7650,8500)]:
        assert np.array_equal(values[a:b],project[key]),key
    assert project['parameters']==frame['parameters']
    assert project['diagnostics']['frame']==frame['frame']
    assert project['diagnostics']['simulationSeconds']==frame['time']
    assert project['body']['offsetX']==frame['parameters']['bodyOffsetMm']/1000


def colors(page, project, column, scale):
    surface=page.evaluate('clothLab.surface()')
    assert np.array_equal(surface['positions'],project['positions'])
    faces=np.array(project['triangles']).reshape(-1,3)
    values=np.array(project['triangleFields']).reshape(-1,8)[:,column]
    sums=np.zeros(850);counts=np.zeros(850)
    for j in range(3):
        np.add.at(sums,faces[:,j],values);np.add.at(counts,faces[:,j],1)
    expected=[colorsys.hls_to_rgb(.61*(1-np.clip(v,0,1)),.54,.64) for v in sums/counts/scale]
    assert np.max(abs(np.array(surface['colors']).reshape(-1,3)-expected))<2e-6


def run(args,base):
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    report={'url':base,'startedAtUnix':time.time(),'checks':{},'pageErrors':[],'consoleErrors':[],
            'badResponses':[],'browserPath':'User-requested repository Playwright; Browser plugin not available.',
            'scope':'Recorded discrete states, seam topology, actual MakeHuman collision and synthetic tensor fields; physical fit NOT_RUN.'}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        context=browser.new_context(viewport={'width':1440,'height':1180},accept_downloads=True)
        context.add_init_script(INSTRUMENT)
        page=context.new_page()
        page.on('pageerror',lambda e:report['pageErrors'].append(str(e)))
        page.on('console',lambda m:report['consoleErrors'].append(m.text) if m.type=='error' else None)
        page.on('response',lambda r:report['badResponses'].append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        api=new_api_context(p,base)
        html=api.get(base);assert html.status==200
        report['htmlSha256']=hashlib.sha256(html.body()).hexdigest()
        if args.expected_html_sha:assert report['htmlSha256']==args.expected_html_sha
        if args.expected_commit:
            build=api.get(urljoin(base,'../build.json')).json()
            assert build['commit']==args.expected_commit
            report['deployedCommit']=build['commit']
        assert page.goto(base,wait_until='networkidle').status==200
        page.wait_for_function('clothLab?.ready')
        assert page.title()=='Pattern Agent · WASM 布料实验室'
        assert page.locator('h1').inner_text() and page.locator('#replay-status').is_visible()
        report['source']=page.evaluate('clothLab.source')
        embedded=json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>',html.text(),re.S).group(1))
        assert report['source']=={'fingerprint':embedded['buildFingerprint'],'wasmSha256':embedded['wasmSha256'],'bodySourceSha256':embedded['body']['sourceSha256']}
        page.evaluate('clothLab.advance(300)')
        page.locator('#record-start').click()
        before=counters(page)
        page.evaluate('clothLab.advance(60)')
        page.locator('#record-stop').click()
        after=counters(page)
        assert after['actual']-before['actual']==after['reported']-before['reported']==60
        trajectory=page.evaluate('clothLab.replay.export()')
        assert len(trajectory['frames'])==61
        assert [f['frame'] for f in trajectory['frames']]==list(range(300,361))
        assert all(abs((b['time']-a['time'])-1/120)<3e-7 for a,b in zip(trajectory['frames'],trajectory['frames'][1:]))
        report['checks']['oneRecordedStatePerRealWASMStep']=True
        page.screenshot(path=str(out/'recorded.png'),full_page=True)
        stable=page.evaluate('clothLab.project()')
        save_json(out/'actual-recording.json',stable)
        # Every saved state must seek exactly, without a WASM integration call.
        all_frames=[];baseline=counters(page)
        page.locator('[data-mode=stress]').click()
        for i,f in enumerate(trajectory['frames']):
            page.locator('#replay-timeline').fill(str(i));page.locator('#replay-timeline').dispatch_event('input')
            saved=state(page);compare_frame(saved,f)
            result=verify(saved,args.body_source)
            all_frames.append({'index':i,'physicsFrame':f['frame'],'time':f['time'],**result})
            if i in (0,30,60):
                save_json(out/'frame-oracles.json',all_frames)
                print(f'Independent recorded-frame oracles: {i+1}/61',flush=True)
                colors(page,saved,3,15000)
                page.screenshot(path=str(out/f'stress-frame-{i:03}.png'),full_page=True)
        assert counters(page)==baseline
        report['allFrames']=all_frames
        report['checks']['all61FramesIndependentSeamsBodyIntersectionsAndTensors']=True
        report['checks']['seekExactPositionsHistoryPinsContactsClockAndNoIntegration']=True
        report['checks']['recordedStressDrivesActualGPUColors']=True
        page.locator('#replay-timeline').fill('31');page.locator('#replay-timeline').dispatch_event('input')
        page.locator('#replay-timeline').press('ArrowLeft')
        assert page.evaluate('clothLab.replay.info().cursor')==30
        page.locator('#replay-prev').click();assert page.evaluate('clothLab.replay.info().cursor')==29
        page.locator('#replay-next').click();assert page.evaluate('clothLab.replay.info().cursor')==30
        page.locator('[data-mode=strain]').click();selected=state(page);colors(page,selected,0,.12)
        page.screenshot(path=str(out/'rewind-strain.png'),full_page=True)
        report['checks']['keyboardTimelinePreviousNextAndStrainColors']=True
        # Download the visible selection and whole trajectory, not a synthetic file.
        for button,filename in [('export-replay','downloaded-replay.json'),('save-html','downloaded-replay.html')]:
            with page.expect_download() as event:page.locator('#'+button).click()
            event.value.save_as(str(out/filename))
        exported=json.loads((out/'downloaded-replay.json').read_text())
        assert len(exported['replay']['frames'])==61 and exported['replay']['cursor']==30
        assert exported['positions']==selected['positions']
        # Controls must advance saved time at the selected rate, with zero integration.
        durations={};automation_durations={}
        for speed in ['0.25','0.5','1','2']:
            page.locator('#replay-first').click();page.select_option('#replay-speed',speed)
            page.evaluate('''() => {window.playbackProbe=new Promise(resolve=>{
                document.querySelector('#replay-play').addEventListener('click',()=>{
                    const start=performance.now();
                    const observe=()=>{if(!clothLab.replay.info().playing)resolve((performance.now()-start)/1000);else requestAnimationFrame(observe);};
                    requestAnimationFrame(observe);
                },{once:true,capture:true});
            });}''')
            clock=time.monotonic();page.locator('#replay-play').click()
            page.wait_for_function('!clothLab.replay.info().playing',timeout=10000)
            automation_durations[speed]=time.monotonic()-clock
            elapsed=page.evaluate('playbackProbe');durations[speed]=elapsed
            assert abs(elapsed-.5/float(speed))<.15,(speed,elapsed)
            assert page.evaluate('clothLab.replay.info().cursor')==60
            compare_frame(state(page),trajectory['frames'][-1])
        assert durations['0.25']/durations['2']>2.5,durations
        assert counters(page)==baseline
        report['playbackWallSeconds']=durations
        report['playbackIncludingAutomationSeconds']=automation_durations
        report['checks']['quarterAndDoubleSpeedPlaybackWithoutIntegration']=True
        page.locator('#replay-first').click();page.select_option('#replay-speed','0.25');page.locator('#replay-play').click()
        page.wait_for_timeout(120);page.locator('#replay-play').click()
        paused=page.evaluate('clothLab.replay.info().cursor');page.wait_for_timeout(150)
        assert page.evaluate('clothLab.replay.info().cursor')==paused
        assert counters(page)==baseline
        report['checks']['pauseFreezesRecordedFrame']=True
        # Offline single HTML must retain the timeline and continue from a past state.
        offline=browser.new_context(offline=True,viewport={'width':1280,'height':1180},accept_downloads=True)
        offline.add_init_script(INSTRUMENT)
        op=offline.new_page();requests=[];offline_errors=[]
        op.on('request',lambda r:requests.append(r.url));op.on('pageerror',lambda e:offline_errors.append(str(e)))
        op.set_content((out/'downloaded-replay.html').read_text(),wait_until='load');op.wait_for_function('clothLab?.ready')
        assert op.evaluate('clothLab.replay.info().frames')==61
        assert op.evaluate('clothLab.replay.info().cursor')==30
        compare_frame(state(op),trajectory['frames'][30])
        op.locator('#replay-last').click();compare_frame(state(op),trajectory['frames'][-1])
        op.locator('#replay-first').click();compare_frame(state(op),trajectory['frames'][0])
        assert counters(op)=={'actual':0,'reported':0}
        op.screenshot(path=str(out/'offline-timeline.png'),full_page=True)
        op.evaluate('clothLab.replay.seek(20)');op.locator('#single-step').click()
        op.wait_for_function('clothLab.stats().frame===321')
        compare_frame(state(op),trajectory['frames'][21])
        assert counters(op)=={'actual':1,'reported':1}
        assert not op.evaluate('clothLab.replay.info().atRecordedState')
        with op.expect_download() as event:op.locator('#save-html').click()
        event.value.save_as(str(out/'second-generation-replay.html'))
        third=offline.new_page();third.set_content((out/'second-generation-replay.html').read_text(),wait_until='load');third.wait_for_function('clothLab?.ready')
        assert third.evaluate('clothLab.replay.info().frames')==61
        compare_frame(state(third),trajectory['frames'][21]);third.close()
        assert not requests and not offline_errors
        report['offline']={'requests':requests,'errors':offline_errors,'htmlBytes':(out/'downloaded-replay.html').stat().st_size}
        report['checks']['offlineTimelineRecursiveHTMLAndExactResumption']=True
        # Reopen the actual JSON through the file input, then reject malformed imports atomically.
        page.locator('#import-replay').set_input_files(str(out/'downloaded-replay.json'))
        page.wait_for_function("!document.querySelector('#import-replay').value")
        page.wait_for_function('clothLab.replay.info().cursor===30')
        compare_frame(state(page),trajectory['frames'][30])
        for name,edit in [
            ('wrong-source',lambda d:d['replay'].update(fingerprint='wrong')),
            ('over-cap',lambda d:d['replay'].update(frames=[{}]*1202)),
            ('invalid-buffer',lambda d:d['replay']['frames'][0].update(state='AAAA')),
            ('invalid-parameters',lambda d:d['replay']['frames'][0]['parameters'].update(bodyOffsetMm=10000)),
            ('selected-state-mismatch',lambda d:d['positions'].__setitem__(0,d['positions'][0]+.01))]:
            invalid=copy.deepcopy(exported);edit(invalid)
            path=out/(name+'.json');save_json(path,invalid)
            previous=state(page);prior=counters(page)
            page.locator('#import-replay').set_input_files(str(path))
            page.wait_for_function("!document.querySelector('#import-replay').value")
            page.wait_for_function("document.querySelector('#replay-note').textContent.startsWith('导入失败')")
            assert state(page)['positions']==previous['positions'] and counters(page)==prior
        report['checks']['actualJSONImportAndAtomicMalformedRecordingRejection']=True
        # Capture a moved body event, force real penetration, and preserve the failure in replay.
        page.evaluate('clothLab.restore({...clothLab.project(false),replay:undefined})')
        page.locator('#record-start').click()
        page.locator('#body-shift').fill('40');page.locator('#body-shift').dispatch_event('input')
        page.locator('#collision').uncheck()
        page.evaluate('clothLab.injectVertex(150,[.14,.82,.08])')
        bad_index=page.evaluate('clothLab.replay.info().cursor')
        bad=state(page)
        assert bad['diagnostics']['maxBodyPenetrationMm']>1
        rejected=expect_rejection(lambda:verify(bad,args.body_source))
        page.locator('#collision').check();page.evaluate('clothLab.advance(240)');page.locator('#record-stop').click()
        moved=page.evaluate('clothLab.project()');report['movedRecovery']=verify(moved,args.body_source)
        moved_frames=moved['replay']['frames'];baseline=counters(page)
        page.evaluate('(i)=>clothLab.replay.seek(i)',bad_index)
        compare_frame(state(page),moved_frames[bad_index])
        assert 'FAIL' in page.locator('#verdict').inner_text()
        report['replayedPenetrationRejection']=expect_rejection(lambda:verify(state(page),args.body_source))
        page.locator('[data-mode=contact]').click();page.screenshot(path=str(out/'replayed-penetration-fail.png'),full_page=True)
        page.locator('#replay-first').click();compare_frame(state(page),moved_frames[0])
        assert page.locator('#body-shift').input_value()=='0'
        page.locator('#replay-last').click();compare_frame(state(page),moved_frames[-1])
        assert page.locator('#body-shift').input_value()=='40'
        report['replayedMovedRecovery']=verify(state(page),args.body_source)
        assert counters(page)==baseline
        page.screenshot(path=str(out/'replayed-moved-recovery.png'),full_page=True)
        save_json(out/'moved-and-negative-recording.json',moved)
        # Resume exactly across changed body transform/pins as well.
        page.evaluate('(i)=>clothLab.replay.seek(i)',len(moved_frames)-2);page.evaluate('clothLab.advance(1)')
        compare_frame(state(page),moved_frames[-1])
        report['checks']['bodyTransformPinsCollisionSwitchAndRealFailedFrameReplayed']=True
        report['checks']['movedBodyExactNextStepContinuation']=True
        # Rejected sewing topology must remain rejected inside the recorded timeline.
        report['seamFaults']={}
        for fault in ['mismatch','open','reverse']:
            page.select_option('#fault',fault)
            assert page.evaluate('clothLab.replay.info().frames')==0
            page.locator('#record-start').click();page.locator('#single-step').click()
            page.wait_for_function('clothLab.stats().frame===1');page.locator('#record-stop').click()
            page.locator('#replay-first').click()
            assert 'FAIL' in page.locator('#verdict').inner_text()
            report['seamFaults'][fault]=expect_rejection(lambda:verify(state(page),args.body_source))
        page.screenshot(path=str(out/'replayed-seam-fail.png'),full_page=True)
        report['checks']['sewingFaultsRemainFailuresAndTopologyEditsClearRecording']=True
        # Real bounded recording, not an allocation-only test: integrate beyond the cap.
        page.select_option('#fault','good');page.locator('#body-shift').fill('0');page.locator('#body-shift').dispatch_event('input')
        page.evaluate('clothLab.advance(300)');page.locator('#record-start').click()
        page.locator('#wind').check()  # One zero-time event makes the cap fall inside a batch.
        before=counters(page);page.evaluate('clothLab.advance(1200)')
        info=page.evaluate('clothLab.replay.info()');after=counters(page)
        assert info['frames']==1201 and not info['recording'] and not info['atRecordedState']
        assert info['bytes']==1201*8500*4
        assert after['actual']-before['actual']==1200
        assert '上限' in page.locator('#replay-note').inner_text()
        page.locator('#replay-first').click();page.locator('#replay-last').click()
        report['boundedRecording']=page.evaluate('clothLab.replay.info()')
        report['checks']['actual1201FrameCapPreservesDataWithoutUnboundedGrowth']=True
        report['performance']=page.evaluate('clothLab.performanceLog()')
        for name in ['captureTimesMs','seekTimesMs','playbackTimesMs']:
            values=report['performance']['replay'][name]
            report[name]={'samples':len(values),'median':statistics.median(values),'p95':float(np.percentile(values,95))}
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(out/'mobile-replay.png'),full_page=True)
        (out/'mobile-snapshot.yml').write_text(page.locator('body').aria_snapshot())
        report['checks']['mobileReplayControlsWithoutOverflow']=True
        assert not report['pageErrors'] and not report['consoleErrors'] and not report['badResponses']
        report['checks']['identityMeaningfulPageAndHealthyConsoleNetwork']=True
        api.dispose();browser.close()
    report.update(verdict='PASS',finishedAtUnix=time.time())
    save_json(out/'receipt.json',report)
    print(json.dumps({'verdict':report['verdict'],'checks':report['checks'],'allFrames':len(all_frames),
                      'maxRecordedSeamGapMm':max(f['maxSeamGapMm'] for f in all_frames),
                      'maxRecordedBodyPenetrationMm':max(f['maxBodyPenetrationMm'] for f in all_frames),
                      'maxRecordedStrainPercent':max(f['maxPrincipalStrainPercent'] for f in all_frames),
                      'timings':{k:report[k] for k in ['captureTimesMs','seekTimesMs','playbackTimesMs']}},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url')
    parser.add_argument('--html',type=Path,default=ROOT/'web/cloth-lab/index.html')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser',default='/usr/bin/chromium')
    parser.add_argument('--body-source',type=Path,default=ROOT/'web/human-studio/assets/human.json')
    parser.add_argument('--expected-html-sha');parser.add_argument('--expected-commit')
    args=parser.parse_args()
    if args.base_url:run(args,args.base_url)
    else:
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self,*a,**k):super().__init__(*a,directory=str(args.html.parent),**k)
            def log_message(self,*a):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:run(args,f'http://127.0.0.1:{server.server_port}/')
        finally:server.shutdown();server.server_close();thread.join()
