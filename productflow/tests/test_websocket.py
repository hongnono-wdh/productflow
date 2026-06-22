"""WebSocket push-layer tests for server.py.

Verifies the RFC6455 handshake (home + project scope) and that each channel's
pushed payload is byte-identical to the matching GET endpoint (parity guard so
the WS layer never silently drifts from the HTTP API).
"""
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import helpers as h  # noqa: E402

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def ws_connect(port, path):
    """Open a WS connection; return (sock, status_line, accept_ok, leftover_bytes)."""
    s = socket.create_connection(("127.0.0.1", port))
    s.settimeout(5)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    )
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(1024)
        if not chunk:
            break
        buf += chunk
    head, _, leftover = buf.partition(b"\r\n\r\n")
    head_s = head.decode(errors="replace")
    status = head_s.splitlines()[0] if head_s else ""
    expect = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
    return s, status, (expect in head_s), leftover


def read_channels(s, leftover, secs=2.5):
    """Read server text frames for `secs`; return {channel: data}."""
    s.settimeout(secs)
    data = leftover
    out = {}
    end = time.time() + secs

    def need(n):
        nonlocal data
        while len(data) < n:
            try:
                chunk = s.recv(8192)
            except socket.timeout:
                return False
            if not chunk:
                return False
            data += chunk
        return True

    while time.time() < end:
        if not need(2):
            break
        op = data[0] & 0x0F
        ln = data[1] & 0x7F
        off = 2
        if ln == 126:
            if not need(4):
                break
            ln = struct.unpack(">H", data[2:4])[0]
            off = 4
        elif ln == 127:
            if not need(10):
                break
            ln = struct.unpack(">Q", data[2:10])[0]
            off = 10
        if not need(off + ln):
            break
        payload = data[off : off + ln]
        data = data[off + ln :]
        if op == 0x1:
            try:
                msg = json.loads(payload.decode())
                out[msg["channel"]] = msg["data"]
            except Exception:
                pass
    return out


class WebSocketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = h.make_home()
        cls.proc, cls.port = h.start_server(cls.home)
        cls.pid = h.create_project(cls.port, "WS Parity Proj", "ws-parity")["id"]

    @classmethod
    def tearDownClass(cls):
        h.stop_server(cls.proc)
        h.rm_home(cls.home)

    def test_project_handshake_and_channels(self):
        s, status, accept_ok, left = ws_connect(self.port, f"/p/{self.pid}/api/ws")
        try:
            self.assertIn("101", status)
            self.assertTrue(accept_ok, "Sec-WebSocket-Accept missing/wrong")
            chans = read_channels(s, left)
        finally:
            s.close()
        # all 14 project channels arrive on connect
        for ch in ["state", "inbox", "health", "pages", "choices", "brief", "explore", "wizard",
                   "agent-log:research", "agent-log:search-refs",
                   "agent-log:stage-4", "agent-log:stage-5", "agent-log:stage-6", "agent-log:stage-7"]:
            self.assertIn(ch, chans, f"channel {ch} not pushed on connect")

    def test_home_handshake_and_channels(self):
        s, status, accept_ok, left = ws_connect(self.port, "/api/ws")
        try:
            self.assertIn("101", status)
            self.assertTrue(accept_ok)
            chans = read_channels(s, left)
        finally:
            s.close()
        self.assertIn("projects", chans)
        self.assertIn("system", chans)

    def test_channel_payload_parity_with_get(self):
        """WS channel data must equal the matching GET endpoint body (no drift)."""
        s, _, _, left = ws_connect(self.port, f"/p/{self.pid}/api/ws")
        try:
            chans = read_channels(s, left)
        finally:
            s.close()
        cases = {
            "state": "/api/state",
            "inbox": "/api/inbox",
            "health": "/api/health",
            "pages": "/api/pages",
            "choices": "/api/choices",
            "brief": "/api/brief",
            "explore": "/api/explore",
            "wizard": "/api/wizard",
        }
        for ch, ep in cases.items():
            status, body = h.http(self.port, f"/p/{self.pid}{ep}")
            self.assertEqual(status, 200, f"GET {ep}")
            self.assertEqual(chans.get(ch), body, f"channel {ch} != GET {ep}")
        # agent-log:stage-6 parity
        st6 = chans.get("agent-log:stage-6")
        status, body = h.http(self.port, f"/p/{self.pid}/api/agent-log?phase=stage-6")
        self.assertEqual(status, 200)
        self.assertEqual(st6, body, "agent-log:stage-6 != GET")
        # projects channel (home scope) parity
        s2, _, _, left2 = ws_connect(self.port, "/api/ws")
        try:
            home = read_channels(s2, left2)
        finally:
            s2.close()
        status, body = h.http(self.port, "/api/projects")
        self.assertEqual(home.get("projects"), body, "projects channel != GET /api/projects")


if __name__ == "__main__":
    unittest.main()
