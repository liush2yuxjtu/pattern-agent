"""Drive the public CLI against local protocol fixtures, never vendor software."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "probe_mcp.py"
SESSION = "local-fixture-session-do-not-log"
INITIALIZED = {
    "protocolVersion": "2025-03-26",
    "serverInfo": {"name": "local-protocol-fixture", "version": "1"},
    "capabilities": {"tools": {}},
}


@contextmanager
def service(reply):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            message = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append({"message": message, "headers": dict(self.headers)})
            reply(self, message)

        def do_GET(self):
            requests.append({"method": "GET"})
            self.send_response(500)
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/mcp", requests
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def respond(handler, message, result=None, *, sse=False, error=None):
    if "id" not in message:
        handler.send_response(202)
        handler.send_header("Content-Length", "0")
        handler.end_headers()
        return
    payload = {"jsonrpc": "2.0", "id": message["id"]}
    payload["error" if error is not None else "result"] = error if error is not None else result
    body = json.dumps(payload).encode()
    if sse:
        # The client must skip comments and unrelated server notifications.
        body = (b': keepalive\n\ndata: {"jsonrpc":"2.0","method":"notifications/progress"}\n\n'
                + b"event: message\ndata: " + body + b"\n\n")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream" if sse else "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Mcp-Session-Id", SESSION)
    handler.end_headers()
    handler.wfile.write(body)


class ProbeCLI(unittest.TestCase):
    def run_cli(self, url):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            process = subprocess.run(
                [sys.executable, str(SCRIPT), "--url", url, "--timeout", "2", "--output", str(output)],
                capture_output=True, text=True, timeout=8,
            )
            report = json.loads(output.read_text()) if output.exists() else None
            return process, report

    def test_json_and_sse_readonly_discovery_with_pagination(self):
        for init_sse in (False, True):
            with self.subTest(init_sse=init_sse):
                def reply(handler, message):
                    if message["method"] == "initialize":
                        respond(handler, message, INITIALIZED, sse=init_sse)
                    elif message["method"] == "notifications/initialized":
                        respond(handler, message)
                    elif message.get("params", {}).get("cursor") == "second":
                        respond(handler, message, {"tools": [{"name": "read_two", "inputSchema": {}}]}, sse=not init_sse)
                    else:
                        respond(handler, message, {"tools": [{"name": "read_one", "inputSchema": {}}], "nextCursor": "second"})

                with service(reply) as (url, requests):
                    process, report = self.run_cli(url)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(report["status"], "connected")
                self.assertEqual(report["tool_count"], 2)
                self.assertFalse(report["garment_simulation_verified"])
                self.assertEqual([r["message"]["method"] for r in requests],
                                 ["initialize", "notifications/initialized", "tools/list", "tools/list"])
                for request in requests[1:]:
                    headers = {k.lower(): v for k, v in request["headers"].items()}
                    self.assertEqual(headers["mcp-session-id"], SESSION)
                    self.assertEqual(headers["mcp-protocol-version"], "2025-03-26")
                self.assertNotIn(SESSION, json.dumps(report) + process.stdout + process.stderr)

    def test_connection_failure_creates_blocked_report(self):
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))  # Bound, but deliberately not listening.
            process, report = self.run_cli(f"http://127.0.0.1:{reserved.getsockname()[1]}/mcp")
        self.assertEqual(process.returncode, 2)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["garment_simulation_verified"])
        self.assertNotIn("Traceback", process.stderr)

    def test_repeated_cursor_is_blocked(self):
        def reply(handler, message):
            result = INITIALIZED if message["method"] == "initialize" else {"tools": [], "nextCursor": "loop"}
            respond(handler, message, result)
        with service(reply) as (url, requests):
            process, report = self.run_cli(url)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("repeated", report["error"])
        self.assertEqual(len(requests), 4)

    def test_redirect_does_not_forward_requests(self):
        with service(lambda handler, message: respond(handler, message, INITIALIZED)) as (destination, forwarded):
            def redirect(handler, _):
                handler.send_response(302)
                handler.send_header("Location", destination)
                handler.send_header("Content-Length", "0")
                handler.end_headers()
            with service(redirect) as (url, _):
                process, report = self.run_cli(url)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(forwarded, [])

    def test_unique_cursors_cannot_create_unbounded_pagination(self):
        page = 0

        def reply(handler, message):
            nonlocal page
            if message["method"] == "initialize":
                respond(handler, message, INITIALIZED)
            elif message["method"] == "notifications/initialized":
                respond(handler, message)
            else:
                page += 1
                respond(handler, message, {"tools": [], "nextCursor": str(page)})

        with service(reply) as (url, _):
            process, report = self.run_cli(url)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(page, 100)
        self.assertIn("exceeded 100 pages", report["error"])

    def test_remote_or_credential_urls_rejected_before_network(self):
        for url in ("https://example.invalid/mcp", "http://example.invalid/mcp",
                    "http://example-user:example-password@127.0.0.1:9/mcp",
                    "http://127.0.0.1:9/mcp?token=example", "http://127.0.0.1:9/mcp#example"):
            with self.subTest(url=url):
                process, report = self.run_cli(url)
                self.assertEqual(process.returncode, 2)
                self.assertIsNone(report)
                self.assertIn("credential-free local HTTP", process.stderr)

    def test_malformed_result_is_blocked_without_traceback(self):
        with service(lambda handler, message: respond(handler, message, [])) as (url, _):
            process, report = self.run_cli(url)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["error_type"], "ValueError")
        self.assertNotIn("Traceback", process.stderr)

    def test_protocol_error_does_not_log_server_message(self):
        with service(lambda handler, message: respond(handler, message, error={
                "code": -32601, "message": "fixture-private-message"})) as (url, _):
            process, report = self.run_cli(url)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("-32601", report["error"])
        self.assertNotIn("fixture-private-message", json.dumps(report))

    def test_invalid_tools_array_is_blocked(self):
        def reply(handler, message):
            respond(handler, message, INITIALIZED if message["method"] == "initialize" else {"tools": "invalid"})
        with service(reply) as (url, _):
            process, report = self.run_cli(url)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(report["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
