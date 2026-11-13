#!/usr/bin/env python3
"""Fresh public-client acceptance: discovery, receipt, status, replay, isolation.

Read-only by default. --submit needs a real approved observation JSON file.
No admin SQL, agent/provider key, browser login or existing client state is used.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "openclaw-skill" / "report.py"
spec = importlib.util.spec_from_file_location("public_report_client", CLIENT)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


def invoke(*args):
    # A clean subprocess has no access to parent API-key environment variables.
    proc = subprocess.run([sys.executable, str(CLIENT), *args], text=True, capture_output=True,
                          env={"PATH": os.defpath, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    if proc.returncode:
        raise client.ClientError(f"Fresh client failed ({proc.returncode}): {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def mcp_tools(url, allow_local_http=False, timeout=20):
    client.checked_url(url, allow_local_http)
    # tools/list is a read-only protocol operation, not a tool submission.
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    req = urllib.request.Request(url, method="POST", data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-03-26", "User-Agent": "cleanapp-fresh-client-acceptance/0.2.0"})
    try:
        with urllib.request.build_opener(client.NoRedirect).open(req, timeout=timeout) as r:
            body = r.read(524288).decode()
    except (urllib.error.URLError, TimeoutError):
        raise client.ClientError("MCP read-only discovery failed") from None
    try:
        if body.lstrip().startswith("{"):
            result = json.loads(body)
        else:
            events = [json.loads(line[5:].strip()) for line in body.splitlines() if line.startswith("data:")]
            result = next(x for x in events if x.get("id") == 1)
        names = {x["name"] for x in result["result"]["tools"]}
    except (ValueError, KeyError, StopIteration):
        raise client.ClientError("MCP tools/list did not return a tool inventory") from None
    required = {"cleanapp_prepare_report", "cleanapp_submit_report", "cleanapp_report_status"}
    if not required <= names:
        raise client.ClientError("MCP is missing report preview, submission or private status tools")
    return sorted(names)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--front-door", default=client.FRONT_DOOR)
    p.add_argument("--allow-local-http", action="store_true")
    p.add_argument("--submit", action="store_true", help="Send the real observation in --input; root/operator authorization required")
    p.add_argument("--input", help="Approved real observation JSON; never a fabricated incident")
    p.add_argument("--receipt-file", help="Private output outside git (required for a submission run)")
    p.add_argument("--timeout", type=int, default=20)
    args = p.parse_args(argv)
    common = ["--front-door", args.front_door, "--timeout", str(args.timeout)]
    if args.allow_local_http:
        common.append("--allow-local-http")
    try:
        endpoints = invoke("--discover", *common)
        tools = mcp_tools(endpoints["mcp_endpoint"], args.allow_local_http, args.timeout)
        result = {"front_door": endpoints["front_door"], "instructions_url": endpoints["instructions_url"],
                  "public_report_endpoint": endpoints["public_report_endpoint"], "mcp_tools": tools,
                  "checks": ["fresh_discovery", "mcp_tool_inventory"], "submitted": False}
        if not args.submit:
            print(json.dumps(result, indent=2))
            return 0
        if not args.input or not args.receipt_file:
            raise client.ClientError("--submit requires --input and --receipt-file")
        # Validate before any write; only the explicit --submit branch invokes intake.
        client.validate_payload(json.loads(Path(args.input).read_text()))
        first = invoke("--submit", "--input", args.input, "--receipt-file", args.receipt_file, *common)
        if first.get("idempotency_replay") is not False:
            raise client.ClientError("Expected one fresh receipt before testing its exact replay")
        saved = json.loads(Path(args.receipt_file).read_text())
        if stat.S_IMODE(Path(args.receipt_file).stat().st_mode) != 0o600:
            raise client.ClientError("Receipt file permissions are not 0600")
        receipt = client.validate_receipt(saved["receipt"], saved["endpoint"], allow_local_http=args.allow_local_http)
        if receipt["tracking_token"] in json.dumps(first):
            raise client.ClientError("Client leaked a tracking token to stdout")
        status = invoke("--status", "--receipt-file", args.receipt_file, *common)
        if status.get("receipt_id") != first["receipt_id"] or status.get("publication_status") != "private":
            raise client.ClientError("Status did not identify the same private receipt")
        replay = invoke("--submit", "--retry", "--input", args.input, "--receipt-file", args.receipt_file, *common)
        if replay.get("receipt_id") != first["receipt_id"] or replay.get("idempotency_replay") is not True:
            raise client.ClientError("Exact replay did not return the same receipt")
        try:
            client.json_request(receipt["status_url"], token="invalid-onboarding-test-token",
                                allow_local_http=args.allow_local_http, timeout=args.timeout)
        except client.HTTPFailure as e:
            if e.status not in {401, 403, 404}:
                raise client.ClientError("Wrong tracking token returned an unexpected failure status") from None
        else:
            raise client.ClientError("Wrong tracking token was accepted")
        result.update({"submitted": True, "receipt_id": first["receipt_id"], "publication_status": "private",
                       "checks": result["checks"] + ["private_quarantine_receipt", "private_file_mode0600", "authenticated_status",
                                                     "exact_replay_same_receipt", "wrong_token_rejected"]})
        print(json.dumps(result, indent=2))
        return 0
    except (client.ClientError, ValueError, KeyError, OSError) as e:
        print(f"Acceptance failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
