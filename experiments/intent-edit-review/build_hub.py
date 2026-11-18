#!/usr/bin/env python3
"""Render the canonical experiment README into the Pages center, checking repo links."""
import argparse
import hashlib
import json
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
    subprocess.run([pandoc, '--from=json', '--to=html5', '--standalone', '--section-divs', '--toc',
                    '--toc-depth=2', '--no-highlight', '--template=' + str(PROJECT / 'hub-template.html'),
                    '--metadata=pagetitle:纸样设计意图实验｜统一入口',
                    '--metadata=readme_sha:' + hashlib.sha256(raw).hexdigest(), '--output=' + str(output)],
                   input=json.dumps(ast, ensure_ascii=False), text=True, check=True)
    print(json.dumps({'html': str(output), 'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'readme_sha256': hashlib.sha256(raw).hexdigest(), 'checked_repo_links': len(links)}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=REPO / 'web/intent-edit-review/experiment/index.html')
    build(p.parse_args().output)
