#!/usr/bin/env python3
"""Exercise the real static site at its project subpath or a live Pages URL."""
import argparse
from contextlib import contextmanager
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urljoin,urlsplit

from playwright.sync_api import sync_playwright
from playwright_http import new_api_context

ROOT=Path(__file__).resolve().parents[1]


@contextmanager
def local_site(directory):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(directory),**kwargs)
        def log_message(self,*args): pass
        def do_GET(self):
            if not self.path.startswith('/pattern-agent/'):
                self.send_error(404); return
            self.path=self.path[len('/pattern-agent'):]
            super().do_GET()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try: yield f'http://127.0.0.1:{server.server_port}/pattern-agent/'
    finally: server.shutdown(); server.server_close(); thread.join()


def verify(base,output,expected_commit=None,executable='/usr/bin/chromium'):
    base=base.rstrip('/')+'/'
    output.mkdir(parents=True,exist_ok=True)
    errors=[]; failed=[]; bad_responses=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
        api=None
        try:
            context=browser.new_context(viewport={'width':1440,'height':1100},accept_downloads=True)
            api=new_api_context(pw,base)
            page=context.new_page()
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('console',lambda message:errors.append(message.text) if message.type=='error' else None)
            page.on('requestfailed',lambda req:failed.append({'url':req.url,'failure':req.failure}) if req.failure!='net::ERR_ABORTED' else None)
            page.on('response',lambda res:bad_responses.append({'url':res.url,'status':res.status}) if res.status>=400 else None)
            response=page.goto(base,wait_until='networkidle',timeout=60000)
            assert response.status==200
            assert page.title()=='Pattern Agent · 基础直身裙纸样'
            page.locator('#pattern-preview').wait_for()
            assert page.locator('#pattern-preview').evaluate('(img)=>img.complete && img.naturalWidth>0')
            metadata_response=api.get(urljoin(base,'build.json'))
            assert metadata_response.status==200
            metadata=metadata_response.json()
            if expected_commit: assert metadata['commit']==expected_commit,(metadata['commit'],expected_commit)
            page.wait_for_function("document.querySelector('#build-id').textContent.includes('·')")
            page.locator('#open-preview').click()
            assert page.locator('#preview-dialog').is_visible()
            page.keyboard.press('Escape')
            assert not page.locator('#preview-dialog').is_visible()
            page.locator('summary').click()
            assert page.locator('details').evaluate('(node)=>node.open')
            assert '后中 1.5 cm' in page.locator('details').inner_text()
            page.locator('summary').click()
            assert not page.locator('details').evaluate('(node)=>node.open')
            downloads=[]
            for link in page.locator('.download-card').all():
                url=urljoin(base,link.get_attribute('href'))
                relative=url[len(base):]
                with page.expect_download() as event: link.click()
                download=event.value
                assert download.failure() is None,download.failure()
                target=output/download.suggested_filename
                download.save_as(target)
                digest=hashlib.sha256(target.read_bytes()).hexdigest()
                assert digest==metadata['files'][relative],relative
                downloads.append({'url':url,'file':download.suggested_filename,'sha256':digest,'bytes':target.stat().st_size})
            page.screenshot(path=str(output/'desktop.png'),full_page=True)
            page.set_viewport_size({'width':375,'height':812})
            page.goto(base,wait_until='networkidle')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Mobile horizontal overflow'
            page.locator('#open-preview').click()
            page.locator('#close-preview').click()
            assert not page.locator('#preview-dialog').is_visible()
            page.screenshot(path=str(output/'mobile.png'),full_page=True)
            # Existing workbench remains a real callable surface after publication.
            page.set_viewport_size({'width':1440,'height':1000})
            page.goto(urljoin(base,'pattern-review/'),wait_until='networkidle')
            assert page.locator('#svg g[data-piece]').count()==4
            old_view=page.locator('#svg').get_attribute('viewBox')
            page.locator('#plus').click()
            assert page.locator('#svg').get_attribute('viewBox')!=old_view
            with page.expect_download() as event: page.locator('#exportSloper').click()
            exported=output/'existing-workbench-export.sloper'
            event.value.save_as(exported)
            project=json.loads(exported.read_text())
            assert project['format']=='pattern' and project['units']=='mm'
            assert sum(o['type']=='piece' for o in project['objects'])==4
            dialogs=[]
            page.on('dialog',lambda dialog:(dialogs.append(dialog.message),dialog.accept()))
            native_point=next(o for o in project['objects'] if o['type']=='freePoint')
            native_point['x']=str(float(native_point['x'])+1.2)
            edited=output/'existing-workbench-edited.sloper'
            edited.write_text(json.dumps(project))
            page.locator('#file').set_input_files(edited)
            page.wait_for_function("document.querySelector('#edits').textContent==='1'")
            assert not page.locator('#cut').is_checked()
            assert page.locator('#svg polyline[fill="none"]').count()==4
            assert any('旧裁剪线已隐藏' in text for text in dialogs)
            # Advanced native skirt projects must be explicitly rejected by this static T-shirt importer.
            with page.expect_download() as event: page.locator('#saveJSON').click()
            reviewed=output/'existing-workbench-review.json'
            event.value.save_as(reviewed)
            assert json.loads(reviewed.read_text())['release']=='DRAFT_NOT_APPROVED'
            advanced_response=api.get(urljoin(base,'patterns/straight-skirt-eu40/straight-skirt-eu40.sloper'))
            assert advanced_response.status==200
            advanced=output/'advanced-skirt.sloper'
            advanced.write_bytes(advanced_response.body())
            dialog_count=len(dialogs)
            page.locator('#file').set_input_files(advanced)
            page.wait_for_timeout(150)
            assert len(dialogs)>dialog_count and dialogs[-1].startswith('导入失败：')
            assert page.locator('#svg g[data-piece]').count()==4
            page.screenshot(path=str(output/'existing-workbench.png'),full_page=True)
            # Nearby edge case: a nonexistent download returns 404, not an HTML SPA fallback.
            missing=api.get(urljoin(base,'patterns/no-such-pattern.pdf'))
            assert missing.status==404
            assert not errors,{'console':errors,'http':bad_responses,'failed':failed}
            assert not failed,failed
            assert not bad_responses,bad_responses
            report={'verdict':'PASS','base_url':base,'commit':metadata['commit'],
                    'source_sha256':metadata['source_sha256'],'downloads':downloads,
                    'checks':['desktop render','modal open and Escape close','print details toggle',
                              'four real downloads match deployed hashes','375 px mobile without overflow',
                              'mobile modal close','existing workbench zoom and native export',
                              'native edit/import hides invalidated cutlines','review export stays unapproved',
                              'unsupported parametric import is explicitly rejected',
                              'missing download returns 404'],
                    'page_errors':errors,'failed_requests':failed,'asset_http_errors':bad_responses}
            (output/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(report,ensure_ascii=False,indent=2))
            return report
        finally:
            if api is not None: api.dispose()
            browser.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url')
    p.add_argument('--directory',type=Path,default=ROOT/'dist')
    p.add_argument('--output',type=Path,default=ROOT/'work/verify-pages')
    p.add_argument('--expected-commit')
    p.add_argument('--browser',default='/usr/bin/chromium')
    args=p.parse_args()
    if args.base_url: verify(args.base_url,args.output,args.expected_commit,args.browser)
    else:
        with local_site(args.directory) as base: verify(base,args.output,args.expected_commit,args.browser)
