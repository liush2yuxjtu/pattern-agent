#!/usr/bin/env python3
"""Run independent geometry acceptance and meaningful file-corruption controls."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import shutil
import struct
import tempfile

from verify_human_studio_geometry import load_glb, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--asset', type=Path, default=Path(__file__).resolve().parents[1]/'web/human-studio/assets/human.json')
    args = parser.parse_args()
    rows = []
    with contextlib.redirect_stdout(io.StringIO()):
        verify(args.fixture, args.asset)
    rows.append(dict(control='actual downloaded files', expected='PASS', observed='PASS'))
    for case in ['wrong_dimension', 'displaced_obj', 'wrong_glb_units']:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            for name in ['human-model.json', 'export-geometry.json', 'human-posed-cm.obj', 'human-rigged.glb']:
                shutil.copy2(args.fixture/name, target/name)
            if case == 'wrong_dimension':
                path = target/'human-model.json'
                state = json.loads(path.read_text())
                state['dimensions']['bust'] += 5
                path.write_text(json.dumps(state))
            elif case == 'displaced_obj':
                path = target/'human-posed-cm.obj'
                lines = path.read_text().splitlines()
                index = next(i for i, line in enumerate(lines) if line.startswith('v '))
                point = list(map(float, lines[index].split()[1:]))
                point[0] += 1
                lines[index] = 'v ' + ' '.join(map(str, point))
                path.write_text('\n'.join(lines))
            else:
                path = target/'human-rigged.glb'
                gltf, binary = load_glb(path)
                root = next(node for node in gltf['nodes'] if node.get('extras', {}).get('exportUnits') == 'metres')
                if 'matrix' in root:
                    root['matrix'][:15] = [value*100 for value in root['matrix'][:15]]
                else:
                    root['scale'] = [value*100 for value in root.get('scale', [1, 1, 1])]
                    root['translation'] = [value*100 for value in root.get('translation', [0, 0, 0])]
                text = json.dumps(gltf).encode()
                text += b' ' * (-len(text) % 4)
                length = 12+8+len(text)+8+len(binary)
                path.write_bytes(struct.pack('<III', 0x46546c67, 2, length) +
                                 struct.pack('<II', len(text), 0x4e4f534a)+text+
                                 struct.pack('<II', len(binary), 0x004e4942)+binary)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    verify(target, args.asset)
            except AssertionError:
                rows.append(dict(control=case, expected='REJECT', observed='REJECT'))
            else:
                raise RuntimeError('Invalid geometry incorrectly accepted: '+case)
    report = dict(verdict='PASS', controls=rows)
    (args.fixture/'negative-controls.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
