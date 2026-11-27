"""Serve the compatibility checker on this computer's loopback interface."""

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from veriabstain_eval.wallet_compatibility import (
    MAX_REPORT_BYTES,
    Timestamp,
    check_compatibility,
    compare_compatibility,
    parse_compatibility_case,
    public_action,
    render_comparison_markdown,
    render_compatibility_markdown,
)
from veriabstain_eval.workers import strict_json


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "apps/web/dist/compatibility"
EXAMPLES = ROOT / "examples/wallet-compatibility"
EXAMPLE_TIME = 1795724572
MAX_REQUEST_BYTES = 12 * MAX_REPORT_BYTES + 1024
STATIC = {
    "/": ("index.html", "text/html"),
    "/compatibility/styles.css": ("styles.css", "text/css"),
    "/compatibility/app.js": ("app.js", "text/javascript"),
}


class ReportInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    case: str
    baseline: str | None = None
    now: Timestamp | None = None
    baseline_now: Timestamp | None = None


def build_report(request: ReportInput) -> dict:
    case = parse_compatibility_case(request.case.encode("utf-8"))
    now = int(time.time()) if request.now is None else request.now
    if request.baseline is None:
        if request.baseline_now is not None:
            raise ValueError("A baseline time requires a baseline")
        report = check_compatibility(case, now)
        return {
            "action": public_action(case.expected),
            "before": None,
            "after": report,
            "markdown": render_compatibility_markdown(case, report),
        }

    baseline = parse_compatibility_case(request.baseline.encode("utf-8"))
    baseline_now = now if request.baseline_now is None else request.baseline_now
    report = compare_compatibility(baseline, case, baseline_now=baseline_now, current_now=now)
    return {
        "action": report["expected_action"],
        "before": report["before"],
        "after": report["after"],
        "expected_input_checks": report["expected_input_checks"],
        "observation_order": report["observation_order"],
        "markdown": render_comparison_markdown(report),
    }


def build_example_report() -> dict:
    case = (EXAMPLES / "receipt-owner-preview.json").read_text(encoding="utf-8")
    baseline = (EXAMPLES / "receipt-owner-developer-mode-off.json").read_text(encoding="utf-8")
    return build_report(ReportInput(case=case, baseline=baseline, now=EXAMPLE_TIME))


class CompatibilityHandler(BaseHTTPRequestHandler):
    timeout = 5

    @property
    def authority(self) -> str:
        return f"127.0.0.1:{self.server.server_port}"

    def log_message(self, *_):
        pass

    def respond(self, status: int, data: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
        )
        self.end_headers()
        self.wfile.write(data)

    def respond_json(self, status: int, data: dict):
        self.respond(status, json.dumps(data).encode("utf-8"), "application/json")

    def do_GET(self):
        if self.headers.get_all("Host") != [self.authority]:
            self.respond_json(403, {"status": "FORBIDDEN"})
            return
        if self.path == "/api/example":
            self.respond_json(200, build_example_report())
            return
        asset = STATIC.get(self.path)
        if asset is None:
            self.respond_json(404, {"status": "NOT_FOUND"})
            return
        name, content_type = asset
        self.respond(200, (ASSETS / name).read_bytes(), content_type)

    def do_POST(self):
        if (
            self.headers.get_all("Host") != [self.authority]
            or self.headers.get_all("Origin") != [f"http://{self.authority}"]
        ):
            self.respond_json(403, {"status": "FORBIDDEN"})
            return
        if self.path != "/api/report":
            self.respond_json(404, {"status": "NOT_FOUND"})
            return
        if self.headers.get_content_type() != "application/json" or self.headers.get("Transfer-Encoding"):
            self.respond_json(415, {"status": "INVALID_CONTENT_TYPE"})
            return
        lengths = self.headers.get_all("Content-Length") or []
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdecimal() or len(lengths[0]) > 6:
            self.respond_json(400, {"status": "INVALID_LENGTH"})
            return
        length = int(lengths[0])
        if length > MAX_REQUEST_BYTES:
            self.respond_json(413, {"status": "INPUT_TOO_LARGE"})
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete request")
            request = ReportInput.model_validate(strict_json(raw.decode("utf-8")))
            report = build_report(request)
        except (OSError, ValueError):
            self.respond_json(400, {"status": "INVALID_REPORT"})
            return
        self.respond_json(200, report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765, help="Local port, or 0 to use an available port.")
    parser.add_argument("--export-demo", action="store_true", help="Regenerate the redacted static demo report.")
    args = parser.parse_args()
    if args.export_demo:
        destination = ASSETS / "example.json"
        destination.write_text(json.dumps(build_example_report(), indent=2) + "\n", encoding="utf-8")
        print(f"Saved {destination.relative_to(ROOT)}")
        return 0
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    with ThreadingHTTPServer(("127.0.0.1", args.port), CompatibilityHandler) as server:
        print(f"VeriAbstain workspace: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
