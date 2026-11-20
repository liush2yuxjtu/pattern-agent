#!/usr/bin/env python3
"""Independently reassemble this benchmark's rendered A4 tile vectors.

The four exporters use different stroke styles and row spacings. The settings
below identify those styles and spacings, so this is an audit of the recorded
benchmark rather than a general-purpose PDF tile reader.
"""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re

import ezdxf
import fitz
from shapely.affinity import translate
from shapely.geometry import LineString, box
from shapely.ops import unary_union


POINTS_PER_MM = 72 / 25.4
TOLERANCE_MM = 0.05
COLUMN_STEP_MM = 180


@dataclass(frozen=True)
class ExportStyle:
    row_step_mm: int
    cutting_stroke_pt: float
    net_stroke_pt: float
    solid_net: bool = False
    black_cutting_only: bool = False


EXPORT_STYLES = {
    (33, 'old_skill'): ExportStyle(250, 0.8, 0.45),
    (33, 'with_skill'): ExportStyle(255, 0.992126, 0.651969, solid_net=True),
    (34, 'old_skill'): ExportStyle(265, 1.133858, 0.708661),
    (34, 'with_skill'): ExportStyle(265, 0.85, 0.55, black_cutting_only=True),
}
TILE_POS = re.compile(r'(?:ROW |R)(\d+)(?:/\d+)? +(?:COLUMN |C)(\d+)', re.I)


def points_to_mm(point):
    return point.x / POINTS_PER_MM, point.y / POINTS_PER_MM


def registration_crosses(drawings):
    axes = set()
    for drawing in drawings:
        for item in drawing.get('items', []):
            if item[0] != 'l':
                continue
            a, b = item[1:]
            if abs(a.distance_to(b) / POINTS_PER_MM - 4) >= 0.02:
                continue
            if abs(a.y - b.y) < 0.01:
                direction = 'h'
            elif abs(a.x - b.x) < 0.01:
                direction = 'v'
            else:
                continue
            x = round((a.x + b.x) / (2 * POINTS_PER_MM), 2)
            y = round((a.y + b.y) / (2 * POINTS_PER_MM), 2)
            axes.add((x, y, direction))
    return {(x, y) for x, y, direction in axes
            if direction == 'h' and (x, y, 'v') in axes}


def outline_layer(drawing, style):
    if drawing['type'] not in ('s', 'fs'):
        return None
    width = drawing['width']
    dashed = drawing['dashes'] != '[] 0'
    if abs(width - style.cutting_stroke_pt) < 0.001 and not dashed:
        if style.black_cutting_only and tuple(drawing['color']) != (0.0, 0.0, 0.0):
            return None
        return 'CUT'
    if abs(width - style.net_stroke_pt) < 0.001 and (dashed or style.solid_net):
        return 'NET'
    return None


def read_tiles(pdf, case_id, style):
    segments = {}
    crosses = {}
    pdf_pages = len(pdf)
    for page in list(pdf)[1:]:
        page_text = page.get_text()
        match = TILE_POS.search(page_text)
        if not match:
            raise ValueError(f'Cannot identify tile on PDF page {page.number + 1}')
        row, column = map(int, match.groups())
        if case_id == 34:
            piece = 'APRON'
        elif 'FRONT' in page_text:
            piece = 'FRONT'
        elif 'BACK' in page_text:
            piece = 'BACK'
        else:
            raise ValueError(f'Cannot identify piece on PDF page {page.number + 1}')
        key = (piece, row, column)
        if key in crosses:
            raise ValueError(f'Duplicate tile {key}')
        drawings = page.get_drawings(extended=True)
        clip = next((item['scissor'] for item in drawings if item['type'] == 'clip'), page.rect)
        visible_area = box(*(value / POINTS_PER_MM for value in clip))
        crosses[key] = registration_crosses(drawings)
        for drawing in drawings:
            layer = outline_layer(drawing, style)
            if not layer:
                continue
            for item in drawing['items']:
                if item[0] != 'l':
                    continue
                a, b = item[1:]
                visible = LineString([points_to_mm(a), points_to_mm(b)]).intersection(visible_area)
                if visible.length:
                    assembled = translate(visible, xoff=(column - 1) * COLUMN_STEP_MM,
                                          yoff=(row - 1) * style.row_step_mm)
                    segments.setdefault((piece, layer), []).append(assembled)
    return segments, crosses, pdf_pages


def read_dxf_outlines(dxf):
    outlines = {}
    for entity in dxf.modelspace().query('LWPOLYLINE'):
        layer = entity.dxf.layer
        if not layer.endswith(('_CUT', '_NET')):
            continue
        key = tuple(layer.rsplit('_', 1))
        if key in outlines or not entity.closed:
            raise ValueError(f'Expected exactly one closed contour on {layer}')
        # Flip the CAD Y coordinate to match PDF page coordinates.
        points = [(x, -y) for x, y in entity.get_points('xy')]
        outlines[key] = LineString(points + [points[0]])
    return outlines


