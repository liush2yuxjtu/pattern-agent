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
from playwright.sync_api import expect, sync_playwright

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


def check_paper_assets(get, base, gallery, build):
    manifest_name = "paper-gallery/manifest.json"
    contents = get(urljoin(gallery, manifest_name))
    assert digest(contents) == build["files"][GALLERY + manifest_name]
    manifest = json.loads(contents)
    assert manifest["schema"] == "pattern-agent-paper-gallery/1"
    entries = manifest["entries"]
    assert len(entries) == len({entry["id"] for entry in entries}) == 26
    catalog = json.loads(get(urljoin(gallery, "catalog/cad.json")))
    by_id = {row["id"]: row for row in catalog["entries"]}
    research = [entry for entry in entries if entry["source"] == "zju"]
    assert len(research) == len({entry["sourceSha256"] for entry in research}) == 19
    assert {id_ for entry in research for id_ in entry["catalogIds"]} == {
        row["id"] for row in catalog["entries"] if row["source"] == "zju"
    }
    for entry in entries:
        if entry["source"] == "zju":
            assert entry["boundaryEdges"] > 1000 and entry["sourceMember"].endswith("2D.obj")
        elif entry.get("catalogIds"):
            assert entry["sourceSha256"] == by_id[entry["catalogIds"][0]]["sha256"]
        url = urljoin(gallery, entry["preview"])
        content = get(url)
        assert digest(content) == entry["previewSha256"] == build["files"][url.removeprefix(base)]
        if url.endswith(".svg"):
            root = ET.fromstring(content)
            assert root.tag == SVG + "svg"
            assert any(element.tag in {SVG + "path", SVG + "polygon", SVG + "polyline"} for element in root.iter())
        else:
            with Image.open(BytesIO(content)) as picture:
                assert picture.format == "WEBP" and picture.width == 1600
                grayscale = picture.convert("L")
                outlines = grayscale.point(lambda pixel: 255 if pixel < 150 else 0)
                assert outlines.histogram()[255] > 1000, entry["id"]
                left, top, right, bottom = outlines.getbbox()
                assert 0 < left < right < picture.width and 0 < top < bottom < picture.height, entry["id"]
                assert sum(grayscale.resize((160, 108)).histogram()[:220]) > 200, entry["id"]
    assert len({entry["previewSha256"] for entry in entries}) == 26
    return entries


