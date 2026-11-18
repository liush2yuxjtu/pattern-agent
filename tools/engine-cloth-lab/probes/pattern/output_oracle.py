from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SHA = '88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e'
NS = {'s': 'http://www.w3.org/2000/svg'}
NUMBER = r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def control_svd():
    cases = [
        {'name': 'IDENTITY', 'uv': [[0, 0], [1000, 0], [0, 1000]], 'xyz': [[0, 0, 0], [1, 0, 0], [0, 1, 0]]},
        {'name': 'DIAG_1_1E_MINUS_9', 'uv': [[0, 0], [1000, 0], [0, 1000]], 'xyz': [[0, 0, 0], [1, 0, 0], [0, 1e-9, 0]]},
        {'name': 'SHEAR_ROTATED_3D', 'uv': [[0, 0], [1000, 0], [0, 1000]], 'xyz': [[0, 0, 0], [0, 1.2, 0], [0.3, 0.4, 0.8]]},
    ]
    script = f"import {{ triangleStretch }} from {json.dumps((ROOT / 'src/metrics.mjs').as_uri())}; const cases = JSON.parse(process.argv[1]); console.log(JSON.stringify(cases.map(c => ({{name:c.name, ...triangleStretch(c.uv,c.xyz)}}))));"
    proc = subprocess.run(['node', '--input-type=module', '-e', script, json.dumps(cases)], check=True, text=True, capture_output=True)
    actual = json.loads(proc.stdout)
    rows = []
    for case, result in zip(cases, actual):
        uv = np.asarray(case['uv'], dtype=np.float64) * 0.001
        xyz = np.asarray(case['xyz'], dtype=np.float64)
        dm = (uv[1:] - uv[0]).T
        ds = (xyz[1:] - xyz[0]).T
        singular = np.linalg.svd(ds @ np.linalg.inv(dm), compute_uv=False)
        np.testing.assert_allclose([result['max'], result['min']], singular, rtol=1e-10, atol=1e-12)
        if case['name'] == 'DIAG_1_1E_MINUS_9':
            assert result['min'] > 0, 'anisotropic compression must not round to zero'
        rows.append({'name': case['name'], 'numpySVD': singular.tolist(), 'exportFunction': result, 'status': 'PASS'})
    return rows


def artifact_svd(path):
    data = json.loads(Path(path).read_text())
    mesh = data['mesh']
    rest = np.asarray(mesh['restXY'], dtype=np.float64) * 0.001
    indices = np.asarray(mesh['triangles'], dtype=np.int64)
    if indices.ndim == 1:
        indices = indices.reshape(-1, 3)
    uv = rest[indices]
    dm = np.transpose(uv[:, 1:] - uv[:, :1], (0, 2, 1))
    determinants = np.linalg.det(dm)
    valid_rest = np.isfinite(determinants) & (np.abs(determinants) >= 1e-16)
    assert valid_rest.all(), 'oracle requires every exported rest triangle to be valid'
    inv = np.linalg.inv(dm)
    frames = data.get('frames', [])
    assert frames, 'browser export has no frames'
    reports = []
    for frame in frames:
        positions = np.asarray(frame['positions'], dtype=np.float64).reshape(-1, 3)
        assert positions.shape[0] == rest.shape[0]
        assert np.isfinite(positions).all()
        xyz = positions[indices]
        ds = np.transpose(xyz[:, 1:] - xyz[:, :1], (0, 2, 1))
        f = np.matmul(ds, inv)
        singular = np.linalg.svd(f, compute_uv=False)
        actual_triangles = frame['metrics']['triangles']
        assert len(actual_triangles) == len(indices)
        assert all(t['valid'] for t in actual_triangles)
        actual = np.asarray([[t['max'], t['min']] for t in actual_triangles], dtype=np.float64)
        np.testing.assert_allclose(actual, singular, rtol=2e-8, atol=2e-10)
        np.testing.assert_allclose([frame['metrics']['maxStretch'], frame['metrics']['minStretch']], [singular[:, 0].max(), singular[:, 1].min()], rtol=2e-8, atol=2e-10)
        errors = np.abs(actual - singular)
        reports.append({'step': frame.get('step'), 'triangles': len(indices), 'maxStretchNumpy': float(singular[:, 0].max()), 'minStretchNumpy': float(singular[:, 1].min()), 'maximumAbsoluteError': errors.max(axis=0).tolist(), 'status': 'PASS'})
    return {'path': str(path), 'sha256': sha(path), 'framesChecked': len(frames), 'frameResults': reports, 'status': 'PASS', 'garmentVerdict': data.get('run', {}).get('garmentVerdict'), 'collisionAuditSummary': data.get('audit', {}).get('summary'), 'interpretation': 'PASS validates metric computation only. It does not validate garment assembly, fit, or continuous collision freedom.'}


