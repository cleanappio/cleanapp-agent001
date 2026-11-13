"""HTTP contract fixture for a genuinely fresh client; never contacts production."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "openclaw-skill/report.py"
HARNESS = ROOT / "tools/onboarding_acceptance.py"
spec = importlib.util.spec_from_file_location("report", CLIENT)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


@contextmanager
def fixture():
    state = {"gets": [], "posts": [], "db": sqlite3.connect(":memory:", check_same_thread=False), "redirect_status": False}
    state["db"].execute("CREATE TABLE intake(source_id TEXT PRIMARY KEY, payload TEXT, receipt_id TEXT, token TEXT, lane TEXT)")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def answer(self, status, obj, content_type="application/json"):
            body = json.dumps(obj).encode() if isinstance(obj, (dict, list)) else obj.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            state["gets"].append(self.path)
            if self.path == "/agents":
                self.answer(200, '<a href="/agents.txt">Agent instructions</a>', "text/html")
            elif self.path == "/agents.txt":
                self.answer(200, f"Canonical page: {base}/agents\nMCP endpoint: {base}/mcp\nMCP authentication: none\nPublic report endpoint: {base}/api/v1/public/agent-reports\nPublic report authentication: none\n", "text/plain")
            elif self.path.startswith("/api/v1/public/agent-reports/receipts/"):
                receipt_id = self.path.rsplit("/", 1)[1]
                row = state["db"].execute("SELECT receipt_id,token,lane FROM intake WHERE receipt_id=?", (receipt_id,)).fetchone()
                if not row or self.headers.get("Authorization") != "Bearer " + row[1]:
                    self.answer(404, {"error": "not_found"})
                else:
                    self.answer(200, {"receipt_id": row[0], "status": "quarantined", "publication_status": "private"})
            else:
                self.answer(404, {"error": "not_found"})

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["posts"].append((self.path, payload, self.headers.get("Authorization")))
            if self.path == "/mcp":
                self.answer(200, {"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": x} for x in
                            ["cleanapp_prepare_report", "cleanapp_submit_report", "cleanapp_report_status"]]}})
            elif self.path == "/api/v1/public/agent-reports":
                source_id = payload["source_id"]
                fingerprint = json.dumps(payload, sort_keys=True)
                row = state["db"].execute("SELECT payload,receipt_id,token FROM intake WHERE source_id=?", (source_id,)).fetchone()
                replay = row is not None
                if row and row[0] != fingerprint:
                    self.answer(409, {"error": "source_id_conflict"})
                    return
                if not row:
                    row = (fingerprint, "rcpt_" + uuid.uuid4().hex, "private-fixture-" + uuid.uuid4().hex)
                    state["db"].execute("INSERT INTO intake VALUES(?,?,?,?,?)", (source_id, *row, "quarantine"))
                    state["db"].commit()
                status_url = "/api/v1/public/agent-reports/receipts/" + row[1]
                if state["redirect_status"]:
                    status_url = "https://example.org/steal-token"
                self.answer(200 if replay else 202, {"source_id": source_id, "receipt_id": row[1], "tracking_token": row[2],
                            "status": "quarantined", "publication_status": "private", "idempotency_replay": replay, "status_url": status_url})
            else:
                self.answer(404, {"error": "not_found"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    base = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield base, state
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
        state["db"].close()


class OnboardingTests(unittest.TestCase):
    def run_script(self, path, *args, data=None):
        return subprocess.run([sys.executable, str(path), *args], input=data, text=True, capture_output=True,
                              env={"PATH": os.defpath, "CLEANAPP_API_TOKEN": "fixture-key-must-not-be-used", "PYTHONDONTWRITEBYTECODE": "1"})

    def test_fresh_public_workflow_persists_one_private_report(self):
        with fixture() as (base, state), tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "approved.json"
            receipt = Path(tmp) / "private.json"
            source.write_text(json.dumps({"description": "Local contract fixture observation; never a public incident."}))
            p = self.run_script(HARNESS, "--front-door", base + "/agents", "--allow-local-http", "--submit",
                                "--input", str(source), "--receipt-file", str(receipt))
            self.assertEqual(p.returncode, 0, p.stderr)
            result = json.loads(p.stdout)
            self.assertIn("wrong_token_rejected", result["checks"])
            self.assertEqual(state["db"].execute("SELECT count(*) FROM intake WHERE lane='quarantine'").fetchone()[0], 1)
            sent = [x for x in state["posts"] if x[0].endswith("/agent-reports")]
            self.assertEqual(len(sent), 2)
            self.assertEqual(sent[0][1], sent[1][1])
            self.assertIsNone(sent[0][2])
            self.assertEqual(uuid.UUID(sent[0][1]["source_id"]).version, 4)
            saved = json.loads(receipt.read_text())
            self.assertNotIn(saved["receipt"]["tracking_token"], p.stdout + p.stderr)
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)

    def test_read_only_acceptance_never_intakes(self):
        with fixture() as (base, state):
            p = self.run_script(HARNESS, "--front-door", base + "/agents", "--allow-local-http")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertFalse(json.loads(p.stdout)["submitted"])
            self.assertEqual(state["db"].execute("SELECT count(*) FROM intake").fetchone()[0], 0)
            self.assertEqual([x[0] for x in state["posts"]], ["/mcp"])

    def test_offline_preview_uses_no_key_or_network(self):
        p = self.run_script(CLIENT, "--front-door", "http://not-a-server.invalid/agents", "--dry-run", "--description", "An observed problem")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout), {"description": "An observed problem"})

    def test_retry_changed_content_rejected_before_second_write(self):
        with fixture() as (base, state), tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "receipt.json")
            args = ("--front-door", base + "/agents", "--allow-local-http", "--submit", "--receipt-file", path)
            first = self.run_script(CLIENT, *args, "--description", "Original fixture observation")
            self.assertEqual(first.returncode, 0, first.stderr)
            changed = self.run_script(CLIENT, *args, "--retry", "--description", "Changed fixture observation")
            self.assertEqual(changed.returncode, 2)
            self.assertIn("Retry payload changed", changed.stderr)
            self.assertEqual(len([x for x in state["posts"] if x[0].endswith("/agent-reports")]), 1)

    def test_receipt_cannot_redirect_tracking_token(self):
        with fixture() as (base, state), tempfile.TemporaryDirectory() as tmp:
            state["redirect_status"] = True
            p = self.run_script(CLIENT, "--front-door", base + "/agents", "--allow-local-http", "--submit",
                                "--receipt-file", str(Path(tmp) / "receipt.json"), "--description", "Fixture observation")
            self.assertEqual(p.returncode, 2)
            self.assertNotIn("private-fixture-", p.stdout + p.stderr)
            self.assertTrue(all(not x.startswith("/steal-token") for x in state["gets"]))

    def test_unknown_context_and_utf8_bounds(self):
        self.assertEqual(report.validate_payload({"description": "Location unknown"}), {"description": "Location unknown"})
        for bad in ({"description": "x", "latitude": 1}, {"description": "x", "source_id": "predictable"},
                    {"description": "é" * 4097}, {"description": "x", "title": "é" * 128},
                    {"description": "x", "url": "https://example.org/" + "é" * 1020},
                    {"description": "x", "longitude": 1, "latitude": True}):
            with self.assertRaises(report.ClientError):
                report.validate_payload(bad)
        upper_uuid = str(uuid.uuid4()).upper()
        self.assertEqual(report.validate_payload({"description": "x", "source_id": upper_uuid})["source_id"], upper_uuid.lower())


if __name__ == "__main__":
    unittest.main()
