"""Verify the built or published Pattern Agent gallery and its source assets."""
from argparse import ArgumentParser
from csv import DictReader
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import gzip
import json
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from playwright_http import new_api_context
from verify_pages import local_site

GALLERY = "pattern-library/"
SAMPLES = ("sandy-standard", "sandy-flared", "shirt-cuff")
VIEWS = ("angle", "front", "back")
SVG = "{http://www.w3.org/2000/svg}"


def digest(content):
    return sha256(content).hexdigest()


def check_sandy(sample, assets, evidence):
    draft, render = evidence["draft"], evidence["render"]
    assert draft["verification"] == draft["independent"]["verdict"] == "PASS"
    assert draft["freesewing"]["version"] == "4.10.2"
    assert draft["steps"] == 120
    assert draft["independent"]["cloth_self_intersections"] == 0
    assert draft["independent"]["body_triangle_intersections"] == 0
    raw_state = gzip.decompress(assets[sample["state"]])
    assert digest(raw_state) == draft["source_state_sha256"] == render["geometry_sha256"]
    assert digest(assets[sample["native"]]) == draft["native_svg_sha256"]
    state = json.loads(raw_state)
    assert state["freesewing"]["length_mm"] == draft["case"]["length_mm"]
    assert len(state["panels"]) == 4
    svg = ET.fromstring(assets[sample["preview"]])
    outlines = svg.findall(f".//{SVG}polygon")
    expected = [piece[key] for piece in state["panels"] for key in ("cutOutline", "polygon")]
    assert len(outlines) == len(expected) == 8
    for outline, polygon in zip(outlines, expected, strict=True):
        assert len(outline.attrib["points"].split()) == len(polygon)

    obj = assets[sample["model"]].decode().splitlines()
    points = [float(axis) for line in obj if line.startswith("v ") for axis in line.split()[1:]]
    uv = [float(axis) for line in obj if line.startswith("vt ") for axis in line.split()[1:]]
    faces = [corner for line in obj if line.startswith("f ") for corner in line.split()[1:]]
    assert len(points) == render["vertices"] * 3 == len(state["positions"])
    assert len(faces) == render["faces"] * 3 == len(state["triangles"])
    assert len(uv) == 2 * len(faces) == len(state["materialCoordinates"])
    for actual, saved in ((points, state["positions"]), (uv, state["materialCoordinates"])):
        assert max(abs(x-y) for x, y in zip(actual, saved, strict=True)) < 1e-10
    for corner, (indices, vertex) in enumerate(zip(faces, state["triangles"], strict=True)):
        assert indices == f"{vertex+1}/{corner+1}"


def wait_image(page, selector, url):
    page.wait_for_function(
        """([selector, url]) => {
            const image = document.querySelector(selector);
            return image.currentSrc.endsWith(url) && image.complete && image.naturalWidth > 0;
        }""",
        arg=[selector, url],
    )


