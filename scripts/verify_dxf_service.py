#!/usr/bin/env python3
"""Real HTTP + browser acceptance of profile-bounded, stateless conversion."""
import argparse,base64,hashlib,io,json,time,zipfile
from pathlib import Path
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

def sha(b):return hashlib.sha256(b).hexdigest()
def verify(base,out,expected=None,browser='/usr/bin/chromium'):
    base=base.rstrip('/')+'/';out.mkdir(parents=True,exist_ok=True);checks=[];errors=[];requests=[];expected_console=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=browser,headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
        try:
            c=b.new_context(viewport={'width':1440,'height':1100},accept_downloads=True)
            health=c.request.get(urljoin(base,'api/health'));assert health.status==200;health=health.json()
            if expected:assert health['source_sha256']==expected
            assert health['execution']=='synchronous_stateless' and health['physical_fit']=='NOT_RUN'
            sample=c.request.get(urljoin(base,'assets/sample.dxf'));assert sample.status==200;sample=sample.body();assert sha(sample)=='1f82b2c4ca094983657ce49fc73cf06aec24d3329a53dcc3472dd5ca2cee87f4'
            start=time.monotonic();r=c.request.post(urljoin(base,'api/preview?units=mm&format=glb'),data=sample,headers={'Content-Type':'application/dxf'},timeout=60000);assert r.status==200,r.text()[:500];model=r.body();modelhash=sha(model);elapsed=time.monotonic()-start
            assert r.headers['x-output-sha256']==modelhash;assert model[:4]==b'glTF'
            again=c.request.post(urljoin(base,'api/preview?units=mm&format=glb'),data=sample,timeout=60000);assert again.status==200;assert again.body()==model;assert again.headers['x-conversion-id']==r.headers['x-conversion-id'];checks+=['real raw-DXF HTTP conversion','repeated HTTP calls return byte-identical GLB and conversion ID']
            for query,raw,code in [('units=mm',b'bad',400),('',sample,400),('units=mm&profile=other',sample,422),('units=cm',sample,422)]:
                rr=c.request.post(urljoin(base,'api/preview?'+query),data=raw);assert rr.status==code,(rr.status,rr.text()[:300]);assert rr.json()['status']=='rejected'
            checks.append('malformed file, absent units, wrong units and unknown profile rejected')
            p=c.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.on('console',lambda m:errors.append(m.text) if m.type=='error' else None);p.on('response',lambda r:requests.append({'url':r.url,'status':r.status}) if r.status>=500 else None)
            assert p.goto(base,wait_until='networkidle').status==200
            assert p.title()=='Pattern Agent · 纸样转三维预览';p.screenshot(path=str(out/'initial-desktop.png'),full_page=True)
            p.locator('#submit').click();assert p.locator('#status').get_attribute('data-state')=='error'
            p.locator('#sample').click();p.wait_for_function('document.querySelector("#model-canvas").dataset.ready==="true"',timeout=90000);assert p.locator('#status').inner_text().startswith('转换完成')
            canvas=p.locator('#model-canvas');raw=canvas.screenshot()
            from PIL import Image,ImageChops
            im=Image.open(io.BytesIO(raw)).convert('RGB');bg=Image.new('RGB',im.size,im.getpixel((0,0)));diff=ImageChops.difference(im,bg).getbbox();assert diff and (diff[2]-diff[0])*(diff[3]-diff[1])>im.width*im.height*.1
            box=canvas.bounding_box();x=box['x']+box['width']*.5;y=box['y']+box['height']*.5;old=canvas.get_attribute('data-yaw');p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+90,y+20,steps=12);p.mouse.up();assert canvas.get_attribute('data-yaw')!=old;assert canvas.screenshot()!=raw
            old=canvas.get_attribute('data-zoom');p.mouse.wheel(0,-150);p.wait_for_timeout(80);assert old!=canvas.get_attribute('data-zoom')
            p.locator('#wireframe').check();wire=canvas.screenshot();p.locator('#wireframe').uncheck();assert wire!=canvas.screenshot();p.locator('#reset-model').click();assert float(canvas.get_attribute('data-yaw'))==-.45;checks+=['real sample selection calls conversion API and draws mesh pixels','pointer rotation, wheel zoom, wireframe and reset']
            for id,name in [('download-model','downloaded.glb'),('download-report','report.json')]:
                with p.expect_download() as event:p.locator('#'+id).click()
                d=event.value;assert d.failure() is None;d.save_as(out/name)
            assert sha((out/'downloaded.glb').read_bytes())==modelhash
            report=json.loads((out/'report.json').read_text());assert report['output_sha256']==modelhash
            with p.expect_download(timeout=60000) as event:p.locator('#download-bundle').click()
            event.value.save_as(out/'offline.zip')
            with zipfile.ZipFile(out/'offline.zip') as z:
                assert z.testzip() is None;assert z.read('model.glb')==model;html=z.read('preview.html').decode();assert '__GENERATED_GLB__' not in html and '__RENDERER_JS__' not in html
            checks.append('real model/report downloads match output hash; offline bundle contains the same generated mesh')
            p.screenshot(path=str(out/'converted-desktop.png'),full_page=True)
            # Real file picker path, not merely the preset sample button.
            p.locator('#dxf-file').set_input_files({'name':'uploaded.dxf','mimeType':'application/dxf','buffer':sample});p.locator('#units').select_option('mm');p.locator('#submit').click();p.wait_for_function('document.querySelector("#result-file").textContent==="uploaded.dxf" && document.querySelector("#model-canvas").dataset.ready==="true"',timeout=60000);checks.append('real uploaded file returns and renders the same supported model')
            assert not errors,errors
            before_rejection=len(errors)
            p.locator('#dxf-file').set_input_files({'name':'invalid.dxf','mimeType':'application/dxf','buffer':b'bad'});p.locator('#submit').click();p.wait_for_function('document.querySelector("#status").dataset.state==="error"');assert not p.locator('#result').is_visible();assert not p.locator('#model-canvas').is_visible();p.screenshot(path=str(out/'rejected-input.png'),full_page=True);checks.append('invalid upload clears stale successful model and downloads')
            expected_console=errors[before_rejection:];assert all('status of 400' in x for x in expected_console),expected_console;del errors[before_rejection:]
            p.set_viewport_size({'width':375,'height':812});p.goto(base,wait_until='networkidle');assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');p.locator('#sample').click();p.wait_for_function('document.querySelector("#model-canvas").dataset.ready==="true"',timeout=60000);assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');p.screenshot(path=str(out/'mobile.png'),full_page=True);checks.append('375 px mobile actual conversion without page overflow')
            assert not errors,errors;assert not requests,requests
            offline=b.new_context(offline=True,viewport={'width':1000,'height':900});pg=offline.new_page();pg.set_content(html,wait_until='load');pg.wait_for_function('document.querySelector("#canvas").dataset.ready==="true"');pg.locator('#wireframe').check();pg.screenshot(path=str(out/'offline.png'),full_page=True);offline.close();checks.append('downloaded self-contained HTML runs with network disabled')
        finally:b.close()
        b=pw.chromium.launch(executable_path=browser,headless=True,args=['--no-sandbox','--disable-webgl'])
        try:
            p=b.new_page();p.goto(base,wait_until='networkidle');p.locator('#sample').click();p.wait_for_function('document.querySelector("#viewer-error").textContent.includes("不能显示")',timeout=60000);assert p.locator('#download-model').is_visible();assert not p.locator('#model-canvas').is_visible();p.screenshot(path=str(out/'no-webgl.png'),full_page=True);checks.append('WebGL-disabled browser still produces downloadable model and explicit display limitation')
        finally:b.close()
    result={'verdict':'PASS','scope':'bounded profile conversion API and browser delivery','base_url':base,'health':health,'model_sha256':modelhash,'model_bytes':len(model),'first_http_seconds':round(elapsed,3),'checks':checks,'page_errors':errors,'expected_rejection_console':expected_console,'server_error_responses':requests,'physical_fit':'NOT_RUN','strict_geometry_release':'NOT_RUN','browser_executable':browser}
    (out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base-url',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--expected-source');p.add_argument('--browser',default='/usr/bin/chromium');a=p.parse_args();verify(a.base_url,a.output,a.expected_source,a.browser)