def canonical_data(path=None):
    path = path or ROOT / 'inputs/golden-garment-1.1.yaml'
    assert sha(path) == CANONICAL_SHA
    # The project already has a YAML parser; its output is only input decoding.
    script = "import {readFileSync} from 'node:fs'; import {parse} from 'yaml'; console.log(JSON.stringify(parse(readFileSync(process.argv[1],'utf8'))));"
    proc = subprocess.run(['node', '--input-type=module', '-e', script, str(path)], cwd=ROOT, check=True, text=True, capture_output=True)
    return json.loads(proc.stdout)


def golden_svg(path, canonical_path=None):
    data = canonical_data(canonical_path)
    svg = ET.parse(path).getroot()
    groups = svg.findall('s:g', NS)
    parts = data['完整二维几何']
    assert len(groups) == len(parts) == 4
    lines = texts = polylines = vertices = 0
    checks = []
    for (name, part), group in zip(parts.items(), groups):
        placement = part['排版放置点']
        translate = [float(x) for x in re.findall(NUMBER, group.attrib['transform'])]
        np.testing.assert_allclose(translate, [placement['横'], -placement['高']], rtol=0, atol=1e-9)
        paths = group.findall('s:path', NS)
        assert len(paths) == len(part['线条'])
        for source, element in zip(part['线条'], paths):
            assert element.attrib['data-line'] == source['名称']
            pts = source.get('点位') or [source.get('起点'), source.get('终点')]
            pts = [p for p in pts if p is not None]
            expected = [[p['横'], -p['高']] for p in pts]
            actual = np.asarray([float(x) for x in re.findall(NUMBER, element.attrib['d'])]).reshape(-1, 2)
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-9)
            assert element.attrib['d'].strip().lower().endswith('z') == (source['闭合方式'] == '闭合')
            lines += 1
            if source['线型'] == '折线':
                polylines += 1
                vertices += len(pts)
        elements = group.findall('s:text', NS)[1:]
        sources = part.get('文字', [])
        assert len(elements) == len(sources)
        for source, element in zip(sources, elements):
            assert ''.join(element.itertext()) == source['文字内容']
            p = source['位置']
            np.testing.assert_allclose([float(element.attrib['x']), float(element.attrib['y'])], [p['横'], -p['高']], rtol=0, atol=1e-9)
            texts += 1
        checks.append({'panel': name, 'placementPreserved': True, 'lineCount': len(paths), 'sourceTextCount': len(elements)})
    assert (lines, texts, polylines, vertices) == (204, 27, 126, 1487)
    assert not svg.attrib.get('width', '').endswith('mm'), 'Golden U must not be relabeled physical millimetres'
    return {'path': str(path), 'sha256': sha(path), 'canonicalSourcePath': str(canonical_path or ROOT/'inputs/golden-garment-1.1.yaml'), 'canonicalSourceSha256': CANONICAL_SHA, 'panels': checks, 'lineCount': lines, 'sourceTextCount': texts, 'polylineCount': polylines, 'polylineVertices': vertices, 'status': 'PASS'}


def demo_svg(path, artifact=None):
    svg = ET.parse(path).getroot()
    assert svg.attrib['width'].endswith('mm') and svg.attrib['height'].endswith('mm')
    width = float(svg.attrib['width'][:-2]); height = float(svg.attrib['height'][:-2])
    viewbox = [float(x) for x in svg.attrib['viewBox'].split()]
    np.testing.assert_allclose([width, height], viewbox[2:], rtol=0, atol=1e-8)
    groups = svg.findall('s:g', NS)
    assert len(groups) == 4
    if artifact:
        draft = json.loads(Path(artifact).read_text())['draft']
        for panel, group in zip(draft['panels'], groups):
            points = np.asarray([float(x) for x in re.findall(NUMBER, group.find('s:path', NS).attrib['d'])]).reshape(-1, 2)
            np.testing.assert_allclose(points, panel['outlineMM'], rtol=0, atol=1e-8)
    return {'path': str(path), 'sha256': sha(path), 'physicalSizeMM': [width, height], 'viewBoxMM': viewbox, 'panelCount': len(groups), 'coordinatesMatchBrowserArtifact': bool(artifact), 'status': 'PASS'}


