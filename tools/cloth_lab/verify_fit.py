#!/usr/bin/env python3
"""Acceptance is clothed anatomy at FIRST READY, resets and replay, plus pressure.
Real unchanged MakeHuman, actual rendered fabric pixels, source-bone anatomical
rays, exact embedded-WASM load coupons and independent tensor/contact equations.
"""
import argparse,base64,colorsys,copy,hashlib,io,json,threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urljoin, quote
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from browser_runtime import (launch_browser, instrument_context, renderer_url, assert_renderer, add_renderer_argument)
from verify_browser import ROOT,new_api_context,save_json,expect_rejection
from verify_replay import INSTRUMENT,state,counters
from oracle import verify
from fit_oracle import pressure,coverage,wear,verify_coupon,pattern_svg


def pixels(page,out,name):
    """Read original fabric screenshot pixels inside projected hip core; no edits."""
    results={}
    for direction in ['front','back','side']:
        page.locator(f'[data-camera={direction}]').click();page.locator('[data-mode=fabric]').click()
        depth=.14 if direction=='front' else -.09 if direction=='back' else .18
        corners=[[x,y,depth] for x in [-.10,.10] for y in [.77,.94]] if direction!='side' else [[depth,y,z] for z in [-.035,.095] for y in [.77,.94]]
        rect=np.array([page.evaluate('(p)=>clothLab.pointToPixel(p)',p) for p in corners])
        raw=page.locator('#viewport').screenshot(path=str(out/(name+'-'+direction+'.png')))
        img=np.array(Image.open(io.BytesIO(raw)).convert('RGB')).astype(float)
        x0,y0=np.ceil(rect.min(axis=0)).astype(int);x1,y1=np.floor(rect.max(axis=0)).astype(int)
        assert 0<=x0<x1<img.shape[1] and 0<=y0<y1<img.shape[0]
        roi=img[y0:y1,x0:x1];skin=(roi[:,:,0]>70)&(roi[:,:,1]/np.maximum(roi[:,:,0],1)>.88)&(roi[:,:,2]/np.maximum(roi[:,:,1],1)>.80)
        count=int(skin.sum());results[direction]={'hipROI':[int(x0),int(y0),int(x1),int(y1)],'skinPixels':count,'pixels':skin.size}
        assert count==0,(direction,count)
    return results


def guard_avatar(page,project):
    audit=page.evaluate('clothLab.sceneAudit()')
    assert audit['bodyVisible'] and audit['bodyOpacity']==1 and audit['bodyDepthTest'] and audit['clothDepthTest'] and audit['clippingPlanes']==0
    assert np.array_equal(audit['bodyPositions'],project['body']['positions'])
    assert np.array_equal(audit['bodyIndices'],project['body']['triangles'])
    v=np.array(audit['bodyPositions']).reshape(-1,3);rgb=np.array(audit['bodyColors']).reshape(-1,3)
    c=np.array([198,198,185])/255;expected=np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
    assert np.max(abs(rgb-expected))<1e-6,'The whole actual avatar must remain a neutral opaque mannequin'


def pressure_colors(page,project):
    page.locator('[data-mode=pressure]').click();surface=page.evaluate('clothLab.surface()')
    values=np.array(project['fitPressure']['nominalClothAreaPressurePa'])
    expected=np.array([colorsys.hls_to_rgb(.61*(1-np.clip(v/100,0,1)),.54,.64) for v in values])
    assert np.max(abs(np.array(surface['colors']).reshape(-1,3)-expected))<2e-6
    assert np.array_equal(surface['positions'],project['positions'])


