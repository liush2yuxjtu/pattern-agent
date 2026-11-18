"""Command-line entry point for the pattern editor."""
import argparse
from base64 import b64decode, b64encode
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

import yaml

from .compiler import NeedsReview, compile_patch, open_source, replay_patch
from .formats import ROOT, FormatError, digest, dump_yaml, load_yaml, split
from .legacy import model_reader

SAMPLES = ROOT / "samples"
BASE_FILES = ("pattern-2d.yaml", "pattern-spec.yaml", "input.dxf")
INPUT_LIMIT = 15_000_000
ERRORS = (ValueError, KeyError, TypeError, IndexError, OSError, yaml.YAMLError, ArithmeticError)


def overlay(base, edited):
    old_rows = model_reader.drawables(base)
    new_rows = model_reader.drawables(edited)
    points = [
        p for rows in (old_rows, new_rows) for row in rows
        for p in (row["点位"] if row["线型"] != "文字" else [row["位置"]])
    ]
    x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
    y0, y1 = min(p[1] for p in points), max(p[1] for p in points)
    margin = 32
    box = f"{x0-margin} {-y1-margin} {x1-x0+2*margin} {y1-y0+2*margin}"
    drawing = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}" role="img">',
        '<title>改前与改后的二维纸样叠加</title>',
        '<desc>橙色虚线是改前，蓝色实线是改后。坐标使用原图形单位 U。</desc>',
    ]
    for layer, rows, color, width, dash in (
        ("before", old_rows, "#a5452e", "1.2", ' stroke-dasharray="4 3"'),
        ("after", new_rows, "#176b97", "1.3", ""),
    ):
        drawing.append(f'<g id="pattern-{layer}">')
        drawing.append(f'<g stroke="{color}" stroke-width="{width}" fill="none"{dash}>')
        for row in rows:
            if row["线型"] == "文字":
                continue
            pts = row["点位"] + ([row["点位"][0]] if row["闭合"] else [])
            coords = " ".join(f"{x:.6f},{-y:.6f}" for x, y in pts)
            drawing.append(f'<polyline points="{coords}" vector-effect="non-scaling-stroke"/>')
        drawing.append('</g><g fill="#274155" font-size="7" font-family="sans-serif">')
        for row in rows:
            if row["线型"] == "文字":
                x, y = row["位置"]
                drawing.append(f'<text x="{x:.6f}" y="{-y:.6f}">{escape(row["内容"])}</text>')
        drawing.append("</g></g>")
    drawing.append("</svg>")
    return ("\n".join(drawing) + "\n").encode()


