#!/usr/bin/env python3
"""Build the project handbook using local Pandoc; no publication configuration changes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

PROJECT = Path(__file__).resolve().parent
REPO = PROJECT.parents[1]
SOURCES = [PROJECT / 'docs' / name for name in (
    '01-user-guide.md', '02-architecture.md', '03-data-and-audit.md', '04-build-and-deploy.md')]


def build(output):
    pandoc = shutil.which('pandoc')
    if not pandoc:
        raise SystemExit('Building the handbook needs Pandoc; tested with 3.1.11.1. The deployed HTML needs no Pandoc.')
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([pandoc, *map(str, SOURCES), '--from=markdown', '--to=html5', '--standalone',
                    '--section-divs', '--toc', '--toc-depth=2', '--no-highlight',
                    '--template=' + str(PROJECT / 'docs/template.html'),
                    '--metadata=pagetitle:原型与改版对照｜项目文档', '--output=' + str(output)], check=True)
    raw = output.read_bytes()
    print(json.dumps({'html': str(output), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                      'source_files': [str(p.relative_to(REPO)) for p in SOURCES]}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=REPO / 'web/intent-edit-review/docs/index.html')
    build(parser.parse_args().output)
