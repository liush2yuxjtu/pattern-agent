"""Plan a whole seam batch offline or run it inside CLO with run_clo()."""
import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Span:
    piece: str
    line: int
    start: float
    end: float

    @property
    def key(self):
        return self.piece, self.line

    @property
    def interval(self):
        return sorted((self.start, self.end))

    def portion(self, start, end):
        return Span(self.piece, self.line, self.start + start * (self.end - self.start),
                    self.start + end * (self.end - self.start))

    def native(self, indices):
        return (indices[self.piece], self.line, *self.interval, self.end > self.start)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, result):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def catalog_lengths(catalog):
    table = {}
    for name, lines in catalog.items():
        for line in lines:
            key = name, int(line["lineIndex"])
            length = float(line["length"])
            require(key not in table and math.isfinite(length) and length > 0,
                    f"Invalid or duplicate native length for {key}")
            table[key] = length
    return table


def parse_span(value, table):
    span = Span(*value)
    require(span.key in table, f"Unknown native edge {span.key}")
    lo, hi = span.interval
    require(0 <= lo < hi <= 1, f"Invalid range on {span.key}: {span.start} → {span.end}")
    return span


def length(span, table):
    lo, hi = span.interval
    return (hi - lo) * table[span.key]


def partition(spans, table):
    sizes = [length(span, table) for span in spans]
    total = sum(sizes)
    breaks = [0.0]
    for size in sizes:
        breaks.append(breaks[-1] + size / total)
    breaks[-1] = 1.0
    return total, breaks


def split(spans, breaks, lo, hi):
    midpoint = (lo + hi) / 2
    i = next(i for i, (start, end) in enumerate(zip(breaks, breaks[1:])) if start <= midpoint <= end)
    start, end = breaks[i:i + 2]
    return spans[i].portion(max(0.0, (lo - start) / (end - start)),
                            min(1.0, (hi - start) / (end - start)))


def coverage(target, sewn, table):
    lo, hi = target.interval
    at = lo
    holes = []
    for start, end in sorted(s.interval for s in sewn if s.key == target.key):
        if start >= hi:
            break
        if end <= at:
            continue
        if start > at + 1e-8:
            holes.append([at, start])
        at = max(at, end)
    if at < hi - 1e-8:
        holes.append([at, hi])
    return [{"piece": target.piece, "line": target.line, "start": a, "end": b,
             "length_mm": round((b - a) * table[target.key], 6)} for a, b in holes]


def compile_plan(plan, catalog):
    table = catalog_lengths(catalog)
    rows, operations, issues = [], [], []
    used = set()
    require(isinstance(plan.get("routes"), list) and plan["routes"], "Provide at least one route")
    require(isinstance(plan.get("coverage"), list) and plan["coverage"],
            "Declare the expected route coverage independently of the segment pairs")
    for route in plan["routes"]:
        name = route["id"]
        require(name not in used, f"Repeated route ID: {name}")
        used.add(name)
        a, b = [[parse_span(s, table) for s in route[side]] for side in ("a", "b")]
        require(a and b, f"{name}: both routes need spans")
        length_a, breaks_a = partition(a, table)
        length_b, breaks_b = partition(b, table)
        limit = float(route["max_delta_mm"])
        require(math.isfinite(limit) and limit >= 0, f"{name}: invalid length tolerance")
        delta = length_a - length_b
        if abs(delta) > limit + 1e-8:
            issues.append(f"{name}: length difference {delta:+.3f} mm exceeds ±{limit:g} mm")
        cuts = []
        for point in sorted(breaks_a + breaks_b):
            if not cuts or point - cuts[-1] > 1e-9:
                cuts.append(point)
        cuts[-1] = 1.0
        pairs = [(split(a, breaks_a, lo, hi), split(b, breaks_b, lo, hi))
                 for lo, hi in zip(cuts, cuts[1:])]
        operations.extend((name, left, right) for left, right in pairs)
        rows.append({"id": name, "a_length_mm": round(length_a, 6), "b_length_mm": round(length_b, 6),
                     "a_minus_b_mm": round(delta, 6), "max_delta_mm": limit, "pairs": len(pairs)})
    names = set()
    for name, a, b in operations:
        key = tuple(sorted((s.piece, s.line, *(round(v, 9) for v in s.interval)) for s in (a, b)))
        require(key not in names and key[0] != key[1], f"{name}: duplicate pair or a span sewn to itself")
        names.add(key)
    sewn = [s for _, a, b in operations for s in (a, b)]
    gaps = [gap for target in plan["coverage"] for gap in coverage(parse_span(target, table), sewn, table)]
    if gaps:
        issues.append("Expected seam coverage has gaps")
    report = {"status": "blocked" if issues else "plan_passed", "routes": rows, "issues": issues,
              "coverage_gaps": gaps, "planned_groups": len(operations),
              "pairs": [{"route": name, "a": vars(a), "b": vars(b)} for name, a, b in operations]}
    return operations, report


