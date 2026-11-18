"""Verify the archived source bytes, exclusions and frozen acceptance records."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'SOURCE-MANIFEST.json').read_text())
assert manifest['siteVersion'] == 14
assert manifest['sourceCommit'] == '5fd4986222886d1e4aaa5944122eaaec397c9a2a'
assert manifest['excludedTrackedPaths'] == ['.openai/hosting.json']
assert not (ROOT / 'app/.openai/hosting.json').exists()
paths = set()
for item in manifest['files']:
    relative = Path(item['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    assert item['path'] not in paths
    paths.add(item['path'])
    data = (ROOT / 'app' / relative).read_bytes()
    assert len(data) == item['bytes'], item['path']
    assert hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
assert len(paths) == 93
assert any('license' in p.lower() and p.startswith('dist/models/') for p in paths)
assert any('license' in p.lower() and p.startswith('dist/vendor/') for p in paths)
state = json.loads((ROOT / 'evidence/state-machine/live-verification.json').read_text())
views = json.loads((ROOT / 'evidence/fold/live-verification.json').read_text())
assert state['status'] == views['status'] == 'PASS'
assert state['count'] == len(state['checks']) == 50
assert views['count'] == len(views['checks']) == 85
for record in [state, views]:
    assert not record['errors'] and not record['warnings']
    assert len(record['productionAssetSha256']) == 6
    for path, digest in record['productionAssetSha256'].items():
        assert hashlib.sha256((ROOT / 'app/dist' / path).read_bytes()).hexdigest() == digest, path
independent = json.loads((ROOT / 'evidence/fold/independent-verification.json').read_text())
assert independent['status'] == 'PASS'
assert independent['cases']['before']['sleeveQualityAbove45'] == 161
assert independent['cases']['after']['sleeveQualityAbove45'] == 0
print(json.dumps({'status': 'PASS', 'sourceFiles': len(paths),
                  'sourceBytes': sum(x['bytes'] for x in manifest['files']),
                  'siteVersion': manifest['siteVersion'], 'sourceCommit': manifest['sourceCommit'],
                  'archivedLiveChecks': [state['count'], views['count']],
                  'productionAssetHashMatches': 12, 'historicalNegativeControlPreserved': True}))
