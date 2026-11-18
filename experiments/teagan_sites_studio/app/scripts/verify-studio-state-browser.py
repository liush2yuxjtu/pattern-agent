"""State-transition regression: real UI, controlled late worker events, and a real solve.

--live reads {origin,token} from stdin. Credentials never enter files or test output.
"""
from pathlib import Path
from urllib.parse import urlparse, unquote
from playwright.sync_api import sync_playwright
from PIL import Image
import json, mimetypes, sys, ssl, urllib.request, urllib.error, random, hashlib

ROOT = Path(__file__).resolve().parents[1] / 'dist'
LIVE = '--live' in sys.argv
WORK = Path('/workspace/work/state-machine-audit') / ('live' if LIVE else 'local')
WORK.mkdir(parents=True, exist_ok=True)
config = json.loads(sys.stdin.readline()) if LIVE else {}
origin = config.get('origin', 'https://pattern-studio.test').rstrip('/')
checks, errors, warnings, asset_hashes = [], [], [], {}

class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme == 'https' and urlparse(newurl).netloc == urlparse(origin).netloc:
            return super().redirect_request(req, fp, code, msg, headers, newurl)
        return None

opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl.create_default_context()), SameOriginRedirect())

def serve(route):
    if LIVE:
        req = urllib.request.Request(route.request.url, headers={
            'OAI-Sites-Authorization': 'Bearer ' + config['token'], 'Accept-Encoding': 'identity'})
        try:
            with opener.open(req, timeout=45) as response:
                headers = {k: v for k, v in response.headers.items()
                           if k.lower() not in ['content-length', 'transfer-encoding', 'connection']}
                route.fulfill(status=response.status, headers=headers, body=response.read())
        except urllib.error.HTTPError as e:
            route.fulfill(status=e.code, body='Production request failed')
    else:
        f = (ROOT / (unquote(urlparse(route.request.url).path).lstrip('/') or 'index.html')).resolve()
        if ROOT not in f.parents or not f.is_file():
            route.fulfill(status=404, body='missing')
            return
        route.fulfill(status=200, body=f.read_bytes(), content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream')

# No product hooks: replace the browser Worker interface in the test context only.
# 'real' policy forwards the unmodified request to an actual native Web Worker.
CONTROLLED_WORKER = '''
window.__jobs=[];window.__workerPolicy='hold';const NativeWorker=window.Worker;
window.Worker=class {
 constructor(url,options){this.id=__jobs.length;this.terminated=false;this.native=__workerPolicy==='real'?new NativeWorker(url,options):null;__jobs.push(this);
  if(this.native){this.native.onmessage=e=>this._message?.(e);this.native.onerror=e=>this._error?.(e);}}
 set onmessage(fn){this._message=fn;if(fn)this.lateMessage=fn;}get onmessage(){return this._message;}
 set onerror(fn){this._error=fn;if(fn)this.lateError=fn;}get onerror(){return this._error;}
 postMessage(data){this.request={diagnostics:!!data.diagnostics,parts:data.panels.map(p=>p.partId)};this.native?.postMessage(data);}
 terminate(){this.terminated=true;this.native?.terminate();}
};
window.__readGates=[];const fileText=File.prototype.text;
File.prototype.text=function(){if(!this.name.startsWith('delayed-'))return fileText.call(this);
 return new Promise((resolve,reject)=>fileText.call(this).then(t=>__readGates.push(()=>resolve(t)),reject));};
'''

def check(name, ok):
    if errors or warnings:
        raise AssertionError({'runtimeErrors': errors, 'warnings': warnings})
    if not ok:
        raise AssertionError(name)
    checks.append(name)
    print('PASS: ' + name, flush=True)

def ready(page):
    page.wait_for_function('__atelier?.fitReady', timeout=240000)

def state(page):
    return page.evaluate('patternStudio.getStateMachine()')

def invariant(page):
    s = state(page)
    assert not s['violations'], s
    assert page.evaluate('__atelier.fitReady') == s['analysis']['ready']
    assert page.evaluate('__jobs.filter(w=>!w.terminated).length') == (1 if s['fit']['workerActive'] else 0)
    for key, enabled in s['display']['views'].items():
        assert page.locator('#' + key + '-panel').is_visible() == enabled
        assert page.locator('[data-panel="' + key + '"]').get_attribute('aria-pressed') == str(enabled).lower()
    spec = page.evaluate('patternStudio.getProject().spec')
    for key, value in spec.items():
        expected = s['pendingSpec']['fields'].get(key, value)
        assert float(page.locator('#' + key).input_value()) == expected
    return s

def slider(page, name, value):
    page.locator('#' + name).evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}', str(value))

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
        args=['--no-sandbox', '--enable-unsafe-swiftshader', '--use-angle=swiftshader'])
    contexts = []

    def setup(extra=None, route_override=None, wait=True):
        ctx = browser.new_context(viewport={'width': 1600, 'height': 1100}, accept_downloads=True)
        contexts.append(ctx)
        ctx.route(origin + '/**', route_override or serve)
        ctx.add_init_script(CONTROLLED_WORKER)
        if extra:
            ctx.add_init_script(extra)
        page = ctx.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error'
                else warnings.append(m.text) if m.type == 'warning' else None)
        page.goto(origin + '/', wait_until='networkidle')
        page.wait_for_function('!!window.patternStudio', timeout=90000)
        if wait:
            ready(page)
        return page

    page = setup()
    try:
        check('Page identity and default view state are correct', 'Teagan' in page.title() and
              page.evaluate('patternStudio.getViews()') == {'paper': True, 'model': True, 'heat': False, 'crease': False})
        check('Initial verified geometry has an explicit READY owner', invariant(page)['fit']['phase'] == 'READY')
        page.evaluate('''()=>{const geometry=patternStudio.getWearGeometry();window.__baseline=geometry.garment;
            window.__validResult={panels:geometry.garment,report:patternStudio.getWearReport().report};}''')
        isolated = page.evaluate('''()=>{
            const describe=()=>JSON.stringify({pattern:patternStudio.getPattern(),
                triangle:patternStudio.getWearGeometry().human.triangles[0],neck:patternStudio.getWearGeometry().landmarks.neck,
                rest:patternStudio.getDeformation().pieces[0].rest2dMm[0],trace:patternStudio.getStateMachine().fit.trace[0]});
            const before=describe(),g=patternStudio.getWearGeometry(),d=patternStudio.getDeformation(),s=patternStudio.getStateMachine();
            g.patternParts.front.points.shoulder.x+=999;g.human.triangles[0][0]=-1;g.landmarks.neck[0]+=999;
            d.pieces[0].rest2dMm[0].x+=999;d.pieces[0].triangles[0][0]=-1;s.fit.trace[0].event='mutated';
            __atelier.metrics.length=-1;return describe()===before;
        }''')
        page.evaluate('patternStudio.selectPart(null)')
        check('Read APIs and debug data return isolated snapshots instead of writable internal geometry', isolated)
        slider(page, 'unfold', 100)
        isolated = page.evaluate('''()=>{const before=JSON.stringify(patternStudio.getWearReport());
            const r=patternStudio.getWearReport();r.assembled.status='mutated';r.assembled.report.sleeveQuality.status='mutated';
            return JSON.stringify(patternStudio.getWearReport())===before;}''')
        slider(page, 'unfold', 0)
        check('Unfold-preview report also isolates its underlying assembled result', isolated and invariant(page)['analysis']['ready'])
        page.evaluate('''()=>{for(const[id,v]of[['lengthDelta',3],['sleeveDelta',2]]){
            const e=document.getElementById(id);e.value=v;e.dispatchEvent(new Event('input'));}}''')
        page.wait_for_function('patternStudio.getProject().spec.lengthDelta===3&&patternStudio.getProject().spec.sleeveDelta===2', timeout=10000)
        check('Native browser debounce commits both fields automatically without an explicit save', invariant(page)['fit']['phase'] == 'SOLVING')
        page.locator('#undo-edit').click()
        ready(page)
        page.evaluate('''()=>{for(const[id,v]of[['lengthDelta',3],['sleeveDelta',2]]){
            const e=document.getElementById(id);e.value=v;e.dispatchEvent(new Event('input'));}patternStudio.saveRevision('immediate');}''')
        saved = page.evaluate('patternStudio.getVersions()[0].state.spec')
        check('Rapid two-field input and immediate saving preserve both values', saved['lengthDelta'] == 3 and saved['sleeveDelta'] == 2)
        check('A committed specification invalidates old geometry and owns one worker', invariant(page)['fit']['phase'] == 'SOLVING' and not page.evaluate('__atelier.fitReady'))
        page.locator('#undo-edit').click()
        ready(page)
        revision = state(page)['documentRevision']
        page.evaluate('''()=>{const e=document.getElementById('lengthDelta');e.value=4;e.dispatchEvent(new Event('input'));patternStudio.undo();}''')
        check('Undo of a pending draft cancels that draft without undoing another document', invariant(page)['documentRevision'] == revision and
              page.evaluate('patternStudio.getProject().spec.lengthDelta') == 0 and not state(page)['pendingSpec']['pending'])

        page.locator('[data-inspector="history"]').click()
        with page.expect_download() as download:
            page.evaluate('''()=>{const e=document.getElementById('lengthDelta');e.value=4;e.dispatchEvent(new Event('input'));document.querySelector('#export-project').click();}''')
        download.value.save_as(str(WORK / 'immediate-project.json'))
        check('Immediate project export flushes current input rather than exporting the old specification',
              json.loads((WORK / 'immediate-project.json').read_text())['spec']['lengthDelta'] == 4)
        page.evaluate('patternStudio.restore()')
        ready(page)

        before = page.evaluate('JSON.stringify(patternStudio.getProject())')
        rejected = page.evaluate('''()=>{try{patternStudio.selectPart('missing');return false;}catch{return true;}}''')
        check('Invalid selection is rejected without corrupting the editor context', rejected and
              page.evaluate('JSON.stringify(patternStudio.getProject())') == before and not invariant(page)['violations'])
        page.evaluate('patternStudio.selectPart("sleeve")')
        rejected = page.evaluate('''()=>{const e=document.getElementById('lengthDelta');e.value=2;e.dispatchEvent(new Event('input'));
            const candidate=patternStudio.getProject();candidate.edits.push({kind:'movePoint',part:'front',name:'shoulder',dx:-5000,dy:0});
            return patternStudio.importProject(JSON.stringify(candidate));}''')
        check('Rejected import preserves the draft, selection and current document', not rejected['ok'] and
              state(page)['pendingSpec']['pending'] and state(page)['display']['selected'] == 'sleeve')
        page.evaluate('patternStudio.undo();patternStudio.selectPart("front")')

        page.locator('[data-inspector="edit"]').click()
        page.locator('#split-edge').click()
        name = page.evaluate('Object.keys(patternStudio.getPattern().parts.front.points).find(n=>n.includes("split"))')
        page.locator('[data-tool="measure"]').click()
        page.locator('#paper [data-part="front"] [data-point="' + name + '"]').dispatch_event('keydown', {'key': 'Enter'})
        page.locator('#paper [data-part="front"] [data-point="shoulder"]').dispatch_event('keydown', {'key': 'Enter'})
        check('Ruler can reference a newly split point', state(page)['editor']['ruler']['names'][0] == name)
        page.locator('#undo-edit').click()
        ready(page)
        check('Undo removes dangling ruler references and redraws the actual source SVG', invariant(page)['editor']['ruler'] is None and
              page.locator('#paper [data-point="' + name + '"]').count() == 0)

        page.locator('[data-tool="point"]').click()
        point = page.locator('#paper [data-part="front"] [data-point="shoulder"]')
        box = point.bounding_box()
        revision = state(page)['documentRevision']
        point.dispatch_event('pointerdown', {'button': 0, 'clientX': box['x'] + 2, 'clientY': box['y'] + 2})
        page.evaluate('window.dispatchEvent(new PointerEvent("pointercancel"))')
        page.evaluate('window.dispatchEvent(new PointerEvent("pointerup"))')
        check('Pointer cancellation clears the drag without an accidental geometry commit', not invariant(page)['editor']['dragging'] and state(page)['documentRevision'] == revision)
        point.dispatch_event('pointerdown', {'button': 0, 'clientX': box['x'] + 2, 'clientY': box['y'] + 2})
        page.evaluate('patternStudio.setOption("lengthDelta",1);window.dispatchEvent(new PointerEvent("pointerup"))')
        check('Document replacement invalidates any drag started against older coordinates', not invariant(page)['editor']['dragging'] and
              len(page.evaluate('patternStudio.getProject().edits')) == 0)
        page.evaluate('patternStudio.restore()')
        ready(page)

        # Async file selection is independently ordered from document revisions.
        page.locator('[data-inspector="history"]').click()
        project = page.evaluate('patternStudio.getProject()')
        project['spec']['sleeveDelta'] = 1
        page.locator('#project-file').set_input_files({'name': 'delayed-first.json', 'mimeType': 'application/json', 'buffer': json.dumps(project).encode()})
        page.wait_for_function('__readGates.length===1')
        page.evaluate('patternStudio.setOption("lengthDelta",1);__readGates.shift()()')
        page.wait_for_timeout(100)
        check('A late file read cannot overwrite a newer document edit', page.evaluate('patternStudio.getProject().spec.lengthDelta===1&&patternStudio.getProject().spec.sleeveDelta===0'))
        page.evaluate('patternStudio.restore()')
        ready(page)
        page.locator('#project-file').set_input_files({'name': 'delayed-old.json', 'mimeType': 'application/json', 'buffer': json.dumps(project).encode()})
        page.wait_for_function('__readGates.length===1')
        project['spec']['sleeveDelta'] = 2
        page.locator('#project-file').set_input_files({'name': 'newest.json', 'mimeType': 'application/json', 'buffer': json.dumps(project).encode()})
        page.evaluate('__readGates.shift()()')
        page.wait_for_timeout(100)
        check('The latest file selection wins over an older delayed read', page.evaluate('patternStudio.getProject().spec.sleeveDelta===2'))
        page.evaluate('patternStudio.restore()')
        ready(page)

        page.locator('[data-panel="heat"]').click()
        page.locator('[data-panel="crease"]').click()
        generation = state(page)['fit']['generation']
        page.evaluate('''()=>{const e=document.getElementById('lengthDelta');e.value=3;e.dispatchEvent(new Event('input'));
            document.querySelector('#crease-range').value='45';document.querySelector('#crease-range').dispatchEvent(new Event('change'));patternStudio.undo();}''')
        check('Cancelling a draft restores derived fold geometry after changing the color range', invariant(page)['fit']['generation'] == generation and
              page.evaluate('patternStudio.getCreaseDisplay().available&&patternStudio.getCreaseDisplay().colorRangeDeg[1]===45'))
        page.locator('#crease-scene canvas').screenshot(path=str(WORK / 'draft-cancel-fold.png'))
        im = Image.open(WORK / 'draft-cancel-fold.png').convert('RGB')
        blue = sum(b > 120 and b > r * 1.4 and b > g * 1.1 for r, g, b in im.get_flattened_data())
        check('Restored fold state is actually rendered, rather than a numeric-only restoration', blue > 100)
        page.locator('#crease-range').select_option('180')

        page.evaluate('patternStudio.setOption("lengthDelta",1)')
        generation = state(page)['fit']['generation']
        jobs = page.evaluate('__jobs.length')
        for mode in ['wire', 'seams', 'compare', 'solid']:
            page.locator('[data-mode="' + mode + '"]').click()
            check('Display mode does not restart or cancel a solve: ' + mode,
                  invariant(page)['fit']['generation'] == generation and page.evaluate('__jobs.length') == jobs and
                  page.evaluate('!__jobs.at(-1).terminated'))
        page.locator('#heat-metric').select_option('shear')
        page.locator('#crease-scope').select_option('quality')
        check('Changing heat units and fold scope cannot expose old values while solving',
              '暂无' in page.locator('#heat-stats').inner_text() and '旧数据已失效' in page.locator('#heat-quality').inner_text() and
              page.evaluate('patternStudio.getCreaseDiagnostics()===null&&patternStudio.getCreaseDisplay().summary===null') and '°' in page.locator('#heat-range option:checked').inner_text())
        check('Analysis exports and peak-location commands are disabled until their data is current',
              all(page.locator('#' + id).is_disabled() for id in ['download-deformation', 'locate-heat-peak', 'locate-crease', 'download-model']))
        page.screenshot(path=str(WORK / 'solving-no-old-values.png'))
        page.evaluate('''()=>{window.__old=__jobs.at(-1);patternStudio.setOption('lengthDelta',2);
            __old.lateError({message:'late old worker',preventDefault(){}});__old.lateMessage({data:{result:{panels:[]}}});}''')
        check('Late error and result events cannot detach or overwrite the new worker', invariant(page)['fit']['phase'] == 'SOLVING' and
              page.evaluate('__jobs.at(-1).terminated===false&&__jobs.slice(0,-1).every(w=>w.terminated)'))
        check('Ignored late events appear in the actual transition trace', any(e['event'] == 'STALE_IGNORED' for e in state(page)['fit']['trace']))
        page.evaluate('patternStudio.restore()')
        ready(page)

        page.evaluate('patternStudio.runDiagnosticSolve()')
        check('Explicit diagnostic solve starts a job that records checkpoints', state(page)['fit']['diagnostics'] and page.evaluate('__jobs.at(-1).request.diagnostics'))
        page.evaluate('patternStudio.setOption("lengthDelta",1)')
        check('Replacing a diagnostic job does not make the next normal job diagnostic or cache-bypassing',
              not invariant(page)['fit']['diagnostics'] and page.evaluate('!__jobs.at(-1).request.diagnostics'))
        page.evaluate('__jobs.at(-1).onmessage({data:{error:"injected solve failure"}})')
        check('Computation failure is explicit and cannot retain a prior PASS report', invariant(page)['fit']['phase'] == 'ERROR' and
              not page.evaluate('__atelier.fitReady') and 'report' not in page.evaluate('patternStudio.getWearReport()'))
        check('Failed solve clears stale heat numbers and exposes retry while 2D stays usable',
              '暂无' in page.locator('#heat-stats').inner_text() and '求解失败' in page.locator('#crease-field-state').inner_text() and page.locator('#retry-fit').is_visible() and
              page.locator('#paper svg [data-part]').count() == 3)
        page.screenshot(path=str(WORK / 'failure-retry.png'))
        page.evaluate('patternStudio.restore()')
        ready(page)
        page.evaluate('patternStudio.retryFit()')
        page.evaluate('''()=>{const bad=structuredClone(__validResult);bad.panels[1].vertices[0]=[NaN,0,0];__jobs.at(-1).onmessage({data:{result:bad}});}''')
        check('Malformed worker result is rejected before it can become valid geometry', invariant(page)['fit']['phase'] == 'ERROR' and not page.evaluate('__atelier.fitReady'))
        page.evaluate('patternStudio.restore()')
        ready(page)
        check('Malformed results cannot poison the verified reference cache', invariant(page)['fit']['cached'] and page.evaluate('patternStudio.getWearReport().status==="PASS"'))
        page.evaluate('patternStudio.retryFit()')
        page.evaluate('__jobs.at(-1).onmessage({data:{error:"injected retry case"}})')
        page.locator('#retry-fit').click()
        page.evaluate('__jobs.at(-1).onmessage({data:{result:structuredClone(__validResult)}})')
        ready(page)
        check('Retry can recover to READY and release its worker', invariant(page)['fit']['phase'] == 'READY' and not state(page)['fit']['workerActive'])

        # A real native worker recomputes and audits this same pattern after all faults.
        start = page.evaluate("()=>{__workerPolicy='real';patternStudio.retryFit();return {state:patternStudio.getStateMachine(),ready:__atelier.fitReady};}")
        check('Real retry starts without claiming old data is current', start['state']['fit']['phase'] == 'SOLVING' and not start['ready'])
        ready(page)
        maximum = page.evaluate('''()=>{const now=patternStudio.getWearGeometry().garment;let max=0;
            now.forEach((p,i)=>p.vertices.forEach((v,j)=>v.forEach((x,k)=>max=Math.max(max,Math.abs(x-__baseline[i].vertices[j][k])))));return max;}''')
        check('Real native-worker solve returns PASS and leaves no active worker', invariant(page)['fit']['phase'] == 'READY' and
              page.evaluate('patternStudio.getWearReport().status==="PASS"&&__jobs.at(-1).terminated') and not state(page)['fit']['workerActive'])
        check('State-management fixes preserve the actual fitted garment coordinates', maximum < 1e-10)
        page.screenshot(path=str(WORK / 'real-retry-pass.png'))
        (WORK / 'real-solve-state.json').write_text(json.dumps(state(page), ensure_ascii=False, indent=2))
        page.evaluate('patternStudio.setViews(["paper"])')

        # A corrupted persistent version list must not prevent subsequent editing.
        storage = setup("localStorage.setItem('teaganExpertVersionsV1',JSON.stringify([null,{name:'bad',time:'invalid',state:{}}]));")
        check('Corrupted saved-version entries are filtered without breaking startup or history',
              storage.evaluate('patternStudio.getVersions().length===0') and not invariant(storage)['violations'])
        storage.context.close()

        calls = {'body': 0}
        def body_failure(route):
            if urlparse(route.request.url).path.endswith('/models/makehuman-body.json'):
                calls['body'] += 1
                if calls['body'] == 1:
                    route.fulfill(status=200, body='{}', content_type='application/json')
                    return
            serve(route)
        missing = setup(route_override=body_failure, wait=False)
        check('Malformed human asset reaches UNAVAILABLE without a false wearing result',
              invariant(missing)['fit']['phase'] == 'UNAVAILABLE' and not missing.evaluate('__atelier.fitReady') and
              missing.locator('#paper svg [data-part]').count() == 3)
        missing.locator('#retry-fit').click()
        missing.wait_for_function('__atelier.human.loaded&&patternStudio.getStateMachine().fit.phase==="SOLVING"')
        check('Asset retry re-enables the human and starts a fresh current fit job', calls['body'] == 2 and
              not missing.locator('#show-human').is_disabled() and not invariant(missing)['violations'])
        missing.context.close()

        fuzz = setup()
        rng = random.Random(20261118)
        for i in range(80):
            choice = rng.randrange(10)
            if choice == 0:
                names = rng.sample(['paper', 'model', 'heat', 'crease'], rng.randrange(1, 5))
                fuzz.evaluate('(names)=>patternStudio.setViews(names)', names)
            elif choice == 1:
                fuzz.evaluate('(id)=>patternStudio.selectPart(id)', rng.choice([None, 'front', 'back', 'sleeve']))
            elif choice == 2:
                slider(fuzz, 'unfold', rng.choice([0, 50, 100]))
            elif choice == 3:
                fuzz.evaluate('(id)=>document.querySelector(`[data-preset="${id}"]`).click()', rng.choice(['basic', 'relaxed', 'cropped']))
            elif choice == 4:
                fuzz.evaluate('patternStudio.undo()' if rng.random() < .5 else 'patternStudio.redo()')
            elif choice == 5:
                fuzz.evaluate('(v)=>patternStudio.setOption("lengthDelta",v)', rng.choice([0, 1, 2, 3]))
            elif choice == 6:
                fuzz.evaluate('(v)=>{const e=document.getElementById("sleeveDelta");e.value=v;e.dispatchEvent(new Event("input"));patternStudio.undo();}', rng.choice([1, 2, 3]))
            elif choice == 7:
                fuzz.evaluate('(id)=>document.querySelector(`[data-mode="${id}"]`).click()', rng.choice(['solid', 'wire', 'seams', 'compare']))
            elif choice == 8:
                fuzz.evaluate('()=>{const e=document.querySelector("#crease-range");e.value=e.value==="180"?"45":"180";e.dispatchEvent(new Event("change"));}')
            else:
                fuzz.evaluate('()=>{const w=__jobs.at(-1);if(w?.terminated)w.lateError?.({message:"late fuzz event",preventDefault(){}});}')
            invariant(fuzz)
        check('80 deterministic mixed UI transitions preserve DOM, specification, worker and geometry ownership invariants', True)
        fuzz.evaluate('patternStudio.restore();patternStudio.setViews(["paper","model","heat","crease"])')
        ready(fuzz)
        generation = state(fuzz)['fit']['generation']
        old_restore = fuzz.evaluate('patternStudio.getRenderDiagnostics().model.restorations')
        fuzz.evaluate('document.querySelector("#scene canvas").getContext("webgl2").getExtension("WEBGL_lose_context").loseContext()')
        fuzz.wait_for_function('(n)=>patternStudio.getRenderDiagnostics().model.restorations>n', arg=old_restore, timeout=15000)
        check('Renderer recovery stays independent of the source and fit lifecycle', invariant(fuzz)['fit']['generation'] == generation and
              state(fuzz)['renderers']['model'] == 'READY' and fuzz.evaluate('__atelier.fitReady'))
        fuzz.set_viewport_size({'width': 390, 'height': 844})
        fuzz.locator('#crease-panel').scroll_into_view_if_needed()
        fuzz.screenshot(path=str(WORK / 'mobile-state-pass.png'))
        check('Mobile renders the resulting four-view state without horizontal overflow', fuzz.evaluate('document.documentElement.scrollWidth<=innerWidth+1') and not invariant(fuzz)['violations'])
        if LIVE:
            for filename in ['index.html', 'studio.js', 'style.css', 'wear-worker.js', 'pattern-kernel.wasm', 'models/teagan-static-fits.json']:
                actual = page.evaluate('''async(path)=>{const r=await fetch('./'+path);if(!r.ok)throw Error('asset unavailable');
                    const h=await crypto.subtle.digest('SHA-256',await r.arrayBuffer());return Array.from(new Uint8Array(h),x=>x.toString(16).padStart(2,'0')).join('');}''', filename)
                expected = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
                check('Production serves the tested bytes: ' + filename, actual == expected)
                asset_hashes[filename] = actual
        check('No unhandled JavaScript errors or WebGL warnings through successful and injected-failure paths', not errors and not warnings)
        result = {'status': 'PASS', 'count': len(checks), 'checks': checks, 'origin': origin,
                  'errors': errors, 'warnings': warnings, 'mixedUITransitions': 80,
                  'realRecomputeMaxDifferenceM': maximum, 'productionAssetSha256': asset_hashes,
                  'faultModel': 'Controlled Worker callbacks, delayed File.text and one malformed asset response; final solve uses a real native Web Worker',
                  'runner': 'Installed Chromium + Playwright', 'browserFallback': 'ego-browser absent; native Playwright connector UNAVAILABLE / Connection failed'}
        (WORK / 'state-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps({'status': 'PASS', 'count': len(checks), 'maxDifferenceM': maximum, 'errors': errors, 'warnings': warnings}), flush=True)
    except Exception:
        page.screenshot(path=str(WORK / 'failure.png'))
        phases = {}
        for name in ['page', 'storage', 'missing', 'fuzz']:
            candidate = locals().get(name)
            if candidate and not candidate.is_closed():
                try:
                    phases[name] = candidate.evaluate('({state:patternStudio.getStateMachine(),render:patternStudio.getRenderDiagnostics()})')
                    candidate.screenshot(path=str(WORK / ('failure-' + name + '.png')))
                except Exception as evidence_error:
                    phases[name] = {'evidenceError': str(evidence_error)}
        (WORK / 'failure-phases.json').write_text(json.dumps(phases, ensure_ascii=False, indent=2))
        (WORK / 'failure.json').write_text(json.dumps({'checks': checks, 'errors': errors, 'warnings': warnings}, ensure_ascii=False, indent=2))
        raise
    finally:
        browser.close()
