#!/usr/bin/env python3
"""Verify actual fitted T-shirt UI and downloaded source artifacts, not physical fit."""
import argparse,hashlib,json,zipfile,io
from pathlib import Path
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
from verify_pages import local_site
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def verify(base,out,expected=None,browser='/usr/bin/chromium'):
    base=base.rstrip('/')+'/';out.mkdir(parents=True,exist_ok=True);errors=[];bad=[];failed=[];downloads=[];checks=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=browser,headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
        try:
            c=b.new_context(viewport={'width':1440,'height':1100},accept_downloads=True);p=c.new_page()
            p.on('pageerror',lambda e:errors.append(str(e)));p.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
            p.on('requestfailed',lambda r:failed.append({'url':r.url,'error':r.failure}) if r.failure!='net::ERR_ABORTED' else None)
            p.on('response',lambda r:bad.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
            meta=c.request.get(urljoin(base,'build.json')).json()
            if expected:assert meta['commit']==expected
            assert p.goto(urljoin(base,'fitted-tshirt/'),wait_until='networkidle').status==200
            assert p.title()=='Pattern Agent · 女士紧身长袖上衣原型'
            assert p.locator('h1').inner_text().replace('\n','')=='女士紧身长袖上衣原型'
            p.wait_for_function('document.querySelector("#render-image").complete && document.querySelector("#render-image").naturalWidth>0')
            assert '合身性尚未验证' in p.locator('.project-state').inner_text()
            p.screenshot(path=str(out/'desktop.png'),full_page=True);checks+=['identity and meaningful desktop render','explicit visual-only status']
            for view in ['front','back','three-quarter']:
                p.locator('[data-view="'+view+'"]').click();p.wait_for_function('(view)=>document.querySelector("#render-image").src.endsWith(view+".png") && document.querySelector("#render-image").complete',arg=view)
            checks.append('three render view controls')
            p.locator('[data-view="model"]').click();p.wait_for_function('document.querySelector("#model-canvas").dataset.ready==="true"',timeout=60000)
            canvas=p.locator('#model-canvas');assert canvas.is_visible();assert int(canvas.get_attribute('data-triangles'))>10000
            # Observe actual canvas pixels, not merely WebGL initialization or a DOM flag.
            from PIL import Image,ImageChops
            raw=canvas.screenshot();im=Image.open(io.BytesIO(raw)).convert('RGB');bg=Image.new('RGB',im.size,im.getpixel((0,0)));box=ImageChops.difference(im,bg).getbbox();assert box and (box[2]-box[0])*(box[3]-box[1])>im.width*im.height*.1
            box=canvas.bounding_box();x=box['x']+box['width']*.5;y=box['y']+box['height']*.5
            oldyaw=canvas.get_attribute('data-yaw');p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+90,y+20,steps=12);p.mouse.up();assert canvas.get_attribute('data-yaw')!=oldyaw
            assert sha(canvas.screenshot())!=sha(raw)
            before=canvas.get_attribute('data-zoom');p.mouse.wheel(0,-220);p.wait_for_timeout(80);assert canvas.get_attribute('data-zoom')!=before
            p.locator('#wireframe').check();wire=canvas.screenshot();p.locator('#wireframe').uncheck();assert sha(wire)!=sha(canvas.screenshot())
            canvas.focus();before=canvas.get_attribute('data-yaw');p.keyboard.press('ArrowLeft');assert canvas.get_attribute('data-yaw')!=before
            p.locator('#reset-model').click();assert float(canvas.get_attribute('data-yaw'))==-.45 and float(canvas.get_attribute('data-zoom'))==1
            p.screenshot(path=str(out/'model.png'),full_page=True);checks+=['actual WebGL mesh pixels','pointer rotation changes canvas pixels','wheel zoom','wireframe pixel change','keyboard rotation and reset']
            p.locator('.size-details summary').click();assert p.locator('#size-rows tr').count()==10;assert p.locator('#size-rows tr').last.inner_text().endswith('59.9')
            p.locator('.size-details summary').click();checks.append('full ten-row eight-size table')
            for link in p.locator('.file-list a').all():
                href=link.get_attribute('href');relative='fitted-tshirt/'+href
                with p.expect_download() as ev:link.click()
                d=ev.value;assert d.failure() is None;target=out/d.suggested_filename;d.save_as(target);blob=target.read_bytes();assert sha(blob)==meta['files'][relative]
                downloads.append({'path':relative,'sha256':sha(blob),'bytes':len(blob)})
            archive=out/'fitted-tshirt-complete.zip'
            with zipfile.ZipFile(archive) as z:
                assert z.testzip() is None;manifest=json.loads(z.read('manifest.json'))
                for name,digest in manifest.items():assert sha(z.read(name))==digest,name
                assert len([n for n in manifest if '/source/' in n])==3
                assert 'source/女紧身款T恤.dxf' in '\n'.join(manifest)
            checks.append('five real downloads match build hashes; all archive entries match source hashes')
            p.set_viewport_size({'width':375,'height':812});p.goto(urljoin(base,'fitted-tshirt/'),wait_until='networkidle');assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            p.locator('[data-view="back"]').click();p.wait_for_function('document.querySelector("#render-image").complete');p.screenshot(path=str(out/'mobile.png'),full_page=True)
            p.locator('.size-details summary').click();assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');assert p.locator('.table-scroll').evaluate('(e)=>e.scrollWidth>e.clientWidth');p.locator('.table-scroll').evaluate('(e)=>e.scrollLeft=250');assert p.locator('.table-scroll').evaluate('(e)=>e.scrollLeft>0');checks.append('375 px mobile with working view controls and contained table scrolling')
            assert not errors,errors;assert not bad,bad;assert not failed,failed
            missing=c.request.get(urljoin(base,'fitted-tshirt/assets/no-such-model.glb'));assert missing.status==404;checks.append('missing model returns 404')
        finally:b.close()
        fallback=pw.chromium.launch(executable_path=browser,headless=True,args=['--no-sandbox','--disable-webgl'])
        try:
            p=fallback.new_page(viewport={'width':1100,'height':900});p.goto(urljoin(base,'fitted-tshirt/'),wait_until='networkidle');p.locator('[data-view="model"]').click();p.wait_for_function('document.querySelector("#model-status").textContent.includes("暂不可用")');assert p.locator('#render-image').is_visible();assert not p.locator('#model-canvas').is_visible();p.screenshot(path=str(out/'webgl-fallback.png'),full_page=True);checks.append('real WebGL-disabled browser exposes loaded image fallback')
        finally:fallback.close()
    report={'verdict':'PASS','claim':'web preview, source downloads and archive integrity only','physical_fit':'NOT_RUN','strict_geometry_release':'NOT_RUN','base_url':base,'commit':meta['commit'],'source_sha256':meta['source_sha256'],'checks':checks,'downloads':downloads,'page_errors':errors,'failed_requests':failed,'asset_http_errors':bad,'browser':'Chromium via local Playwright; ego-browser unavailable'}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base-url');p.add_argument('--output',type=Path,default=ROOT/'work/verify-fitted-tshirt');p.add_argument('--expected-commit');p.add_argument('--browser',default='/usr/bin/chromium');a=p.parse_args()
    if a.base_url:verify(a.base_url,a.output,a.expected_commit,a.browser)
    else:
        with local_site(ROOT/'dist') as url:verify(url,a.output,a.expected_commit,a.browser)
