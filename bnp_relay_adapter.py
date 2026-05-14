"""
Custom requests transport adapter that routes BNP traffic through the phone relay.

Usage:
    from bnp_relay_adapter import install_relay_adapter
    install_relay_adapter(browser, relay_url="https://xxx.trycloudflare.com", secret="mysecret")

Where `browser` is the woob BNP browser instance (has a .session attribute).
"""
import base64
import json

import requests
from requests.adapters import HTTPAdapter
from requests.models import Response
from urllib3.response import HTTPResponse
from io import BytesIO


class RelayAdapter(HTTPAdapter):
    def __init__(self, relay_url, secret=None):
        self.relay_url = relay_url.rstrip("/")
        self.secret = secret
        self._relay_session = requests.Session()
        super().__init__()

    def send(self, request, **kwargs):
        headers = dict(request.headers)

        # Strip hop-by-hop headers
        hop_by_hop = {
            "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
            "te", "trailers", "transfer-encoding", "upgrade", "proxy-connection",
        }
        headers = {k: v for k, v in headers.items() if k.lower() not in hop_by_hop}

        body = request.body
        if isinstance(body, str):
            body = body.encode()
        body_b64 = base64.b64encode(body).decode() if body else None

        payload = {
            "method": request.method,
            "url": request.url,
            "headers": headers,
            "body": body_b64,
        }

        relay_headers = {"Content-Type": "application/json"}
        if self.secret:
            relay_headers["X-Relay-Secret"] = self.secret

        try:
            relay_resp = self._relay_session.post(
                self.relay_url,
                json=payload,
                headers=relay_headers,
                timeout=60,
            )
            relay_resp.raise_for_status()
            envelope = relay_resp.json()
        except Exception as e:
            raise requests.exceptions.ConnectionError(f"Relay unreachable: {e}") from e

        if not envelope.get("ok"):
            error_type = envelope.get("error_type", "unknown")
            error_msg = envelope.get("error", "")
            raise requests.exceptions.ConnectionError(
                f"Relay error [{error_type}]: {error_msg}"
            )

        r = envelope["response"]
        status = r["status"]
        resp_headers = r["headers"]
        body_bytes = base64.b64decode(r["body"])

        # Recalculate Content-Length
        resp_headers["Content-Length"] = str(len(body_bytes))

        response = Response()
        response.status_code = status
        response.headers = requests.structures.CaseInsensitiveDict(resp_headers)
        response.url = request.url
        response.request = request
        response.encoding = response.apparent_encoding

        response.raw = HTTPResponse(
            body=BytesIO(body_bytes),
            headers=resp_headers,
            status=status,
            preload_content=False,
        )
        response._content = body_bytes
        response._content_consumed = True

        return response


def install_relay_adapter(browser, relay_url, secret=None):
    adapter = RelayAdapter(relay_url=relay_url, secret=secret)
    browser.session.mount("https://mabanque.bnpparibas", adapter)
    browser.session.mount("http://mabanque.bnpparibas", adapter)
    return adapter
