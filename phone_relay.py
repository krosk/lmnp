"""
BNP relay server — runs in Termux on the phone.
Receives HTTP POST requests from the sandbox, forwards them to BNP from the phone's IP,
returns the response. Exposed via a Cloudflare HTTP tunnel.

Usage:
    python phone_relay.py [--secret SECRET] [--port PORT]

Then expose with:
    cloudflared tunnel --url http://localhost:8888 --no-autoupdate
"""
import argparse
import base64
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

HOP_BY_HOP = frozenset([
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
    "proxy-connection", "content-encoding",
])

def filter_headers(headers):
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP}


class RelayHandler(BaseHTTPRequestHandler):
    secret = None
    session = None

    def log_message(self, fmt, *args):
        print(fmt % args, file=sys.stderr)

    def send_json_error(self, code, error_type, message):
        body = json.dumps({"ok": False, "error_type": error_type, "error": message}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Auth check
        if self.secret:
            token = self.headers.get("X-Relay-Secret", "")
            if token != self.secret:
                self.send_response(403)
                self.end_headers()
                return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            req = json.loads(raw)
        except Exception as e:
            self.send_json_error(400, "parse_error", str(e))
            return

        method = req.get("method", "GET").upper()
        url = req.get("url", "")
        headers = filter_headers(req.get("headers", {}))
        body = req.get("body")  # base64-encoded string or null

        if body is not None:
            body = base64.b64decode(body)

        # Force correct Host header
        from urllib.parse import urlparse
        parsed = urlparse(url)
        headers["Host"] = parsed.netloc

        try:
            resp = self.session.request(
                method=method,
                url=url,
                headers=headers,
                data=body,
                allow_redirects=False,
                timeout=30,
                verify=True,
            )
        except requests.exceptions.SSLError as e:
            self.send_json_error(200, "ssl_error", str(e))
            return
        except requests.exceptions.ConnectionError as e:
            self.send_json_error(200, "connection_error", str(e))
            return
        except requests.exceptions.Timeout as e:
            self.send_json_error(200, "timeout", str(e))
            return
        except Exception as e:
            self.send_json_error(200, "unknown_error", str(e))
            return

        resp_headers = filter_headers(dict(resp.headers))
        resp_body_b64 = base64.b64encode(resp.content).decode()

        envelope = json.dumps({
            "ok": True,
            "response": {
                "status": resp.status_code,
                "headers": resp_headers,
                "body": resp_body_b64,
            }
        }).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(envelope)))
        self.end_headers()
        self.wfile.write(envelope)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--secret", default="", help="Shared secret for X-Relay-Secret header")
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()

    RelayHandler.secret = args.secret or None
    RelayHandler.session = requests.Session()
    RelayHandler.session.max_redirects = 0

    print(f"Relay listening on port {args.port}", file=sys.stderr)
    if args.secret:
        print(f"Secret: {args.secret}", file=sys.stderr)

    server = HTTPServer(("0.0.0.0", args.port), RelayHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
