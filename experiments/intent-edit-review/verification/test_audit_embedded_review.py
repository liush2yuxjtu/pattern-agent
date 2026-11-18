from copy import deepcopy
import base64
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("embedded_review_audit", HERE / "audit_embedded_review.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def svg_for(rows):
    tags = []
    for row in rows:
        if row["kind"] == "TEXT":
            continue
        tags.append('<polyline points="' + ' '.join(f'{x},{y}' for x, y in row["points"]) + '"/>')
    return '<svg xmlns="http://www.w3.org/2000/svg"><g transform="scale(1,-1)">' + ''.join(tags) + '</g></svg>'


class EmbeddedReviewAuditTests(unittest.TestCase):
    def test_application_payload_is_unique(self):
        raw = b'<html><script type="application/json" id="app-data">{"cases":[]}</script></html>'
        self.assertEqual(audit.extract_payload(raw), {"cases": []})
        with self.assertRaises(audit.AuditFailure):
            audit.extract_payload(raw + raw)

    def test_complete_file_bytes_and_digest(self):
        raw = '完整中文规格\n领深: 92.388916\n'.encode()
        record = {"base64": base64.b64encode(raw).decode(), "byte_length": len(raw), "sha256": audit.sha(raw)}
        self.assertEqual(audit.decode_record(record), raw)
        record["byte_length"] -= 1
        with self.assertRaises(audit.AuditFailure):
            audit.decode_record(record)

    def test_real_baseline_full_CAD_and_YAML(self):
        source = audit.source_files("baseline")
        model = audit.yaml.safe_load(source["yaml"])
        rows, units = audit.read_dxf(source["dxf"])
        self.assertIsNone(units)
        record = {"source_dxf_sha256": audit.sha(source["dxf"]), "source_yaml_sha256": audit.sha(source["yaml"]), "primitives": rows, "svg": svg_for(rows)}
        report = audit.audit_two_d(record, source, model)
        self.assertEqual((report["entities"], report["curves"], report["text_annotations"]), (231, 204, 27))
        record["primitives"] = [r for r in rows if r["kind"] != "TEXT"]
        with self.assertRaises(audit.AuditFailure):
            audit.audit_two_d(record, source, model)

    def test_svg_composed_transform(self):
        svg = '<svg><g transform="translate(10,-5)"><g transform="scale(1,-1)"><line x1="2" y1="3" x2="4" y2="5"/></g></g></svg>'
        self.assertEqual(audit.svg_curve_points(svg), audit.Counter({((12., -8.), (14., -10.)): 1}))

    def test_stale_SVG_cannot_use_fresh_lineage_hashes(self):
        source = audit.source_files("04_front_neck")
        baseline = audit.source_files("baseline")
        rows, _ = audit.read_dxf(source["dxf"])
        old_rows, _ = audit.read_dxf(baseline["dxf"])
        record = {"source_dxf_sha256": audit.sha(source["dxf"]), "source_yaml_sha256": audit.sha(source["yaml"]), "primitives": rows, "svg": svg_for(old_rows)}
        with self.assertRaisesRegex(audit.AuditFailure, "SVG geometry"):
            audit.audit_two_d(record, source, audit.yaml.safe_load(source["yaml"]))

    def test_all_five_real_meshes_have_source_bound_geometry(self):
        for case in ("baseline", *audit.CASES):
            with self.subTest(case=case):
                model = json.loads((audit.REPO / "experiments/intent-edit-review/geometry" / (case + ".mesh.json")).read_text())
                report, signatures = audit.audit_mesh_geometry(model, audit.source_files(case), case)
                self.assertEqual(len(report["panels"]), 5)
                self.assertEqual(len(signatures), 5)

    def test_reused_old_mesh_is_rejected_even_with_forged_source_digests(self):
        model = json.loads((audit.REPO / "experiments/intent-edit-review/geometry/baseline.mesh.json").read_text())
        source = audit.source_files("01_sleeve_length")
        model["id"] = "01_sleeve_length"
        model["source_dxf_sha256"] = audit.sha(source["dxf"])
        model["source_spec_sha256"] = audit.sha(source["yaml"])
        sources, _ = audit.independent_piece_sources(source["dxf"])
        for panel in model["panels"]:
            panel["binding"]["source_piece_polyline_sha256"] = audit.sha(json.dumps(sources[panel["source_piece"]]["curves"], sort_keys=True, separators=(',', ':')).encode())
        with self.assertRaisesRegex(audit.AuditFailure, "boundary UV.*actual case DXF"):
            audit.audit_mesh_geometry(model, source, "01_sleeve_length")

    def test_3D_positions_are_checked_beyond_correct_UV_and_source_hashes(self):
        model = json.loads((audit.REPO / "experiments/intent-edit-review/geometry/baseline.mesh.json").read_text())
        model["panels"][0]["positions"][20][0] += .137
        with self.assertRaisesRegex(audit.AuditFailure, "3D boundary"):
            audit.audit_mesh_geometry(model, audit.source_files("baseline"), "baseline")


if __name__ == "__main__":
    unittest.main()
