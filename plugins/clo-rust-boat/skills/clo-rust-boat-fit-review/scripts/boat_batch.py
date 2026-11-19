#!/usr/bin/env python3
"""Execute one packaged CLO Rust batch on Linux and publish complete results."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

from batch_io import review_seams, seam_sources

ARCH = {"x86_64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}
MODES = ("review", "seam-walk", "fit-export")


def select_binary(root, architecture=None):
    if platform.system() != "Linux" and architecture is None:
        raise ValueError("Boat 批处理需要 Linux")
    architecture = architecture or ARCH.get(platform.machine())
    if not architecture:
        raise ValueError(f"暂不支持 Linux {platform.machine()}")
    binary = root / architecture / "pattern-native"
    hashes = json.loads((root / "sha256.json").read_text())
    if hashlib.sha256(binary.read_bytes()).hexdigest() != hashes[architecture]:
        raise ValueError("Rust 二进制摘要不一致")
    return binary


def execute(args):
    output = args.output.resolve()
    inputs = args.input.resolve()
    if output.exists() or inputs == output or inputs in output.parents:
        raise ValueError("结果目录必须是输入目录之外的新路径")
    bundled = args.native is None
    binary = select_binary(args.runtime) if bundled else args.native.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".clo-boat-", dir=output.parent) as temp:
        staging = Path(temp)
        usable = staging / "pattern-native"
        shutil.copyfile(binary, usable)
        usable.chmod(0o700)
        results = staging / "results"
        if args.mode == "seam-walk":
            results.mkdir()
            notes = review_seams(usable, seam_sources(inputs, required=True), results)
            print("\n".join(notes))
        else:
            script = Path(__file__).resolve().with_name("run_review.py")
            command = [sys.executable, str(script), str(inputs), str(results),
                       "--native", str(usable), "--runtime-label", args.runtime_label]
            if args.mode == "fit-export":
                command.append("--require-all-maps")
            subprocess.run(command, check=True)
        receipt = {"mode": args.mode, "runtime": args.runtime_label, "machine": platform.machine(),
                   "binary_sha256": hashlib.sha256(usable.read_bytes()).hexdigest(),
                   "binary_source": "bundled" if bundled else "explicit"}
        (results / "run.json").write_text(json.dumps(receipt, indent=2) + "\n")
        results.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--runtime", type=Path, default=Path(__file__).resolve().parents[3] / "assets/runtime")
    parser.add_argument("--native", type=Path)
    parser.add_argument("--runtime-label", default="Boat Linux")
    args = parser.parse_args()
    try:
        execute(args)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
