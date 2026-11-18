"""Real browser acceptance for the source-bound experiment gallery."""
import base64
import hashlib
import io
from urllib.parse import urljoin
from PIL import Image


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canvas_pixels(canvas):
    raw = canvas.screenshot()
    image = Image.open(io.BytesIO(raw)).convert('RGB')
    count = sum(sum(abs(pixel[k] - [238, 241, 243][k]) for k in range(3)) > 45 for pixel in image.getdata())
    assert count > 500, 'Model viewport is blank'
    return {'sha256': sha(raw), 'foreground_pixels': count, 'size': list(image.size)}


def drive_gallery(page, out, data):
    out.mkdir(parents=True, exist_ok=True)
    entries = [data['baseline'], *data['cases']]
    report = {'downloads': [], 'models': [], 'cases': [], 'viewports': []}
    hub_url = page.url.split('#')[0]
    page.locator('body[data-gallery-ready="true"]').wait_for(timeout=30000)
    assert page.locator('#gallery-view').is_visible() and not page.locator('#readme-view').is_visible()
    assert page.locator('#gallery-title').inner_text() == '设计案例'
    assert page.locator('.case-card:visible').count() == 5
    assert page.locator('body').evaluate('(el)=>getComputedStyle(el).backgroundColor') == 'rgb(255, 255, 255)'
    assert page.locator('.case-card h2').first.evaluate('(el)=>getComputedStyle(el).borderBottomStyle') == 'none'
    for entry in entries:
        card = page.locator(f'.case-card[data-case-id="{entry["id"]}"]')
        canvas = card.locator('canvas[data-ready="true"]')
        assert canvas.get_attribute('data-model-id') == entry['id']
        assert canvas.get_attribute('data-model-hash') == entry['threeD']['artifact_sha256']
        assert card.locator('.pattern-full').evaluate('(el,svg)=>{const d=document.createElement("div");d.innerHTML=svg;return el.innerHTML===d.innerHTML;}', entry['twoD']['svg'])
        report['models'].append({'id': entry['id'], **canvas_pixels(canvas)})
    for width, height in [(1487, 1058), (1280, 1000), (768, 1000), (375, 850), (320, 740)]:
        page.set_viewport_size({'width': width, 'height': height}); page.evaluate('scrollTo(0,0)')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
        assert page.locator('.case-card:visible').count() == 5
        page.screenshot(path=str(out / f'gallery-{width}.png'))
        report['viewports'].append({'width': width, 'overflow': False})
    page.set_viewport_size({'width': 1487, 'height': 1058})
    page.locator('[data-filter="sewn"]').click()
    assert set(page.locator('.case-card:visible').evaluate_all('(els)=>els.map(el=>el.dataset.caseId)')) == {'baseline', '03_cuff_width'}
    page.locator('[data-filter="blocked"]').click()
    assert set(page.locator('.case-card:visible').evaluate_all('(els)=>els.map(el=>el.dataset.caseId)')) == {'01_sleeve_length', '02_body_length', '04_front_neck'}
    page.locator('#case-search').fill('前领深 +10U')
    assert page.locator('.case-card:visible').count() == 1
    assert page.locator('.case-card:visible').get_attribute('data-case-id') == '04_front_neck'
    page.locator('[data-filter="sewn"]').click()
    assert page.locator('#empty-state').is_visible() and page.locator('.case-card:visible').count() == 0
    page.locator('#clear-filters').click()
    assert page.locator('.case-card:visible').count() == 5 and page.locator('#case-search').input_value() == ''
    report['combined_filters_and_empty_recovery'] = True
    page.locator('button[data-preview="2d"]').click()
    assert page.locator('.pattern-full:visible').count() == 5
    assert page.locator('.case-media canvas:visible').count() == 0
    page.screenshot(path=str(out / 'gallery-2d.png'))
    page.locator('button[data-preview="3d"]').click()
    assert page.locator('.case-media canvas:visible').count() == 5
    for entry in entries:
        cid = entry['id']; opener = page.locator(f'[data-open-case="{cid}"]'); opener.click()
        dialog = page.locator('#case-dialog'); assert dialog.is_visible() and dialog.get_attribute('data-case-id') == cid
        if entry.get('intent'): assert page.locator('#case-intent').inner_text() == entry['intent']
        actual_spec = page.locator('#case-spec').text_content().encode()
        assert actual_spec == base64.b64decode(entry['files']['yaml']['base64'])
        page.locator('#full-spec summary').click(); assert page.locator('#case-spec').is_visible()
        assert page.locator('#case-spec').evaluate('(el)=>el.scrollTop') == 0
        page.locator('#case-spec').evaluate('(el)=>el.scrollTop=el.scrollHeight')
        assert page.locator('#case-spec').evaluate('(el)=>el.scrollTop>0')
        page.locator('#full-spec summary').click()
        for kind, record in entry['files'].items():
            with page.expect_download() as download:
                page.locator(f'[data-case-file="{kind}"]').click()
            saved = out / 'downloads' / cid / record['name']; saved.parent.mkdir(parents=True, exist_ok=True)
            download.value.save_as(saved); raw = saved.read_bytes()
            assert raw == base64.b64decode(record['base64']) and sha(raw) == record['sha256']
            report['downloads'].append({'id': cid, 'kind': kind, 'bytes': len(raw), 'sha256': sha(raw)})
        supported = cid in ['baseline', '03_cuff_width']
        assert page.locator('#case-sewn-link').is_visible() == supported
        if supported: assert page.locator('#case-sewn-link').get_attribute('href') == '../sewn/' + cid + '/files/preview.html'
        else: assert 'BLOCKED' in page.locator('#case-sewing-status').inner_text()
        if cid == '03_cuff_width':
            canvas = page.locator('#case-model'); initial = canvas_pixels(canvas); box = canvas.bounding_box()
            page.mouse.move(box['x']+box['width']*.45, box['y']+box['height']*.5)
            page.mouse.down(); page.mouse.move(box['x']+box['width']*.7, box['y']+box['height']*.57, steps=8); page.mouse.up()
            dragged = canvas_pixels(canvas); assert dragged['sha256'] != initial['sha256']
            canvas.focus(); page.keyboard.press('ArrowRight'); keyed = canvas_pixels(canvas); assert keyed['sha256'] != dragged['sha256']
            box = canvas.bounding_box(); page.mouse.move(box['x']+box['width']*.5, box['y']+box['height']*.5)
            page.mouse.wheel(0, -160); page.wait_for_function('Number(document.querySelector("#case-model").dataset.zoom)>1')
            zoomed = canvas_pixels(canvas); assert zoomed['sha256'] != keyed['sha256']
            page.locator('#reset-case-view').click(); assert canvas_pixels(canvas)['sha256'] == initial['sha256']
            page.screenshot(path=str(out / 'case-detail-desktop.png'))
            report['detail_camera'] = {'initial': initial, 'drag': dragged, 'keyboard': keyed, 'zoom': zoomed, 'reset_exact': True}
        target = '../' + ('' if cid == 'baseline' else '?case=' + cid)
        assert page.locator('#case-compare').get_attribute('href') == target
        with page.expect_navigation(wait_until='load'):
            page.locator('#case-compare').click()
        page.locator('body[data-ready="true"]').wait_for(timeout=30000)
        expected_case = cid if cid != 'baseline' else data['cases'][0]['id']
        assert page.locator('body').get_attribute('data-selected-case') == expected_case
        report['cases'].append({'id': cid, 'complete_yaml': True, 'actual_comparison_case': expected_case, 'sewn_link_available': supported})
        page.go_back(wait_until='load'); page.locator('body[data-gallery-ready="true"]').wait_for(timeout=30000)
        if page.locator('#case-dialog').is_visible(): page.locator('#close-case').click()
    page.goto(urljoin(hub_url, '../?case=unknown-case'), wait_until='load')
    page.locator('body[data-ready="true"]').wait_for(timeout=30000)
    assert page.locator('body').get_attribute('data-selected-case') == data['cases'][0]['id']
    report['unknown_comparison_case_falls_back'] = True
    page.goto(hub_url, wait_until='load'); page.locator('body[data-gallery-ready="true"]').wait_for(timeout=30000)
    page.set_viewport_size({'width': 375, 'height': 850}); page.evaluate('scrollTo(0,0)')
    page.locator('#prototype-input').click(); assert page.locator('#case-dialog').get_attribute('data-case-id') == 'baseline'
    assert page.evaluate('document.querySelector("#case-dialog").scrollWidth<=document.querySelector("#case-dialog").clientWidth')
    page.screenshot(path=str(out / 'case-detail-mobile.png'))
    page.keyboard.press('Escape'); assert not page.locator('#case-dialog').is_visible()
    assert page.locator('#prototype-input').evaluate('(el)=>el===document.activeElement')
    assert page.evaluate('document.body.style.overflow') == ''
    report['mobile_dialog_escape_focus_scroll_restored'] = True
    page.set_viewport_size({'width': 1487, 'height': 1058}); page.goto(hub_url, wait_until='load')
    page.locator('body[data-gallery-ready="true"]').wait_for(timeout=30000)
    assert len(report['downloads']) == 18
    report['verdict'] = 'PASS'
    return report
