#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys, tempfile

ROOT=Path(__file__).resolve().parents[2]
IMPORTER=ROOT/"tools/pattern-json-v2/import_golden_garment.py"
INPUT=ROOT/"patterns/fitted-tshirt/input-spec.yaml"
EXPECTED_SHA="88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e"

with tempfile.TemporaryDirectory() as td:
    output=Path(td)/"pattern.json"
    result=subprocess.run([sys.executable,str(IMPORTER),str(INPUT),str(output),"--check","--expected-sha256",EXPECTED_SHA],cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout); print(result.stderr,file=sys.stderr); raise SystemExit(result.returncode)
    report=json.loads(result.stdout)
    assert report=={
        "coordinate_unit":"U","interfaces":25,"measurements":23,"mm_per_unit":None,
        "pieces":4,"production_release":False,"schema":"2.0.0",
        "source_sha256":EXPECTED_SHA,"status":"PASS"
    }
    payload=json.loads(output.read_text(encoding="utf-8"))
    assert payload["source_document"]["文件约定"]["格式版本"]=="1.1"
    assert payload["units"]["coordinate_unit"]=="U"
    assert payload["units"]["mm_per_unit"] is None
    assert len(payload["geometry"])==4
    assert [p["piece_id"] for p in payload["pieces"]]==["front-bodice","back-bodice","sleeve","neckband"]

print("PASS: Golden Garment YAML 1.1 -> Pattern JSON v2 contract")
