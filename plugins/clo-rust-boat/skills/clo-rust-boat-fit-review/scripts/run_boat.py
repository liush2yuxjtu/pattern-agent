#!/usr/bin/env python3
"""Send one prepared CLO batch to an already running Boat sandbox."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile

from batch_io import native_maps, read_manifest, seam_sources
from boat_batch import ARCH, MODES

SCRIPTS = Path(__file__).resolve().parent
RUNTIME = SCRIPTS.parents[2] / "assets/runtime"

BOOTSTRAP = """
from pathlib import Path
import shutil
import subprocess
import sys

job = Path(sys.argv[1])
uploaded = job.with_suffix(".zip")
job.mkdir()
shutil.unpack_archive(uploaded, job, "zip")
subprocess.run([sys.executable, "boat_batch.py", *sys.argv[2:]], cwd=job, check=True)
shutil.make_archive(str(job) + "-results", "zip", job / "results")
uploaded.unlink()
"""


def collect(mode, inputs):
    files = list(seam_sources(inputs, required=mode == "seam-walk"))
    if mode != "seam-walk":
        files.append(inputs / "manifest.json")
        manifest = read_manifest(inputs)
        for pose in manifest["poses"]:
            files.append(inputs / (pose["id"] + ".glb"))
            for pair in native_maps(inputs, pose).values():
                files.extend(path for path in pair if path.is_file())
                if mode == "fit-export" and not all(path.is_file() for path in pair):
                    raise ValueError(f'姿势 {pose["label"]} 缺少 CLO 原生试穿或应力图')
        if (inputs / "line-art.png").is_file():
            files.append(inputs / "line-art.png")
    return files


def copy_file(path, inputs, target):
    relative = path.relative_to(inputs)
    if path.resolve() != path.absolute() or not path.is_file():
        raise ValueError(f"需要普通文件：{relative}")
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)


def run(args):
    if args.output.exists():
        raise ValueError("结果目录已存在")
    if not re.fullmatch(r"bx_[A-Za-z0-9]+", args.sandbox):
        raise ValueError("需要实际 Boat sandbox ID")
    source = args.input.resolve()
    files = collect(args.mode, source)
    boat = [args.boat, "--no-update"]
    remote = f"clo-batch-{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix="clo-boat-") as folder:
        stage = Path(folder) / remote
        for path in files:
            copy_file(path, source, stage / "inputs")
        for filename in ("batch_io.py", "boat_batch.py", "run_review.py", "requirements.txt"):
            shutil.copyfile(SCRIPTS / filename, stage / filename)
        command = [args.mode, "inputs", "results"]
        hashes = {}
        if args.remote_native:
            command.extend(["--native", args.remote_native])
        else:
            hashes = json.loads((RUNTIME / "sha256.json").read_text())
            runtime = stage / "runtime"
            runtime.mkdir()
            for architecture in ("x86_64", "aarch64"):
                if architecture in hashes:
                    copy_file(RUNTIME / architecture / "pattern-native", RUNTIME, runtime)
            shutil.copyfile(RUNTIME / "sha256.json", runtime / "sha256.json")
            command.extend(["--runtime", "runtime"])
        uploaded = shutil.make_archive(str(stage), "zip", stage)
        print(f"Boat 工作目录 {remote}", flush=True)
        subprocess.run([*boat, "scp", uploaded, f"{args.sandbox}:{remote}.zip"], check=True)
        subprocess.run([*boat, "exec", "--timeout", str(args.timeout), args.sandbox,
                        "--", args.python, "-c", BOOTSTRAP, remote, *command], check=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".clo-boat-result-", dir=args.output.parent) as downloaded:
            destination = Path(downloaded) / "results"
            archive = Path(downloaded) / "results.zip"
            subprocess.run([*boat, "scp", f"{args.sandbox}:{remote}-results.zip", str(archive)], check=True)
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(destination)
            receipt = json.loads((destination / "run.json").read_text())
            if receipt["mode"] != args.mode or receipt["runtime"] != "Boat Linux":
                raise ValueError("Boat 结果回执与批次不一致")
            if hashes and hashes[ARCH[receipt["machine"]]] != receipt["binary_sha256"]:
                raise ValueError("Boat 回执中的二进制摘要不一致")
            destination.rename(args.output)



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sandbox")
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--boat", default="boat")
    parser.add_argument("--python", default="python3", help="Python executable in the sandbox")
    parser.add_argument("--remote-native", help="Explicit native executable path on Boat")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
