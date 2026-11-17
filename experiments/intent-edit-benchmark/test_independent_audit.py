"""Small independent tests for the audit's guards, CAD oracle and replay."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("independent_audit", HERE / "audit_benchmark.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class IndependentAuditTests(unittest.TestCase):
    def test_real_source_pair_and_measurement(self):
        model = audit.read_model(audit.REPO / "patterns/fitted-tshirt/input-spec.yaml")
        raw = (audit.REPO / "patterns/fitted-tshirt/input.dxf").read_bytes()
        rows, counts = audit.read_cad(raw)
        self.assertEqual(counts["entities"], 231)
        self.assertEqual(counts["polyline_vertices"], 1487)
        self.assertEqual(audit.canonical(rows), audit.canonical(audit.model_rows(model)))
        self.assertAlmostEqual(audit.measure_model(model)["dimensions"]["袖片纵线"], 593.272857, places=6)

    def test_byte_exact_dxf_forward_inverse_and_old_guard(self):
        raw = b"0\r\nSECTION\r\n10\r\n 12.500000\r\n0\r\nEOF\r\n"
        operations = [{"pair_index": 1, "code": 10, "old": " 12.500000", "value": "32.500000"}]
        patch = {"base_sha256": audit.sha(raw), "operations": operations}
        generated = audit.replay_dxf(raw, patch)
        self.assertEqual(generated, raw.replace(b" 12.500000", b"32.500000"))
        self.assertEqual(audit.replay_dxf(generated, patch, reverse=True, target_raw=generated), raw)
        bad = deepcopy(patch); bad["operations"][0]["old"] = "12.500000"
        with self.assertRaises(audit.AuditFailure):
            audit.replay_dxf(raw, bad)

    def test_dxf_base_digest_and_repeated_index_guard(self):
        raw = b"10\n1.0\n20\n2.0\n"
        patch = {"base_sha256": "0" * 64, "operations": []}
        with self.assertRaises(audit.AuditFailure):
            audit.replay_dxf(raw, patch)
        patch = {"base_sha256": audit.sha(raw), "operations": [{"pair_index": 0, "code": 10, "old": "1.0", "value": "1.0\n0\nLINE"}]}
        with self.assertRaises(audit.AuditFailure):
            audit.replay_dxf(raw, patch)
        patch = {"base_sha256": audit.sha(raw), "operations": [{"pair_index": 0, "code": 10, "old": "1.0", "value": "3.0"}] * 2}
        with self.assertRaises(audit.AuditFailure):
            audit.replay_dxf(raw, patch)

    def test_spec_unicode_pointer_replay_and_inverse(self):
        document = {"领/口": {"a~b": [1, 2]}, "保留": True}
        operations = [{"op": "replace", "path": "/领~1口/a~0b/0", "old": 1, "value": 3}, {"op": "add", "path": "/说明", "value": "加深"}, {"op": "remove", "path": "/领~1口/a~0b/1", "old": 2}]
        target = audit.apply_spec_operations(document, operations)
        self.assertEqual(target, {"领/口": {"a~b": [3]}, "保留": True, "说明": "加深"})
        self.assertEqual(audit.apply_spec_operations(target, operations, reverse=True), document)
        operations[0]["old"] = 42
        with self.assertRaises(audit.AuditFailure):
            audit.apply_spec_operations(document, operations)

    def test_geometric_crossing_and_overlap_oracle(self):
        self.assertTrue(audit.segment_intersection((0, 0), (2, 2), (0, 2), (2, 0)))
        self.assertTrue(audit.segment_intersection((0, 0), (2, 0), (1, 0), (3, 0)))
        self.assertTrue(audit.segment_intersection((0, 0), (1, 0), (1, 0), (2, 0)))
        self.assertTrue(audit.segment_intersection((0, 0), (2, 0), (1, 0), (1, 1)))
        self.assertFalse(audit.segment_intersection((0, 0), (1, 0), (0, 1), (1, 1)))

    def test_nonfinite_and_duplicate_field_rejected(self):
        with self.assertRaises(audit.AuditFailure):
            audit.number(float("nan"))
        with self.assertRaises(audit.AuditFailure):
            audit.yaml.load("领深: 10\n领深: 20\n", Loader=audit.UniqueLoader)


class IndependentAuditArtifactControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = audit.REPO / "work/intent-edit-benchmark/results"
        cls.evidence = audit.REPO / "work/intent-edit-benchmark/audit"
        cls.evidence.mkdir(parents=True, exist_ok=True)
        if not all((cls.results / name / "new-spec.yaml").is_file() for name in audit.EXPECTED):
            raise unittest.SkipTest("Run the public benchmark CLI before artifact-adversarial controls.")

    def copy_positive_artifacts(self, destination):
        for name in audit.EXPECTED:
            folder = destination / name; folder.mkdir(parents=True)
            for file in ("new-spec.yaml", "output.dxf", "spec-diff.json", "geometry-patch.json"):
                shutil.copyfile(self.results / name / file, folder / file)

    def run_cli(self, destination, evidence_name):
        command = [sys.executable, str(HERE / "audit_benchmark.py"), "--results", str(destination), "--output", str(destination / "report")]
        result = subprocess.run(command, text=True, capture_output=True)
        report = json.loads((destination / "report/independent-audit.json").read_text())
        (self.evidence / evidence_name).write_text(json.dumps({"command": command, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "report": report}, ensure_ascii=False, indent=2) + "\n")
        return result, report

    def test_full_cli_missing_negative_cases_fails(self):
        with tempfile.TemporaryDirectory(prefix="missing-controls-", dir=self.evidence) as directory:
            destination = Path(directory)
            self.copy_positive_artifacts(destination)
            result, report = self.run_cli(destination, "cli-missing-negative-controls.json")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(report["verdict"], "FAIL")
            self.assertEqual(report["positive_pass_count"], 4)
            self.assertEqual(set(report["missing_negative_cases"]), set(audit.EXPECTED_NEGATIVE))

    def test_full_cli_tampered_DXF_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="tampered-output-", dir=self.evidence) as directory:
            destination = Path(directory)
            self.copy_positive_artifacts(destination)
            for name in audit.EXPECTED_NEGATIVE:
                folder = destination / name; folder.mkdir()
                shutil.copyfile(self.results / name / "case-result.json", folder / "case-result.json")
            cad = destination / "01_sleeve_length/output.dxf"
            lines, pairs = audit.cad_pairs(cad.read_bytes())
            index = next(i for i, (code, value) in enumerate(pairs) if code == 10)
            body = lines[index * 2 + 1].rstrip(b"\r\n")
            ending = lines[index * 2 + 1][len(body):]
            lines[index * 2 + 1] = str(float(pairs[index][1]) + 0.137).encode() + ending
            cad.write_bytes(b"".join(lines))
            result, report = self.run_cli(destination, "cli-tampered-output.json")
            self.assertEqual(result.returncode, 1)
            failed = next(r for r in report["positive_cases"] if r["case"] == "01_sleeve_length")
            self.assertEqual(failed["verdict"], "FAIL")
            self.assertIn("真实DXF与新YAML几何/文字不一致", failed["error"])


if __name__ == "__main__":
    unittest.main()
