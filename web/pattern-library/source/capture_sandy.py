"""Save two real FreeSewing drafts and solved states from the existing runtime."""
from argparse import ArgumentParser
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import sys

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve()
ROOT = next(p for p in HERE.parents if (p / "experiments/freesewing_cloth_lab/independent.py").is_file())
sys.path.insert(0, str(ROOT / "experiments/freesewing_cloth_lab"))
from independent import run as audit

CASES = (
    {"id": "sandy-standard", "length_mm": 560, "circle_percent": 38.75, "material": "cotton"},
    {"id": "sandy-flared", "length_mm": 650, "circle_percent": 60, "material": "linen"},
)
STEPS = 120


def write_obj(path, state):
    points = state["positions"]
    uv = state["materialCoordinates"]
    faces = state["triangles"]
    def triples(values, size):
        return zip(*(values[i::size] for i in range(size)), strict=True)
    obj = ["# Pattern Agent FreeSewing Sandy. Metres, Y up. Skirt shell.", "o Sandy"]
    obj.extend(f"v {x:.10f} {y:.10f} {z:.10f}" for x, y, z in triples(points, 3))
    obj.extend(f"vt {x:.10f} {y:.10f}" for x, y in triples(uv, 2))
    if len(uv) != 2 * len(faces):
        raise ValueError("Sandy UVs must be provided per triangle corner")
    for i, face in enumerate(triples(faces, 3)):
        obj.append("f " + " ".join(f"{vertex+1}/{3*i+corner+1}" for corner, vertex in enumerate(face)))
    path.write_text("\n".join(obj) + "\n", encoding="utf-8")


def capture(destination, browser_executable):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=ROOT / "web"))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/freesewing-cloth-lab.html"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=browser_executable, args=["--no-sandbox","--enable-unsafe-swiftshader"])
            page = browser.new_page(viewport={"width": 1440, "height": 1050})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            for case in CASES:
                target = destination / case["id"]
                target.mkdir(parents=True, exist_ok=True)
                response = page.goto(url, wait_until="networkidle")
                assert response.ok, response.status
                page.wait_for_function("window.clothLab?.ready", timeout=30000)
                page.locator("#length").fill(str(case["length_mm"]))
                page.locator("#hem").fill(str(case["circle_percent"]))
                page.locator("#material").select_option(case["material"])
                initial = page.evaluate("clothLab.project().freesewing")
                assert initial["length_mm"] == case["length_mm"], initial["length_mm"]
                assert abs(initial["circleRatio"] * 100 - case["circle_percent"]) < 1e-6
                stats = page.evaluate("(n) => clothLab.step(n)", STEPS)
                current = page.evaluate("clothLab.verify()")
                state = page.evaluate("clothLab.project()")
                assert stats["steps"] == STEPS and current["verdict"] == "PASS", current["checks"]
                assert not errors, errors
                native = page.evaluate("clothLab.nativeSVG()")
                svg = page.evaluate("clothLab.patternSVG()")
                assert native and svg and state["freesewing"]["design"] == "Sandy"
                (target / "native.svg").write_text(native, encoding="utf-8")
                (target / "pattern.svg").write_text(svg, encoding="utf-8")
                (target / "state.json").write_text(json.dumps(state, separators=(",",":")), encoding="utf-8")
                write_obj(target / "skirt.obj", state)
                print(case["id"], "saved", stats, flush=True)

                independent = audit(state, ROOT, negative=False)
                result = {
                    "case": case,
                    "runtime": "web/freesewing-cloth-lab.html",
                    "runtime_sha256": sha256(response.body()).hexdigest(),
                    "freesewing": state["freesewing"],
                    "steps": STEPS,
                    "stats": stats,
                    "verification": current["verdict"],
                    "independent": independent,
                    "native_svg_sha256": sha256(native.encode()).hexdigest(),
                    "source_state_sha256": sha256((target / "state.json").read_bytes()).hexdigest(),
                    "physical_fit": "NOT_RUN",
                }
                (target / "draft-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                if independent["verdict"] != "PASS":
                    raise ValueError(f"Independent state check failed for {case['id']}: {independent}")
            browser.close()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", default="/usr/bin/chromium")
    args = parser.parse_args()
    capture(args.output.resolve(), args.browser)
