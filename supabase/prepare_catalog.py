#!/usr/bin/env python3
"""Prepare a transactional PostgreSQL import from the Pattern Agent catalog."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "pattern_agent"
BATCH_ROWS = 600


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def drive_file_id(value):
    url = urlsplit(value)
    if not url.netloc:
        file_id = value
    elif url.scheme == "https" and url.netloc == "drive.google.com":
        match = re.match(r"^/file/d/([^/]+)(?:/|$)", url.path)
        file_id = match.group(1) if match else parse_qs(url.query).get("id", [""])[0]
    else:
        file_id = ""
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", file_id):
        raise ValueError("A Google Drive file ID or file link is required")
    return file_id


def drive_locations(assets, index_path, research_archive):
    by_hash = {a["sha256"]: a for a in assets if a["sha256"]}
    locations = {}
    if index_path:
        with index_path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                asset = by_hash.get(row["sha256"])
                if not asset or not row["drive_url"]:
                    continue
                if int(row["bytes"]) != asset["bytes"]:
                    raise ValueError(f"Drive index disagrees with catalog bytes for {asset['asset_id']}")
                stored_format = Path(row["drive_object"]).suffix.removeprefix(".").upper()
                member = None if stored_format in asset["formats"] else row["archive_member"]
                if stored_format not in asset["formats"] and not member:
                    raise ValueError(f"Archive member is missing for {asset['asset_id']}")
                locations.setdefault(asset["asset_id"], {
                    "asset_id": asset["asset_id"],
                    "file_id": drive_file_id(row["drive_url"]),
                    "archive_member": member,
                })
    if research_archive:
        file_id = drive_file_id(research_archive)
        for asset in assets:
            if asset["source_code"] == "zju" and asset["sha256"]:
                locations[asset["asset_id"]] = {
                    "asset_id": asset["asset_id"], "file_id": file_id, "archive_member": asset["source_member"],
                }
    return list(locations.values())


def read_catalog(directory, drive_index=None, research_archive=None):
    cad = read_json(directory / "cad.json")
    feedback = read_json(directory / "review-signals.json")
    notes = read_json(directory / "review-notes.json")
    summary = read_json(directory / "summary.json")
    intents = yaml.safe_load((directory / "review-design-intents.yaml").read_text(encoding="utf-8"))
    if (cad["schema"], feedback["schema"], intents["schema"]) != (
        "pattern-agent-cad/1", "pattern-agent-feedback/1", "intent-corpus/v1",
    ):
        raise ValueError("Unsupported Pattern Agent catalog format")

    assets = [{
        "asset_id": row["id"], "title": row["title"], "original_name": row["name"],
        "formats": row.get("formats", [row["format"]]), "garment": row.get("garment") or None,
        "source_code": row["source"], "source_name": cad["sources"][row["source"]], "source_url": row["url"],
        "source_member": row.get("member") or None, "role": row.get("role") or None,
        "audit": row["audit"], "bytes": row.get("bytes"), "sha256": row.get("sha256"),
    } for row in cad["entries"]]
    sources = [{
        "source_code": code, "title": row["title"], "source_url": row["url"], "license": row["license"],
        "archive_filename": row["filename"], "archive_sha256": row["archive_sha256"],
        "citation_url": row.get("citation"), "counts": row["counts"],
    } for code, row in feedback["sources"].items()]
    reviews, signals = {}, []
    for row in feedback["entries"]:
        record = {
            "review_id": row["review_id"], "source_code": row["source_id"], "source_index": row["source_index"],
            "product_id": row["product_id"], "garment": row["garment"], "source_garment": row["source_garment"],
            "rating": None if row.get("rating") in ("", None) else str(row["rating"]),
        }
        if reviews.setdefault(row["review_id"], record) != record:
            raise ValueError(f"Inconsistent review metadata for {row['review_id']}")
        signals.append({
            "signal_id": row["id"], "review_id": row["review_id"], "part_code": row["part"],
            "action_code": row["action"], "evidence": row["evidence"],
        })
    curated = [{
        "feedback_id": row["id"], "part_code": row["part"], "garment": row["garment"],
        "publisher": row["publisher"], "locator": row["locator"], "source_url": row["url"],
        "evidence": row["evidence"], "candidate": row["candidate"],
        "measurement": row["measurement"], "preserve": row["preserve"],
    } for row in notes]
    intent_sources = {f"intent-{row['feedback_id'].lower()}": row["feedback_id"] for row in curated}
    designs = [{
        "intent_id": row["id"], "feedback_id": intent_sources[row["id"]], "region": row["region"],
        "request": row["candidate_request"], "measurement_inputs": row["measurement_inputs"],
        "preserve": row["preserve"], "target": row["target"], "state": row["state"],
    } for row in intents["cases"]]
    counts = {
        "asset-total": sum(asset["sha256"] is not None for asset in assets),
        "review-total": len(reviews), "signal-total": len(signals), "curated-total": len(curated),
    }
    formats = Counter(asset["formats"][0] for asset in assets if asset["sha256"])
    leads = len(assets) - counts["asset-total"]
    if (counts != summary or formats != cad["counts"]["formats"]
            or leads != cad["counts"]["publisher_records"] or len(designs) != len(curated)):
        raise ValueError("Input counts disagree with the catalog manifests")
    return {
        "cad_assets": assets,
        "cad_drive_locations": drive_locations(assets, drive_index, research_archive),
        "feedback_sources": sources,
        "feedback_parts": [
            {"part_code": code, "label": row["label"], "measurement": row["measurement"], "preserve": row["preserve"]}
            for code, row in feedback["parts"].items()
        ],
        "feedback_actions": [{"action_code": code, "label": label} for code, label in feedback["actions"].items()],
        "feedback_reviews": list(reviews.values()),
        "feedback_signals": signals,
        "curated_feedback": curated,
        "design_intents": designs,
    }


def sql_batches(tables):
    for table, rows in tables.items():
        if not rows:
            continue
        columns = tuple(rows[0])
        key = columns[0]
        if len({row[key] for row in rows}) != len(rows):
            raise ValueError(f"Duplicate keys in {table}")
        fields = ", ".join(columns)
        kept = {"target", "state"} if table == "design_intents" else set()
        changed = [col for col in columns[1:] if col not in kept]
        assignments = ", ".join(f"{col} = excluded.{col}" for col in changed)
        old = ", ".join(f"current_row.{col}" for col in changed)
        new = ", ".join(f"excluded.{col}" for col in changed)
        for start in range(0, len(rows), BATCH_ROWS):
            payload = json.dumps(rows[start:start+BATCH_ROWS], ensure_ascii=False, separators=(",", ":"))
            delimiter = "$pattern_agent$"
            while delimiter in payload:
                delimiter = delimiter[:-1] + "x$"
            yield (
                f"insert into {SCHEMA}.{table} as current_row ({fields}) "
                f"select {fields} from jsonb_populate_recordset(null::{SCHEMA}.{table}, {delimiter}{payload}{delimiter}::jsonb) "
                f"on conflict ({key}) do update set {assignments} where row({old}) is distinct from row({new});"
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "web/pattern-library/catalog")
    parser.add_argument("--drive-index", type=Path, help="Original private Drive index with file URLs and SHA-256")
    parser.add_argument("--research-archive", help="Drive file ID or URL for the Zhejiang University source archive")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = read_catalog(args.catalog, args.drive_index, args.research_archive)
    statements = list(sql_batches(rows))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("begin;\n" + "\n".join(statements) + "\ncommit;\n", encoding="utf-8")
    print(json.dumps({table: len(data) for table, data in rows.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
