#!/usr/bin/env python3
"""Stage executed functional evidence and official review pages for existing Pages."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def copy_tree(source, target):
    shutil.copytree(source, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def build(workspace, evidence, site):
    evidence.mkdir(parents=True, exist_ok=True)
    site.mkdir(parents=True, exist_ok=True)
    for name in ['protocol.json', 'functional-evals.json', 'frozen-assertions.json',
                 'hillclimb-proposal.json', 'selection.json', 'history.json', 'notification-metadata.json']:
        if (workspace / name).is_file():
            shutil.copy2(workspace / name, evidence / name)
    for name in ['fixtures', 'skill-snapshot-v0', 'skill-candidate-v1']:
        copy_tree(workspace / name, evidence / name)
    for iteration in [1, 2]:
        origin = workspace / f'iteration-{iteration}'
        target = evidence / f'iteration-{iteration}'
        target.mkdir(exist_ok=True)
        for case in sorted(origin.glob('eval-*')):
            copy_tree(case, target / case.name)
            for run in sorted(case.glob('*/run-*')):
                config = run.parent.name
                copy_tree(run / 'outputs', site / 'artifacts' / f'iteration-{iteration}' / case.name / config)
        for name in ['benchmark.json', 'benchmark.md', 'benchmark-upstream-raw.json',
                     'benchmark-upstream-raw.md', 'aggregate-upstream.log', 'analysis.json']:
            if (origin / name).exists():
                shutil.copy2(origin / name, target / name)
        command = [sys.executable, str(HERE / 'build_functional_review.py'), '--workspace', str(origin),
                   '--benchmark', str(origin / 'benchmark.json'), '--out', str(site / ('iteration-1.html' if iteration == 1 else 'eval.html'))]
        if iteration == 2:
            command += ['--previous-workspace', str(workspace / 'iteration-1')]
        subprocess.run(command, check=True)
        shutil.copy2(origin / 'benchmark.json', site / f'benchmark-iteration-{iteration}.json')
    checksums = {str(p.relative_to(site)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(site.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
    manifest = dict(scope='Synthetic-control functional review; not native Claude triggering or six-image generation quality',
                    iterations=2, executions=12, files=checksums)
    (site / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (evidence / 'site-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--site', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.workspace.resolve(), args.evidence.resolve(), args.site.resolve())
    print(json.dumps(dict(files=len(result['files']), executions=result['executions'])))