def run(base, output, expected_commit, browser_executable):
    base = base.rstrip("/") + "/"
    gallery = urljoin(base, GALLERY)
    output.mkdir(parents=True, exist_ok=True)
    failures = []
    with sync_playwright() as playwright:
        api = new_api_context(playwright, base)
        browser = playwright.chromium.launch(executable_path=browser_executable, args=["--no-sandbox"])
        try:
            def get(url):
                response = api.get(url, timeout=45000)
                assert response.status == 200, (url, response.status)
                return response.body()

            build = json.loads(get(urljoin(base, "build.json")))
            if expected_commit:
                assert build["commit"] == expected_commit, (build["commit"], expected_commit)
            manifest_contents = get(urljoin(gallery, "gallery/manifest.json"))
            assert digest(manifest_contents) == build["files"][GALLERY + "gallery/manifest.json"]
            manifest = json.loads(manifest_contents)
            assert manifest["schema"] == "pattern-agent-gallery/1"
            assert tuple(s["id"] for s in manifest["samples"]) == SAMPLES
            assets = {}
            for file, expected in manifest["sha256"].items():
                url = urljoin(gallery, file)
                content = get(url)
                assert digest(content) == expected == build["files"][url.removeprefix(base)], file
                assets[file] = content

            mesh_checks = {}
            for sample in manifest["samples"]:
                file = sample["evidence"]
                evidence = json.loads(assets[file])
                assert evidence["physical_fit"] == "NOT_RUN"
                if sample["id"].startswith("sandy"):
                    check_sandy(sample, assets, evidence)
                else:
                    decision = evidence["decision"]
                    assert decision["verdict"] == "PASS" and decision["seams"] == 15
                    assert evidence["render"]["geometry_sha256"] == decision["model_sha256"] == digest(assets[sample["model"]])
                    assert assets[sample["model"]].startswith(b"glTF")
                    independent = json.loads(get(urljoin(urljoin(gallery, file), evidence["verification"])))
                    assert independent["verdict"] == "PASS"
                hashes = set()
                for view in VIEWS:
                    image = assets[sample["views"][view]]
                    hashes.add(digest(image))
                    with Image.open(BytesIO(image)) as picture:
                        assert picture.size == (940, 840) and picture.format == "WEBP"
                        thumbnail = picture.convert("RGB").resize((47, 42))
                        pixels = thumbnail.load()
                        fabric = [(row, column) for row in range(42) for column in range(47)
                                  if max(pixels[column, row])-min(pixels[column, row]) > 32]
                        assert len(fabric) > 100, (sample["id"], view)
                        assert all(0 < row < 41 and 0 < column < 46 for row, column in fabric), (sample["id"], view)
                assert len(hashes) == 3
                mesh_checks[sample["id"]] = {
                    "vertices": evidence["render"]["vertices"],
                    "faces": evidence["render"]["faces"],
                    "renders": {view: manifest["sha256"][sample["views"][view]] for view in VIEWS},
                }

            def browser_issue(message):
                failures.append(message)
            context = browser.new_context(viewport={"width": 1440, "height": 1040}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda error: browser_issue(str(error)))
            page.on("console", lambda event: browser_issue(event.text) if event.type == "error" else None)
            page.on("requestfailed", lambda req: browser_issue(f"{req.url} {req.failure}") if req.failure != "net::ERR_ABORTED" else None)
            page.on("response", lambda res: browser_issue(f"{res.status} {res.url}") if res.status >= 400 else None)
            assert page.goto(base, wait_until="networkidle", timeout=60000).ok
            page.get_by_role("link", name="纸样与三维图册").click()
            page.get_by_role("heading", name="纸样与三维图册").wait_for()
            assert page.url == gallery
            for sample in manifest["samples"]:
                button = page.locator(f'[data-sample="{sample["id"]}"]')
                button.click()
                assert button.get_attribute("aria-pressed") == "true"
                wait_image(page, "#pattern-img", sample["preview"])
                assert page.locator("#sample-name").inner_text() == sample["name"]
                for view in VIEWS:
                    button = page.locator(f'[data-view="{view}"]')
                    button.click()
                    assert button.get_attribute("aria-pressed") == "true"
                    wait_image(page, "#render-img", sample["views"][view])
                    assert f"sample={sample['id']}&view={view}" in page.url
                page.locator('[data-view="angle"]').click()
                wait_image(page, "#render-img", sample["views"]["angle"])
                page.screenshot(path=str(output / f"{sample['id']}.png"), animations="disabled")

            page.locator("#zoom-pattern").focus()
            page.keyboard.press("Enter")
            assert page.locator("#pattern-dialog").is_visible()
            wait_image(page, "#enlarged-pattern", "gallery/shirt-cuff/preview.svg")
            page.keyboard.press("Escape")
            assert not page.locator("#pattern-dialog").is_visible()
            assert page.locator("#zoom-pattern").evaluate("(node) => document.activeElement === node")
            for mode, path in {
                "before": "edits/original.svg",
                "after": "editor/example-output/edited.svg",
                "overlay": "editor/example-output/before-after.svg",
            }.items():
                button = page.locator(f'[data-edit="{mode}"]')
                button.click()
                assert button.get_attribute("aria-pressed") == "true"
                wait_image(page, "#edit-img", path)
            page.locator("#editor").screenshot(path=str(output / "editor.png"), animations="disabled")

            downloads = {}
            for selector in (
                "#pattern-download", "#model-download", 'a[href="downloads/pattern-agent-editor.zip"]',
                'a[href="editor/example-output/edit.patch.yaml"]',
                'a[href="editor/example-output/edited.dxf"]',
                'a[href="data/pattern-assets.csv"]', 'a[href="data/feedback-catalog.csv"]',
                'a[href="data/feedback-derived-intents.yaml"]',
            ):
                link = page.locator(selector).first
                url = urljoin(page.url, link.get_attribute("href"))
                with page.expect_download(timeout=45000) as event:
                    link.click()
                download = event.value
                assert not download.failure()
                destination = output / download.suggested_filename
                download.save_as(destination)
                checksum = digest(destination.read_bytes())
                assert checksum == build["files"][url.removeprefix(base)]
                downloads[destination.name] = checksum
            with ZipFile(output / "pattern-agent-editor.zip") as archive:
                assert archive.testzip() is None
                for name in ("edit.patch.yaml", "edited.dxf"):
                    assert digest(archive.read(f"pattern-agent-editor/example-output/{name}")) == downloads[name]
            rows = lambda file: list(DictReader(StringIO((output / file).read_text(encoding="utf-8-sig"))))
            patterns = rows("pattern-assets.csv")
            feedback = rows("feedback-catalog.csv")
            classes = {"project_baseline", "vendor_training", "public_tutorial"}
            originals = {row["sha256"] for row in patterns if row["dataset_class"] in classes}
            assert len(originals) == 38, sorted({row["dataset_class"] for row in patterns})
            assert len(feedback) == 36 and len({row["url"] for row in feedback}) == 28
            assert len({row["id"] for row in feedback}) == 36

            for width in (390, 375, 320):
                page.set_viewport_size({"width": width, "height": 840})
                assert page.goto(gallery + "?sample=sandy-flared&view=back", wait_until="networkidle").ok
                wait_image(page, "#render-img", "gallery/sandy-flared/back.webp")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.locator("#zoom-pattern").click()
                wait_image(page, "#enlarged-pattern", "gallery/sandy-flared/preview.svg")
                page.get_by_role("button", name="关闭纸样大图").click()
                assert not page.locator("#pattern-dialog").is_visible()
            page.screenshot(path=str(output / "mobile-320.png"), full_page=True, animations="disabled")
            assert page.goto(gallery + "?sample=missing&view=constructor", wait_until="networkidle").ok
            wait_image(page, "#render-img", "gallery/sandy-standard/angle.webp")
            assert page.locator("#gallery-problem").is_hidden()
            assert not failures, failures
            report = {
                "verdict": "PASS", "base_url": base, "commit": build["commit"],
                "source_sha256": build["source_sha256"], "hashed_gallery_assets": len(assets),
                "gallery_manifest_sha256": digest(manifest_contents),
                "meshes": mesh_checks, "record_counts": {"patterns": len(originals), "feedback": len(feedback)},
                "browser": {
                    "anonymous": True, "navigation": "home -> gallery",
                    "image_changes": 9, "edit_modes": 3, "deep_links": True, "invalid_query_fallback": True,
                    "keyboard_zoom_and_focus_restore": True, "mobile_widths": [390, 375, 320], "errors": failures,
                    "download_sha256": downloads,
                },
            }
            (output / "browser-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps(report, ensure_ascii=False, indent=2))
        finally:
            browser.close()
            api.dispose()


if __name__ == "__main__":
    cli = ArgumentParser(description=__doc__)
    cli.add_argument("--directory", type=Path, default=ROOT / "dist")
    cli.add_argument("--base-url")
    cli.add_argument("--expected-commit")
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--browser", default="/usr/bin/chromium")
    args = cli.parse_args()
    if args.base_url:
        run(args.base_url, args.output, args.expected_commit, args.browser)
    else:
        with local_site(args.directory) as url:
            run(url, args.output, args.expected_commit, args.browser)
