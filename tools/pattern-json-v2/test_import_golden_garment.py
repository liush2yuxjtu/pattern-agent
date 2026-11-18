#!/usr/bin/env python3
"""Consumer-visible import, corruption and freshness controls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
IMPORTER = ROOT / "tools/pattern-json-v2/import_golden_garment.py"
INPUT = ROOT / "patterns/fitted-tshirt/input-spec.yaml"
EXPECTED_SHA = "88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e"
spec = importlib.util.spec_from_file_location("import_golden_garment", IMPORTER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
RAW = INPUT.read_bytes()
DOC = yaml.safe_load(RAW)


def raw_doc(doc):
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False).encode("utf-8")


class GoldenGarmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = module.import_golden_garment(RAW)

    def test_golden_inventory_and_source_preservation(self):
        v2 = self.baseline
        self.assertEqual(v2["provenance"]["source_sha256"], EXPECTED_SHA)
        self.assertEqual(v2["source_document"], DOC)
        self.assertEqual(v2["geometry"], DOC["完整二维几何"])
        self.assertEqual([len(v2[name]) for name in ("pieces", "edges", "measurements", "interfaces", "seam_pairs", "seam_relations")], [4, 204, 23, 25, 11, 9])
        self.assertEqual(v2["units"]["coordinate_unit"], "U")
        self.assertIsNone(v2["units"]["mm_per_unit"])
        self.assertFalse(v2["garment"]["production_ready"])
        self.assertFalse(v2["status"]["production_release"])
        self.assertIsNone(v2["revision"]["spec_patch"])
        self.assertIsNone(v2["revision"]["geometry_patch"])
        self.assertEqual(v2["review_events"], [])

    def test_both_sleeve_roles_and_unknown_cut_quantities(self):
        sleeve = next(piece for piece in self.baseline["pieces"] if piece["piece_id"] == "sleeve")
        self.assertEqual({role["name"] for role in sleeve["roles"]}, {"左袖", "右袖"})
        for piece in self.baseline["manufacturing"]["pieces"]:
            self.assertIsNone(piece["cut_quantity"]["value"])
            self.assertEqual(piece["cut_quantity"]["status"], "UNKNOWN")
            self.assertEqual(piece["notches"]["status"], "MISSING")
            self.assertIsNone(piece["grading"]["value"])

    def test_four_sleeve_mappings_stay_unresolved(self):
        sides = [seam["side_b"] for seam in self.baseline["seam_pairs"] if seam["side_b"]["status"] == "UNRESOLVED"]
        self.assertEqual(len(sides), 4)
        for side in sides:
            self.assertIsNone(side["interface_ids"])
            self.assertEqual(len(side["candidate_interface_ids"]), 2)

    def test_known_disconnected_hem_is_preserved(self):
        hem = next(row for row in self.baseline["interfaces"] if row["piece"] == "前片" and row["name"] == "下摆")
        self.assertEqual(hem["段间间隙"], [426.184448])

    def test_boolean_strings_null_and_safe_loader_isolation(self):
        doc = copy.deepcopy(DOC)
        doc["parser-control"] = {"words": ["yes", "no", "on", "off"], "true": True, "false": False, "null": None}
        imported = module.import_golden_garment(raw_doc(doc))
        self.assertEqual(imported["source_document"]["parser-control"], doc["parser-control"])
        self.assertEqual(yaml.safe_load("value: yes"), {"value": True})
        direct = module.parse_source(RAW + b"\nparser-control: [yes, no, on, off, true, false, null]\n")
        self.assertEqual(direct["parser-control"], ["yes", "no", "on", "off", True, False, None])

    def test_wrong_source_version_rejected(self):
        doc = copy.deepcopy(DOC)
        doc["文件约定"]["格式版本"] = "9.9"
        with self.assertRaisesRegex(ValueError, "version"):
            module.import_golden_garment(raw_doc(doc))

    def test_duplicate_yaml_key_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            module.import_golden_garment(RAW + "\n文件约定: duplicate\n".encode())

    def test_non_string_yaml_key_rejected(self):
        with self.assertRaisesRegex(ValueError, "keys must be strings"):
            module.import_golden_garment(RAW + b"\n123: invalid\n")

    def test_non_finite_coordinate_rejected(self):
        doc = copy.deepcopy(DOC)
        doc["完整二维几何"]["前片"]["线条"][0]["点位"][0]["横"] = float("nan")
        with self.assertRaises(ValueError):
            module.import_golden_garment(raw_doc(doc))

    def test_dangling_interface_line_rejected(self):
        doc = copy.deepcopy(DOC)
        doc["裁片接口"]["前片"]["领圈"]["组成"][0]["线条"] = "missing"
        with self.assertRaisesRegex(ValueError, "reference"):
            module.import_golden_garment(raw_doc(doc))

    def test_dangling_measurement_and_seam_references_rejected(self):
        for scope in ("measurement", "seam"):
            with self.subTest(scope=scope):
                doc = copy.deepcopy(DOC)
                if scope == "measurement":
                    doc["关键尺寸"]["项目"]["前中纵线"]["线条"] = ["missing"]
                else:
                    doc["缝级关系图"]["缝级记录"][0]["边一"][0]["接口"] = "missing"
                with self.assertRaisesRegex(ValueError, "Missing"):
                    module.import_golden_garment(raw_doc(doc))

    def test_deleted_geometry_and_duplicate_line_name_rejected(self):
        for scope in ("deleted", "duplicate"):
            with self.subTest(scope=scope):
                doc = copy.deepcopy(DOC)
                lines = doc["完整二维几何"]["前片"]["线条"]
                if scope == "deleted":
                    lines.clear()
                else:
                    lines[1]["名称"] = lines[0]["名称"]
                with self.assertRaises(ValueError):
                    module.import_golden_garment(raw_doc(doc))

    def test_connection_summary_dangling_reference_rejected_by_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            doc = copy.deepcopy(DOC)
            doc["连接关系"]["左肩缝"]["连接一"]["接口"] = "DOES_NOT_EXIST"
            source = Path(directory) / "dangling.yaml"
            source.write_bytes(raw_doc(doc))
            output = Path(directory) / "output.json"
            result = subprocess.run([sys.executable, str(IMPORTER), str(source), str(output), "--check"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(output.exists())
            self.assertIn("Missing interface", result.stderr)

    def test_measurement_self_and_multi_node_cycles_rejected(self):
        for dependencies in [("前中纵线",), ("前中纵线", "后中纵线")]:
            with self.subTest(dependencies=dependencies):
                doc = copy.deepcopy(DOC)
                for name, dependency in zip(dependencies, dependencies[1:] + dependencies[:1]):
                    doc["关键尺寸"]["项目"][name].update(计算方式="尺寸相加", 尺寸项目=[dependency])
                with self.assertRaisesRegex(ValueError, "Cyclic measurement"):
                    module.import_golden_garment(raw_doc(doc))

    def test_duplicate_id_output_coordinate_and_source_tampering_rejected(self):
        for scope in ("id", "coordinate", "source", "version"):
            with self.subTest(scope=scope):
                v2 = copy.deepcopy(self.baseline)
                if scope == "id":
                    v2["interfaces"][1]["interface_id"] = v2["interfaces"][0]["interface_id"]
                elif scope == "coordinate":
                    v2["geometry"]["前片"]["线条"][0]["点位"][0]["横"] += 1
                elif scope == "source":
                    v2["source_document"]["完整二维几何"]["前片"]["线条"][0]["点位"][0]["横"] += 1
                else:
                    v2["schema"]["version"] = "9.9"
                self.assertTrue(module.validate_invariants(v2))

    def test_content_revision_changes_with_stable_geometry_ids(self):
        doc = copy.deepcopy(DOC)
        doc["完整二维几何"]["前片"]["线条"][0]["点位"][0]["横"] += 1
        changed = module.import_golden_garment(raw_doc(doc))
        self.assertNotEqual(changed["revision"]["revision_id"], self.baseline["revision"]["revision_id"])
        self.assertEqual([e["edge_id"] for e in changed["edges"]], [e["edge_id"] for e in self.baseline["edges"]])

    def test_line_reordering_preserves_ids_by_name(self):
        doc = copy.deepcopy(DOC)
        doc["完整二维几何"]["前片"]["线条"].reverse()
        changed = module.import_golden_garment(raw_doc(doc))
        key_ids = lambda manifest: {(edge["piece_id"], edge["name"]): edge["edge_id"] for edge in manifest["edges"]}
        self.assertEqual(key_ids(changed), key_ids(self.baseline))

    def test_reformatting_changes_byte_hash_but_preserves_revision(self):
        changed = module.import_golden_garment(raw_doc(DOC))
        self.assertNotEqual(changed["provenance"]["source_sha256"], EXPECTED_SHA)
        self.assertEqual(changed["revision"]["revision_id"], self.baseline["revision"]["revision_id"])

    def test_old_results_become_stale_and_unchanged_results_stay_current(self):
        previous = copy.deepcopy(self.baseline)
        control_result = {"fixture": "freshness-only", "observed": [1, 2]}
        for kind in module.ARTIFACTS:
            previous["derived_artifacts"][kind] = {"status": "CURRENT", "source_revision_id": previous["revision"]["revision_id"], "result": control_result}
        same = module.import_golden_garment(RAW, previous=previous)
        self.assertTrue(all(record["status"] == "CURRENT" for record in same["derived_artifacts"].values()))
        doc = copy.deepcopy(DOC)
        doc["完整二维几何"]["前片"]["线条"][0]["点位"][0]["横"] += 1
        changed = module.import_golden_garment(raw_doc(doc), previous=previous)
        self.assertEqual(changed["revision"]["parent_revision"], previous["revision"]["revision_id"])
        for record in changed["derived_artifacts"].values():
            self.assertEqual(record["status"], "STALE")
            self.assertEqual(record["result"], control_result)
            self.assertEqual(record["source_revision_id"], previous["revision"]["revision_id"])
        self.assertTrue(all(row["status"] == "NOT_RUN" for row in self.baseline["derived_artifacts"].values()))

    def test_invalid_previous_manifest_rejected(self):
        previous = copy.deepcopy(self.baseline)
        previous["derived_artifacts"]["physics"]["status"] = "CURRENT"
        with self.assertRaisesRegex(ValueError, "Invalid previous"):
            module.import_golden_garment(RAW, previous=previous)

    def test_cli_exact_hash_readback_and_optional_dxf_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pattern.json"
            dxf = ROOT / "patterns/fitted-tshirt/input.dxf"
            result = subprocess.run([sys.executable, str(IMPORTER), str(INPUT), str(output), "--check", "--expected-sha256", EXPECTED_SHA, "--reference-dxf", str(dxf)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["seam_pairs"], 11)
            v2 = json.loads(output.read_text())
            self.assertEqual(v2["provenance"]["source_path"], module.SOURCE_PATH)
            self.assertEqual(v2["provenance"]["reference_assets"], [{"source_path": "patterns/fitted-tshirt/input.dxf", "sha256": hashlib.sha256(dxf.read_bytes()).hexdigest(), "role": "reference-only"}])
            self.assertFalse(module.validate_invariants(v2, EXPECTED_SHA))

    def test_cli_bad_hash_and_bad_source_preserve_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pattern.json"
            output.write_bytes(b"existing output")
            bad = Path(directory) / "bad.yaml"
            bad.write_bytes(RAW + "\n文件约定: duplicate\n".encode())
            for source, extra in ((INPUT, ["--expected-sha256", "0" * 64]), (bad, [])):
                result = subprocess.run([sys.executable, str(IMPORTER), str(source), str(output), *extra], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(output.read_bytes(), b"existing output")

    def test_cli_input_location_does_not_change_output_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "different-name.yaml"
            copied.write_bytes(RAW)
            outputs = [Path(directory) / "a.json", Path(directory) / "b.json"]
            for source, output in zip((INPUT, copied), outputs):
                result = subprocess.run([sys.executable, str(IMPORTER), str(source), str(output)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())

    def test_cli_refuses_to_overwrite_source_or_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "copy.yaml"
            source.write_bytes(RAW)
            reference = Path(directory) / "reference.dxf"
            original_reference = (ROOT / "patterns/fitted-tshirt/input.dxf").read_bytes()
            reference.write_bytes(original_reference)
            for output in (source, reference):
                result = subprocess.run([sys.executable, str(IMPORTER), str(source), str(output),
                                         "--reference-dxf", str(reference)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(source.read_bytes(), RAW)
                self.assertEqual(reference.read_bytes(), original_reference)

    def test_cli_previous_reopens_and_invalidates_all_results(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory) / "previous.json"
            fixture = copy.deepcopy(self.baseline)
            original_revision = fixture["revision"]["revision_id"]
            for record in fixture["derived_artifacts"].values():
                record.update(status="CURRENT", source_revision_id=original_revision,
                              result={"fixture": "revision-control-only"})
            previous.write_text(json.dumps(fixture, ensure_ascii=False))
            same = Path(directory) / "same.json"
            result = subprocess.run([sys.executable, str(IMPORTER), str(INPUT), str(same),
                                     "--previous", str(previous)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(r["status"] == "CURRENT" for r in
                                json.loads(same.read_text())["derived_artifacts"].values()))
            doc = copy.deepcopy(DOC)
            doc["完整二维几何"]["前片"]["线条"][0]["点位"][0]["横"] += 1
            changed_source = Path(directory) / "changed.yaml"
            changed_source.write_bytes(raw_doc(doc))
            changed = Path(directory) / "changed.json"
            result = subprocess.run([sys.executable, str(IMPORTER), str(changed_source), str(changed),
                                     "--previous", str(same)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            reopened = json.loads(changed.read_text())
            self.assertNotEqual(reopened["revision"]["revision_id"], original_revision)
            self.assertEqual(reopened["revision"]["parent_revision"], original_revision)
            self.assertTrue(all(r["status"] == "STALE" and r["source_revision_id"] == original_revision
                                for r in reopened["derived_artifacts"].values()))
            repeated = Path(directory) / "repeated.json"
            result = subprocess.run([sys.executable, str(IMPORTER), str(changed_source), str(repeated),
                                     "--previous", str(changed)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(repeated.read_bytes(), changed.read_bytes())


if __name__ == "__main__":
    unittest.main()
