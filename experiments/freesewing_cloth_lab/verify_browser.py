"""Real Playwright controls, downloads, offline replay, responsive and print checks."""
import argparse,hashlib,json,time,xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
from pathlib import Path
import fitz
import numpy as np
from playwright.sync_api import sync_playwright

def run(url,out,browser='/usr/bin/chromium'):
    out.mkdir(parents=True,exist_ok=True);checks={};errors=[];messages=[];requests=[];failed=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=browser,headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
        ctx=b.new_context(viewport={'width':1440,'height':1100},device_scale_factor=1,accept_downloads=True)
        page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:messages.append({'type':m.type,'text':m.text}));page.on('request',lambda r:requests.append(r.url));page.on('requestfailed',lambda r:failed.append({'url':r.url,'failure':r.failure}))
        response=page.goto(url,wait_until='networkidle');page.wait_for_function('window.clothLab?.ready')
        document_sha256=hashlib.sha256(response.body()).hexdigest()
        checks['identity']=response.status==200 and page.title()=='Pattern Agent · FreeSewing Cloth Lab'
        checks['meaningful_render']=page.locator('#patternCanvas [data-panel]').count()==4 and page.evaluate('clothLab.stats().render.triangles')>30000
        checks['no_overlay']=page.locator('vite-error-overlay,nextjs-portal').count()==0
        initial=page.evaluate('clothLab.snapshot()');page.get_by_role('button',name='Run drape',exact=True).click();page.wait_for_function('clothLab.stats().steps>=12',timeout=30000);page.get_by_role('button',name='Pause',exact=True).click()
        changed=page.evaluate('clothLab.snapshot()');checks['real_run_pause']=changed['steps']>0 and changed['positions']!=initial['positions']
        page.evaluate('clothLab.step(360-clothLab.stats().steps)')
        page.get_by_role('button',name='Run verification',exact=True).click();checks['verification_dialog']=page.locator('#reportDialog').is_visible() and page.locator('#reportSummary').inner_text().startswith('PASS')
        report=page.evaluate('clothLab.project().report');(out/'app-report.json').write_text(json.dumps(report,indent=2));page.locator('#reportDialog').get_by_role('button',name='Close',exact=True).click()
        page.screenshot(path=str(out/'fabric.png'),full_page=True)
        baseline=page.evaluate('clothLab.project()');(out/'state.json').write_text(json.dumps(baseline))
        for view in ['strain','stress','seams','contact','fold','curvature']:
            page.get_by_role('button',name={'fold':'Fold · 折角','curvature':'Curvature · 曲率'}.get(view,view.capitalize()),exact=True).click();checks['view_'+view]=page.locator(f'[data-view="{view}"]').get_attribute('class')=='active';page.screenshot(path=str(out/(view+'.png')),full_page=True)
        page.locator('[data-seam="1"]').click();checks['trace_seam']=page.locator('[data-view="seams"]').get_attribute('class')=='active'
        for side in ['Side','Back','Front']:
            old=page.evaluate('clothLab.camera()');page.get_by_role('button',name=side,exact=True).click();new=page.evaluate('clothLab.camera()');checks['camera_'+side.lower()]=new!=old;page.screenshot(path=str(out/(side.lower()+'.png')),full_page=True)
        canvas=page.locator('#scene');r=canvas.bounding_box();old=page.evaluate('clothLab.camera()');page.mouse.move(r['x']+r['width']*.5,r['y']+r['height']*.5);page.mouse.down();page.mouse.move(r['x']+r['width']*.5+90,r['y']+r['height']*.5+10,steps=12);page.mouse.up();page.wait_for_timeout(250);checks['orbit_pointer']=page.evaluate('clothLab.camera()')!=old
        for button,name in [('SVG 1:1','pattern.svg'),('FreeSewing source SVG','freesewing-native.svg'),('DXF · mm','pattern.dxf'),('Export 3D','garment.obj'),('Export simulation + sewing JSON','simulation.json'),('Save single HTML','downloaded.html')]:
            with page.expect_download() as info:page.get_by_role('button',name=button,exact=True).click()
            info.value.save_as(str(out/name));checks['download_'+name]=(out/name).stat().st_size>100
        baseline_next=page.evaluate('()=>{clothLab.step(1);return clothLab.project().positions;}')
        source=ET.fromstring((out/'pattern.svg').read_text());viewbox=[float(x) for x in source.attrib['viewBox'].split()];checks['native_freesewing_svg']='<svg' in (out/'freesewing-native.svg').read_text() and page.evaluate('clothLab.project().freesewing.version')=='4.10.2';checks['svg_mm']=source.attrib['width'].endswith('mm') and abs(float(source.attrib['width'][:-2])-viewbox[2])<.001
        squares=[e for e in source.iter() if e.tag.endswith('rect') and e.attrib.get('width')=='100' and e.attrib.get('height')=='100'];checks['svg_100mm_calibration']=len(squares)==1
        checks['dxf_mm']='9\n$INSUNITS\n70\n4\n' in (out/'pattern.dxf').read_text()
        obj=(out/'garment.obj').read_text().splitlines();checks['obj_geometry']=sum(x.startswith('v ') for x in obj)==13380+1856 and sum(x.startswith('f ') for x in obj)==26756+3584
        with page.expect_popup() as info:page.get_by_role('button',name='Print A4',exact=True).click()
        popup=info.value;popup.wait_for_load_state();tile_count=popup.locator('section').count();popup.pdf(path=str(out/'pattern-a4.pdf'),prefer_css_page_size=True,print_background=True)
        pdf=fitz.open(out/'pattern-a4.pdf');checks['a4_tiles']=len(pdf)==tile_count and len(pdf)>1 and all(abs(p.rect.width-210/25.4*72)<.6 and abs(p.rect.height-297/25.4*72)<.6 for p in pdf)
        lengths=[]
        for p in pdf:
            for d in p.get_drawings():
                for item in d['items']:
                    if item[0]=='l':lengths.append(float(abs(item[1]-item[2])))
                    if item[0]=='re':lengths.extend([item[1].width,item[1].height])
        checks['pdf_100mm_line']=any(abs(x-100/25.4*72)<.15 for x in lengths)
        pdf[0].get_pixmap(matrix=fitz.Matrix(1,1)).save(out/'print-preview.png');pdf.close();popup.close()
        # Change the real range and material controls; verify generated pattern state.
        page.get_by_label('Skirt length in millimetres').focus();page.keyboard.press('End');checks['length_input']=page.locator('#lengthValue').inner_text()=='650 mm' and page.evaluate('clothLab.project().seams[0].lengthA_mm')==650
        before_ratio=page.evaluate('clothLab.project().materialCoordinates');page.get_by_label('FreeSewing circle ratio percent',exact=True).focus();page.keyboard.press('End');checks['freesewing_ratio_input']=page.evaluate('clothLab.project().freesewing.settings.options.circleRatio')==.6 and page.evaluate('clothLab.project().materialCoordinates')!=before_ratio
        page.get_by_label('Material assumption').select_option('linen');checks['material_input']=page.evaluate('clothLab.project().material.E')==160000
        page.get_by_role('button',name='Reset',exact=True).click();checks['reset']=page.evaluate('clothLab.stats().steps')==0
        with page.expect_download() as info:page.get_by_role('button',name='Save single HTML',exact=True).click()
        info.value.save_as(str(out/'edited.html'))
        # Managed Chrome blocks file:// by policy. Serve only the saved document,
        # block all other requests, then disconnect the browser context.
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(out.resolve())));Thread(target=server.serve_forever,daemon=True).start();offline_ctx=b.new_context(viewport={'width':1440,'height':1100});offline=offline_ctx.new_page();offline_requests=[];offline.on('request',lambda r:offline_requests.append(r.url));offline.on('pageerror',lambda e:errors.append('offline: '+str(e)));offline.route('**/*',lambda r:r.continue_() if r.request.is_navigation_request() and r.request.url.startswith(f'http://127.0.0.1:{server.server_port}/') else r.abort());offline.goto(f'http://127.0.0.1:{server.server_port}/downloaded.html');offline.wait_for_function('window.clothLab?.ready');restored=offline.evaluate('clothLab.project()');offline_ctx.set_offline(True);checks['offline_single_file']=all(x==f'http://127.0.0.1:{server.server_port}/downloaded.html' for x in offline_requests);checks['offline_saved_view']=offline.evaluate('clothLab.project().view')==json.loads((out/'simulation.json').read_text())['view'] and offline.locator('[data-view].active').get_attribute('data-view')==offline.evaluate('clothLab.project().view');checks['offline_state_exact']=np.array_equal(np.array(restored['positions']),np.array(baseline['positions'])) and restored['simulation']['steps']==360
        offline.screenshot(path=str(out/'offline.png'),full_page=True);offline_next=offline.evaluate('()=>{clothLab.step(1);return clothLab.project().positions;}');checks['offline_next_step_exact']=np.array_equal(np.array(offline_next),np.array(baseline_next));offline_ctx.set_offline(False);offline.goto(f'http://127.0.0.1:{server.server_port}/edited.html');offline.wait_for_function('window.clothLab?.ready');checks['offline_edited_design']=offline.locator('#lengthValue').inner_text()=='650 mm' and offline.evaluate('clothLab.project().material.E')==160000 and offline.evaluate('clothLab.project().freesewing.settings.options.circleRatio')==.6;offline_ctx.close();server.shutdown();server.server_close()
        page.reload(wait_until='networkidle');page.wait_for_function('window.clothLab?.ready');page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(200);checks['mobile_no_overflow']=page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.evaluate('clothLab.step(360)');checks['mobile_drape']=page.evaluate('clothLab.verify().verdict')=='PASS';page.screenshot(path=str(out/'mobile.png'),full_page=True)
        page.get_by_role('button',name='Research & method',exact=True).click();checks['research_dialog']=page.locator('#aboutDialog').is_visible();page.locator('#aboutDialog').get_by_role('button',name='Close',exact=True).click()
        checks['console_errors']=not errors and not any(x['type']=='error' for x in messages)
        checks['network']=not failed and not any(x.startswith('http') and x!=url for x in requests)
        checks['solver_budget']=report['stats']['solver_ms_p95']<100
        checks['scene_budget']=report['stats']['render']['calls']<20 and report['stats']['render']['triangles']<50000
        (out/'snapshot.txt').write_text(page.locator('body').aria_snapshot());(out/'console.json').write_text(json.dumps({'exceptions':errors,'messages':messages,'failed_requests':failed,'requests':requests},indent=2))
        result={'verdict':'PASS' if all(checks.values()) else 'FAIL','url':url,'html_sha256':document_sha256,'browser':'Chromium / SwiftShader; Playwright explicitly requested; Browser plugin absent','viewports':['1440x1100','390x844'],'checks':checks,'performance':report['stats'],'printing':{'pages':tile_count,'format':'A4, 210 x 297 mm','calibration100mm':checks['pdf_100mm_line'],'page_format_tolerance_mm':.22,'calibration_line_tolerance_mm':.053},'warnings':[x for x in messages if x['type']=='warning'],'limitations':['Software rendering does not establish real-device 60 fps','Managed Chrome blocks file://; saved HTML tested over document-only local HTTP with network disabled after load','Stress uncalibrated; fit NOT_VALIDATED','Discrete self-contact enabled; independent geometry checked separately; universal CCD not certified','FreeSewing Sandy skirt shell; native waistband not simulated','Fold/curvature are geometric wrinkle proxies; permanent crease/material calibration NOT_RUN']}
        (out/'browser-report.json').write_text(json.dumps(result,indent=2));b.close();return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--browser',default='/usr/bin/chromium');a=p.parse_args();r=run(a.url,a.out,a.browser);print(json.dumps(r,indent=2));raise SystemExit(0 if r['verdict']=='PASS' else 2)
