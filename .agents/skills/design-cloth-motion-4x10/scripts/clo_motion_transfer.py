"""Transfer evidence through the authenticated Boat command channel with SHA-256 verification."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from shlex import quote
import subprocess
import time


def cli(worker, command, *, stream=False):
    args = ["boat", "--no-update", "--json"]
    args.extend(["exec", worker, "--timeout", "60"])
    if stream:
        args.append("--stream")
    args.append(command)
    for attempt in range(3):
        try:
            completed = subprocess.run(args, capture_output=True, timeout=70)
            completed.check_returncode()
            if stream:
                events = [json.loads(line) for line in completed.stdout.splitlines()]
                if not events or events[-1].get("type") != "exit" or events[-1].get("exitCode") != 0:
                    raise RuntimeError("incomplete Boat output stream")
                return "".join(event["data"] for event in events if event.get("type") == "stdout").encode()
            data = json.loads(completed.stdout)
            if data.get("success"):
                return data["stdout"]
            raise RuntimeError(f"guest status {data.get('exitCode')}")
        except (RuntimeError, ValueError, subprocess.SubprocessError):
            if attempt == 2:
                raise RuntimeError("authenticated Boat file transfer command failed") from None
            time.sleep(1+attempt)


def put(worker, source, target, jobs=6, expected_sha=None):
    checksum = " | sha256sum --check --status -"
    if expected_sha is not None:
        check = "printf '%s  %s\\n' " + quote(expected_sha) + " " + quote(target) + checksum
        if cli(worker, "if " + check + " 2>/dev/null; then printf cached; fi") == "cached":
            return
    contents = source.read_bytes()
    sha = hashlib.sha256(contents).hexdigest()
    if expected_sha is not None and sha != expected_sha:
        raise ValueError("local Boat input changed after calculating its fingerprint")
    chunk_path = target + ".parts-" + sha[:12]
    cli(worker, "mkdir -p " + quote(chunk_path))
    block_size = 55_296  # One bounded, base64-encoded argument per Boat command.
    parts = list(range(0, len(contents), block_size))

    def send(offset):
        data = base64.b64encode(contents[offset:offset+block_size]).decode()
        path = chunk_path + "/%012d" % offset
        # The numbered part is retriable and never appends to an existing file.
        cli(worker, "printf %s " + quote(data)+" | base64 -d > "+quote(path))
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for _ in pool.map(send, parts):
            pass
    tmp = target + ".temp-" + sha[:12]
    cli(worker, "set -e; cat " + quote(chunk_path) + "/[0-9]* > " + quote(tmp)
        + "; printf '%s  %s\\n' " + quote(sha) + " " + quote(tmp) + " | sha256sum -c -; mv "
        + quote(tmp) + " " + quote(target) + "; rm -- " + quote(chunk_path) + "/[0-9]*"
        + "; rmdir -- " + quote(chunk_path))


def get(worker, source, target, jobs=5):
    remote = quote(source)
    sha, total = cli(worker, "set -e; sha256sum " + remote + " | cut -d ' ' -f1; stat -c %s " + remote).split()
    block_size = 1048576
    partial = target.with_suffix(target.suffix + ".partial")
    number = (int(total)+block_size-1)//block_size

    def receive(index):
        data = cli(worker, f"set -o pipefail; dd if={remote} bs={block_size} skip={index} count=1 status=none | base64", stream=True)
        value = base64.b64decode(b"".join(data.split()),validate=True)
        expected = min(block_size, int(total)-block_size*index)
        if len(value) != expected:
            raise ValueError(f"chunk {index}: received {len(value)}, expected {expected}")
        return value
    target.parent.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=jobs) as pool, partial.open("wb") as file:
        checksum=hashlib.sha256()
        for value in pool.map(receive, range(number)):
            file.write(value)
            checksum.update(value)
    if checksum.hexdigest() != sha:
        raise ValueError("Boat download differs from the remote SHA-256")
    partial.replace(target)
