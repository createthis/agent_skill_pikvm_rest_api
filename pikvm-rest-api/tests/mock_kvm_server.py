#!/usr/bin/env python3
"""Mock KVMD (PiKVM) HTTP server for offline tests of scripts/pikvm.sh.

Stdlib only. Speaks just enough of the KVMD REST API for the client to be
exercised end to end, and logs every request as one JSON line for assertions:

  python3 mock_kvm_server.py --port 0 --portfile /tmp/port \
      --logfile /tmp/reqs.jsonl --expected-user testuser --expected-password testpass

--port 0 binds 127.0.0.1 on an ephemeral port and writes the actual port to
--portfile. --reset truncates the log first. Every endpoint requires
HTTP Basic auth matching the expected user/password (else 401).

Endpoints:
  GET  /api/info                JSON info (query slow=1 -> 2s delay)
  GET  /api/atx                 JSON ATX state
  GET  /api/hid                 JSON HID state
  GET  /api/streamer/snapshot   image/jpeg (small embedded JPEG)
  POST /api/hid/print           JSON {"chars": <len of raw body>}
  POST /api/hid/events/send_*   JSON {"ok": true}
  POST /api/atx/power           JSON {"ok": true}
  any endpoint with query boom=1 -> 503 {"error": "UnavailableError"}
  anything else                 404 {"error": "NotFound"}

Test-only hook (not a real KVMD endpoint):
  POST /api/test/snapshot-fail?value=1|0
      toggles whether GET /api/streamer/snapshot answers 503, to exercise the
      client's "video stream offline" path.

Terminate with SIGTERM (the test harness does this; no persistent state).
"""
import argparse
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

# A real 64x40 JPEG (676 bytes), embedded so the mock has no Pillow dependency.
JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAoHBwgHBgoICAgLCgoLDhgQDg0NDh0VFhEYIx8l"
    "JCIfIiEmKzcvJik0KSEiMEExNDk7Pj4+JS5ESUM8SDc9Pjv/2wBDAQoLCw4NDhwQEBw7KCIo"
    "Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozv/"
    "wAARCAAoAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QA"
    "tRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2Jy"
    "ggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqD"
    "hIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi"
    "4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QA"
    "tREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLR"
    "ChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6"
    "goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna"
    "4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDhKKKK9A4QooooAKKKKACiiigAoooo"
    "AKKKKACiiigAooooAKKKKAP/2Q=="
)
# Strip any whitespace the literal might pick up before decoding.
JPEG_BODY = base64.b64decode("".join(JPEG_B64.split()))

JSON_INFO = {
    "system": {"kvmd": {"version": "mock"}, "uptime": 123},
    "hw": {"platform": {"model": "mock-kvm"}},
}
JSON_ATX = {"acts": ["on", "off", "reset_hard"], "busy": False, "leds": {"power": "on"}}
JSON_HID = {"keyboard": {"online": True}, "mouse": {"online": True, "absolute": True}}

_log_lock = threading.Lock()
_log_path = ""
_snapshot_fail = threading.Event()


def log_request(rec):
    with _log_lock:
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")


def make_handler(expected_user, expected_password):
    class Handler(BaseHTTPRequestHandler):
        server_version = "mock-kvmd/1.0"

        def log_message(self, *args):  # silence default stderr logging
            pass

        def _auth_ok(self):
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Basic "):
                return False
            try:
                decoded = base64.b64decode(auth[len("Basic "):]).decode("utf-8")
            except Exception:
                return False
            return decoded == "%s:%s" % (expected_user, expected_password)

        def _send(self, code, content_type, body):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, code, obj):
            self._send(code, "application/json", json.dumps(obj).encode("utf-8"))

        def _handle(self, method):
            parts = urlsplit(self.path)
            query = parts.query
            qs = parse_qs(query, keep_blank_values=True)
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            rec = {
                "method": method,
                "path": parts.path,
                "query": query,
                "user_agent": self.headers.get("User-Agent", ""),
                "authorization": self.headers.get("Authorization", ""),
                "body": body.decode("utf-8", "replace") if body else None,
                "ts": time.time(),
            }
            log_request(rec)

            if not self._auth_ok():
                self._send_json(401, {"error": "Unauthorized"})
                return
            if "boom" in qs:
                self._send_json(503, {"error": "UnavailableError"})
                return
            if "slow" in qs and parts.path == "/api/info":
                time.sleep(2)

            if method == "POST" and parts.path == "/api/test/snapshot-fail":
                _snapshot_fail.set() if "1" in (qs.get("value", ["1"])) else _snapshot_fail.clear()
                self._send_json(200, {"ok": True})
                return

            if method == "GET" and parts.path == "/api/info":
                self._send_json(200, JSON_INFO)
            elif method == "GET" and parts.path == "/api/atx":
                self._send_json(200, JSON_ATX)
            elif method == "GET" and parts.path == "/api/hid":
                self._send_json(200, JSON_HID)
            elif method == "GET" and parts.path == "/api/streamer/snapshot":
                if _snapshot_fail.is_set():
                    self._send_json(503, {"error": "UnavailableError"})
                else:
                    self._send(200, "image/jpeg", JPEG_BODY)
            elif method == "POST" and parts.path == "/api/hid/print":
                self._send_json(200, {"chars": len(body)})
            elif method == "POST" and parts.path.startswith("/api/hid/events/send_"):
                self._send_json(200, {"ok": True})
            elif method == "POST" and parts.path == "/api/hid/reset":
                self._send_json(200, {"ok": True})
            elif method == "POST" and parts.path == "/api/atx/power":
                self._send_json(200, {"ok": True})
            else:
                self._send_json(404, {"error": "NotFound"})

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

    return Handler


def main():
    global _log_path
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--portfile", required=True)
    ap.add_argument("--logfile", required=True)
    ap.add_argument("--expected-user", required=True)
    ap.add_argument("--expected-password", required=True)
    ap.add_argument("--reset", action="store_true", help="truncate the log first")
    a = ap.parse_args()

    if a.reset:
        open(a.logfile, "w").close()
    _log_path = a.logfile

    server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(
        a.expected_user, a.expected_password))
    actual_port = server.server_address[1]
    with open(a.portfile, "w") as f:
        f.write(str(actual_port))
    print("READY %d" % actual_port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