def run(args,base):
    base=renderer_url(base,args.renderer)
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    report={'url':base,'checks':{},'cases':{},'pageErrors':[],'consoleErrors':[]}
    with sync_playwright() as p:
        browser=launch_browser(p,args.browser)
        context=browser.new_context(viewport={'width':1440,'height':1200},accept_downloads=True);instrument_context(context);context.add_init_script(INSTRUMENT)
        page=context.new_page();api=new_api_context(p,base)
        page.on('pageerror',lambda e:report['pageErrors'].append(str(e)));page.on('console',lambda m:report['consoleErrors'].append(m.text) if m.type=='error' else None)
        try:
            html=api.get(base);assert html.status==200;report['htmlSha256']=hashlib.sha256(html.body()).hexdigest()
            if args.expected_html_sha:assert report['htmlSha256']==args.expected_html_sha
            if args.expected_commit:
                build=api.get(urljoin(base,'../build.json')).json();assert build['commit']==args.expected_commit;report['rootCommit']=build['commit']
            assert page.goto(base,wait_until='networkidle').status==200;page.wait_for_function('window.clothLab?.ready',timeout=60000)
            report['rendering']=assert_renderer(page,args.renderer)
            initial=state(page);save_json(out/'first-ready.json',initial);guard_avatar(page,initial)
            assert initial['parameters']['patternType']=='anatomical-sector' and initial['diagnostics']['frame']==240
            assert counters(page)=={'actual':240,'reported':240},'Initial drape must be real physics, with its clock retained'
            assert initial['diagnostics']['maxPrincipalStrainPercent']<20
            assert initial['diagnostics']['coverage']['exposedSamples']==0
            assert initial['diagnostics']['pressure']['ready'] and initial['diagnostics']['pressure']['consistent']
            report['cases']['firstReady']=verify(initial,args.body_source)
            report['patternSVG']={'default':pattern_svg(page.evaluate('clothLab.patternSVG()'),initial['parameters'])}
            report['initialPixels']=pixels(page,out,'first-ready')
            report['checks']['firstReadyAnatomyCoveredWithRealInitializedPhysics']=True
            report['checks']['completeOpaqueNeutralAvatarAndNormalDepthTesting']=True
            report['checks']['defaultStrainBelowUnchanged20PercentWarning']=True
            assert initial['diagnostics']['wear']['fitted']
            report['checks']['actualWaistLevelClearanceAndSeparateFrontBackPatternLengths']=True
            pressure_colors(page,initial);page.screenshot(path=str(out/'first-ready-pressure.png'),full_page=True)
            report['checks']['realMultiplierPressureDrivesGPUColors']=True
            # A closed, fully covering garment can still be worn incorrectly.
            # Move only the upper edge and its pins; keep seam pairs coincident.
            report['waistFaults']={}
            for name,kind in [('floating-waist','radial'),('wrong-waist-height','vertical')]:
                fake=copy.deepcopy(initial)
                for index in list(range(17))+list(range(425,442)):
                    point=np.array(initial['positions'][3*index:3*index+3]);delta=np.array([0.,.03,0.])
                    if kind=='radial':
                        direction=point-np.array([0.,point[1],.06]);delta=direction/np.linalg.norm(direction)*.03
                    for field in ['positions','previous','pinPositions']:
                        fake[field][3*index:3*index+3]=(point+delta).tolist()
                page.evaluate('(s)=>clothLab.restore(s)',fake);bad=state(page)
                assert bad['diagnostics']['maxSeamGapMm']<.001 and bad['diagnostics']['coverage']['exposedSamples']==0
                assert not bad['diagnostics']['wear']['fitted'] and 'FAIL' in page.locator('#verdict').inner_text()
                rejected=expect_rejection(lambda:wear(bad,args.body_source))
                report['waistFaults'][name]={'rejection':rejected,'wear':bad['diagnostics']['wear']}
                save_json(out/(name+'.json'),bad);page.locator('[data-camera=side]').click();page.screenshot(path=str(out/(name+'.png')),full_page=True)
            page.evaluate('(s)=>clothLab.restore(s)',initial)
            report['checks']['coveringNonpenetratingButFloatingOrWrongHeightWaistsRejected']=True
            # Load calibration is a new instance of the SAME embedded WASM.
            coupons={}
            for name,spec in {'zero':{'loadPa':0},'gravity':{'loadPa':.22*9.81},'500Pa':{'loadPa':500},'1000Pa':{'loadPa':1000},'2000Pa':{'loadPa':2000},'inclined':{'loadPa':1000,'tilt':30},'refined':{'loadPa':1000,'cells':6},'detachedGravity':{'loadPa':.22*9.81,'detached':True,'steps':4},'disabled':{'loadPa':1000,'collision':False,'steps':1}}.items():
                result=page.evaluate('(s)=>clothLab.pressureCoupon(s)',spec);coupons[name]=result;verify_coupon(result)
            save_json(out/'actual-wasm-coupons.json',coupons);report['coupons']={k:verify_coupon(v) for k,v in coupons.items()}
            before=state(page);page.locator('#pressure-calibrate').click();page.wait_for_function("document.querySelector('#pressure-coupon').textContent.includes('载荷校验通过')")
            assert state(page)['positions']==before['positions'] and state(page)['body']==before['body']
            page.screenshot(path=str(out/'known-load.png'),full_page=True)
            report['checks']['sameWASMKnownLoadsInclineRefinementAndDetachedControls']=True
            report['checks']['realCalibrationButtonPreservesMainAvatarAndGarment']=True
            # Reset must itself return a clothed state; no manual settle is permitted.
            page.locator('#reset').click();reset=state(page);assert reset['diagnostics']['coverage']['exposedSamples']==0
            report['cases']['reset']=verify(reset,args.body_source);report['resetPixels']=pixels(page,out,'reset')
            report['checks']['resetCoveredBeforeAnyUserStep']=True
            for name,width,length in [('short-wide',800,400),('long-narrow',550,700)]:
                page.locator('#width').fill(str(width));page.locator('#width').dispatch_event('input');page.locator('#length').fill(str(length));page.locator('#length').dispatch_event('input')
                snapshot=state(page);save_json(out/(name+'.json'),snapshot);report['cases'][name]=verify(snapshot,args.body_source)
                report['patternSVG'][name]=pattern_svg(page.evaluate('clothLab.patternSVG()'),snapshot['parameters'])
                assert snapshot['diagnostics']['coverage']['exposedSamples']==0
                guard_avatar(page,snapshot);report[name+'Pixels']=pixels(page,out,name)
                verdict=page.locator('#verdict').inner_text()
                if snapshot['diagnostics']['maxPrincipalStrainPercent']>20:assert '应变偏大' in verdict
                report.setdefault('parameterWarnings',{})[name]=verdict
            report['checks']['changedPatternExtremesRemainCoveredWithRecomputedPhysics']=True
            report['checks']['trueScaleSectorArcsExact10mmAllowanceAndNoPageClipping']=True
            page.locator('#width').fill('650');page.locator('#width').dispatch_event('input');page.locator('#length').fill('600');page.locator('#length').dispatch_event('input')
            page.select_option('#material','soft');soft=state(page);report['cases']['soft']=verify(soft,args.body_source);report['softPixels']=pixels(page,out,'soft')
            page.select_option('#material','woven');page.locator('#body-shift').fill('40');page.locator('#body-shift').dispatch_event('input');page.evaluate('clothLab.advance(240)')
            moved=state(page);report['cases']['moved']=verify(moved,args.body_source);save_json(out/'moved.json',moved)
            report['checks']['materialAndMovingAvatarPressureCoverageCollisionRecomputed']=True
            # Save pressure multipliers, then seek real recorded frames without integration.
            page.locator('#record-start').click();page.evaluate('clothLab.advance(24)');page.locator('#record-stop').click()
            recorded=page.evaluate('clothLab.project()');baseline=counters(page)
            for index in [0,6,12,24]:
                page.evaluate('(i)=>clothLab.replay.seek(i)',index);snapshot=state(page);report['cases']['replay-'+str(index)]=verify(snapshot,args.body_source)
                assert snapshot['pressureState']==recorded['replay']['frames'][index]['pressureState']
                pressure_colors(page,snapshot)
            assert counters(page)==baseline
            report['checks']['recordedPressureAndCoverageRestoreWithoutIntegration']=True
            page.screenshot(path=str(out/'replayed-pressure.png'),full_page=True)
            # Actual exported HTML must reopen all pressure contacts offline.
            with page.expect_download() as ev:page.locator('#save-html').click()
            ev.value.save_as(str(out/'actual-fit-snapshot.html'))
            saved=state(page);offline=browser.new_context(offline=True,viewport={'width':1280,'height':1100});op=offline.new_page();requests=[];op.on('request',lambda r:requests.append(r.url))
            op.set_content((out/'actual-fit-snapshot.html').read_text());op.wait_for_function('clothLab?.ready')
            assert state(op)['positions']==saved['positions'] and state(op)['pressureState']==saved['pressureState'] and not requests
            report['cases']['offline']=verify(state(op),args.body_source);op.screenshot(path=str(out/'offline-pressure.png'),full_page=True)
            report['checks']['offlineSingleHTMLRetainsRealPressureAndCoveredGeometry']=True
            # A coherent but physically impossible far-away contact cannot pass as pressure.
            original=page.evaluate('clothLab.project()');fake=copy.deepcopy(original);fake.pop('replay',None)
            raw=np.frombuffer(base64.b64decode(fake['pressureState']['samples']),dtype='<f4').copy()
            row=np.array([400,1e-6,0,1,0],dtype='<f4');fake['pressureState']['samples']=base64.b64encode(np.r_[raw,row].astype('<f4').tobytes()).decode()
            page.evaluate('(s)=>clothLab.restore(s)',fake)
            forged=state(page);assert 'FAIL' in page.locator('#verdict').inner_text()
            report['forgedPressureRejected']=expect_rejection(lambda:pressure(forged))
            page.evaluate('(s)=>clothLab.restore(s)',original)
            fake=copy.deepcopy(original);fake['fitPressure']['nominalClothAreaPressurePa'][0]+=500
            report['forgedPressureFieldRejected']=expect_rejection(lambda:pressure(fake))
            report['checks']['fabricatedPressureRejectedByForceLedgerAndContactGeometry']=True
            page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(out/'mobile.png'),full_page=True);(out/'snapshot.yml').write_text(page.locator('body').aria_snapshot())
            report['performance']=page.evaluate('clothLab.performanceLog()')
            assert not report['pageErrors'] and not report['consoleErrors']
            report['checks']['healthyRuntimeAndMobileWithoutOverflow']=True
            report['verdict']='PASS'
        except Exception as e:
            report['verdict']='FAIL';report['error']=str(e)
            try:page.screenshot(path=str(out/'failure.png'),full_page=True)
            except Exception:pass
            raise
        finally:save_json(out/'receipt.json',report);api.dispose();browser.close()
    print(json.dumps({'verdict':report['verdict'],'checks':report['checks'],'firstReady':report['cases']['firstReady']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base-url');parser.add_argument('--html',type=Path,default=ROOT/'web/cloth-lab/index.html');parser.add_argument('--output',type=Path,required=True);parser.add_argument('--browser',default='/usr/bin/chromium');parser.add_argument('--body-source',type=Path,default=ROOT/'web/human-studio/assets/human.json');parser.add_argument('--expected-html-sha');parser.add_argument('--expected-commit');add_renderer_argument(parser);args=parser.parse_args()
    if args.base_url:run(args,args.base_url)
    else:
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self,*a,**k):super().__init__(*a,directory=str(args.html.parent),**k)
            def log_message(self,*a):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:run(args,f'http://127.0.0.1:{server.server_port}/{quote(args.html.name)}')
        finally:server.shutdown();server.server_close();thread.join()
