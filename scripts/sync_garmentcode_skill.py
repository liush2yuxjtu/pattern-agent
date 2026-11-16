#!/usr/bin/env python3
"""Publish the canonical agent skill as readable Pages files and a deterministic .skill."""
import argparse
from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.agents/skills/garmentcode-preview'
TARGET = ROOT / 'web/garmentcode-preview/skill/garmentcode-preview'
PACKAGE = ROOT / 'web/garmentcode-preview/garmentcode-preview.skill'


def source_files():
    return sorted(p for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                  and p.suffix != '.pyc')


def package_bytes():
    with tempfile.TemporaryDirectory() as folder:
        archive = Path(folder) / 'garmentcode-preview.skill'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
            for path in source_files():
                name = 'garmentcode-preview/' + path.relative_to(SOURCE).as_posix()
                info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                output.writestr(info, path.read_bytes())
        return archive.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files = source_files()
    expected = {p.relative_to(SOURCE).as_posix() for p in files}
    if args.check:
        actual = {p.relative_to(TARGET).as_posix() for p in TARGET.rglob('*') if p.is_file()}
        assert actual == expected, 'Readable published skill files differ from canonical source'
        for path in files:
            assert path.read_bytes() == (TARGET / path.relative_to(SOURCE)).read_bytes(), str(path)
        assert PACKAGE.read_bytes() == package_bytes(), 'Downloadable .skill is stale'
        print(f'PASS: {len(files)} canonical/published files and deterministic package match')
        return
    # Only replace this generated mirror; preserve other website artifacts and experiments.
    if TARGET.exists():
        shutil.rmtree(TARGET)
    for path in files:
        target = TARGET / path.relative_to(SOURCE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    PACKAGE.write_bytes(package_bytes())
    print(f'Published {len(files)} files and {PACKAGE.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
