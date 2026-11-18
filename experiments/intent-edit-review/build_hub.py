#!/usr/bin/env python3
"""Render the canonical experiment README into the Pages center, checking repo links."""
import argparse
import base64
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote, unquote, urlsplit

PROJECT = Path(__file__).resolve().parent
REPO = PROJECT.parents[1]
README = PROJECT / 'README.md'
GITHUB = 'https://github.com/liush2yuxjtu/pattern-agent/'


def build(output):
    pandoc = shutil.which('pandoc')
    if not pandoc:
        raise SystemExit('The experiment hub build needs Pandoc; tested with 3.1.11.1.')
    raw = README.read_bytes()
    ast = json.loads(subprocess.check_output([pandoc, str(README), '--from=markdown', '--to=json']))
    if ast['blocks'][0]['t'] != 'Header' or ast['blocks'][0]['c'][0] != 1:
        raise ValueError('The central README needs one opening title')
    ast['blocks'].pop(0)
    links = []

    def visit(node):
        if isinstance(node, dict):
            if node.get('t') == 'Link':
                target = node['c'][2][0]
                parsed = urlsplit(target)
                if not parsed.scheme and not target.startswith('#'):
                    path = (README.parent / unquote(parsed.path)).resolve()
                    if not path.is_relative_to(REPO) or not path.exists():
                        raise ValueError('Broken central README link: ' + target)
                    kind = 'tree' if path.is_dir() else 'blob'
                    href = GITHUB + kind + '/main/' + quote(str(path.relative_to(REPO)))
                    if parsed.fragment: href += '#' + quote(parsed.fragment)
                    node['c'][2][0] = href
                    links.append({'source': target, 'path': str(path.relative_to(REPO)), 'href': href})
            for value in node.values(): visit(value)
        elif isinstance(node, list):
            for value in node: visit(value)

    visit(ast)
    output = output.resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    page = subprocess.check_output([pandoc, '--from=json', '--to=html5', '--standalone', '--section-divs', '--toc',
                    '--toc-depth=2', '--no-highlight', '--template=' + str(PROJECT / 'hub-template.html'),
                    '--metadata=pagetitle:纸样设计意图实验｜案例库',
                    '--metadata=readme_sha:' + hashlib.sha256(raw).hexdigest()],
                   input=json.dumps(ast, ensure_ascii=False), text=True)
    comparison = (REPO / 'web/intent-edit-review/index.html').read_text()
    match = re.search(r'<script[^>]*id="app-data"[^>]*>(.*?)</script>', comparison, re.S)
    if not match:
        raise ValueError('Build the source-bound comparison before the gallery')
    data = json.loads(match[1])
    manifest = json.loads((REPO / 'web/intent-edit-review/sewn/manifest.json').read_text())
    entries = [data['baseline'], *data['cases']]
    if len(entries) != 5 or {e['id'] for e in entries} != {e['id'] for e in manifest['cases']}:
        raise ValueError('Gallery and sewn catalog must describe the same five inputs')
    for entry in entries:
        for record in entry['files'].values():
            raw_file = base64.b64decode(record['base64'], validate=True)
            source = (REPO / record['path']).resolve()
            if not source.is_relative_to(REPO) or source.read_bytes() != raw_file or hashlib.sha256(raw_file).hexdigest() != record['sha256']:
                raise ValueError('Gallery download does not match its actual repository source')
        sewn = next(e for e in manifest['cases'] if e['id'] == entry['id'])
        if sewn['source_dxf_sha256'] != entry['files']['dxf']['sha256'] or sewn['source_yaml_sha256'] != entry['files']['yaml']['sha256']:
            raise ValueError('Sewing outcome belongs to a different design revision')
    sewing = {'verdict': manifest['verdict'], 'cases': {e['id']: e['verdict'] for e in manifest['cases']}}
    for marker, value in [('__GALLERY_STYLE__', (PROJECT / 'gallery.css').read_text()),
                          ('__GALLERY_DATA__', match[1]),
                          ('__SEWING_DATA__', json.dumps(sewing, ensure_ascii=False)),
                          ('__VIEWER__', (PROJECT / 'viewer.js').read_text()),
                          ('__GALLERY_APP__', (PROJECT / 'gallery.js').read_text())]:
        if page.count(marker) != 1:
            raise ValueError('Missing gallery template marker: ' + marker)
        page = page.replace(marker, value)
    output.write_text(page)
    print(json.dumps({'html': str(output), 'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'readme_sha256': hashlib.sha256(raw).hexdigest(), 'checked_repo_links': len(links),
                      'gallery_cases': len(entries), 'complete_files': sum(len(e['files']) for e in entries)}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=REPO / 'web/intent-edit-review/experiment/index.html')
    build(p.parse_args().output)
