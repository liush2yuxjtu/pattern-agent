"""Plan, validate and replay an input-bound YAML edit patch."""
from copy import deepcopy
from importlib import import_module
import math
from pathlib import Path
import re

from .formats import FormatError, PIECES, PROFILE, check_schema, digest, dump_yaml, join, load_yaml, split
from .legacy import audit_benchmark as audit
from .legacy import engine

CASES = {
    "sleeve_length": ("01_sleeve_length", ("袖片纵线",)),
    "body_length": ("02_body_length", ("前中纵线", "后中纵线")),
    "cuff_width": ("03_cuff_width", ("袖口展开线长",)),
    "front_neck_depth": ("04_front_neck", ("前片领深",)),
}
GRAMMAR = (
    ("sleeve_length", r"(lengthen|shorten) (?:the )?sleeves? (?:by )?"),
    ("body_length", r"(lengthen|shorten) (?:the )?(?:body|bodice|torso) (?:by )?"),
    ("cuff_width", r"(widen|narrow) (?:the )?cuffs? (?:by )?"),
    ("front_neck_depth", r"(deepen) (?:the )?front neck(?:line)? (?:by )?"),
)
CHINESE = {
    "sleeve_length": r"袖(?:子|长)(加长|缩短|减短)",
    "body_length": r"(?:衣长|衣身|前后衣身)(加长|缩短|减短)",
    "cuff_width": r"袖口(加宽|放宽|收窄|缩窄)",
    "front_neck_depth": r"前领(?:口|深)?(加深)",
}
AMOUNT = r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<units>U|mm|cm|in|毫米|厘米|英寸)"
CONVERSIONS = {"mm": 1, "cm": 10, "in": 25.4}


class NeedsReview(FormatError):
    """The intent needs human confirmation before an edit can be compiled."""


def resolve(intent, pattern):
    check_schema("design-intent", intent)
    if (intent["pattern_id"], intent["size"]) != (pattern["pattern_id"], pattern["size"]):
        raise FormatError("The intent must identify the same pattern and size")
    op = intent.get("operation")
    if op is None:
        op = parse_text(intent["text"])
    else:
        try:
            plain = parse_text(intent["text"])
        except NeedsReview:
            plain = None
        if plain is not None and plain != op:
            raise NeedsReview("The stated amount or operation conflicts with the structured operation")
    delta = op["delta"]
    unit = op["unit"]
    if unit != "U":
        scale = pattern["coordinates"]["mm_per_unit"]
        if not scale:
            raise NeedsReview("Physical units require an approved millimetres-per-U calibration")
        delta *= CONVERSIONS[unit] / scale
    delta = round(delta, 6)
    if not math.isfinite(delta) or not delta or abs(delta) > 100000:
        raise FormatError("The resolved change must be finite, nonzero and representable in U")
    if op["type"] == "front_neck_depth" and delta <= 0:
        raise NeedsReview("This front-neck operation supports a positive deepening")
    return {"type": op["type"], "delta": delta, "unit": "U"}


def parse_text(text):
    cleaned = text.strip().rstrip(".。").strip()
    for name, prefix in (*GRAMMAR, *CHINESE.items()):
        match = re.fullmatch(prefix + r"\s*" + AMOUNT, cleaned, re.I)
        if not match:
            continue
        verb, amount, unit = match.groups()
        negative = verb.lower() in {"shorten", "narrow", "缩短", "减短", "收窄", "缩窄"}
        normalized = {"u": "U", "毫米": "mm", "厘米": "cm", "英寸": "in"}.get(unit.lower(), unit.lower())
        return {"type": name, "delta": float(amount) * (-1 if negative else 1), "unit": normalized}
    raise NeedsReview("Supply one supported operation, direction, amount and unit. Review the original request if any are missing.")


def open_source(pattern_data, spec_data, dxf):
    pattern = load_yaml(pattern_data)
    spec = load_yaml(spec_data)
    model = join(pattern, spec)
    drawing_hash = digest(dxf)
    if pattern["source"]["sha256"] != drawing_hash:
        raise FormatError("The DXF bytes do not match the source digest in the 2D YAML")
    if split(model, drawing_hash) != (pattern, spec):
        raise FormatError("The supplied YAML includes profile data that cannot round-trip")
    rows, _ = audit.read_cad(dxf)
    if audit.canonical(rows) != audit.canonical(audit.model_rows(model)):
        raise FormatError("The 2D YAML geometry and original DXF disagree")
    return pattern, spec, model


