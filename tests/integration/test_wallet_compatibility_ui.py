import io
import json
import runpy
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SERVER = runpy.run_path(str(ROOT / "tools/serve_wallet_compatibility.py"))
HOST = "127.0.0.1:8765"
ORIGIN = f"http://{HOST}"


class MemoryConnection:
    def __init__(self, wire: bytes):
        self.request = io.BytesIO(wire)
        self.response = io.BytesIO()

    def settimeout(self, timeout):
        pass

    def makefile(self, mode, *_):
        return self.request if mode == "rb" else self.response

    def sendall(self, data):
        self.response.write(data)


def request(method, path, body=b"", *, host=HOST, origin=ORIGIN):
    wire = (
        f"{method} {path} HTTP/1.1\r\nHost: {host}\r\nOrigin: {origin}\r\n"
        f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n"
    ).encode("ascii") + body
    connection = MemoryConnection(wire)
    SERVER["CompatibilityHandler"](connection, ("127.0.0.1", 12345), SimpleNamespace(server_port=8765))
    headers, response = connection.response.getvalue().split(b"\r\n\r\n", 1)
    return int(headers.split(b" ", 2)[1]), headers, response


def test_ui_serves_only_approved_paths_and_uses_a_same_origin_policy():
    status, headers, body = request("GET", "/")
    assert status == 200
    assert b"Wallet Compatibility | VeriAbstain" in body
    assert b"connect-src 'self'" in headers
    assert b"Cache-Control: no-store" in headers
    assert request("GET", "/../../README.md")[0] == 404
    assert request("GET", "/", host="example.test")[0] == 403


def test_example_returns_owner_comparison_and_redacted_export():
    status, _, body = request("GET", "/api/example")
    report = json.loads(body)
    assert status == 200
    assert report["before"]["checks"]["developer_mode"] == "DISABLED"
    assert report["after"]["checks"]["developer_mode"] == "ENABLED"
    assert report["after"]["checks"]["app_confirmation"] == "MISMATCH"
    assert report["after"]["status"] == "INCONCLUSIVE"
    assert report["after"]["evidence"] == "USER_REPORTED"
    assert report["observation_order"] == "SUPPLIED"
    assert "# VeriAbstain before-and-after report" in report["markdown"]


def test_hosted_demo_uses_the_same_redacted_example():
    assets = SERVER["ASSETS"]
    demo_report = json.loads((assets / "example.json").read_text(encoding="utf-8"))
    assert demo_report == SERVER["build_example_report"]()
    assert "0x519664" not in json.dumps(demo_report)
    public_page = (assets.parent / "index.html").read_text(encoding="utf-8")
    assert 'href="/compatibility/index.html"' in public_page
    assert request("GET", "/compatibility/app.js")[0] == 200
    assert request("GET", "/compatibility/styles.css")[0] == 200


def test_import_uses_the_existing_checker_and_keeps_the_payload_private():
    case = (SERVER["EXAMPLES"] / "receipt-preview-matched.json").read_text(encoding="utf-8")
    payload = json.loads(case)
    body = json.dumps({"case": case, "now": 1795724500}).encode()
    status, _, response = request("POST", "/api/report", body)
    report = json.loads(response)
    assert status == 200
    assert report["after"]["status"] == "PREVIEW_MATCHED"
    assert report["after"]["evidence"] == "FIXTURE"
    assert report["before"] is None
    assert payload["expected"]["sender"].encode() not in response
    assert payload["expected"]["calldata"].encode() not in response


def test_import_rejects_cross_origin_and_invalid_input_without_echoing_case():
    body = json.dumps({"case": '{"schema_version":1,"schema_version":"private-value"}'}).encode()
    assert request("POST", "/api/report", body, origin="http://example.test")[0] == 403
    status, _, response = request("POST", "/api/report", body)
    assert status == 400
    assert json.loads(response) == {"status": "INVALID_REPORT"}
