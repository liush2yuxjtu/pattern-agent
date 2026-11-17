#!/usr/bin/env python3
"""Read-only discovery of the MCP service running inside the Style3D machine."""

import argparse
import datetime
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Keep the local service from forwarding MCP requests to another endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_reply(response, request_id):
    content_type = response.headers.get("Content-Type", "").lower()
    if "text/event-stream" not in content_type:
        body = response.read(8 * 1024 * 1024 + 1)
        if len(body) > 8 * 1024 * 1024:
            raise ValueError("MCP response exceeded 8 MiB")
        if not body:
            return None
        return json.loads(body)
    event_data = []
    total = 0
    for raw_line in response:
        total += len(raw_line)
        if total > 8 * 1024 * 1024:
            raise ValueError("MCP event stream exceeded 8 MiB")
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if line.startswith("data:"):
            event_data.append(line[5:].lstrip(" "))
        elif not line and event_data:
            item = json.loads("\n".join(event_data))
            event_data = []
            if isinstance(item, dict) and item.get("id") == request_id:
                return item
    raise ValueError("MCP stream ended before the matching reply")


class Client:
    def __init__(self, url, timeout):
        self.url = url
        self.timeout = timeout
        self.session_id = None
        self.protocol_version = None
        self.request_id = 0
        # This script runs on the same machine as Studio. Loopback must stay local.
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect()
        )

    def send(self, method, params=None, notification=False):
        message = {"jsonrpc": "2.0", "method": method}
        if not notification:
            self.request_id += 1
            message["id"] = self.request_id
        if params is not None:
            message["params"] = params
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        request = urllib.request.Request(
            self.url, data=json.dumps(message).encode("utf-8"), headers=headers
        )
        with self.opener.open(request, timeout=self.timeout) as response:
            self.session_id = response.headers.get("Mcp-Session-Id", self.session_id)
            if notification:
                return None
            item = read_reply(response, message["id"])
        if not isinstance(item, dict) or item.get("id") != message["id"]:
            raise ValueError("MCP server returned an unexpected reply")
        if "error" in item:
            error = item["error"]
            raise ValueError("MCP protocol error: " + str(error.get("code")))
        if "result" not in item:
            raise ValueError("MCP reply has no result")
        if not isinstance(item["result"], dict):
            raise ValueError("MCP result must be an object")
        return item["result"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:57281/mcp")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--output", default="style3d-mcp-discovery.json")
    args = parser.parse_args()
    parsed = urllib.parse.urlsplit(args.url)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        parser.error("Use a credential-free local HTTP MCP URL on the Style3D machine")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    report = {
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "endpoint": args.url,
        "status": "blocked",
        "scope": "MCP initialize and tools/list only; no garment operation is performed",
        "official_reference": "https://help.style3d.com/studio/en/1f8f/120a2",
        "garment_simulation_verified": False,
    }
    try:
        client = Client(args.url, args.timeout)
        initialized = client.send("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "style3d-readonly-probe", "version": "1.0"},
        })
        client.protocol_version = initialized.get("protocolVersion")
        if not isinstance(client.protocol_version, str) or not client.protocol_version:
            raise ValueError("MCP initialization omitted the negotiated protocol version")
        report["protocol_version"] = client.protocol_version
        report["server_info"] = initialized.get("serverInfo")
        report["server_capabilities"] = initialized.get("capabilities")
        client.send("notifications/initialized", notification=True)
        tools = []
        seen_cursors = set()
        params = {}
        for _ in range(100):
            page = client.send("tools/list", params)
            page_tools = page.get("tools")
            if not isinstance(page_tools, list) or not all(isinstance(t, dict) for t in page_tools):
                raise ValueError("MCP tools/list must return an array of tool objects")
            tools.extend(page_tools)
            cursor = page.get("nextCursor")
            if not cursor:
                break
            if not isinstance(cursor, str):
                raise ValueError("MCP pagination cursor must be a string")
            if cursor in seen_cursors:
                raise ValueError("MCP server repeated a pagination cursor")
            seen_cursors.add(cursor)
            params = {"cursor": cursor}
        else:
            raise ValueError("MCP tools/list exceeded 100 pages")
        report.update(status="connected", tool_count=len(tools), tools=tools)
    except (OSError, ValueError, TypeError, KeyError) as error:
        # Headers, session IDs, passwords and verification codes are never printed.
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "tool_count": report.get("tool_count"),
                      "report": str(output), "error_type": report.get("error_type")}, ensure_ascii=False))
    return 0 if report["status"] == "connected" else 2


if __name__ == "__main__":
    sys.exit(main())
