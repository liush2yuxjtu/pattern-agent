#!/usr/bin/env python3
"""Read back deployed build identity and primary functional-review asset bytes."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request


def verify(base, commit, out):
    out.mkdir(parents=True, exist_ok=True)
    base = base.rstrip('/') + '/'
    def get(path):
        with urllib.request.urlopen(base + path, timeout=30) as response:
            if response.status != 200:
                raise ValueError('Expected HTTP200: ' + path)
            return response.read()
    build = json.loads(get('build.json'))
    if build['commit'] != commit:
        raise ValueError('Hosted build commit mismatch: ' + build['commit'])
    paths = ['garment-body/eval.html', 'garment-body/iteration-1.html',
             'garment-body/benchmark-iteration-1.json', 'garment-body/benchmark-iteration-2.json',
             'garment-body/manifest.json',
             'garment-body/artifacts/iteration-2/eval-viewer-sync/with_skill/viewer.html',
             'garment-body/artifacts/iteration-2/eval-viewer-sync/with_skill/body.obj']
    def check(path):
        data = get(path)
        digest = hashlib.sha256(data).hexdigest()
        if build['files'].get(path) != digest:
            raise ValueError('Hosted bytes do not match deployed build manifest: ' + path)
        target = out / 'downloads' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return dict(path=path, bytes=len(data), sha256=digest, matched=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        checks = list(pool.map(check, paths))
    benchmark = json.loads((out / 'downloads/garment-body/benchmark-iteration-2.json').read_text())
    if benchmark['native_trigger_results'] is not None or len(benchmark['runs']) != 6:
        raise ValueError('Unexpected public benchmark protocol or run count')
    result = dict(verdict='PASS', scope='Hosted build identity and7 primary review/artifact byte hashes; browser behavior separately verified',
                  base_url=base, deployed_commit=commit, source_sha256=build['source_sha256'], checks=checks)
    (out / 'asset-readback.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    verify(args.base_url, args.expected_commit, args.out)
