"""Verify original-file identities, review evidence and the real catalog browser."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from csv import DictReader
from hashlib import sha256
from io import StringIO, TextIOWrapper
from pathlib import Path
from urllib.parse import urljoin
from zipfile import ZipFile
import json
import sys

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from playwright_http import new_api_context
from verify_pages import local_site
from build_catalog_feedback import DATASET_FILE, normalize

CATALOG = "pattern-library/catalog/"
FILES = (
    "cad.json", "summary.json", "review-signals.json", "review-notes.json",
    "cad-origins.csv", "cad-publisher-links.csv", "review-signals.csv", "review-notes.csv",
)


def verify_sources(entries, wec, fit):
    expected = defaultdict(dict)
    for entry in entries:
        expected[entry["source_id"]].setdefault(entry["source_index"], []).append(entry)
    seen = 0
    with ZipFile(wec) as archive, archive.open(DATASET_FILE) as source:
        for row in DictReader(TextIOWrapper(source, encoding="utf-8-sig")):
            for entry in expected["WEC"].get(int(row[""]), ()):
                assert entry["evidence"] in normalize(row["Review Text"])
                assert entry["product_id"] == row["Clothing ID"]
                seen += 1
    with ZipFile(fit) as archive:
        for code, filename in (("RTR", "renttherunway_final_data.json"), ("MOD", "modcloth_final_data.json")):
            with archive.open(filename) as stream:
                for index, line in enumerate(stream):
                    selected = expected[code].get(index)
                    if selected:
                        row = json.loads(line)
                        for entry in selected:
                            assert entry["evidence"] in normalize(row["review_text"]), entry["id"]
                            assert entry["product_id"] == str(row["item_id"])
                            seen += 1
    assert seen == len(entries)
    return seen


def verify_data(files, source, fit):
    def csv(name):
        return list(DictReader(StringIO(files[name].decode("utf-8-sig"))))

    summary = json.loads(files["summary.json"])
    catalog = json.loads(files["cad.json"])
    feedback = json.loads(files["review-signals.json"])
    notes = json.loads(files["review-notes.json"])
    assets = [row for row in catalog["entries"] if row.get("sha256")]
    sources = [row for row in catalog["entries"] if not row.get("sha256")]
    assert len(assets) == len({row["sha256"] for row in assets}) == summary["asset-total"]
    assert Counter(row["format"] for row in assets) == catalog["counts"]["formats"]
    assert len(sources) == catalog["counts"]["publisher_records"]
    assert {r["id"]: r["sha256"] for r in csv("cad-origins.csv")} == {r["id"]: r["sha256"] for r in assets}
    assert {r["id"]: r["url"] for r in csv("cad-publisher-links.csv")} == {r["id"]: r["url"] for r in sources}
    research = [row for row in assets if row["source"] == "zju"]
    assert len(research) == 24 and sum(row["role"] == "同款变姿态工程" for row in research) == 7
    assert len({entry["review_id"] for entry in feedback["entries"]}) == summary["review-total"]
    assert len(feedback["entries"]) == len({e["id"] for e in feedback["entries"]}) == summary["signal-total"]
    assert Counter(row["part"] for row in feedback["entries"]) == feedback["issue_counts"]
    assert {row["id"] for row in csv("review-signals.csv")} == {row["id"] for row in feedback["entries"]}
    assert len(notes) == len({row["id"] for row in notes}) == summary["curated-total"]
    assert {row["id"] for row in csv("review-notes.csv")} == {row["id"] for row in notes}
    assert all(row["url"].startswith("https://") for row in notes)
    evidence_count = verify_sources(feedback["entries"], source, fit) if source and fit else None
    return summary, catalog, feedback, notes, evidence_count


def run(base, output, expected_commit, executable, source, fit):
    output.mkdir(exist_ok=True, parents=True)
    base = base.rstrip("/") + "/"
    url = urljoin(base, CATALOG)
    with sync_playwright() as pw:
        api = new_api_context(pw, base)
        browser = pw.chromium.launch(executable_path=executable, args=["--no-sandbox"])
        try:
            build_response = api.get(urljoin(base, "build.json"), timeout=45000)
            assert build_response.ok
            build = build_response.json()
            if expected_commit:
                assert build["commit"] == expected_commit, (build["commit"], expected_commit)
            files = {}
            for file in FILES:
                response = api.get(urljoin(url, file), timeout=45000)
                assert response.ok, (file, response.status)
                contents = response.body()
                assert sha256(contents).hexdigest() == build["files"][CATALOG + file]
                files[file] = contents
            summary, catalog, feedback, notes, evidence_count = verify_data(files, source, fit)
            errors = []
            context = browser.new_context(viewport={"width": 1360, "height": 1000}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda res: errors.append(f"{res.status} {res.url}") if res.status >= 400 else None)
            page.on("requestfailed", lambda req: errors.append(f"{req.url} {req.failure}") if req.failure != "net::ERR_ABORTED" else None)
            page.on("console", lambda event: errors.append(event.text) if event.type == "error" else None)
            assert page.goto(urljoin(base, "pattern-library/"), wait_until="networkidle", timeout=45000).ok
            page.get_by_role("link", name="查看全部纸样和反馈").click()
            expect(page.get_by_role("heading", name="纸样与版型反馈资料库")).to_be_visible()
            expect(page.locator("#results-count")).to_contain_text(f"{len(catalog['entries'])} 项")
            expect(page.locator("#asset-total")).to_have_text(str(summary["asset-total"]))
            page.locator("#category").select_option("PRJ")
            expect(page.locator("#results-count")).to_contain_text("17 项")
            page.locator("#source").select_option("et")
            expect(page.locator("#results-count")).to_contain_text("16 项")
            page.locator("#source").select_option("zju")
            expect(page.locator("#results-count")).to_have_text("没有找到匹配项")
            page.locator("#category").select_option("ZPRJ")
            expect(page.locator("#results-count")).to_contain_text("24 项")
            page.locator("#query").fill("男式连帽衫")
            expect(page.locator("#results-count")).to_contain_text("3 项")
            page.locator("#entries summary").first.click()
            expect(page.locator('#entries details[open]')).to_contain_text("SHA-256")
            page.locator("#query").fill("")
            page.screenshot(path=str(output / "cad.png"), animations="disabled")

            downloads = {}
            for mode, names in (("patterns", ("cad-origins.csv", "cad-publisher-links.csv")),
                                ("feedback", ("review-signals.csv", "review-notes.csv"))):
                page.locator(f'[data-mode="{mode}"]').click()
                expect(page.locator("#filters")).to_be_visible(timeout=45000)
                for control, name in zip(("download", "download-extra"), names, strict=True):
                    with page.expect_download(timeout=45000) as event:
                        page.locator(f"#{control}").click()
                    result = event.value
                    assert not result.failure()
                    file = output / name
                    result.save_as(file)
                    digest = sha256(file.read_bytes()).hexdigest()
                    assert digest == build["files"][CATALOG+name]
                    downloads[name] = digest
            total = len(notes) + len(feedback["entries"])
            expect(page.locator("#results-count")).to_contain_text(f"{total:,} 项")
            assert page.locator("#entries article").count() == 24
            page.locator("#next").click()
            expect(page.locator("#results-count")).to_contain_text("25–48")
            page.locator("#category").select_option("pockets")
            page.locator("#source").select_option("manual")
            expect(page.locator("#results-count")).to_contain_text(f"{sum(r['part']=='pockets' for r in notes)} 项")
            expect(page.locator("#entries article").first).to_contain_text("候选改法")
            page.screenshot(path=str(output / "feedback.png"), animations="disabled")
            page.set_viewport_size({"width": 360, "height": 860})
            assert page.goto(url+"?view=feedback&q=C-05", wait_until="networkidle", timeout=60000).ok
            expect(page.locator("#entries article")).to_have_count(1, timeout=45000)
            expect(page.locator("#entries")).to_contain_text("Dickies")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output / "mobile.png"), animations="disabled")
            assert not errors, errors
            report = {"verdict": "PASS", "base_url": base, "commit": build["commit"], "summary": summary,
                      "source_sha256": build["source_sha256"], "checked_asset_records": len(catalog["entries"]),
                      "all_normalized_review_spans_match_original_inputs": evidence_count,
                      "browser_downloads_sha256": downloads, "browser_errors": errors}
            (output/"browser-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
        finally:
            browser.close()
            api.dispose()


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "dist")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--expected-commit")
    parser.add_argument("--browser", default="/usr/bin/chromium")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--fit-source", type=Path)
    args = parser.parse_args()
    command = (args.output, args.expected_commit, args.browser, args.source, args.fit_source)
    if args.base_url:
        run(args.base_url, *command)
    else:
        with local_site(args.directory) as base:
            run(base, *command)