def compare_contours(segments, outlines):
    if set(segments) != set(outlines):
        raise ValueError('The PDF and DXF contour identities differ')
    assembled = {key: unary_union(lines) for key, lines in segments.items()}
    contours = []
    for (piece, layer), actual in sorted(assembled.items()):
        actual_cut = assembled[piece, 'CUT']
        expected_cut = outlines[piece, 'CUT']
        dx = actual_cut.bounds[0] - expected_cut.bounds[0]
        dy = actual_cut.bounds[1] - expected_cut.bounds[1]
        expected = translate(outlines[piece, layer], xoff=dx, yoff=dy)
        missing = expected.difference(actual.buffer(TOLERANCE_MM)).length
        extra = actual.difference(expected.buffer(TOLERANCE_MM)).length
        contours.append({'piece': piece, 'layer': layer,
                         'missing_length_mm': round(missing, 6),
                         'extra_length_mm': round(extra, 6)})
    return contours


def compare_registration(crosses, style, pieces):
    expected = {(piece, row, column) for piece in pieces
                for row in range(1, 4) for column in range(1, 5)}
    if set(crosses) != expected:
        raise ValueError(f'Tile grid mismatch. Missing {sorted(expected - set(crosses))}, '
                         f'extra {sorted(set(crosses) - expected)}')
    neighbors = []
    for (piece, row, column), origin in sorted(crosses.items()):
        options = ((0, 1, COLUMN_STEP_MM, 0), (1, 0, 0, style.row_step_mm))
        for delta_row, delta_column, dx, dy in options:
            target = (piece, row + delta_row, column + delta_column)
            if target not in crosses:
                continue
            aligned = {(x, y) for x, y in origin
                       if (round(x - dx, 2), round(y - dy, 2)) in crosses[target]}
            neighbors.append({'piece': piece, 'from': [row, column],
                              'to': [target[1], target[2]],
                              'aligned_crosses': len(aligned)})
    return neighbors


def audit(workspace):
    runs = []
    for target in sorted(workspace.glob('eval-*/*/outputs')):
        case_id = int(target.parent.parent.name.split('-')[1])
        mode = target.parent.name
        if (case_id, mode) not in EXPORT_STYLES:
            continue
        style = EXPORT_STYLES[case_id, mode]
        pieces = ['FRONT', 'BACK'] if case_id == 33 else ['APRON']
        for version in ('base', 'revision'):
            directory = target / version
            metadata = {'case': case_id, 'configuration': mode, 'variant': version}
            try:
                dxf = ezdxf.readfile(directory / 'pattern.dxf')
                if dxf.units != 4:
                    raise ValueError(f'{directory} DXF is not in millimeters')
                outlines = read_dxf_outlines(dxf)
                with fitz.open(directory / 'a4.pdf') as pdf:
                    segments, crosses, page_count = read_tiles(pdf, case_id, style)
                contours = compare_contours(segments, outlines)
                neighbors = compare_registration(crosses, style, pieces)
            except (OSError, RuntimeError, ValueError, ezdxf.DXFError) as exc:
                runs.append({**metadata, 'passed': False, 'error': str(exc)})
                continue
            matched = sum(row['aligned_crosses'] >= 2 for row in neighbors)
            passed = matched == len(neighbors) and all(
                row['missing_length_mm'] == row['extra_length_mm'] == 0 for row in contours)
            runs.append({**metadata, 'pages': page_count, 'column_step_mm': COLUMN_STEP_MM,
                         'row_step_mm': style.row_step_mm, 'contours': contours,
                         'adjacent_pairs_matched': matched, 'adjacent_pairs_total': len(neighbors),
                         'neighbors': neighbors, 'passed': passed})
    if len(runs) != 8:
        raise ValueError(f'Expected eight exported artifact sets, found {len(runs)}')
    return {'scope': 'PDF vector geometry and printed registration marks represented in the file',
            'physical_print_tested': False, 'distance_tolerance_mm': TOLERANCE_MM,
            'runs': runs, 'passed': all(run['passed'] for run in runs)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    result = audit(args.workspace)
    args.receipt.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    for run in result['runs']:
        detail = run.get('error') or f"{run['adjacent_pairs_matched']}/{run['adjacent_pairs_total']} joins"
        print(f"{run['case']}/{run['configuration']}/{run['variant']}: {detail}, {'PASS' if run['passed'] else 'FAIL'}")
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
