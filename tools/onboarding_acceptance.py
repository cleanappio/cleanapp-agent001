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
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "openclaw-skill" / "report.py"
USER_AGENT = "cleanapp-fresh-client-acceptance/0.2.0"
REGISTRY = "https://registry.modelcontextprotocol.io/v0.1/servers"
REGISTRY_NAME = "io.github.cleanappio/cleanapp"
REGISTRY_OFFICIAL = "io.modelcontextprotocol.registry/official"
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


def mcp_request(url, headers, message, timeout):
    req = urllib.request.Request(url, method="POST", headers=headers,
                                 data=json.dumps({"jsonrpc": "2.0", **message}).encode())
    method = message["method"]
    try:
        with urllib.request.build_opener(client.NoRedirect).open(req, timeout=timeout) as r:
            session = r.headers.get("MCP-Session-Id")
            if "id" not in message:
                return None, session
            body = r.read(524289)
    except urllib.error.HTTPError as e:
        raise client.ClientError(f"MCP {method} returned HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError):
        raise client.ClientError(f"MCP {method} network request failed") from None
    if len(body) > 524288:
        raise client.ClientError(f"MCP {method} response exceeded 512 KiB")
    try:
        body = body.decode("utf-8")
        if body.lstrip().startswith("{"):
            response = json.loads(body)
        else:
            events = [json.loads(line[5:].strip()) for line in body.splitlines() if line.startswith("data:")]
            response = next(x for x in events if x.get("id") == message["id"])
        if response.get("id") != message["id"] or not isinstance(response.get("result"), dict):
            raise ValueError()
        return response["result"], session
    except (ValueError, TypeError, AttributeError, StopIteration):
        raise client.ClientError(f"MCP {method} did not return a valid result") from None


def mcp_tools(url, allow_local_http=False, timeout=20):
    client.checked_url(url, allow_local_http)
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "User-Agent": USER_AGENT}
    initial, session = mcp_request(url, headers, {"id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-03-26", "capabilities": {},
        "clientInfo": {"name": USER_AGENT, "version": "0.2.0"},
    }}, timeout)
    try:
        headers["MCP-Protocol-Version"] = initial["protocolVersion"]
        version = initial["serverInfo"]["version"]
        if not all(isinstance(value, str) and value for value in (headers["MCP-Protocol-Version"], version)):
            raise ValueError()
        if session:
            headers["MCP-Session-Id"] = session
        # These protocol messages neither invoke tools nor submit reports.
        mcp_request(url, headers, {"method": "notifications/initialized"}, timeout)
        inventory, _ = mcp_request(url, headers, {"id": 2, "method": "tools/list", "params": {}}, timeout)
        names = {x["name"] for x in inventory["tools"]}
        if not all(isinstance(name, str) for name in names):
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise client.ClientError("MCP initialize or tools/list returned unexpected fields") from None
    required = {"cleanapp_prepare_report", "cleanapp_submit_report", "cleanapp_report_status"}
    if not required <= names:
        raise client.ClientError("MCP is missing report preview, submission or private status tools")
    return version, sorted(names)


def verify_homepage(front_door, timeout):
    homepage = urllib.parse.urljoin(front_door, "/")
    try:
        _, html = client.request(homepage, timeout=timeout)
    except client.ClientError as e:
        raise client.ClientError(f"CleanApp homepage check failed: {e}") from None
    links = client.Links()
    links.feed(html)
    if not any(urllib.parse.urljoin(homepage, link) == front_door for link in links.hrefs):
        raise client.ClientError("CleanApp homepage does not link to the agent guide")


def registry_get(path, label, timeout):
    req = urllib.request.Request(REGISTRY + path, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    try:
        with urllib.request.build_opener(client.NoRedirect).open(req, timeout=timeout) as response:
            body = response.read(524289)
        if len(body) > 524288:
            raise client.ClientError(f"MCP Registry {label} response exceeded 512 KiB")
        return json.loads(body)
    except urllib.error.HTTPError as e:
        raise client.ClientError(f"MCP Registry {label} returned HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError):
        raise client.ClientError(f"MCP Registry {label} network request failed") from None
    except ValueError:
        raise client.ClientError(f"MCP Registry {label} did not return JSON") from None


def registry_version(entry, endpoints, label):
    try:
        server = entry["server"]
        official = entry["_meta"][REGISTRY_OFFICIAL]
        version = server["version"]
        active_listing = (server["name"] == REGISTRY_NAME and official["status"] == "active"
                          and official["isLatest"] is True and isinstance(version, str) and version)
        matching_links = server["websiteUrl"] == endpoints["front_door"] and any(
            remote["type"] == "streamable-http" and remote["url"] == endpoints["mcp_endpoint"]
            for remote in server["remotes"])
    except (KeyError, TypeError):
        raise client.ClientError(f"MCP Registry {label} returned unexpected fields") from None
    if not active_listing:
        raise client.ClientError(f"MCP Registry {label} did not identify CleanApp's active latest listing")
    if not matching_links:
        raise client.ClientError(f"MCP Registry {label} guide or remote endpoint disagrees with agent instructions")
    return version


def verify_registry(endpoints, timeout):
    exact_path = f"/{urllib.parse.quote(REGISTRY_NAME, safe='')}/versions/latest"
    exact = registry_version(registry_get(exact_path, "exact lookup", timeout), endpoints, "exact lookup")
    search_path = "?" + urllib.parse.urlencode({"search": "CleanApp", "version": "latest", "limit": 20})
    results = registry_get(search_path, "brand search", timeout)
    try:
        match = next(entry for entry in results["servers"] if entry["server"]["name"] == REGISTRY_NAME)
    except (KeyError, TypeError, StopIteration):
        raise client.ClientError("MCP Registry brand search did not return CleanApp in the first 20 results") from None
    if registry_version(match, endpoints, "brand search") != exact:
        raise client.ClientError("MCP Registry exact lookup and brand search disagree on CleanApp's latest version")
    return exact


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--front-door", default=client.FRONT_DOOR)
    p.add_argument("--allow-local-http", action="store_true")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--submit", action="store_true", help="Send the real observation in --input; root/operator authorization required")
    mode.add_argument("--discovery-probe", action="store_true", help="Check homepage and official registry discovery in read-only mode")
    p.add_argument("--input", help="Approved real observation JSON; never a fabricated incident")
    p.add_argument("--receipt-file", help="Private output outside git (required for a submission run)")
    p.add_argument("--timeout", type=int, default=20)
    args = p.parse_args(argv)
    common = ["--front-door", args.front_door, "--timeout", str(args.timeout)]
    if args.allow_local_http:
        common.append("--allow-local-http")
    try:
        if args.discovery_probe:
            verify_homepage(args.front_door, args.timeout)
        endpoints = invoke("--discover", *common)
        version, tools = mcp_tools(endpoints["mcp_endpoint"], args.allow_local_http, args.timeout)
        result = {"front_door": endpoints["front_door"], "instructions_url": endpoints["instructions_url"],
                  "public_report_endpoint": endpoints["public_report_endpoint"], "mcp_server_version": version,
                  "mcp_tools": tools, "checks": ["fresh_discovery", "mcp_initialize", "mcp_tool_inventory"],
                  "submitted": False}
        if args.discovery_probe:
            result["registry_latest_version"] = verify_registry(endpoints, args.timeout)
            if result["registry_latest_version"] != version:
                raise client.ClientError("Official MCP Registry and live MCP server disagree on the version")
            result["checks"].insert(0, "homepage_agent_link")
            result["checks"].extend(["registry_exact_lookup", "registry_brand_search", "live_version_matches_registry"])
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
