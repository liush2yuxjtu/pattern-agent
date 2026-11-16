#!/usr/bin/env python3
"""Build the pinned GarmentCode Warp fork for Linux x86_64 CPU simulation.

Run inside the isolated Python environment described in references/setup.md.
The compiler wheel supplies only warp-clang.so; the custom solver stays intact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

COMMIT = '63baf6855efdd89b2834b74640f84b3bb0d86b50'


def run(*args, cwd=None):
    subprocess.run(list(map(str, args)), cwd=cwd, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--warp-repo', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    args = p.parse_args()
    repo, cache = args.warp_repo.resolve(), args.cache.resolve()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        p.error('This fallback is tested only on Linux x86_64. Use the upstream complete build on other platforms.')
    revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != COMMIT:
        p.error(f'Expected pinned custom Warp commit {COMMIT}, got {revision}')
    cache.mkdir(parents=True, exist_ok=True)
    # Prefer uv if present: a uv-created venv may intentionally omit pip.
    import shutil
    if shutil.which('uv'):
        run('uv', 'pip', 'install', '--python', sys.executable, 'pip')
    run(sys.executable, '-m', 'pip', 'download', '--no-deps', '--dest', cache, 'warp-lang==0.15.1')
    wheels = list(cache.glob('warp_lang-0.15.1-*manylinux2014_x86_64.whl'))
    if len(wheels) != 1:
        p.error('Expected exactly one official warp-lang 0.15.1 Linux x86_64 wheel.')
    run(sys.executable, 'build_lib.py', '--no_standalone', cwd=repo)
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as z:
        (repo / 'warp/bin/warp-clang.so').write_bytes(z.read('warp/bin/warp-clang.so'))
    # 0.15.1 compiler ABI adds verify_fp; the fork's older five-argument call
    # otherwise passes an undefined value, enabling invalid FP checks.
    build = repo / 'warp/build.py'
    old = 'runtime.llvm.compile_cpp(src, cpp_path, inc_path, obj_path, mode == "debug")'
    new = 'runtime.llvm.compile_cpp(src, cpp_path, inc_path, obj_path, mode == "debug", verify_fp)'
    text = build.read_text()
    if old in text:
        build.with_suffix('.py.before-compiler-shim').write_text(text)
        build.write_text(text.replace(old, new))
    elif new not in text:
        p.error('Unknown build_cpu implementation; refusing an unverified compatibility patch.')
    run(sys.executable, '-m', 'pip', 'install', '-e', repo, 'usd-core')
    manifest = {'warp_commit': COMMIT, 'compiler_wheel': wheel.name,
                'compiler_wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
                'compatibility_change': 'Add explicit verify_fp sixth argument to compiler call',
                'solver_replaced': False}
    (cache / 'cpu-build.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
