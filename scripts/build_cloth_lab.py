#!/usr/bin/env python3
"""Compatibility entry point for the canonical offline Node cloth-lab builder.

All arguments and the exit status are forwarded to web/cloth-lab/build.js.
Set NODE to select a local Node executable; ZIG, ESBUILD and PYTHON retain their
usual meanings in the builder. Run --help for the current command line.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def build(argv=None):
    node = os.environ.get('NODE') or shutil.which('node')
    if not node:
        print('cloth-lab: Node.js >=18 is required. Set NODE to its executable.', file=sys.stderr)
        return 1
    try:
        return subprocess.run([node, str(ROOT/'web/cloth-lab/build.js'),
                               *(sys.argv[1:] if argv is None else argv)], check=False).returncode
    except OSError as error:
        print(f'cloth-lab: Could not start Node.js: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(build())
