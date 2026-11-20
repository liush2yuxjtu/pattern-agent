#!/usr/bin/env python3
"""Prove the artifact checker rejects damaged exports and accepts regenerated ones."""

import argparse
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import ezdxf
import fitz


SPEC = spec_from_file_location('zero_draft_grader', Path(__file__).with_name('grade-zero-draft.py'))
GRADER = module_from_spec(SPEC)
SPEC.loader.exec_module(GRADER)


def rejected(action):
    try:
        action()
    except ValueError as error:
        return str(error)
    raise AssertionError('Damage was not detected')


def exercise(trial, case):
    original=trial/'outputs/base'
    names=case['pieces']
    with tempfile.TemporaryDirectory(prefix='controls-',dir=trial) as temp:
        scratch=Path(temp)
        mislabeled=scratch/'inch.dxf'
        dxf=ezdxf.readfile(original/'pattern.dxf')
        dxf.units=1
        dxf.saveas(mislabeled)
        units=rejected(lambda:GRADER.read_dxf(mislabeled,names))

        scaled=scratch/'scaled.pdf'
        with fitz.open(original/'full.pdf') as source, fitz.open() as altered:
            for i,page in enumerate(source):
                paper=altered.new_page(width=page.rect.width,height=page.rect.height)
                smaller=fitz.Rect(0,0,paper.rect.width*.96,paper.rect.height*.96)
                paper.show_pdf_page(smaller,source,i)
            altered.save(scaled)
        scale=rejected(lambda:GRADER.pdf_detail(scaled,False))

        missing=scratch/'missing-tile.pdf'
        with fitz.open(original/'a4.pdf') as d:
            d.delete_page(len(d)//2)
            d.save(missing)
        pages=rejected(lambda:GRADER.pdf_detail(missing,True,names=names))

        rebuilt=scratch/'repaired'
        subprocess.run(['sh',str(trial/'outputs/rebuild.sh'),str(trial/'base.json'),str(rebuilt)],
                       cwd=trial, env=dict(os.environ,PATTERN_EVAL_PYTHON=sys.executable), check=True,
                       capture_output=True, timeout=45)
        shapes=GRADER.read_dxf(rebuilt/'pattern.dxf',names)
        return {'wrong_units_rejected':units,'96_percent_pdf_rejected':scale,'deleted_tile_rejected':pages,
                'repaired_dimensions':GRADER.dims_and_allowance(shapes,case['base'],names),
                'repaired_full':GRADER.pdf_detail(rebuilt/'full.pdf',False,[(shapes[f'{n}_NET'],shapes[f'{n}_CUT']) for n in names]),
                'repaired_a4':GRADER.pdf_detail(rebuilt/'a4.pdf',True,names=names)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace',type=Path)
    args=parser.parse_args()
    root=args.workspace.resolve()
    verified={case['name']:exercise(root/f'eval-{case["id"]}-{case["name"]}'/'with_skill',case) for case in GRADER.CASES}
    (root/'negative-controls.json').write_text(json.dumps(verified,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:'3 项损坏均被拒绝，重建通过' for key in verified},ensure_ascii=False))
