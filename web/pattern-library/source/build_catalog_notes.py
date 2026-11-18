#!/usr/bin/env python3
"""Merge the curated source cards with the generated catalog metadata."""
from csv import DictReader, DictWriter
from pathlib import Path
import argparse
import json
import yaml

BASE_PARTS = (
    "variant", "sleeve_length", "hem_length", "armhole", "material", "armhole", "sleeve_length", "chest", "pockets",
    "variant", "pockets", "rise", "inseam", "pockets", "inseam", "documentation", "waist_fit", "thigh",
    "armhole", "upper_arm", "upper_arm", "cuff", "rise", "pockets", "torso", "pockets", "torso", "leg_opening",
    "neckline", "closure", "pockets", "inseam", "documentation", "documentation", "leg_opening", "torso",
)


def read_csv(path, delimiter=","):
    with path.open(encoding="utf-8-sig") as file:
        return list(DictReader(file, delimiter=delimiter))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "supplement", "feedback", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.feedback.read_text())
    data["parts"]["documentation"] = {"label": "纸样交付与质检", "measurement": "关键尺寸和交付文件版本", "preserve": "已确认的几何轮廓"}
    notes = []
    for part, row in zip(BASE_PARTS, read_csv(args.baseline), strict=True):
        notes.append(dict(id=row["id"], part=part, garment=row["garment"], publisher=row["where"],
                          locator=row["review_locator"], url=row["url"], evidence=row["reported"],
                          candidate=row["candidate"], measurement=row["needs"], preserve=row["preserve"], source_id="manual"))
    for number, row in enumerate(read_csv(args.supplement, "\t"), 1):
        notes.append(dict(id=f"C-{number:02d}", source_id="manual", **row))
    assert all(row["part"] in data["parts"] for row in notes)
    assert len({row["id"] for row in notes}) == len(notes)
    write_json(args.output/"review-signals.json", data)
    write_json(args.output/"review-notes.json", notes)
    with (args.output/"review-notes.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = DictWriter(stream, fieldnames=list(notes[0]))
        writer.writeheader()
        writer.writerows(notes)
    write_json(args.output/"summary.json", {
        "asset-total": json.loads((args.output/"cad.json").read_text())["counts"]["archived"],
        "review-total": data["counts"]["matched_reviews"],
        "signal-total": data["counts"]["issue_rows"], "curated-total": len(notes)
    })
    intents = {"schema": "intent-corpus/v1",
               "interpretation": "根据公开反馈提出候选操作。每条都需核对尺码、实物量法和目标。",
               "cases": [dict(id=f"intent-{row['id'].lower()}",
                    evidence={key: row[key] for key in ("url", "locator", "evidence")},
                    garment=row["garment"], region=data["parts"][row["part"]]["label"],
                    candidate_request=row["candidate"], measurement_inputs=row["measurement"],
                    preserve=row["preserve"], target=None, state="needs_confirmation") for row in notes]}
    (args.output/"review-design-intents.yaml").write_text(yaml.safe_dump(intents, allow_unicode=True, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
