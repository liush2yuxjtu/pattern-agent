"""Exercise the four real studio views, locally or against authenticated production.

Local: python3 scripts/verify-four-views-browser.py
Live:  ... --live (read {origin, token} from hidden stdin; never persist credentials).
The live transport verifies TLS using system trust and serves only production bytes.
"""
from pathlib import Path
from urllib.parse import urlparse, unquote
from itertools import combinations
from playwright.sync_api import sync_playwright
from PIL import Image
import hashlib, json, math, mimetypes, ssl, sys, urllib.request, urllib.error

ROOT = Path(__file__).resolve().parents[1] / 'dist'
LIVE = '--live' in sys.argv
WORK = Path('/workspace/work/fold-color-audit') / ('live' if LIVE else 'local')
WORK.mkdir(parents=True, exist_ok=True)
config = json.loads(sys.stdin.readline()) if LIVE else {}
origin = config.get('origin', 'https://pattern-studio.test').rstrip('/')
checks, errors, warnings, asset_hashes, pixel_results = [], [], [], {}, {}
KINDS = ['paper', 'model', 'heat', 'crease']
HOSTS = {'model': '#scene', 'heat': '#heat-scene', 'crease': '#crease-scene'}

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    checks.append(name)
    print('PASS: ' + name, flush=True)

class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlparse(newurl)
        if target.scheme == 'https' and target.netloc == urlparse(origin).netloc:
            return super().redirect_request(req, fp, code, msg, headers, newurl)
        return None

opener = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=ssl.create_default_context()), SameOriginRedirect())

