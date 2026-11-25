#!/usr/bin/env python3
"""Capture evidence from the open Style3D project without changing its state."""

import argparse
from collections import Counter
import gzip
import http.client
import json
import math
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit


class McpError(RuntimeError):
    pass


class Style3D:
    """Client for Style3D's local Streamable HTTP endpoint."""

    def __init__(self, endpoint, journal, *, log_arguments=True):
        url = urlsplit(endpoint)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "::1", "localhost"}
                or url.username or url.password or url.query or url.fragment):
            raise ValueError("Use a loopback URL, such as http://127.0.0.1:57281/mcp")
        self.connection = http.client.HTTPConnection(url.hostname, url.port, timeout=90)
        self.path = url.path or "/mcp"
        self.headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        self.sequence = 0
        self.journal = journal
        self.log_arguments = log_arguments
        self.calls = Counter()

    def start(self):
        reply = self.rpc("initialize", {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "style3d-audit", "version": "1.0"},
        })
        self.headers["MCP-Protocol-Version"] = reply["result"]["protocolVersion"]
        self.rpc("notifications/initialized", notification=True)

    def rpc(self, method, params=None, notification=False):
        self.sequence += 1
        request = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            request["params"] = params
        if not notification:
            request["id"] = self.sequence

        started = time.monotonic()
        label = method
        if method == "tools/call":
            label = params["arguments"].get("method", params["name"])
        self.calls[label] += 1
        record = {"sequence": self.sequence, "rpc": method, "operation": label}
        if method == "tools/call" and self.log_arguments:
            record["arguments"] = params["arguments"]
        try:
            self.connection.request("POST", self.path, json.dumps(request), self.headers)
            response = self.connection.getresponse()
            raw = response.read()
            if response.status not in (200, 202, 204):
                raise McpError(f"HTTP {response.status}: {raw.decode(errors='replace')[:300]}")
            session = response.getheader("Mcp-Session-Id")
            if session:
                self.headers["Mcp-Session-Id"] = session
            answer = json.loads(raw) if raw else {}
            if "error" in answer:
                raise McpError(str(answer["error"]))
            if "result" in answer and answer["result"].get("isError"):
                blocks = answer["result"].get("content", [])
                raise McpError(str(blocks[0].get("text", blocks) if blocks else answer))
            record["ok"] = True
            return answer
        except (OSError, http.client.HTTPException, ValueError, McpError) as error:
            record["ok"] = False
            record["error"] = str(error)
            self.connection.close()
            raise McpError(f"{label}: {error}") from error
        finally:
            record["milliseconds"] = round((time.monotonic() - started) * 1000, 1)
            print(json.dumps(record, ensure_ascii=False), file=self.journal, flush=True)

    def tool(self, name, data=None):
        result = self.rpc("tools/call", {"name": name, "arguments": data or {}})["result"]
        if "structuredContent" in result:
            return result["structuredContent"]
        blocks = result.get("content") or []
        if blocks and blocks[0].get("type") == "text":
            try:
                data = json.loads(blocks[0]["text"])
            except (ValueError, KeyError) as error:
                raise McpError(f"{name}: expected JSON tool output") from error
            if (isinstance(data, dict) and data.get("error")
                    and ("valid" not in data or isinstance(data["error"], dict))):
                raise McpError(f"{name}: {data['error']}")
            return data
        return result

    def call(self, method, **data):
        return self.tool("CallApi", {"method": method, "data": data})

    def close(self):
        self.connection.close()


