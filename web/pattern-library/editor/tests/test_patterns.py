"""Coverage of split documents, signed deltas, independent replay and holds."""
import copy
import unittest

from pattern_tool.compiler import NeedsReview, compile_patch, open_source, replay_patch
from pattern_tool.formats import ROOT, FormatError, digest, dump_yaml, load_yaml, split
from pattern_tool.legacy.audit_benchmark import AuditFailure

SAMPLES = ROOT / "samples"


class PatternTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pattern, cls.spec, cls.dxf = [(SAMPLES / x).read_bytes() for x in ("pattern-2d.yaml", "pattern-spec.yaml", "input.dxf")]
        cls.intent = (SAMPLES / "intent.yaml").read_bytes()
        cls.patch, cls.measure = compile_patch(cls.pattern, cls.spec, cls.dxf, cls.intent)

    def test_lossless_split(self):
        original = load_yaml((SAMPLES / "input-spec.yaml").read_bytes())
        self.assertEqual(split(original, digest(self.dxf)), (load_yaml(self.pattern), load_yaml(self.spec)))
        self.assertEqual(open_source(self.pattern, self.spec, self.dxf)[2], original)

    def test_sleeve_compile_and_replay(self):
        outputs = replay_patch(self.pattern, self.spec, self.dxf, dump_yaml(self.patch))
        self.assertEqual(outputs[3]["measured_targets"][0]["delta"], 23.0)
        self.assertEqual(outputs[3]["inventory"]["entities"], 231)
        self.assertEqual(digest(outputs[2]), self.patch["target"]["dxf"])
        self.assertEqual(outputs[3]["production"], "BLOCKED")

    def test_more_deltas(self):
        for name, delta in (("shorter-sleeve", -12.5), ("longer-body", 17), ("shorter-body", -13), ("cuff", 7.25), ("neck", 8)):
            with self.subTest(name=name):
                intent = (SAMPLES / "intents" / (name + ".yaml")).read_bytes()
                patch, direct = compile_patch(self.pattern, self.spec, self.dxf, intent)
                *_, reopened, base, edited = replay_patch(self.pattern, self.spec, self.dxf, dump_yaml(patch))
                self.assertEqual(reopened, direct)
                self.assertTrue(all(m["delta"] == delta for m in reopened["measured_targets"]))

    def test_confirmed_scale(self):
        pattern = load_yaml(self.pattern)
        pattern["coordinates"]["mm_per_unit"] = 0.8
        legacy = pattern["coordinates"]["source_metadata"]["实际比例"]
        legacy.update({"状态": "已标定", "每U毫米数": 0.8})
        intent = (SAMPLES / "intents" / "uncalibrated.yaml").read_bytes()
        patch, report = compile_patch(dump_yaml(pattern), self.spec, self.dxf, intent)
        self.assertEqual(patch["resolved_operation"]["delta"], 25.0)
        self.assertEqual(report["measured_targets"][0]["delta"], 25.0)

    def test_ambiguous_or_uncalibrated(self):
        for name in ("uncalibrated", "ambiguous"):
            with self.subTest(name=name), self.assertRaises(NeedsReview):
                compile_patch(self.pattern, self.spec, self.dxf, (SAMPLES / "intents" / (name + ".yaml")).read_bytes())

    def test_invalid_cuff_and_lock(self):
        intent = load_yaml(self.intent)
        intent.update(text="Test a width below zero", operation={"type": "cuff_width", "delta": -1000, "unit": "U"})
        with self.assertRaises(ValueError):
            compile_patch(self.pattern, self.spec, self.dxf, dump_yaml(intent))
        intent["preserve_pieces"] = ["sleeve"]
        with self.assertRaises(NeedsReview):
            compile_patch(self.pattern, self.spec, self.dxf, dump_yaml(intent))

    def test_edit_chains_against_new_revision(self):
        p, s, d, *_ = replay_patch(self.pattern, self.spec, self.dxf, dump_yaml(self.patch))
        intent = (SAMPLES / "intents" / "cuff.yaml").read_bytes()
        patch, result = compile_patch(p, s, d, intent)
        self.assertEqual(patch["base"]["dxf"], digest(d))
        *_, verified, _, _ = replay_patch(p, s, d, dump_yaml(patch))
        self.assertEqual(result, verified)

    def test_wrong_revision(self):
        with self.assertRaises(FormatError):
            replay_patch(self.pattern, self.spec, self.dxf + b" ", dump_yaml(self.patch))

    def test_tampered_patch(self):
        patch = copy.deepcopy(self.patch)
        patch["dxf_operations"][0]["old"] = "0"
        with self.assertRaises(ValueError):
            replay_patch(self.pattern, self.spec, self.dxf, dump_yaml(patch))
        patch = copy.deepcopy(self.patch)
        patch["pattern_operations"][0]["old"] = "bad"
        with self.assertRaises(AuditFailure):
            replay_patch(self.pattern, self.spec, self.dxf, dump_yaml(patch))

    def test_intent_conflict_and_duplicate_keys(self):
        i = load_yaml(self.intent)
        i["operation"] = {"type": "cuff_width", "delta": 10, "unit": "U"}
        with self.assertRaises(NeedsReview):
            compile_patch(self.pattern, self.spec, self.dxf, dump_yaml(i))
        with self.assertRaises(ValueError):
            load_yaml(b"id: one\nid: two\n")


if __name__ == "__main__":
    unittest.main()