def validate_geometry(base, edited, dxf, case, delta):
    raw, inventory = audit.read_cad(dxf)
    if audit.canonical(raw) != audit.canonical(audit.model_rows(edited)):
        raise FormatError("Edited YAML geometry and DXF disagree")
    audit.preserve_structure(base, edited)
    for piece in case["preserve_pieces"]:
        if base["完整二维几何"][piece] != edited["完整二维几何"][piece]:
            raise FormatError(f"Edit changed protected piece {piece}")
    before = audit.measure_model(base)
    after = audit.measure_model(edited)
    old_dimensions, new_dimensions = before["dimensions"], after["dimensions"]
    old_contours = audit.contour_quality(base)
    new_contours = audit.contour_quality(edited)
    max_gap = 0
    for name, old in old_contours.items():
        new = new_contours[name]
        if new["crosses"] - old["crosses"] or new["zeros"] - old["zeros"]:
            raise FormatError(f"New contour intersection or zero-length segment: {name}")
        tol = audit.GAP_ROUNDING_TOL
        newly_open = any(a <= tol < b for a, b in zip(old["gaps"], new["gaps"], strict=True))
        if newly_open or max(new["gaps"]) > max(old["gaps"]) + tol:
            raise FormatError(f"Contour closure regressed: {name}")
        max_gap = max(max_gap, *new["gaps"])
    protected = audit.intent_checks(case["audit_case"], base, edited, before, after, delta)
    names = case["target_measurements"]
    measurements = []
    for name in names:
        a, b = old_dimensions[name], new_dimensions[name]
        if not math.isclose(b - a, delta, abs_tol=5e-6, rel_tol=0):
            raise FormatError(f"{name} does not meet the declared delta: {b - a:.6f} U")
        measurements.append({"name": name, "before": round(a, 6), "after": round(b, 6), "delta": round(b - a, 6), "unit": "U"})
    interface_changes = []
    for key, a in before["ports"].items():
        b = after["ports"][key]
        if abs(a-b) > 1e-6:
            interface_changes.append({"piece": key[0], "interface": key[1], "change_U": round(b-a, 6)})
    return {
        "result": "PASS",
        "scope": "2D geometric candidate",
        "measured_targets": measurements,
        "changed_interface_lengths": interface_changes,
        "max_existing_contour_gap_U": round(max_gap, 6),
        "inventory": inventory,
        "protected_geometry_checks": protected,
        "production": "BLOCKED",
        "physical_fit": "NOT_RUN",
        "production_holds": engine.reader.production_status(edited)["阻止生产的项目"],
    }


def draft_case(op, intent):
    module_name, targets = CASES[op["type"]]
    module = import_module(f".legacy.cases.{module_name}", package=__package__)
    case = deepcopy(module.CASE)
    case["id"] = intent["id"]
    case["intent"] = intent["text"]
    case["parameters"] = dict(op)
    case["audit_case"] = module_name
    case["target_measurements"] = targets
    locked = {PIECES[k] for k in intent.get("preserve_pieces", [])}
    if locked.intersection(case["affected_pieces"]):
        raise NeedsReview("The requested operation conflicts with a locked piece")
    return module, case


def hashes(pattern_data, spec_data, dxf):
    return {"pattern": digest(pattern_data), "spec": digest(spec_data), "dxf": digest(dxf)}


def compile_patch(pattern_data, spec_data, dxf, intent_data):
    pattern, spec, base = open_source(pattern_data, spec_data, dxf)
    intent = load_yaml(intent_data)
    op = resolve(intent, pattern)
    module, case = draft_case(op, intent)
    edited = deepcopy(base)
    details = module.edit(edited, op["delta"])
    engine.recompute(edited)
    engine.record_execution(edited, case, details, digest(Path(module.__file__).read_bytes()), digest(spec_data))
    edited["结构决策与操作方案"]["本轮有序操作序列"][0]["实现"] = "pattern_tool/legacy/cases/" + CASES[op["type"]][0] + ".py"
    engine.reader.validate(edited)
    cad, result_dxf, _ = engine.geometry_patch(dxf, base, edited)
    if not cad["operations"]:
        raise FormatError("No DXF coordinate change was generated")
    result_pattern, result_spec = split(edited, digest(result_dxf))
    result_pattern_data, result_spec_data = dump_yaml(result_pattern), dump_yaml(result_spec)
    report = validate_geometry(base, edited, result_dxf, case, op["delta"])
    patch = {
        "schema": "pattern-edit-patch/v1",
        "profile": PROFILE,
        "intent": intent,
        "resolved_operation": op,
        "base": hashes(pattern_data, spec_data, dxf),
        "target": hashes(result_pattern_data, result_spec_data, result_dxf),
        "pattern_operations": engine.semantic_diff(pattern, result_pattern),
        "spec_operations": engine.semantic_diff(spec, result_spec),
        "dxf_operations": cad["operations"],
    }
    check_schema("edit-patch", patch)
    return patch, report


def replay_patch(pattern_data, spec_data, dxf, patch_data):
    patch = check_schema("edit-patch", load_yaml(patch_data))
    if patch["base"] != hashes(pattern_data, spec_data, dxf):
        raise FormatError("Patch base digests disagree with the submitted inputs")
    pattern, spec, base = open_source(pattern_data, spec_data, dxf)
    if patch["profile"] != pattern["profile"] or patch["resolved_operation"] != resolve(patch["intent"], pattern):
        raise FormatError("Patch operation is inconsistent with the original intent or profile")
    _, case = draft_case(patch["resolved_operation"], patch["intent"])
    pattern = audit.apply_spec_operations(pattern, patch["pattern_operations"])
    spec = audit.apply_spec_operations(spec, patch["spec_operations"])
    result_pattern_data, result_spec_data = dump_yaml(pattern), dump_yaml(spec)
    dxf_patch = {
        "base_sha256": patch["base"]["dxf"], "target_sha256": patch["target"]["dxf"], "operations": patch["dxf_operations"]
    }
    result_dxf = engine.apply_dxf_patch(dxf, dxf_patch)
    if patch["target"] != hashes(result_pattern_data, result_spec_data, result_dxf):
        raise FormatError("Replayed outputs do not match the expected digests")
    _, _, edited = open_source(result_pattern_data, result_spec_data, result_dxf)
    # Verify that changed source tags are exactly the coordinate edits implied by
    # the two vector graphs. This also binds raw tags to their real entities.
    cad, expected_dxf, _ = engine.geometry_patch(dxf, base, edited)
    if cad["operations"] != patch["dxf_operations"] or result_dxf != expected_dxf:
        raise FormatError("DXF patch contains operations outside the model's coordinate edits")
    report = validate_geometry(base, edited, result_dxf, case, patch["resolved_operation"]["delta"])
    return result_pattern_data, result_spec_data, result_dxf, report, base, edited