def check_paper_page(page, gallery, entries, output):
    expect(page.get_by_role("heading", name="二维纸样图册")).to_be_visible()
    expect(page.locator("#paper-grid li")).to_have_count(len(entries))
    assert page.url == gallery
    assert page.locator("#render-img").count() == 0
    # Reopen each actual image at its rendered thumbnail, including lazy-loaded cards.
    for entry in entries:
        selector = f'[data-pattern="{entry["id"]}"] img'
        page.locator(selector).scroll_into_view_if_needed()
        wait_image(page, selector, entry["preview"].removeprefix("../"))
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=str(output / "paper-desktop.png"), animations="disabled")

    page.locator("#paper-source").select_option("zju")
    expect(page.locator("#paper-grid li")).to_have_count(19)
    page.locator("#paper-garment").select_option("裤装")
    expect(page.locator("#paper-grid li")).to_have_count(4)
    page.locator("#paper-query").fill("ZJU-06")
    expect(page.locator("#paper-grid li")).to_have_count(1)
    tile = page.locator('[data-pattern="zju-male-2-bottom"]')
    tile.focus()
    page.keyboard.press("Enter")
    dialog = page.get_by_role("dialog", name="男式运动裤 02")
    expect(dialog).to_be_visible()
    wait_image(page, "#paper-image", "paper-gallery/zju-male-2-bottom.webp")
    selected = next(entry for entry in entries if entry["id"] == "zju-male-2-bottom")
    expect(dialog.get_by_role("link", name="查看发布方")).to_have_attribute("href", selected["sourceUrl"])
    expect(dialog.get_by_role("link", name="打开原图")).to_have_attribute("href", selected["preview"])
    assert page.url.endswith("?pattern=zju-male-2-bottom")
    page.keyboard.press("Escape")
    expect(dialog).to_be_hidden()
    assert tile.evaluate("(link) => document.activeElement === link")
    page.locator("#paper-query").fill("does-not-exist")
    expect(page.locator("#paper-status")).to_contain_text("没有匹配的纸样")

    page.set_viewport_size({"width": 390, "height": 860})
    assert page.goto(gallery + "?pattern=pa-04", wait_until="networkidle").ok
    expect(page.get_by_role("dialog", name="无袖衣身 · v001")).to_be_visible()
    wait_image(page, "#paper-image", "paper-gallery/pa-04.svg")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    expect(page.locator("#paper-download")).to_have_attribute("href", "downloads/bodice-v001.dxf")
    page.screenshot(path=str(output / "paper-mobile-detail.png"), animations="disabled")
    page.get_by_role("button", name="关闭纸样大图").click()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path=str(output / "paper-mobile.png"), animations="disabled")
    page.set_viewport_size({"width": 1440, "height": 1040})

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

            paper_entries = check_paper_assets(get, base, gallery, build)
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
            page.get_by_role("link", name="二维纸样图册").click()
            check_paper_page(page, gallery, paper_entries, output)
            page.get_by_role("link", name="三维渲染案例").click()
            page.get_by_role("heading", name="三维渲染案例").wait_for()
            page.wait_for_url(gallery + "rendered.html")
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
            downloads = {}

            def download_file(selector):
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

            for selector in ("#pattern-download", "#model-download"):
                download_file(selector)
            page.get_by_role("link", name="打开改版工具").click()
            page.wait_for_url(gallery + "#editor")
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
            for selector in (
                'a[href="downloads/pattern-agent-editor.zip"]', 'a[href="editor/example-output/edit.patch.yaml"]',
                'a[href="editor/example-output/edited.dxf"]', 'a[href="catalog/cad-origins.csv"]',
                'a[href="catalog/review-design-intents.yaml"]',
            ):
                download_file(selector)
            with ZipFile(output / "pattern-agent-editor.zip") as archive:
                assert archive.testzip() is None
                for name in ("edit.patch.yaml", "edited.dxf"):
                    assert digest(archive.read(f"pattern-agent-editor/example-output/{name}")) == downloads[name]
            rows = lambda file: list(DictReader(StringIO((output / file).read_text(encoding="utf-8-sig"))))
            patterns = rows("cad-origins.csv")
            originals = {row["sha256"] for row in patterns}
            assert len(originals) == len(patterns) == 62
            feedback = list(DictReader(StringIO(get(urljoin(gallery, "data/feedback-catalog.csv")).decode("utf-8-sig"))))
            assert len(feedback) == 36 and len({row["url"] for row in feedback}) == 28
            assert len({row["id"] for row in feedback}) == 36

            for width in (390, 375, 320):
                page.set_viewport_size({"width": width, "height": 840})
                assert page.goto(gallery + "?sample=sandy-flared&view=back", wait_until="load").ok
                page.wait_for_url(gallery + "rendered.html?sample=sandy-flared&view=back")
                wait_image(page, "#render-img", "gallery/sandy-flared/back.webp")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.locator("#zoom-pattern").click()
                wait_image(page, "#enlarged-pattern", "gallery/sandy-flared/preview.svg")
                page.get_by_role("button", name="关闭纸样大图").click()
                assert not page.locator("#pattern-dialog").is_visible()
            page.screenshot(path=str(output / "mobile-320.png"), full_page=True, animations="disabled")
            assert page.goto(gallery + "?sample=missing&view=constructor", wait_until="load").ok
            page.wait_for_url(gallery + "rendered.html?sample=missing&view=constructor")
            wait_image(page, "#render-img", "gallery/sandy-standard/angle.webp")
            assert page.locator("#gallery-problem").is_hidden()
            assert not failures, failures
            report = {
                "verdict": "PASS", "base_url": base, "commit": build["commit"],
                "source_sha256": build["source_sha256"], "hashed_gallery_assets": len(assets),
                "gallery_manifest_sha256": digest(manifest_contents),
                "paper_previews": len(paper_entries),
                "research_2d_layouts": sum(entry["source"] == "zju" for entry in paper_entries),
                "meshes": mesh_checks, "record_counts": {"patterns": len(originals), "initial_curated_feedback": len(feedback)},
                "browser": {
                    "anonymous": True, "navigation": "home -> 2D gallery -> 3D cases -> YAML editor",
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
