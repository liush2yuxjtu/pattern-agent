#!/usr/bin/env python3
"""Use the pinned Anthropic review generator and safely embed saved HTML outputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--benchmark', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    generator = ROOT / 'tools/skill_evals/upstream/eval-viewer/generate_review.py'
    subprocess.run([sys.executable, str(generator), str(args.workspace),
                    '--skill-name', 'garmentcode-preview', '--benchmark', str(args.benchmark),
                    '--static', str(args.output)], check=True)
    html = args.output.read_text()
    marker = 'const EMBEDDED_DATA = '
    assert html.count(marker) == 1, 'Pinned upstream embedding marker changed'
    start = html.index(marker) + len(marker)
    data, length = json.JSONDecoder().raw_decode(html[start:])
    # A literal </script> in an output preview closes the outer data script,
    # even inside a JSON string. Escape JSON data, never alter the pinned vendor.
    encoded = json.dumps(data, ensure_ascii=False).replace('<', r'\u003c')
    encoded = encoded.replace('\u2028', r'\u2028').replace('\u2029', r'\u2029')
    assert json.loads(encoded) == data, 'Escaping changed review data'
    args.output.write_text(html[:start] + encoded + html[start+length:])
    print(f'PASS: preserved official review data; escaped HTML script delimiters in {args.output}')


if __name__ == '__main__':
    main()
