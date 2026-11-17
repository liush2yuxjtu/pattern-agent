"""Verify the imported 1D baseline against the immutable original DXF.

This checks the baseline snapshot only. It is not a semantic compiler, DXF
patch applier, or physical garment validator. Uses the Python standard library.
"""
from pathlib import Path
from collections import Counter
from hashlib import sha256
import json
import math


def verify(spec, root):
    raw = (root / spec['source']['file']).read_bytes()
    if sha256(raw).hexdigest() != spec['source']['sha256']:
        raise ValueError('The DXF baseline digest does not match')
    lines = raw.splitlines(keepends=True)
    geometry = spec['geometry']
    if any(key != entity['id'] for key, entity in geometry.items()):
        raise ValueError('Entity identity mismatch')
    indexes = [entity['index'] for entity in geometry.values()]
    if len(set(indexes)) != len(indexes):
        raise ValueError('Duplicate imported entity indexes')
    all_part_ids = [ref for part in spec['parts'] for ref in part['entity_ids']]
    if Counter(all_part_ids) != Counter(geometry.keys()):
        raise ValueError('Each imported entity must belong to exactly one candidate part')
    checked_lines = set()
    for binding in spec['source_bindings']:
        line = binding['source_value_line']
        if line in checked_lines:
            raise ValueError('Duplicate source field binding')
        checked_lines.add(line)
        if int(lines[line - 1]) != binding['source_group_code']:
            raise ValueError('Source tag code mismatch')
        value = geometry[binding['entity_id']]
        for key in binding['path']:
            value = value[key]
        source = lines[line].rstrip(b'\r\n').decode(spec['source']['encoding_for_text'])
        if binding['kind'] == 'number':
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('Non-finite or nonnumeric geometry')
            if float(source) != value:
                raise ValueError('Snapshot coordinate differs from the baseline')
        elif source != value:
            raise ValueError('Snapshot text differs from the baseline')
    for measurement in spec['measurements'].values():
        total = sum(geometry[entity_id]['length_drawing_units'] for entity_id in measurement['entity_ids'])
        if abs(total - measurement['value']) > 1e-6:
            raise ValueError('Observed measurement reference mismatch')
    if spec['program']['operations']:
        raise ValueError('This package verifies the unchanged baseline only')
    for rule in spec['rule_assets']:
        if sha256((root / rule['file']).read_bytes()).hexdigest() != rule['sha256']:
            raise ValueError('Rule document digest differs')
    return {'source_integrity': 'PASS', 'entity_part_coverage': 'PASS',
            'bound_coordinate_and_text_fields': len(checked_lines),
            'geometry_counts': dict(Counter(e['type'] for e in geometry.values())),
            'observed_measurement_paths_checked': len(spec['measurements']),
            'semantic_compile': 'NOT_IMPLEMENTED', 'edited_dxf': 'NOT_GENERATED',
            'new_3d_preview': 'NOT_GENERATED'}


if __name__ == '__main__':
    root = Path(__file__).parent
    spec = json.loads((root / 'prototype-spec.json').read_text(encoding='utf-8'))
    print(json.dumps(verify(spec, root), ensure_ascii=False, indent=2))
