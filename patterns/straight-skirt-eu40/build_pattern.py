#!/usr/bin/env python3
"""Draft an editable straight skirt using the installed OpenSloper MCP tools."""
import base64
import json
import math
import os
import shutil
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CLI = os.environ.get('OPENSLOPER_CLI') or shutil.which('opensloper-cli')
if not CLI:
    raise SystemExit('Set OPENSLOPER_CLI to an installed OpenSloper 0.2.0 CLI executable.')
STEM = 'straight-skirt-eu40'


class MCP:
    def __init__(self):
        self.process = subprocess.Popen([CLI, 'serve'], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, text=True, cwd=ROOT)
        self.counter = 0
        self.log = []
        self.rpc('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {},
                               'clientInfo': {'name': 'skirt-pattern-builder', 'version': '1'}})
        self.process.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
        self.process.stdin.flush()

    def rpc(self, method, params):
        self.counter += 1
        req = {'jsonrpc': '2.0', 'id': self.counter, 'method': method, 'params': params}
        self.process.stdin.write(json.dumps(req) + '\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('OpenSloper stopped')
        reply = json.loads(line)
        self.log.append(req)
        if 'error' in reply or reply.get('result', {}).get('isError'):
            raise RuntimeError(f'{method} {params}: {reply}')
        return reply['result']

    def call(self, tool, **arguments):
        result = self.rpc('tools/call', {'name': tool, 'arguments': arguments})
        contents = result.get('content', [])
        for content in contents:
            if content['type'] == 'text':
                try:
                    return json.loads(content['text'])
                except json.JSONDecodeError:
                    continue
        return result

    def render(self, destination, fmt, **kwargs):
        result = self.rpc('tools/call', {'name': 'render', 'arguments': {'format': fmt, **kwargs}})
        for item in result['content']:
            if item['type'] == 'image':
                destination.write_bytes(base64.b64decode(item['data']))
                return
            if item['type'] == 'text' and '<svg' in item['text']:
                destination.write_text(item['text'])
                return
        raise RuntimeError(f'No {fmt} image returned')

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=10)
        (ROOT / 'mcp-calls.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in self.log))


def write_json(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    # Only bootstrap files and page layouts are written directly. All drafting
    # and subsequent pattern changes go through MCP tools/call.
    write_json('measurements-eu40.slm', {
        'format': 'measurements', 'version': 1, 'units': 'mm',
        'name': 'Burda regular size 40 - standard reference',
        'notes': ('Waist and hip: Burda official regular size 40, reference height 168 cm. '
                  'This is a chosen standard size, not a population average or personal measurements. '
                  'Waist-to-hip 200 mm and skirt body length 600 mm are drafting assumptions. '
                  'Source: https://www.burdastyle.com/how-to-take-measurements'),
        'measurements': [
            {'key': 'waist', 'value': 740, 'description': 'Body waist; Burda regular 40'},
            {'key': 'hip', 'value': 980, 'description': 'Body hip; Burda regular 40'},
            {'key': 'waist_to_hip', 'value': 200, 'description': 'Draft assumption; replace with actual'},
            {'key': 'skirt_length', 'value': 600, 'description': 'Skirt body only; waistband adds 40 mm'},
        ]})
    pattern_path = ROOT / (STEM + '.sloper')
    if pattern_path.exists():
        pattern_path.rename(ROOT / (STEM + '.previous.sloper'))
    write_json(pattern_path.name, {
        'format': 'pattern', 'version': 1, 'units': 'mm',
        'measurementFile': 'measurements-eu40.slm',
        'notes': ('Straight skirt, Burda reference 40: body W740 H980; finished W750 H1020. '
                  'Body length 600 + waistband 40. Darts are sewn markings, NOT cutouts. '
                  'Main seams 10 mm; back centre 15 mm; hem 30 mm; front fold 0. '
                  'Back zip 200 mm; centre-back slit 180 mm. Make a toile and true waist/hem after fitting.')})
    m = MCP()
    try:
        m.call('open', path=str(pattern_path))
        for name, formula, description in [
            ('hip_ease', '40', 'Total hip ease'),
            ('waist_ease', '10', 'Total waist ease'),
            ('half_hip', '(@hip + #hip_ease) / 2', 'Half the finished hip'),
            ('back_hip', '#half_hip / 2 - 10', 'Back quarter width'),
            ('front_hip', '#half_hip - #back_hip', 'Front quarter width'),
            ('suppression', '(@hip + #hip_ease - @waist - #waist_ease) / 2', 'Half-skirt shaping'),
            ('side_take', '#suppression / 4', 'Waist intake at each quarter side'),
            ('back_dart', '#suppression * 0.3', 'Back dart intake'),
            ('front_dart', '#suppression * 0.2', 'Front dart intake'),
            ('back_dart_length', '140', 'Back dart length'),
            ('front_dart_length', '90', 'Front dart length'),
            ('waistband_height', '40', 'Finished folded waistband height'),
            ('waistband_overlap', '30', 'Extension for hook/bar fastening'),
            ('zip_length', '200', 'Back zipper length'),
            ('slit_height', '180', 'Centre-back walking slit'),
        ]:
            m.call('add_variable', name=name, formula=formula, description=description)
        m.call('set_material', material='Main', color='#C9DDD7', allowance=10, width=1500)

        def point(name, base=None, dx=None, dy=None, x=None, y=None):
            if base is None:
                return m.call('add_point', type='freePoint', name=name, x=x, y=y)
            return m.call('add_point', type='offsetPoint', name=name, base=base,
                          mode='cartesian', dx=dx, dy=dy)

        def edge(name, start, end, role='outline'):
            return m.call('add_edge', type='line', name=name, start=start, end=end, role=role)

        pieces = {}
        for prefix, xbase, piece_name in [('B', 0, 'Back'), ('F', 350, 'Front')]:
            quarter = '#back_hip' if prefix == 'B' else '#front_hip'
            dart = '#back_dart' if prefix == 'B' else '#front_dart'
            dartlen = '#back_dart_length' if prefix == 'B' else '#front_dart_length'
            p = lambda suffix: prefix + '_' + suffix
            point(p('A'), x=str(xbase), y='0')
            for suffix, dx, dy in [
                ('Hem_centre', '0', '@skirt_length'),
                ('Hip_side', quarter, '@waist_to_hip'),
                ('Hem_side', quarter, '@skirt_length'),
                ('Waist_side', quarter + ' - #side_take', '0'),
                ('Dart_left', f'({quarter} - #side_take - {dart}) / 2', '0'),
                ('Dart_right', f'({quarter} - #side_take + {dart}) / 2', '0'),
                ('Dart_tip', f'({quarter} - #side_take) / 2', dartlen),
                ('Dart_cap', f'({quarter} - #side_take) / 2', f'-{dart} * {dart} / (4 * {dartlen})'),
                ('Hip_centre', '0', '@waist_to_hip'),
            ]:
                point(p(suffix), base=p('A'), dx=dx, dy=dy)
            edge(p('Waist_centre'), p('A'), p('Dart_left'))
            edge(p('Cap_left'), p('Dart_left'), p('Dart_cap'))
            edge(p('Cap_right'), p('Dart_cap'), p('Dart_right'))
            edge(p('Waist_outer'), p('Dart_right'), p('Waist_side'))
            m.call('add_edge', type='curve', name=p('Side_curve'), role='outline',
                   start=p('Waist_side'), end=p('Hip_side'), angle1='275',
                   length1='@waist_to_hip / 3', angle2='90', length2='@waist_to_hip / 3')
            edge(p('Side_lower'), p('Hip_side'), p('Hem_side'))
            edge(p('Hem'), p('Hem_side'), p('Hem_centre'))
            edge(p('Centre'), p('A'), p('Hem_centre'))
            result = m.call('create_piece', x=xbase + 80, y=300, name=piece_name, allowance='10')
            pieces[piece_name] = result['id']
            m.call('set_edge_allowance', name=piece_name, edge=p('Hem'), allowance='30')
            m.call('set_grainline', name=piece_name, angle='90')
            m.call('set_cut', name=piece_name, count=2 if prefix == 'B' else 1, mirrored=prefix == 'B')
            if prefix == 'F':
                m.call('set_fold', name=piece_name, edge=p('Centre'))
            else:
                m.call('set_edge_allowance', name=piece_name, edge=p('Centre'), allowance='15')
                point(p('Zip_end'), base=p('A'), dx='0', dy='#zip_length')
                point(p('Slit_top'), base=p('A'), dx='0', dy='@skirt_length - #slit_height')
                m.call('add_notch', name=piece_name, point=p('Zip_end'))
                m.call('add_notch', name=piece_name, point=p('Slit_top'))
            # Keep the complete dart fabric. Its legs are internal stitch marks.
            edge(p('Dart_leg_1'), p('Dart_left'), p('Dart_tip'), role='stitch')
            edge(p('Dart_leg_2'), p('Dart_tip'), p('Dart_right'), role='stitch')
            m.call('set_marker', name=p('Dart_tip'), marker='match', size='2')
            edge(p('Hip_guide'), p('Hip_centre'), p('Hip_side'), role='placement')
            for suffix in ['Hip_side', 'Dart_left', 'Dart_right']:
                m.call('add_notch', name=piece_name, point=p(suffix))
            m.call('add_note', name=p('Info'), anchor={'point': p('A')}, dx='35', dy='330', size=10,
                   text=('BACK | EU40\nCUT 2 MIRRORED\nCentre back: 15 mm\nZip 200 / slit 180 mm' if prefix == 'B' else
                         'FRONT | EU40\nCUT 1 ON FOLD\nKeep dart fabric\nSew marked dart legs'))
            m.call('add_note', name=p('Hem_note'), anchor={'point': p('A')}, dx='40',
                   dy='@skirt_length - 45', size=9, text='HEM: 30 mm included')

        # Single folded waistband, including fastening overlap.
        point('WB_A', x='0', y='700')
        band = m.call('add_rectangle', corner='WB_A', width='@waist + #waist_ease + #waistband_overlap',
                      height='2 * #waistband_height', role='outline')
        for obj, name in zip(band, ['WB_Attach', 'WB_End', 'WB_Upper', 'WB_Start']):
            m.call('rename', id=obj['id'], newName=name)
        piece = m.call('create_piece', x=200, y=730, name='Waistband', allowance='10')
        pieces['Waistband'] = piece['id']
        m.call('set_grainline', name='Waistband', angle='0')
        m.call('set_cut', name='Waistband', count=1)
        point('WB_Fold_start', base='WB_A', dx='0', dy='#waistband_height')
        point('WB_Fold_end', base='WB_A', dx='@waist + #waist_ease + #waistband_overlap', dy='#waistband_height')
        edge('WB_Fold', 'WB_Fold_start', 'WB_Fold_end', role='fold')
        point('WB_Overlap_start', base='WB_A', dx='@waist + #waist_ease', dy='0')
        point('WB_Overlap_end', base='WB_Overlap_start', dx='0', dy='2 * #waistband_height')
        edge('WB_Overlap', 'WB_Overlap_start', 'WB_Overlap_end', role='placement')
        for position in [
            '#back_hip - #side_take - #back_dart',
            '(@waist + #waist_ease) / 2',
            '@waist + #waist_ease - (#back_hip - #side_take - #back_dart)',
            '@waist + #waist_ease',
        ]:
            m.call('add_notch', name='Waistband', edge='WB_Attach', position=position)
        m.call('add_note', name='WB_Info', anchor={'point': 'WB_A'}, dx='20', dy='12', size=9,
               text='WAISTBAND | CUT 1 MAIN + 1 FUSIBLE | FOLD TO 40 mm | 30 mm OVERLAP')

        seam = m.call('add_seam', name='Side_seam_match',
                      sideA=[{'piece': 'Back', 'edge': 'B_Side_curve'}, {'piece': 'Back', 'edge': 'B_Side_lower'}],
                      sideB=[{'piece': 'Front', 'edge': 'F_Side_curve'}, {'piece': 'Front', 'edge': 'F_Side_lower'}],
                      tolerance='0.5', ease='0')
        evaluation = m.call('evaluate')
        assert not evaluation['problems'] and evaluation.get('blocked', 0) == 0, evaluation
        report = m.call('check')
        write_json('validation-opensloper.json', report)
        m.call('save')
        m.render(ROOT / 'draft-preview.svg', 'svg', labels=False, hiddenRoles=['construction'])
        m.render(ROOT / 'draft-preview.png', 'png', width=1800, labels=False, hiddenRoles=['construction'])

        objects = m.call('list_objects')
        byname = {obj['name']: obj for obj in objects['objects']}
        variables = {obj['name']: obj for obj in objects['variables']}
        write_json('computed-objects.json', objects)
        # Check the sewn waist, ignoring the dart caps that fold into the darts.
        sewn_waist = 2 * sum(byname[n]['length'] for n in
                             ['B_Waist_centre', 'B_Waist_outer', 'F_Waist_centre', 'F_Waist_outer'])
        assert math.isclose(sewn_waist, 750, abs_tol=0.01), sewn_waist
        for prefix in ['B', 'F']:
            assert math.isclose(byname[prefix+'_Dart_leg_1']['length'],
                                byname[prefix+'_Dart_leg_2']['length'], abs_tol=0.01)
        side_b = byname['B_Side_curve']['length'] + byname['B_Side_lower']['length']
        side_f = byname['F_Side_curve']['length'] + byname['F_Side_lower']['length']
        assert abs(side_b - side_f) < 0.01
        summary = {'source': 'https://www.burdastyle.com/how-to-take-measurements',
                   'size': 'Burda regular 40', 'body_waist_mm': 740, 'body_hip_mm': 980,
                   'sewn_waist_mm': sewn_waist, 'finished_hip_mm': 1020,
                   'skirt_body_length_mm': 600, 'waistband_finished_height_mm': 40,
                   'side_seams_mm': [side_b, side_f], 'side_seam_difference_mm': abs(side_b-side_f),
                   'dart_intakes_mm': {'back_each': 40.5, 'front_each': 27},
                   'problems': evaluation['problems'], 'mcp_call_count_before_export': len(m.log)}
        write_json('validation-summary.json', summary)

        # Print one paper template per unique piece; Back says CUT 2 MIRRORED.
        # Positions are relative to the piece's cutting-line bounding rectangle.
        layout = {'format': 'layout', 'version': 1, 'units': 'mm',
                  'name': 'Straight skirt EU40 | W74 H98 | 100 percent', 'nextId': 2,
                  'sources': [{'id': 1, 'pattern': pattern_path.name}],
                  'output': {'kind': 'tiled', 'paper': 'A4', 'margin': 6, 'overlap': 10,
                             'marks': 'diamond', 'fill': 'none'},
                  'placements': [
                      {'source': 1, 'piece': pieces['Back'], 'copy': 1, 'x': 5, 'y': 5, 'rotation': 0},
                      {'source': 1, 'piece': pieces['Front'], 'copy': 1, 'x': 295, 'y': 5, 'rotation': 0},
                      {'source': 1, 'piece': pieces['Waistband'], 'copy': 1, 'x': 5, 'y': 665, 'rotation': 0},
                  ],
                  'titleBlock': {'corner': 'bottomRight', 'fields': ['pattern.name', 'measurements.name'], 'everyPage': False}}
        write_json('print-a4.slayout', layout)
        m.call('export', layout=str(ROOT/'print-a4.slayout'), path=str(ROOT/'print-a4.pdf'), format='pdf')
        layout['output'] = {'kind': 'large', 'rollWidth': 914, 'margin': 10, 'fill': 'none'}
        write_json('print-fullsize.slayout', layout)
        m.call('export', layout=str(ROOT/'print-fullsize.slayout'), path=str(ROOT/'print-fullsize.pdf'), format='pdf')
        m.call('export', layout=str(ROOT/'print-fullsize.slayout'), path=str(ROOT/'cutting-layout.svg'), format='svg')
        m.call('export', layout=str(ROOT/'print-fullsize.slayout'), path=str(ROOT/'cutting-layout.dxf'), format='dxf')
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print('MCP calls:', len(m.log))
    finally:
        m.close()


if __name__ == '__main__':
    main()
