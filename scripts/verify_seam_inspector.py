#!/usr/bin/env python3
"""Verify a source-bound sewing inspector artifact; never claims hosted acceptance."""
from pathlib import Path
import argparse,json,mimetypes,sys,traceback


def run_browser(ARTIFACT,DATA,OUT,browser_path):
    from playwright.sync_api import sync_playwright
    errors=[];checks=[];expected_console=[]
    BASE='https://seam-inspector.local.test/'
    def serve(route):
        from urllib.parse import urlsplit,unquote
        name=unquote(urlsplit(route.request.url).path).lstrip('/') or 'index.html'
        p=(ARTIFACT/name).resolve()
        if not p.is_relative_to(ARTIFACT.resolve()) or not p.is_file():route.fulfill(status=404,body='missing');return
        route.fulfill(status=200,body=p.read_bytes(),content_type=mimetypes.guess_type(p.name)[0] or 'application/octet-stream')

    def point(locator,fraction=.5):
        return locator.evaluate('(e,t)=>{const p=e.getPointAtLength(e.getTotalLength()*t);const q=new DOMPoint(p.x,p.y).matrixTransform(e.getScreenCTM());return {x:q.x,y:q.y};}',fraction)

    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=str(browser_path),headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
        context=browser.new_context(viewport={'width':1280,'height':1080},accept_downloads=True)
        context.route(BASE+'**',serve);page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.goto(BASE,wait_until='networkidle');page.locator('#seam-proof-visual[data-ready=true]').wait_for()
        assert page.title()=='女士紧身上衣裁片连接验收'
        assert page.locator('iframe').count()==0
        assert page.locator('#sp-mesh').get_attribute('data-render-mode')=='full-mesh'
        assert page.locator('#sp-seams button').count()==len(DATA['seams'])
        assert int(page.locator('#seam-proof-visual').get_attribute('data-triangles'))==DATA['face_count']
        root=page.locator('#seam-proof-visual')
        assert root.get_attribute('data-model-sha256')==DATA['model_sha256']
        checks.append('Native page renders every actual face and exposes all independently declared seams')
        for seam in DATA['seams']:
            button=page.locator('#sp-seams button').filter(has_text=seam['label']);button.click()
            assert root.get_attribute('data-selected-seam')==seam['name']
            assert float(root.get_attribute('data-actual-gap'))==seam['measurement']['max_gap_mm']
            assert float(root.get_attribute('data-actual-length-error'))==seam['measurement']['length_error_mm']
            assert int(root.get_attribute('data-shared-count'))==seam['measurement']['samples']
            assert page.locator('#sp-seams button[aria-pressed=true]').count()==1
            visible=page.locator('#sp-selected').inner_text()
            assert f"共用顶点 {seam['measurement']['samples']}/{seam['measurement']['samples']}" in visible
            assert f"间隙 {seam['measurement']['max_gap_mm']:.3f}" in visible
            assert f"缝长误差 {seam['measurement']['length_error_mm']:.4f}" in visible
            assert page.locator('#sp-selected').is_visible()
        checks.append('All 15 native buttons update 2D edges, 3D seam and exact independently measured values')
        page.locator('#sp-seams button').filter(has_text='左侧缝').click()
        target=page.locator('#sp-flat g[data-seam="shoulder.left"] .sp-hit').first
        xy=point(target,.45);page.mouse.click(xy['x'],xy['y'])
        assert root.get_attribute('data-selected-seam')=='shoulder.left'
        checks.append('Actual mouse click on a 2D shoulder edge selects that seam')
        page.locator('#sp-front').click()
        target=page.locator('#sp-overlay .sp-context[data-seam="side.right"]')
        xy=point(target,.43);page.mouse.click(xy['x'],xy['y'])
        assert root.get_attribute('data-selected-seam')=='side.right'
        checks.append('Actual mouse click on an unselected 3D side seam selects and highlights it')
        page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
        before=page.locator('#sp-overlay .sp-seam-a').get_attribute('d');page.locator('#sp-back').click()
        assert page.locator('#sp-degrees').inner_text()=='180°'
        assert page.locator('#sp-overlay .sp-seam-a').get_attribute('d')!=before
        page.locator('#sp-front').click();assert page.locator('#sp-degrees').inner_text()=='0°'
        box=page.locator('#sp-view').bounding_box();x=box['x']+box['width']*.5;y=box['y']+box['height']*.5
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+70,y+14,steps=6);page.mouse.up()
        assert abs(float(page.locator('#sp-mesh').get_attribute('data-angle')))>30
        page.locator('#sp-angle').focus();page.locator('#sp-angle').press('End');assert page.locator('#sp-degrees').inner_text()=='180°'
        page.locator('#sp-original').uncheck();assert page.locator('#sp-flat .sp-raw-line').count()==0
        page.locator('#sp-original').check();assert page.locator('#sp-flat .sp-raw-line').count()>0
        checks.append('Front/back buttons, real drag, keyboard camera slider and source-line toggle work')
        page.locator('#sp-seams button').filter(has_text='右袖底缝').click();page.reload(wait_until='networkidle')
        assert root.get_attribute('data-selected-seam')=='underarm.right'
        assert page.locator('#sp-degrees').inner_text()=='180°'
        checks.append('Selected seam and angle are restored after a real page reload')
        for text,name in [('下载验收报告','independent-report.json'),('下载离线视图','seam-inspector-offline.html')]:
            with page.expect_download() as d:page.get_by_role('link',name=text,exact=True).click()
            d.value.save_as(OUT/name);assert (OUT/name).read_bytes()==(ARTIFACT/name).read_bytes()
        assert page.get_by_role('link',name='复用原纸样',exact=True).get_attribute('href')=='https://pattern-agent-convert.vercel.app/?reuse=fitted-tshirt-v1#convert'
        checks.append('Report and single-file HTML downloads preserve the actual packaged bytes; reuse link targets the existing converter')
        before_rejection=len(errors)
        page.route(BASE+'seam-inspector-offline.html',lambda r:r.fulfill(status=503,body='temporarily unavailable'))
        page.get_by_role('link',name='下载离线视图',exact=True).click();page.wait_for_function('document.querySelector("#site-download-status").textContent.includes("下载未完成")')
        page.unroute(BASE+'seam-inspector-offline.html')
        expected_console=errors[before_rejection:];assert all('status of 503' in e for e in expected_console),expected_console
        del errors[before_rejection:]
        with page.expect_download() as retry:page.get_by_role('link',name='下载离线视图',exact=True).click()
        retry.value.save_as(OUT/'retried-offline.html');assert (OUT/'retried-offline.html').read_bytes()==(ARTIFACT/'seam-inspector-offline.html').read_bytes()
        checks.append('A real failed download response shows a visible error and a subsequent retry succeeds')
        for width in [768,375,320]:
            page.set_viewport_size({'width':width,'height':1000});page.wait_for_timeout(120)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
        checks.append('Native layout and controls fit desktop through 320px without overflow')
        touch=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
        touch.route(BASE+'**',serve);phone=touch.new_page();phone.on('pageerror',lambda e:errors.append(str(e)))
        phone.goto(BASE,wait_until='networkidle');phone.locator('#sp-front').click();phone.locator('#sp-view').scroll_into_view_if_needed()
        target=phone.locator('#sp-overlay .sp-context[data-seam="side.right"]');xy=point(target,.43)
        phone.touchscreen.tap(xy['x'],xy['y']);assert phone.locator('#seam-proof-visual').get_attribute('data-selected-seam')=='side.right'
        view=phone.locator('#sp-view');box=view.bounding_box();x=box['x']+box['width']*.5;y=box['y']+box['height']*.5
        session=touch.new_cdp_session(phone)
        session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y,'id':1}]})
        for step in range(1,7):session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+step*9,'y':y+step,'id':1}]})
        session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        assert abs(float(phone.locator('#sp-mesh').get_attribute('data-angle')))>25
        phone.screenshot(path=str(OUT/'touch.png'),full_page=True)
        checks.append('Real touch tap selects a 3D seam; real touch swipe rotates the model')
        offline=browser.new_context(offline=True);op=offline.new_page();op.on('pageerror',lambda e:errors.append(str(e)))
        # Direct file:// navigation is blocked by the managed browser policy;
        # render the exact downloaded document with networking disabled instead.
        op.set_content((OUT/'seam-inspector-offline.html').read_text(),wait_until='load')
        op.locator('#seam-proof-visual[data-ready=true]').wait_for()
        op.locator('#sp-seams button').filter(has_text='领条合口').click();assert op.locator('#seam-proof-visual').get_attribute('data-selected-seam')=='band.end'
        with op.expect_download() as download:op.get_by_role('link',name='下载验收报告',exact=True).click()
        download.value.save_as(OUT/'offline-report.json');assert (OUT/'offline-report.json').read_bytes()==(ARTIFACT/'independent-report.json').read_bytes()
        checks.append('Exact downloaded standalone HTML executes with networking disabled, supports seam selection and downloads the embedded original report')
        assert not errors,errors
        browser.close()
        browser=pw.chromium.launch(executable_path=str(browser_path),headless=True,args=['--no-sandbox','--disable-webgl'])
        ctx=browser.new_context();ctx.route(BASE+'**',serve);p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
        p.goto(BASE,wait_until='networkidle');p.locator('#seam-proof-visual[data-ready=true]').wait_for()
        assert p.locator('#sp-mesh').get_attribute('data-render-mode')=='seams-only'
        p.locator('#sp-seams button').filter(has_text='右肩缝').click();assert p.locator('#seam-proof-visual').get_attribute('data-selected-seam')=='shoulder.right'
        checks.append('WebGL-disabled fallback still supports seam selection and measurement display')
        assert not errors,errors;browser.close()
    return {'verdict':'PASS','scope':'exact local static artifact rendered with first-party file fulfillment; not live/private-site authentication','checks':checks,'page_errors':errors,'expected_rejection_console':expected_console,'browser_closed':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    target=parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--html',type=Path,help='Self-contained accepted inspector HTML')
    target.add_argument('--artifact-dir',type=Path,help='Actual Sites dist containing index.html and all assets')
    parser.add_argument('--glb',type=Path,required=True)
    parser.add_argument('--dxf',type=Path,required=True)
    parser.add_argument('--units',choices=['mm','cm','inch'],required=True)
    parser.add_argument('--browser',type=Path,default=Path('/usr/bin/chromium'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    receipt={'verdict':'FAIL','scope':'source-bound local sewing inspector artifact, not authenticated hosted UI','commands':sys.argv,'physical_fit':'NOT_RUN','material_mechanics':'NOT_RUN','production_cutting_approval':'NOT_RUN'}
    try:
        from seam_inspector_binding import bind_artifact,digest
        html_path=args.html or args.artifact_dir/'index.html';html=html_path.read_text()
        data,raw_report,measured,binding=bind_artifact(html,args.glb,args.dxf,args.units)
        (out/'independent-reopen.json').write_text(json.dumps(measured,ensure_ascii=False,indent=2)+'\n')
        (out/'binding.json').write_text(json.dumps(binding,indent=2)+'\n');receipt['binding']=binding
        if args.artifact_dir:
            artifact=args.artifact_dir.resolve()
            assert (artifact/'independent-report.json').read_bytes()==raw_report,'SERVED_REPORT_DIFFERS_FROM_EMBEDDED_REPORT'
        else:
            artifact=out/'runtime';artifact.mkdir(exist_ok=True)
            (artifact/'index.html').write_bytes(html_path.read_bytes())
            (artifact/'seam-inspector-offline.html').write_bytes(html_path.read_bytes())
            (artifact/'independent-report.json').write_bytes(raw_report)
        if not args.browser.is_file():raise FileNotFoundError('Browser executable unavailable: '+str(args.browser))
        ui=run_browser(artifact,data,out,args.browser)
        (out/'browser.json').write_text(json.dumps(ui,ensure_ascii=False,indent=2)+'\n')
        receipt.update(verdict='PASS',browser=ui,html_sha256=digest(html_path.read_bytes()),files={p.name:digest(p.read_bytes()) for p in artifact.iterdir() if p.is_file()})
    except (FileNotFoundError,ModuleNotFoundError) as exc:
        receipt.update(verdict='BLOCKED',reason=str(exc))
    except Exception as exc:
        receipt.update(verdict='FAIL',reason=str(exc));(out/'failure.log').write_text(traceback.format_exc())
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False,indent=2));return 0 if receipt['verdict']=='PASS' else 3 if receipt['verdict']=='BLOCKED' else 2

if __name__=='__main__':raise SystemExit(main())
