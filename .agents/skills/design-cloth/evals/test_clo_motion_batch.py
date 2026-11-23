import importlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

batch = importlib.import_module("clo-motion-batch")


class MotionEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.request = {"fingerprint": "abc", "frames": [0, 1, 2],
                        "thresholds": dict(pressure=1, stress=22, strain=60,
                                           fold=70, crossings=0, coverage=0)}
        Image.new("RGB", (64, 64), "blue").save(self.path / "map.png")
        Image.new("RGB", (64, 64), "red").save(self.path / "strain.png")
        (self.path / "test.avi").touch()
        (self.path / "recorded.zprj").touch()
        self.receipt = {
            "fingerprint": "abc", "engine": "CLO 3D", "boat_id": "bx_test", "clo_version": "2026.1.382",
            "motion_checks_pass": True, "project_checks_pass": True, "video": "test.avi",
            "recording": {"source_frames": 3, "last_frame": 2, "cloth_geometry_changed": True,
                          "project": "recorded.zprj"},
            "frames": [self.frame(index) for index in range(3)],
        }

    def frame(self, index):
        maps = {key: {"image": "map.png", "frame": index, "value": .5, "unit": unit,
                      "source": "CLO mesh dihedral" if key == "fold" else "CLO native"}
                for key, unit in batch.UNITS.items()}
        maps["strain"]["image"] = "strain.png"
        maps["appearance"] = {"image": "map.png", "frame": index,
                              "views": {"back": "map.png", "side": "map.png"}}
        return {"index": index, "seconds": index / 30, "maps": maps, "crossings": 0, "coverage": 0}

    def result(self):
        batch.save(self.path / "receipt.json", self.receipt)
        return batch.review(self.path, self.request)

    def test_scope_and_threshold(self):
        self.assertEqual(self.result()["status"], "PASS")
        self.receipt["frames"][1]["crossings"] = 1
        self.assertEqual(self.result()["status"], "FAIL")
        self.receipt["fingerprint"] = "stale"
        self.assertEqual(self.result()["status"], "BLOCKED")

    def test_pressure_visual_only(self):
        del self.receipt["frames"][1]["maps"]["pressure"]["value"]
        result = self.result()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("1 帧缺少有效 pressure 读数", result["issues"])
        self.assertTrue(result["frames"][1]["maps"]["pressure"]["image"])

    def test_missing_map_mismatched_frame_and_truncated_track(self):
        self.receipt["frames"][1]["maps"]["stress"]["frame"] = 2
        self.receipt["frames"][1]["maps"]["strain"]["image"] = "absent.png"
        self.receipt["recording"]["last_frame"] = 1
        result = self.result()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(len(result["issues"]), 3)

    def test_invalid_picture_and_missing_last_frame(self):
        self.receipt["frames"].pop()
        (self.path / "map.png").write_text("not an image")
        result = self.result()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("缺少规定抽查帧或末帧", result["issues"])
        self.assertIn("1 帧缺少或错配 pressure 图", result["issues"])

    def test_identical_fit_maps_block(self):
        self.receipt["frames"][1]["maps"]["strain"]["image"] = "map.png"
        result = self.result()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("1 帧应力和应变图内容相同，需要核实原生图层", result["issues"])

    def test_path_traversal(self):
        self.assertIsNone(batch.evidence_path(self.path, "../another-run.png"))

    def test_resume_with_matching_fingerprint(self):
        self.assertEqual(self.result()["status"], "PASS")
        self.request["fingerprint"] = "changed seed"
        self.assertEqual(self.result()["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