def demo_pdf(path, artifact=None):
    import fitz
    doc = fitz.open(path)
    assert len(doc) == 1
    page = doc[0]
    texts = page.get_text()
    assert '100 mm' in texts
    assert 'ENGINE_CONFORMANCE' in texts and 'NO SEAM ALLOWANCE' in texts
    lines = []
    for drawing in page.get_drawings():
        for item in drawing['items']:
            if item[0] == 'l':
                a, b = item[1:3]
                length = ((a.x-b.x)**2+(a.y-b.y)**2)**0.5*25.4/72
                lines.append({'a': [a.x, a.y], 'b': [b.x, b.y], 'lengthMM': length, 'horizontal': abs(a.y-b.y)<1e-5})
    ruler = [line for line in lines if line['horizontal'] and abs(line['lengthMM']-100)<1e-3]
    assert ruler, 'PDF must contain a physical 100 mm vector line'
    mm_size = [page.rect.width*25.4/72, page.rect.height*25.4/72]
    result = {'path': str(path), 'sha256': sha(path), 'pages': len(doc), 'pageSizeMM': mm_size, 'rulerLengthMM': ruler[-1]['lengthMM'], 'vectorLineCount': len(lines), 'status': 'PASS'}
    if artifact:
        draft = json.loads(Path(artifact).read_text())['draft']
        x = 15; max_h = 0
        expected_lines = []
        for panel in draft['panels']:
            pts = np.asarray(panel['outlineMM'], dtype=np.float64)
            min_xy = pts.min(axis=0); wh = pts.max(axis=0)-min_xy
            translated = pts + [x-min_xy[0], 30-min_xy[1]]
            for i in range(len(pts)):
                expected_lines.append([translated[i].tolist(), translated[(i+1)%len(pts)].tolist()])
            x += wh[0]+25; max_h=max(max_h,wh[1])
        np.testing.assert_allclose(mm_size, [x,max_h+65], rtol=0, atol=1e-3)
        assert len(lines) == len(expected_lines)+1
        actual_mm = np.asarray([[line['a'], line['b']] for line in lines[:-1]], dtype=np.float64)*25.4/72
        # PDF top-left coordinates after PyMuPDF match the exporter layout.
        np.testing.assert_allclose(actual_mm, expected_lines, rtol=0, atol=1e-3)
        result['allPanelVectorsMatchMMLayout'] = True
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--artifact', type=Path)
    ap.add_argument('--golden-svg', type=Path)
    ap.add_argument('--canonical-yaml', type=Path)
    ap.add_argument('--demo-svg', type=Path)
    ap.add_argument('--demo-pdf', type=Path)
    ap.add_argument('--output', type=Path, default=ROOT/'probes/pattern/output-oracle-result.json')
    args = ap.parse_args()
    result = {'oracle': 'Independent NumPy float64 SVD and XML/PDF file inspection', 'numpyVersion': np.__version__, 'metricsSourceSha256': sha(ROOT/'src/metrics.mjs'), 'controls': control_svd(), 'checks': [], 'pending': []}
    for name, path, check in [('artifact', args.artifact, artifact_svd), ('golden-svg', args.golden_svg, lambda p: golden_svg(p,args.canonical_yaml)), ('demo-svg', args.demo_svg, lambda p: demo_svg(p,args.artifact)), ('demo-pdf', args.demo_pdf, lambda p: demo_pdf(p,args.artifact))]:
        if path and path.exists():
            result['checks'].append({'kind': name, **check(path)})
        else:
            result['pending'].append({'kind': name, 'path': str(path) if path else None})
    result['status'] = 'PASS' if not result['pending'] else 'PARTIAL_FILES_PENDING'
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
