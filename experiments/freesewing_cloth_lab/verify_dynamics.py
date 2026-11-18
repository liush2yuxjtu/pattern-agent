"""Exercise the requested HTML's actual WASM and multiple cloth states.

The public app is not changed. The WASM loader is observed without changing its
arguments or return value. The captured distributed bytes are tested separately
against analytic gravity and an elastic constraint. Cloth/body audits use the
existing independent NumPy/SciPy oracle, never the runtime BVH.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from playwright.sync_api import sync_playwright
from independent import run as audit

ROOT=Path(__file__).resolve().parents[2]


def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def run(args):
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    result={'url':args.url,'startedAtUnix':time.time(),'scope':'Actual target HTML, analytic WASM controls and four discrete dynamic states; not CCD, calibrated fabric or manufacturing certification','checks':{},'states':{},'exceptions':[],'console':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
        context=browser.new_context(viewport={'width':1440,'height':1100},device_scale_factor=1)
        context.add_init_script('''(() => {
          const original = WebAssembly.instantiate;
          WebAssembly.instantiate = function(bytes, imports) {
            if (!window.__observedWasm && (bytes instanceof ArrayBuffer || ArrayBuffer.isView(bytes))) {
              const view = bytes instanceof ArrayBuffer ? new Uint8Array(bytes) : new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength);
              window.__observedWasm = Array.from(view);
            }
            return Reflect.apply(original, WebAssembly, arguments);
          };
        })();''')
        page=context.new_page()
        page.on('pageerror',lambda e:result['exceptions'].append(str(e)))
        page.on('console',lambda m:result['console'].append({'type':m.type,'text':m.text}))
        response=page.goto(args.url,wait_until='networkidle');page.wait_for_function('window.clothLab?.ready')
        result['htmlSHA256']=hashlib.sha256(response.body()).hexdigest()
        result['checks']['correctPage']=response.status==200 and page.title()=='Pattern Agent · FreeSewing Cloth Lab'
        payload=bytes(page.evaluate('window.__observedWasm'))
        assert payload[:4]==b'\x00asm'
        (out/'actual-public-solver.wasm').write_bytes(payload)
        result['wasmSHA256']=hashlib.sha256(payload).hexdigest()
        probe=page.evaluate('''async()=>{
          const w=(await WebAssembly.instantiate(new Uint8Array(window.__observedWasm),{})).instance.exports;
          const x=new Float64Array(w.memory.buffer,0,6),previous=new Float64Array(w.memory.buffer,48,6),weights=new Float64Array(w.memory.buffer,96,2);
          x.set([0,1,0,1,2,3]);previous.set(x);weights.set([1,0]);
          for(let i=0;i<12;i++)w.integrate(2,0,48,96,1/120,0);
          const gravity=Array.from(x);
          x.set([0,1,0,2,1,0]);weights.set([1,1]);
          const e=new DataView(w.memory.buffer);e.setInt32(112,0,true);e.setInt32(116,1,true);e.setFloat64(120,1,true);e.setFloat64(128,0,true);e.setFloat64(136,0,true);
          w.solve(1,0,96,112,(1/120)**2);
          return {gravity,elastic:Array.from(x),memoryBytes:w.memory.buffer.byteLength};
        }''')
        velocity=displacement=0.
        for _ in range(12):
            velocity=.992*velocity-9.81/(120*120)
            displacement+=velocity
        expected=np.array([0,1+displacement,0,1,2,3])
        gravity_error=float(np.max(np.abs(np.array(probe['gravity'])-expected)))
        elastic=np.array(probe['elastic']).reshape(-1,3)
        result['kernel']={**probe,'expectedGravity':expected.tolist(),'gravityMaxError_m':gravity_error,'elasticDistanceAfter_m':float(np.linalg.norm(elastic[1]-elastic[0]))}
        result['checks']['actualWasmGravity']=gravity_error<1e-10
        result['checks']['actualWasmPin']=probe['gravity'][3:]==[1,2,3]
        result['checks']['actualWasmElasticConstraint']=abs(result['kernel']['elasticDistanceAfter_m']-1)<1e-10
        initial=page.evaluate('clothLab.project()')
        p0=np.array(initial['positions']).reshape(-1,3);nc=initial['parameters']['NC']
        initial_report=page.evaluate('clothLab.verify()')
        result['initialArrangement']={'appVerdict':initial_report['verdict'],'collision':initial_report['collision'],'note':'Pre-gravity arrangement is deliberately recorded separately from post-simulation acceptance.'}
        page.screenshot(path=str(out/'step-000-arrangement.png'),full_page=True)
        current=0
        for target in [120,240,360]:
            page.evaluate('(n)=>clothLab.step(n)',target-current);current=target
            state=page.evaluate('clothLab.project()');positions=np.array(state['positions']).reshape(-1,3)
            own=page.evaluate('clothLab.verify()');state=page.evaluate('clothLab.project()')
            key=f'step-{target:03d}'
            with gzip.open(out/(key+'.json.gz'),'wt') as f:json.dump(state,f)
            page.screenshot(path=str(out/(key+'.png')),full_page=True)
            independent=audit(state,ROOT,negative=False)
            result['states'][key]={'appVerdict':own['verdict'],'independent':independent,'sampledClearance_mm':own['collision']['minClearance_mm'],'bodyContacts':state['simulation']['contacts'],'rmsDisplacement_m':float(np.sqrt(np.mean((positions-p0)**2))),'maxPinDisplacement_m':float(np.max(np.abs(positions[:nc]-p0[:nc]))),'meanVerticalDisplacement_m':float(np.mean(positions[nc:,1]-p0[nc:,1]))}
            result['checks'][key]=own['verdict']=='PASS' and independent['verdict']=='PASS'
            result['checks'][key+'-pins']=result['states'][key]['maxPinDisplacement_m']<1e-12
            write(out/'progress.json',result)
        result['checks']['gravityChangesCloth']=result['states']['step-360']['meanVerticalDisplacement_m']<-.001
        result['checks']['actualBodyContacts']=result['states']['step-360']['bodyContacts']>0
        # Real slider input applies wind; a separate identical page supplies the
        # zero-wind trajectory for the same number of actual solver steps.
        page.get_by_label('Wind acceleration',exact=True).focus();page.keyboard.press('End')
        assert page.locator('#windValue').inner_text()=='5.0 m/s²'
        page.evaluate('clothLab.step(120)')
        own=page.evaluate('clothLab.verify()');wind=page.evaluate('clothLab.project()')
        with gzip.open(out/'wind-step-480.json.gz','wt') as f:json.dump(wind,f)
        independent=audit(wind,ROOT,negative=False)
        reference=context.new_page();reference.goto(args.url,wait_until='networkidle');reference.wait_for_function('window.clothLab?.ready');reference.evaluate('clothLab.step(480)')
        reference_positions=np.array(reference.evaluate('clothLab.project().positions')).reshape(-1,3)
        wind_positions=np.array(wind['positions']).reshape(-1,3)
        difference=float(np.sqrt(np.mean((wind_positions-reference_positions)**2)))
        result['states']['wind-step-480']={'appVerdict':own['verdict'],'independent':independent,'windVsNoWindRMS_m':difference,'sampledClearance_mm':own['collision']['minClearance_mm']}
        result['checks']['windInputChangesActualPhysics']=difference>1e-5
        result['checks']['windCollisionAndGeometry']=own['verdict']=='PASS' and independent['verdict']=='PASS'
        reference.close()
        page.get_by_role('button',name='Front',exact=True).click();page.screenshot(path=str(out/'wind-fabric.png'),full_page=True)
        for view in ['strain','stress','contact','fold','curvature']:
            page.get_by_role('button',name={'fold':'Fold · 折角','curvature':'Curvature · 曲率'}.get(view,view.capitalize()),exact=True).click();page.screenshot(path=str(out/(view+'.png')),full_page=True)
        for angle in ['Side','Back']:
            page.get_by_role('button',name=angle,exact=True).click();page.screenshot(path=str(out/(angle.lower()+'.png')),full_page=True)
        result['performance']=page.evaluate('clothLab.stats()')
        result['checks']['consoleHealthy']=not result['exceptions'] and not any(x['type']=='error' for x in result['console'])
        (out/'snapshot.yml').write_text(page.locator('body').aria_snapshot())
        browser.close()
    result['verdict']='PASS' if all(result['checks'].values()) else 'FAIL'
    result['finishedAtUnix']=time.time();write(out/'receipt.json',result)
    print(json.dumps({'verdict':result['verdict'],'checks':result['checks'],'states':{k:{'verdict':v['independent']['verdict'],'bodyIntersections':v['independent']['body_triangle_intersections'],'selfIntersections':v['independent']['cloth_self_intersections'],'clearance_mm':v['sampledClearance_mm']} for k,v in result['states'].items()},'kernel':result['kernel']},indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='https://liush2yuxjtu.github.io/pattern-agent/cloth-lab.html');parser.add_argument('--output',type=Path,required=True);parser.add_argument('--browser',default='/usr/bin/chromium');args=parser.parse_args();result=run(args);raise SystemExit(0 if result['verdict']=='PASS' else 2)