def live_catalog(api):
    indices = {}
    catalog = {}
    for i in range(api.GetPatternCount()):
        name = api.GetPatternPieceName(i)
        require(name not in indices, f"Give each piece a unique name: {name}")
        indices[name] = i
        catalog[name] = json.loads(api.GetPatternLineInfo(i))["lines"]
    return indices, catalog


def run_clo(plan_path, report_path, pattern_api, utility_api, *, apply=False, steps=0):
    """Use apply=True on your disposable seam checkpoint. Always write one report."""
    report = {"status": "error", "groups_added": 0, "simulation_steps": 0}
    try:
        plan = load(plan_path)
        indices, catalog = live_catalog(pattern_api)
        ops, preflight = compile_plan(plan, catalog)
        before = pattern_api.GetSeamlinePairGroupCount()
        report.update(preflight, groups_before=before, groups_after=before)
        if preflight["issues"] or not apply:
            return report
        require(isinstance(steps, int) and steps >= 0, "steps must be a nonnegative integer")
        require(type(plan.get("expected_groups_before")) is int, "Set expected_groups_before for live apply")
        require(before == plan["expected_groups_before"],
                f"Group count changed: expected {plan['expected_groups_before']}, got {before}")
        report["status"] = "applying"
        for name, a, b in ops:
            left, right = a.native(indices), b.native(indices)
            a_before = set(pattern_api.GetSeamlinePairGroupListInPattern(left[0]))
            b_before = set(pattern_api.GetSeamlinePairGroupListInPattern(right[0]))
            rc = pattern_api.AddSeamlinePairGroupPartial(*left, *right)
            after = pattern_api.GetSeamlinePairGroupCount()
            report["groups_after"] = after
            delta = after - before
            expected = report["groups_added"] + 1
            require(delta == expected, f"{name}: expected group delta {expected}, got {delta}; API return {rc}")
            report["groups_added"] = delta
            a_new = set(pattern_api.GetSeamlinePairGroupListInPattern(left[0])) - a_before
            b_new = set(pattern_api.GetSeamlinePairGroupListInPattern(right[0])) - b_before
            require(len(a_new & b_new) == 1, f"{name}: new group was not found on both pieces")
        if steps:
            require(utility_api.Simulate(steps), "CLO simulation did not return success")
            report["simulation_steps"] = steps
        report["status"] = "native_groups_verified"
        return report
    except Exception as exc:
        if report["status"] == "applying":
            try:
                after = pattern_api.GetSeamlinePairGroupCount()
                report.update(groups_after=after, groups_added=after - report["groups_before"])
            except Exception as readback_error:
                report["readback_error"] = str(readback_error)
        report.update(status="error", error=str(exc))
        return report
    finally:
        write(report_path, report)


def main():
    parser = argparse.ArgumentParser(description="Preflight CLO seam routes without changing a project.")
    parser.add_argument("--plan", type=Path, required=True, help="JSON route and coverage plan")
    parser.add_argument("--catalog", type=Path, required=True, help="JSON by piece name with native line records")
    parser.add_argument("--report", type=Path, required=True, help="Destination JSON receipt")
    args = parser.parse_args()
    try:
        _, report = compile_plan(load(args.plan), load(args.catalog))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        report = {"status": "error", "error": str(exc)}
    write(args.report, report)
    print(json.dumps({k: v for k, v in report.items() if k != "pairs"}, ensure_ascii=False))
    return 0 if report["status"] == "plan_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