def store_raw(folder, name, data):
    filename = name + ".json.gz"
    with gzip.open(folder / filename, "wt", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
    return filename


def state(client, sections):
    diagnostics = client.call("Simulation.GetDiagnostics")
    if not diagnostics.get("projectLoaded") or diagnostics.get("running") or diagnostics.get("recording"):
        details = ", ".join(f"{key}={diagnostics.get(key)}" for key in ("projectLoaded", "running", "recording"))
        raise McpError(f"Capture requires an open, stopped project ({details}).")
    data = {"diagnostics": diagnostics, "project": client.call("Project.GetGarmentInfo")}
    if sections & {"fit", "pressure"}:
        # Native fitting APIs cover main pieces. Keep the full list to expose coverage gaps.
        data["pieces"] = client.call("Pattern.GetAllClothPieceIds")["clothPieceIds"]
        data["mainPieces"] = client.call("Pattern.GetAllMainClothPieceIds")["clothPieceIds"]
        data["avatars"] = client.call("Avatar.GetAllIds")["avatarIds"]
    if "seams" in sections:
        data["seams"] = client.call("Sewing.GetAllIds")["connectPairIds"]
    return data


def safe_id(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise McpError(f"Unexpected Style3D entity identifier: {value!r}")
    return value


def audit_maps(client, folder, current, fit, issues):
    methods = [
        ("strain", "Simulation.GetClothStrainMap", "ratio"),
        ("stress", "Simulation.GetClothStressMap", "kPa"),
    ] if fit else []
    methods.append(("cloth-pressure", "Simulation.GetClothPressureMap", "Pa"))
    results = {}
    mesh_files = {}

    def capture(kind, method, unit, entity_arg, entity_id, known_mesh):
        name = f"{kind}-{safe_id(entity_id)}"
        args = {entity_arg: entity_id}
        try:
            raw = client.call(method, **args, includeMesh=not known_mesh)
            fingerprint = raw.get("meshFingerprint")
            if known_mesh and raw.get("valid") and (not fingerprint or fingerprint not in known_mesh):
                raw = client.call(method, **args, includeMesh=True)
                fingerprint = raw.get("meshFingerprint")
            mesh = raw.get("mesh")
            values = raw.get("values")
            count = raw.get("vertexCount")
            if (raw.get("valid") is not True or raw.get("status") != "ok"
                    or raw.get("unit") != unit or not isinstance(values, list) or not values
                    or len(values) != count or raw.get("actualValueCount") != count
                    or not all(type(v) in (int, float) and math.isfinite(v) for v in values)):
                reason = raw.get("error") or (
                    f"status={raw.get('status')!r}, unit={raw.get('unit')!r} (expected {unit}), "
                    f"vertexCount={count}, actualValueCount={raw.get('actualValueCount')}, "
                    f"returnedValues={len(values) if isinstance(values, list) else 'invalid'}"
                )
                raise McpError(reason)
            if isinstance(mesh, dict):
                if (mesh.get("valid") is not True or len(mesh.get("positions", [])) != count
                        or not fingerprint):
                    raise McpError("Returned mesh does not match the values.")
                if fingerprint not in known_mesh:
                    known_mesh[fingerprint] = store_raw(folder, "mesh-" + name, mesh)
                    mesh_files.update(known_mesh)
                raw.pop("mesh")
            if fingerprint not in known_mesh:
                raise McpError("No matching geometry for the returned mesh fingerprint.")
            nonzero = sum(v != 0 for v in values)
            result = {"unit": unit, "vertexCount": count, "nonzero": nonzero,
                      "min": min(values), "max": max(values), "source": raw.get("source"),
                      "meshFingerprint": fingerprint, "meshFile": known_mesh[fingerprint],
                      "valuesFile": store_raw(folder, name, raw)}
            if kind == "avatar-pressure" and not nonzero:
                issues.append(f"{name}: all readings are zero; reconcile with the native pressure view.")
            results[name] = result
        except McpError as error:
            issues.append(f"{name}: {error}")
            results[name] = {"error": str(error)}
            if "raw" in locals():
                results[name]["diagnosticFile"] = store_raw(folder, name + "-invalid", raw)

    omitted = sorted(set(current["pieces"]) - set(current["mainPieces"]))
    if omitted:
        issues.append(f"Fitting APIs use main pieces; separately review these pieces: {', '.join(omitted)}.")
    if not current["mainPieces"] or not current["avatars"]:
        issues.append("Fitting evidence needs at least one main cloth piece and an avatar.")
    for piece in current["mainPieces"]:
        known_mesh = {}
        for kind, method, unit in methods:
            capture(kind, method, unit, "clothPieceId", piece, known_mesh)
    for avatar in current["avatars"]:
        capture("avatar-pressure", "Simulation.GetAvatarPressureMap", "Pa", "avatarId", avatar, {})
    return {"maps": results, "meshes": mesh_files, "otherPieces": omitted}


def audit_seams(client, folder, ids, issues):
    results = {}
    for raw_id in ids:
        entity = safe_id(raw_id)
        row = {}
        for key, method in (("lengths", "GetLengths"), ("segments", "GetSegments"), ("property", "GetProperty")):
            try:
                row[key] = client.call("Sewing." + method, connectPairId=entity)
            except McpError as error:
                issues.append(f"Seam {entity}: {error}")
                row[key] = {"error": str(error)}
        results[entity] = row
    lengths = []
    for entity, seam in results.items():
        a = seam["lengths"].get("sideALengthMm")
        b = seam["lengths"].get("sideBLengthMm")
        if all(type(n) in (int, float) and math.isfinite(n) and n > 0 for n in (a, b)):
            lengths.append({"id": entity, "sideAMm": a, "sideBMm": b, "differenceMm": abs(a - b)})
        else:
            issues.append(f"Seam {entity}: no two positive native side lengths.")
    return {"seamFile": store_raw(folder, "seams", results), "count": len(ids),
            "largestDifferences": sorted(lengths, key=lambda row: row["differenceMm"], reverse=True)[:8]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for the journal, summary and raw evidence")
    parser.add_argument("--section", action="append", choices=("fit", "pressure", "seams"),
                        help="only collect the selected section(s); default: fit + seams")
    parser.add_argument("--endpoint", default="http://127.0.0.1:57281/mcp")
    parser.add_argument("--expected-project", help="expected garment name for the currently open project")
    parser.add_argument("--case", help="label for the pose, size and revision already open")
    args = parser.parse_args()
    sections = set(args.section or ["fit", "seams"])
    args.output.mkdir(parents=True)
    summary = {"case": args.case, "sections": sorted(sections), "issues": []}
    with (args.output / "requests.jsonl").open("x", encoding="utf-8") as journal:
        client = Style3D(args.endpoint, journal)
        try:
            client.start()
            summary["software"] = client.tool("GetSoftwareInfo")
            initial = state(client, sections)
            summary["initial"] = initial
            if args.expected_project and initial["project"].get("garmentName") != args.expected_project:
                raise McpError("The currently open project does not match --expected-project.")
            if sections & {"fit", "pressure"}:
                summary["fitting"] = audit_maps(client, args.output, initial, "fit" in sections, summary["issues"])
            if "seams" in sections:
                summary["sewing"] = audit_seams(client, args.output, initial["seams"], summary["issues"])
            summary["final"] = state(client, sections)
            if initial != summary["final"]:
                summary["issues"].append("Project identity, object IDs or diagnostic state changed during capture.")
        except (McpError, KeyError, TypeError) as error:
            summary["issues"].append(str(error))
        finally:
            summary["requestCounts"] = dict(sorted(client.calls.items()))
            summary["mcpRequests"] = sum(client.calls.values())
            summary["captureStatus"] = "needs_review" if summary["issues"] else "captured"
            client.close()
            (args.output / "summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['captureStatus']} · {summary['mcpRequests']} MCP requests · {args.output / 'summary.json'}")
    for issue in summary["issues"][:5]:
        print(issue)
    return 2 if summary["issues"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        sys.exit(str(error))
