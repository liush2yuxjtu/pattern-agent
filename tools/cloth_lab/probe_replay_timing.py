#!/usr/bin/env python3
"""Eight real-WebGPU playback timing runs on an actual downloaded recording."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from playwright.sync_api import sync_playwright
from browser_runtime import launch_browser, instrument_context, assert_renderer, renderer_url
from verify_replay import INSTRUMENT, counters, state, compare_frame
from verify_browser import new_api_context


def run(args):
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    raw=args.project.read_bytes();project=json.loads(raw);frames=project['replay']['frames']
    assert len(frames)==61, 'Use an actual downloaded 61-frame recording'
    assert [f['frame'] for f in frames]==list(range(frames[0]['frame'],frames[0]['frame']+61))
    # The solver clock is float32. Retain the original replay suite's per-step
    # bound rather than assuming 60 accumulated steps equal exactly 0.5 seconds.
    assert all(abs(b['time']-a['time']-1/120)<3e-7 for a,b in zip(frames,frames[1:]))
    url=renderer_url(args.base_url,'webgpu')
    report={'url':url,'sourceJsonSha256':hashlib.sha256(raw).hexdigest(),
            'thresholdSeconds':.15,'runs':[],'pageErrors':[],'consoleErrors':[],
            'recordedDurationSeconds':frames[-1]['time']-frames[0]['time'],
            'expectedNominalDurationSeconds':.5,
            'startedAtUnix':time.time(),'verdict':'RUNNING'}
    def save():
        (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    with sync_playwright() as p:
        browser=launch_browser(p,args.browser)
        context=browser.new_context(viewport={'width':1440,'height':1180},accept_downloads=True)
        instrument_context(context);context.add_init_script(INSTRUMENT)
        page=context.new_page();api=new_api_context(p,url)
        page.on('pageerror',lambda e:report['pageErrors'].append(str(e)))
        page.on('console',lambda m:report['consoleErrors'].append(m.text) if m.type=='error' else None)
        try:
            assert page.goto(url,wait_until='networkidle').status==200
            page.wait_for_function('clothLab?.ready',timeout=60000)
            report['htmlSha256']=hashlib.sha256(api.get(url).body()).hexdigest()
            assert report['htmlSha256']==args.expected_html_sha
            report['rendering']=assert_renderer(page,'webgpu')
            page.locator('#import-replay').set_input_files(args.project)
            page.wait_for_function('clothLab.replay.info().frames===61')
            baseline=counters(page);report['integrationBaseline']=baseline
            for speed in ['0.25','0.5','1','2']*2:
                page.locator('#replay-first').click();page.select_option('#replay-speed',speed)
                page.evaluate('''() => {window.playbackProbe=new Promise(resolve=>{
                    document.querySelector('#replay-play').addEventListener('click',()=>{
                        const start=performance.now();
                        const observe=()=>{if(!clothLab.replay.info().playing)resolve((performance.now()-start)/1000);else requestAnimationFrame(observe);};
                        requestAnimationFrame(observe);
                    },{once:true,capture:true});
                });}''')
                start=time.monotonic();page.locator('#replay-play').click()
                page.wait_for_function('!clothLab.replay.info().playing',timeout=10000)
                elapsed=page.evaluate('playbackProbe')
                result={'speed':speed,'expectedSeconds':.5/float(speed),'actualSeconds':elapsed,
                        'includingAutomationSeconds':time.monotonic()-start,
                        'absoluteErrorSeconds':abs(elapsed-.5/float(speed)),
                        'counters':counters(page),
                        'playbackCostsMs':page.evaluate('clothLab.replay.info().playbackTimesMs.slice(-12)')}
                report['runs'].append(result);save()
                print(speed,elapsed,flush=True)
                assert result['absoluteErrorSeconds']<.15,result
                assert counters(page)==baseline and page.evaluate('clothLab.replay.info().cursor')==60
                compare_frame(state(page),frames[-1])
            assert not report['pageErrors'] and not report['consoleErrors']
            report['finalRendering']=assert_renderer(page,'webgpu')
            report['verdict']='PASS'
            page.screenshot(path=str(out/'completed.png'),full_page=True)
        except BaseException as error:
            report['verdict']='FAIL';report['error']=str(error);raise
        finally:
            report['finishedAtUnix']=time.time();save()
            api.dispose();context.close();browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',required=True)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--expected-html-sha',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser',default='/usr/bin/chromium')
    run(parser.parse_args())
