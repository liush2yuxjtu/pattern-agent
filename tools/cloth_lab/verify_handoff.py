#!/usr/bin/env python3
"""Real JSON handoff, delayed file-read transaction and replay status checks.

Only delay File.text completion; use the actual uploaded/downloaded file bytes.
No mocked physics or restored body. Pair with the full numerical/replay suite.
"""
import argparse
import copy
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright
import numpy as np
from verify_browser import ROOT,new_api_context,save_json
from verify_replay import INSTRUMENT,state,counters,compare_frame
from oracle import verify


def run(args,base):
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    report={'url':base,'checks':{},'observations':{},'pageErrors':[],'consoleErrors':[]}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        context=browser.new_context(viewport={'width':1440,'height':1180},accept_downloads=True)
        context.add_init_script(INSTRUMENT);page=context.new_page();api=new_api_context(p,base)
        page.on('pageerror',lambda e:report['pageErrors'].append(str(e)))
        page.on('console',lambda m:report['consoleErrors'].append(m.text) if m.type=='error' else None)
        try:
            actual=api.get(base);assert actual.status==200
            report['htmlSha256']=hashlib.sha256(actual.body()).hexdigest()
            if args.expected_html_sha:assert report['htmlSha256']==args.expected_html_sha
            if args.expected_commit:
                build=api.get(urljoin(base,'../build.json')).json();assert build['commit']==args.expected_commit
                report['deployedCommit']=build['commit']
            assert page.goto(base,wait_until='networkidle').status==200
            page.wait_for_function('window.clothLab?.ready');report['source']=page.evaluate('clothLab.source')
            page.evaluate('clothLab.advance(300)');page.locator('#record-start').click();page.evaluate('clothLab.advance(10)');page.locator('#record-stop').click()
            with page.expect_download() as event:page.locator('#export-replay').click()
            event.value.save_as(str(out/'original.json'))
            original=json.loads((out/'original.json').read_text())
            reordered=copy.deepcopy(original)
            reordered['parameters']=dict(reversed(list(reordered['parameters'].items())))
            assert reordered['parameters']==original['parameters']
            save_json(out/'same-values-reordered-keys.json',reordered)
            page.locator('#body-shift').fill('40');page.locator('#body-shift').dispatch_event('input')
            page.locator('#import-replay').set_input_files(str(out/'same-values-reordered-keys.json'))
            page.wait_for_function("!document.querySelector('#import-replay').value")
            restored=state(page)
            accepted=(restored['positions']==original['positions'] and restored['parameters']==original['parameters'] and page.evaluate('clothLab.replay.info().frames')==11)
            report['checks']['sameParameterValuesIndependentOfJSONKeyOrder']=accepted
            report['observations']['reorderedImport']={'accepted':accepted,'message':page.locator('#replay-note').inner_text()}
            page.screenshot(path=str(out/'reordered-import.png'),full_page=True)
            # Restore the unmodified actual file before testing asynchronous input.
            page.locator('#import-replay').set_input_files(str(out/'original.json'))
            page.wait_for_function("!document.querySelector('#import-replay').value")
            compare_frame(state(page),original['replay']['frames'][-1])
            page.locator('#run').click();page.wait_for_function('clothLab.stats().frame>312')
            page.evaluate('''() => {const original=File.prototype.text;
                File.prototype.text=function(){File.prototype.text=original;const actual=original.call(this);
                    window.fileReadWaiting=true;return new Promise((resolve,reject)=>{
                      window.releaseFileRead=()=>{window.fileReadWaiting=false;actual.then(resolve,reject);};
                    });
                };
            }''')
            page.locator('#import-replay').set_input_files(str(out/'original.json'))
            page.wait_for_function('window.fileReadWaiting===true')
            locked={id:page.locator('#'+id).is_disabled() for id in ['width','length','material','fault','body-shift','collision','wind','record-start','run','single-step','reset','replay-timeline','import-replay']}
            before=counters(page);page.wait_for_timeout(200);after=counters(page)
            report['checks']['pendingFileReadLocksMutatingControls']=all(locked.values())
            report['checks']['pendingFileReadPausesRealWASMIntegration']=before==after
            report['observations']['pendingRead']={'locked':locked,'before':before,'after':after,'activity':page.locator('#activity').inner_text()}
            page.screenshot(path=str(out/'pending-import.png'),full_page=True)
            page.evaluate('window.releaseFileRead()')
            page.wait_for_function("!document.querySelector('#import-replay').value")
            compare_frame(state(page),original['replay']['frames'][-1])
            report['checks']['actualUploadedBytesRestoreAllRecordedState']=True
            report['independentReopenedGeometry']=verify(state(page),args.body_source)
            # A real semantic difference must still be rejected without state loss.
            invalid=copy.deepcopy(original);invalid['parameters']['wind']=not invalid['parameters']['wind']
            save_json(out/'selected-frame-parameter-mismatch.json',invalid)
            before=state(page);count=counters(page)
            page.locator('#import-replay').set_input_files(str(out/'selected-frame-parameter-mismatch.json'))
            page.wait_for_function("!document.querySelector('#import-replay').value")
            after=state(page)
            assert '导入失败' in page.locator('#replay-note').inner_text()
            for key in ['positions','previous','pinPositions','contactFlags','parameters']:assert before[key]==after[key],key
            assert count==counters(page)
            assert page.evaluate('clothLab.replay.info().frames')==11
            assert page.locator('#import-replay').is_enabled() and page.locator('#single-step').is_enabled()
            report['checks']['semanticMismatchStillRejectedAtomicallyAndControlsRecovered']=True
            page.locator('[data-mode=strain]').click();page.locator('#replay-first').click()
            expected='1 / 11';activity=page.locator('#activity').inner_text()
            report['checks']['activityDescribesDisplayedReplayFrame']=expected in activity
            report['observations']['replayActivity']=activity
            page.screenshot(path=str(out/'replay-status.png'),full_page=True)
            (out/'snapshot.yml').write_text(page.locator('body').aria_snapshot())
            report['performance']=page.evaluate('clothLab.performanceLog()')
            assert not report['pageErrors'] and not report['consoleErrors']
            assert all(report['checks'].values()),{k:v for k,v in report['checks'].items() if not v}
            report['verdict']='PASS'
        except Exception as e:
            report['verdict']='FAIL';report['error']=str(e)
            try:page.screenshot(path=str(out/'failure.png'),full_page=True)
            except Exception:pass
            raise
        finally:
            save_json(out/'receipt.json',report);api.dispose();browser.close()
    print(json.dumps({'verdict':report['verdict'],'checks':report['checks']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url');parser.add_argument('--html',type=Path,default=ROOT/'web/cloth-lab/index.html')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--browser',default='/usr/bin/chromium')
    parser.add_argument('--body-source',type=Path,default=ROOT/'web/human-studio/assets/human.json')
    parser.add_argument('--expected-html-sha');parser.add_argument('--expected-commit');args=parser.parse_args()
    if args.base_url:run(args,args.base_url)
    else:
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self,*a,**k):super().__init__(*a,directory=str(args.html.parent),**k)
            def log_message(self,*a):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:run(args,f'http://127.0.0.1:{server.server_port}/')
        finally:server.shutdown();server.server_close();thread.join()