def render_outputs(pattern, spec, dxf, patch_data):
    p, s, edited_cad, report, base, edited = replay_patch(pattern, spec, dxf, patch_data)
    files = {
        "edit.patch.yaml": patch_data,
        "edited-pattern.yaml": p,
        "edited-spec.yaml": s,
        "edited.dxf": edited_cad,
        "edited.svg": model_reader.export_svg(edited, model_reader.drawables(edited)).encode(),
        "before-after.svg": overlay(base, edited),
        "report.json": (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode(),
    }
    return files, report


def write_outputs(target, files):
    if target.exists():
        raise FormatError(f"Choose a new output directory: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Stage all files before moving the finished directory into place.
    with TemporaryDirectory(dir=target.parent) as temp:
        staged = Path(temp) / "complete"
        staged.mkdir()
        for name, content in files.items():
            (staged / name).write_bytes(content)
        staged.rename(target)


def cli():
    parser = argparse.ArgumentParser(description="Compile and replay fitted T-shirt pattern edits")
    cmd = parser.add_subparsers(dest="mode", required=True)
    split_args = cmd.add_parser("split", help="Split the Chinese v1.1 standalone YAML into 2D and 1D inputs")
    split_args.add_argument("--legacy-spec", type=Path, default=SAMPLES / "input-spec.yaml")
    split_args.add_argument("--dxf", type=Path, default=SAMPLES / "input.dxf")
    split_args.add_argument("--output", type=Path, required=True)
    for mode in ("compile", "apply", "run"):
        sub = cmd.add_parser(mode)
        sub.add_argument("--pattern", type=Path, default=SAMPLES / BASE_FILES[0])
        sub.add_argument("--spec", type=Path, default=SAMPLES / BASE_FILES[1])
        sub.add_argument("--dxf", type=Path, default=SAMPLES / BASE_FILES[2])
        if mode == "apply":
            sub.add_argument("--patch", type=Path, required=True)
        else:
            sub.add_argument("--intent", type=Path, default=SAMPLES / "intent.yaml")
        sub.add_argument("--output", type=Path, required=True)
    server = cmd.add_parser("serve", help="Open the workstation at a localhost URL")
    server.add_argument("--port", type=int, default=8765)
    return parser.parse_args()


class Workstation(BaseHTTPRequestHandler):
    def render(self, data, kind, status=200):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def json_response(self, data, status=200):
        self.render(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/":
            self.render((ROOT / "workstation.html").read_bytes(), "text/html; charset=utf-8")
        elif route == "/api/samples":
            files = {name: encode((SAMPLES / name).read_bytes()) for name in (*BASE_FILES, "intent.yaml")}
            self.json_response({"files": files})
        else:
            self.send_error(404)

    def do_POST(self):
        route = self.path
        if route not in ("/api/run", "/api/compile", "/api/replay"):
            self.send_error(404)
            return
        port = self.server.server_port
        if self.headers.get("Origin") not in (None, f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
            self.send_error(403)
            return
        try:
            size = int(self.headers.get("Content-Length", 0))
            if not 0 < size <= INPUT_LIMIT or self.headers.get_content_type() != "application/json":
                raise FormatError("A JSON body of 15 MB or less is required")
            body = json.loads(self.rfile.read(size))
            pattern, spec, drawing = (b64decode(body[name], validate=True) for name in ("pattern", "spec", "dxf"))
            if route != "/api/replay":
                patch, _ = compile_patch(pattern, spec, drawing, body["intent"].encode())
                patch_data = dump_yaml(patch)
            else:
                patch_data = b64decode(body["patch"], validate=True)
            if route == "/api/compile":
                files, report = {"edit.patch.yaml": patch_data}, {"result": "PASS", "scope": "Patch compiled"}
            else:
                files, report = render_outputs(pattern, spec, drawing, patch_data)
            self.json_response({"files": {k: encode(v) for k, v in files.items()}, "report": report})
        except NeedsReview as exc:
            self.json_response({"status": "NEEDS_REVIEW", "message": str(exc)}, 422)
        except ERRORS as exc:
            self.json_response({"status": "REJECTED", "message": str(exc)[:600]}, 400)


def encode(data):
    return b64encode(data).decode("ascii")


def main():
    args = cli()
    try:
        if args.mode == "serve":
            with ThreadingHTTPServer(("127.0.0.1", args.port), Workstation) as service:
                print(f"http://127.0.0.1:{service.server_port}", flush=True)
                service.serve_forever()
            return 0
        if args.mode == "split":
            model = load_yaml(args.legacy_spec.read_bytes())
            drawing = args.dxf.read_bytes()
            pattern, spec = split(model, digest(drawing))
            p, s = dump_yaml(pattern), dump_yaml(spec)
            open_source(p, s, drawing)
            write_outputs(args.output, {BASE_FILES[0]: p, BASE_FILES[1]: s})
        else:
            pattern, spec, dxf = (p.read_bytes() for p in (args.pattern, args.spec, args.dxf))
            if args.mode == "apply":
                patch_data = args.patch.read_bytes()
            else:
                patch, _ = compile_patch(pattern, spec, dxf, args.intent.read_bytes())
                patch_data = dump_yaml(patch)
            files = {"edit.patch.yaml": patch_data} if args.mode == "compile" else render_outputs(pattern, spec, dxf, patch_data)[0]
            write_outputs(args.output, files)
        print(json.dumps({"status": "PASS", "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (KeyboardInterrupt, BrokenPipeError):
        return 130
    except NeedsReview as exc:
        print(json.dumps({"status": "NEEDS_REVIEW", "message": str(exc)}, ensure_ascii=False))
        return 2
    except ERRORS as exc:
        print(json.dumps({"status": "REJECTED", "message": str(exc)[:600]}, ensure_ascii=False))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