def serve(route):
    if LIVE:
        request = urllib.request.Request(route.request.url, headers={
            'OAI-Sites-Authorization': 'Bearer ' + config['token'], 'Accept-Encoding': 'identity'})
        try:
            with opener.open(request, timeout=45) as response:
                headers = {k: v for k, v in response.headers.items()
                           if k.lower() not in ['content-length', 'transfer-encoding', 'connection']}
                route.fulfill(status=response.status, headers=headers, body=response.read())
        except urllib.error.HTTPError as e:
            route.fulfill(status=e.code, body='Production asset request failed')
    else:
        f = (ROOT / (unquote(urlparse(route.request.url).path).lstrip('/') or 'index.html')).resolve()
        if ROOT not in f.parents or not f.is_file():
            route.fulfill(status=404, body='missing')
            return
        route.fulfill(status=200, body=f.read_bytes(),
                      content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream')

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
        args=['--no-sandbox', '--enable-unsafe-swiftshader', '--use-angle=swiftshader'])
    context = browser.new_context(viewport={'width': 1920, 'height': 1080}, accept_downloads=True)
    context.route(origin + '/**', serve)
    page = context.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error'
            else warnings.append(m.text) if m.type == 'warning' else None)

    def views():
        return page.evaluate('patternStudio.getViews()')

    def render():
        return page.evaluate('patternStudio.getRenderDiagnostics()')

    def ready():
        page.wait_for_function('__atelier?.fitReady', timeout=180000)

    def select(names):
        # Real UI multiselect; enable before disabling so the workspace never empties.
        for kind in names:
            if not views()[kind]:
                page.locator('[data-panel="' + kind + '"]').click()
        for kind, enabled in views().items():
            if enabled and kind not in names:
                page.locator('[data-panel="' + kind + '"]').click()
        page.wait_for_timeout(180)

    def slider(selector, value):
        page.locator(selector).evaluate(
            '(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}', str(value))

    def fingerprint(expression):
        return page.evaluate('async()=>{const data=new TextEncoder().encode(JSON.stringify('+expression+'));const hash=await crypto.subtle.digest("SHA-256",data);return Array.from(new Uint8Array(hash),x=>x.toString(16).padStart(2,"0")).join("");}')

    def mesh():
        # Hash the exact JS JSON, including every source point and fitted vertex.
        return fingerprint('({pattern:patternStudio.getPattern(),garment:patternStudio.getWearGeometry().garment})')

    def pixels(kind, name):
        el = page.locator(HOSTS[kind] + ' canvas')
        el.scroll_into_view_if_needed()
        page.wait_for_timeout(100)
        file = WORK / (name + '.png')
        el.screenshot(path=str(file))
        im = Image.open(file).convert('RGB')
        counts = {'red': 0, 'teal': 0, 'green': 0, 'pink': 0, 'blue': 0}
        for r, g, b in im.get_flattened_data():
            counts['red'] += r > 120 and r > g * 1.3 and r > b * 1.3
            counts['teal'] += g > 120 and b > 100 and r < g * .85 and abs(g - b) < 70
            counts['green'] += g > r + 10 and g > b + 10
            counts['blue'] += b > 120 and b > r * 1.4 and b > g * 1.1
            counts['pink'] += r > 150 and b > 100 and g < 130 and r > g * 1.6 and b > g * 1.3
        pixel_results[name] = {**counts, 'size': list(im.size)}
        return counts

    try:
        page.goto(origin + '/', wait_until='networkidle')
        ready()
        check('Default is only 2D and plain 3D', views() ==
              {'paper': True, 'model': True, 'heat': False, 'crease': False})
        check('Both optional renderers and fold scan are initially absent',
              render()['heat'] is None and render()['crease'] is None and
              page.evaluate('patternStudio.getCreaseDiagnostics()') is None)
        check('Real pattern, body, WASM and static wearing checks are ready',
              page.locator('#paper svg [data-part]').count() == 3 and
              page.evaluate('__atelier.wasm&&__atelier.human.visible&&__atelier.geometricWear.status==="PASS"'))
        baseline = mesh()
        for count in ([4] if '--targeted' in sys.argv else range(1, 5)):
            for names in combinations(KINDS, count):
                select(names)
                check('Independent UI combination: ' + ','.join(names),
                      views() == {k: k in names for k in KINDS} and
                      page.locator('.stage>section:visible').count() == count and
                      all(page.locator('#' + k + '-panel').is_visible() == (k in names) for k in KINDS))
        check('All combinations leave exact source pattern and fitted vertices unchanged', mesh() == baseline)
        check('Fold pane derives its values from the actual fitted sleeves',
              page.evaluate('patternStudio.getCreaseDiagnostics().status==="PASS"&&Math.abs(patternStudio.getCreaseDiagnostics().peak.angleDeg-31.902069243381185)<1e-7'))
        check('Fold legend names degrees and the full garment / angle coverage',
              '全衣' in page.locator('#crease-field-legend').inner_text() and
              '0–180°' in page.locator('#crease-field-legend').inner_text())
        a, b, c = pixels('model', 'plain'), pixels('heat', 'stretch'), pixels('crease', 'fold')
        check('Three simultaneously live renderers display distinct measured fields',
              a['green'] > 100 and b['red'] > a['red'] + 100 and
              c['blue'] > a['blue'] + 100)
        check('Default fold view covers all four panels and all six seam groups',
              page.evaluate('patternStudio.getCreaseDiagnostics().parts.length===4&&patternStudio.getCreaseDiagnostics().seams.samples.length===720&&patternStudio.getCreaseDiagnostics().seams.missingGroups.length===0'))
        check('Full 0–180 degree scale and all regions are selected by default',
              page.evaluate('patternStudio.getCreaseDisplay().scope==="all"&&patternStudio.getCreaseDisplay().colorRangeDeg[1]===180'))
        check('Full maximum and historical sleeve quality maximum are separately reported',
              page.evaluate('Math.abs(patternStudio.getCreaseDiagnostics().full.peak.angleDeg-90.19343015412645)<1e-7&&Math.abs(patternStudio.getCreaseDiagnostics().peak.angleDeg-31.902069243381185)<1e-7') and
              '90.19' in page.locator('#crease-field-stats').inner_text())
        check('Previously excluded underarm edges remain measured and exported',
              page.evaluate('patternStudio.getCreaseDiagnostics().underarm.sharpCount===2&&Math.abs(patternStudio.getCreaseDiagnostics().underarm.peak.angleDeg-58.864704548281615)<1e-7'))
        check('Open hems and neckline are explicitly non-applicable boundaries',
              page.evaluate('patternStudio.getCreaseDiagnostics().openBoundaries.length>0') and '角度不适用' in page.locator('#crease-field-legend').inner_text())
        check('Color legend renders the explicit fixed full-range ticks', page.locator('#crease-color-ticks span').all_text_contents()==['0°','90°','180°'] and page.evaluate('getComputedStyle(document.querySelector("#crease-color-bar")).backgroundImage!=="none"'))
        numerical = fingerprint('patternStudio.getCreaseDiagnostics()')
        page.locator('#crease-range').select_option('45')
        detail_pixels = pixels('crease', 'detail-scale')
        check('Detail scale changes actual colors while preserving exact measured angles and geometry',
              fingerprint('patternStudio.getCreaseDiagnostics()') == numerical and mesh() == baseline and
              detail_pixels != c and page.evaluate('patternStudio.getCreaseDisplay().saturatedAboveDeg===45'))
        page.locator('#crease-scope').select_option('quality')
        quality_pixels = pixels('crease', 'quality-scope')
        check('Historical sleeve-only scope stays optional and explicitly omits seam neighborhoods',
              page.evaluate('patternStudio.getCreaseDisplay().summary.sharpCount===0&&patternStudio.getCreaseDisplay().scope==="quality"') and
              quality_pixels['blue'] < c['blue'] * .7 and '排除袖底15 mm' in page.locator('#crease-field-state').inner_text())
        page.locator('#crease-scope').select_option('all')
        page.locator('#crease-range').select_option('180')
        check('Returning to full range restores the original measured values and exact garment',
              fingerprint('patternStudio.getCreaseDiagnostics()') == numerical and mesh() == baseline)
        cameras = render()
        page.locator('#crease-back').click()
        back_pixels = pixels('crease', 'full-back')
        check('Back panel has actual fold colors and only the fold camera moves',
              back_pixels['blue'] > 100 and all(math.dist(cameras[k]['camera'], render()[k]['camera'])<1e-8 for k in ['model','heat']))
        page.locator('#crease-front').click()
        page.screenshot(path=str(WORK / 'four-views-wide.png'))
        for kind in HOSTS:
            page.locator(HOSTS[kind] + ' canvas').focus()
            before = render()
            page.keyboard.press('ArrowRight')
            page.wait_for_timeout(300)
            after = render()
            check('Camera rotates independently: ' + kind,
                  math.dist(before[kind]['camera'], after[kind]['camera']) > .01 and
                  all(math.dist(before[k]['camera'], after[k]['camera']) < 1e-8 for k in HOSTS if k != kind))
            page.locator('#' + ('' if kind == 'model' else kind + '-') + 'front').click()
        page.locator('.crease-diagnostics > summary').click()
        before = render()
        page.locator('#locate-crease').click()
        after = render()
        check('Peak location moves only the fold camera and reports a real edge',
              math.dist(before['crease']['camera'], after['crease']['camera']) > .01 and
              all(math.dist(before[k]['camera'], after[k]['camera']) < 1e-8 for k in ['model', 'heat']) and
              'sleeve-' in page.locator('#crease-probe').inner_text())
        check('Peak closeup selects a ray-tested view clear of the body and garment', page.evaluate('patternStudio.getCreaseProbe().cameraVisibility.unoccluded'))
        pixels('crease', 'peak-closeup')
        page.locator('#crease-scene canvas').click(position={
            'x': page.locator('#crease-scene canvas').bounding_box()['width'] / 2,
            'y': page.locator('#crease-scene canvas').bounding_box()['height'] / 2})
        probe = page.evaluate('patternStudio.getCreaseProbe()')
        check('Real pointer raycast returns a garment face and measured adjacent edge or seam',
              'face' in probe and (probe['face'] in probe['faces'] or (probe.get('counterpart',{}).get('partId')==probe.get('pickedPartId') and probe['counterpart']['face']==probe['face'])) and probe['angleDeg'] >= 0)
        pixels('crease', 'fold-picked-edge')
        page.locator('#analysis-clear-selection').click()
        page.locator('#crease-front').click()
        slider('#crease-unfold', 100)
        check('Fold unfold control shares geometry with both other sliders and pauses fold colors',
              page.evaluate('__atelier.unfold===1&&!__atelier.human.visible') and
              all(page.locator(s).input_value() == '100' for s in ['#unfold', '#heat-unfold']) and
              '暂停' in page.locator('#crease-field-state').inner_text())
        check('Unfold never displays stale assembled-pose fold colors', pixels('crease', 'fold-unfolded')['blue'] < 20)
        slider('#heat-unfold', 0)
        check('Reassembly restores fold colors and the identical fitted mesh',
              page.locator('#crease-unfold').input_value() == '0' and mesh() == baseline and
              pixels('crease', 'fold-reassembled')['blue'] > 100)
        for kind in HOSTS:
            prior = render()
            page.evaluate('(selector)=>document.querySelector(selector).getContext("webgl2").getExtension("WEBGL_lose_context").loseContext()', HOSTS[kind] + ' canvas')
            page.wait_for_function('([kind,n])=>patternStudio.getRenderDiagnostics()[kind].restorations>n',
                                   arg=[kind, prior[kind]['restorations']], timeout=15000)
            after = render()
            check('Context loss recovers without stopping sibling renderers: ' + kind,
                  not after[kind]['contextLost'] and after[kind]['frames'] > prior[kind]['frames'] and
                  all(after[k]['frames'] > prior[k]['frames'] for k in HOSTS if k != kind))
        check('Recovered fold canvas retains its measured colors', pixels('crease', 'fold-context-restored')['blue'] > 100)
        page.locator('[data-preset="relaxed"]').click()
        ready()
        check('Changing the source rebuilds fold diagnostics in the selected fourth pane',
              views()['crease'] and page.evaluate('patternStudio.getCreaseDiagnostics()?.status==="PASS"') and
              mesh() != baseline)
        page.locator('#undo-edit').click()
        ready()
        check('Undo restores exact pattern, vertices and recomputed fold result', mesh() == baseline and
              page.evaluate('Math.abs(patternStudio.getCreaseDiagnostics().peak.angleDeg-31.902069243381185)<1e-7'))
        with page.expect_download() as download:
            page.locator('#download-crease-log').click()
        download.value.save_as(str(WORK / 'fold-log.json'))
        exported = json.loads((WORK / 'fold-log.json').read_text())
        check('Export includes measured edges, actual body and timed scan plus picked edge events',
              exported['diagnostic']['parts'][0]['edges'] and len(exported['geometry']['human']['vertices']) > 1000 and
              any(e['stage'] == 'geometry-fold-scan' and e.get('durationMs', 0) > 0 for e in exported['performance']['events']) and
              any(e['stage'] == 'select-fold' for e in exported['performance']['events']))
        select(['crease'])
        page.locator('[data-panel="crease"]').click()
        check('Last fold pane cannot be disabled into an empty workspace', views()['crease'] and
              page.locator('#show-creases').is_checked() and page.locator('.stage>section:visible').count() == 1)
        page.locator('#show-creases').click()
        check('Side checkbox also preserves and resynchronizes the last pane', views()['crease'] and page.locator('#show-creases').is_checked())
        select(KINDS)
        page.locator('#show-creases').uncheck()
        check('Side checkbox closes only the fold pane', views() ==
              {'paper': True, 'model': True, 'heat': True, 'crease': False})
        page.locator('[data-panel="crease"]').click()
        for width, height in [(1440, 900), (1399, 1000), (1024, 900), (820, 1180), (761, 1000), (390, 844)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.wait_for_function('''()=>{
                const h=document.querySelector('.canvas-header').getBoundingClientRect();
                const s=document.querySelector('.stage').getBoundingClientRect();
                return h.bottom+5<=s.top&&document.documentElement.scrollWidth<=innerWidth+1&&
                    Array.from(document.querySelectorAll('.stage>section')).every(p=>p.clientWidth>100&&p.clientHeight>=300);
            }''', timeout=15000)
            page.evaluate('window.scrollTo(0,0)')
            layout = page.evaluate('''()=>({
                header:document.querySelector('.canvas-header').getBoundingClientRect().toJSON(),
                stage:document.querySelector('.stage').getBoundingClientRect().toJSON(),
                overflow:document.documentElement.scrollWidth>innerWidth+1,
                panels:Array.from(document.querySelectorAll('.stage>section')).map(p=>[p.clientWidth,p.clientHeight])})''')
            check('Wrapped view buttons stay clear of the panes at ' + str(width),
                  layout['header']['bottom'] + 5 <= layout['stage']['top'] and not layout['overflow'] and
                  all(w > 100 and h >= 300 for w, h in layout['panels']))
            if width in [820, 390]:
                page.screenshot(path=str(WORK / ('four-views-' + str(width) + '.png')))
            for kind in HOSTS:
                page.locator(HOSTS[kind] + ' canvas').scroll_into_view_if_needed()
                data = render()[kind]
                check('Live nonblank-sized ' + kind + ' viewport at ' + str(width),
                      data['client'][0] > 100 and data['client'][1] > 100 and not data['contextLost'])
        mobile_fold = pixels('crease', 'mobile-fold')
        check('Mobile independently renders fold color and numeric legend',
              mobile_fold['blue'] > 100 and page.locator('#crease-field-stats').is_visible())
        mobile_heat = pixels('heat', 'mobile-stretch')
        mobile_plain = pixels('model', 'mobile-plain')
        # Compare blue heat colors with the naturally shaded plain cloth;
        # compare color coverage, accounting for each pane's different canvas size.
        fold_coverage = mobile_fold['blue'] / math.prod(pixel_results['mobile-fold']['size'])
        plain_coverage = mobile_plain['blue'] / math.prod(pixel_results['mobile-plain']['size'])
        check('Mobile stretch and plain views retain distinct garment pixels',
              mobile_heat['red'] > 100 and mobile_plain['red'] < 20 and
              mobile_plain['green'] > 100 and fold_coverage > plain_coverage * 2)
        page.set_viewport_size({'width': 1920, 'height': 1080})
        page.evaluate('window.scrollTo(0,0);document.querySelector(".stage").scrollTop=0')
        for kind in HOSTS:
            page.locator('#' + ('' if kind == 'model' else kind + '-') + 'front').click()
        page.screenshot(path=str(WORK / 'four-views-final.png'))
        # Verify the deployed response bytes, never a locally substituted release.
        if LIVE:
            for filename in ['index.html', 'studio.js', 'style.css', 'wear-worker.js',
                             'pattern-kernel.wasm', 'models/teagan-static-fits.json']:
                actual = page.evaluate('''async(path)=>{
                    const r=await fetch('./'+path);if(!r.ok)throw Error('asset '+path+' '+r.status);
                    const h=await crypto.subtle.digest('SHA-256',await r.arrayBuffer());
                    return Array.from(new Uint8Array(h),x=>x.toString(16).padStart(2,'0')).join('');}''', filename)
                expected = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
                check('Production matches the tested asset bytes: ' + filename, actual == expected)
                asset_hashes[filename] = actual
        page.reload(wait_until='networkidle')
        ready()
        check('Reload starts with only 2D plus plain 3D and neither optional renderer', views() ==
              {'paper': True, 'model': True, 'heat': False, 'crease': False} and
              render()['heat'] is None and render()['crease'] is None)
        check('No JavaScript errors or WebGL warnings', not errors and not warnings)
        result = {'status': 'PASS', 'checks': checks, 'count': len(checks), 'origin': origin,
                  'errors': errors, 'warnings': warnings, 'pixels': pixel_results,
                  'productionAssetSha256': asset_hashes,
                  'runner': 'Installed Chromium + Playwright; TLS-verified production bytes' if LIVE
                            else 'Installed Chromium + Playwright; exact dist bytes'}
        (WORK / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps({'status': 'PASS', 'count': len(checks), 'errors': errors, 'warnings': warnings}), flush=True)
    except Exception:
        page.screenshot(path=str(WORK / 'failure.png'))
        (WORK / 'failure.json').write_text(json.dumps({'checks': checks, 'errors': errors, 'warnings': warnings,
                                                     'pixels': pixel_results}, indent=2))
        raise
    finally:
        browser.close()
