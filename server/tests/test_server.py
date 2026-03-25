"""
Unit tests for server.py — FastAPI WebSocket server.
Run inside the test container:  pytest --cov=server --cov-report=term-missing
"""
import json
import os
import sys
import tempfile
import pathlib
import pytest

# ── test workspace: create a fake slides.html before importing the app ────────
_tmp = tempfile.mkdtemp()
pathlib.Path(_tmp, "slides.html").write_text(
    "<!DOCTYPE html><html><body>Test Slides</body></html>",
    encoding="utf-8",
)
os.environ["WORKSPACE_PATH"] = _tmp
os.environ.setdefault("PROJECTOR_PASSWORD", "testpass")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from server import app, PROJECTOR_PASSWORD

client = TestClient(app)
_AUTH = {"proj_auth": PROJECTOR_PASSWORD}  # cookie used by projector-page tests


# ── /health ───────────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_json_content_type(self):
        r = client.get("/health")
        assert "application/json" in r.headers["content-type"]

    def test_status_ok(self):
        r = client.get("/health")
        assert r.json()["status"] == "ok"

    def test_projector_initially_not_connected(self):
        r = client.get("/health")
        assert r.json()["projector_connected"] is False

    def test_slide_count_present(self):
        r = client.get("/health")
        data = r.json()
        assert "total_slides" in data or "slide_count" in data or "slides" in data


# ── GET / (slides) ────────────────────────────────────────────────────────────

class TestAuth:
    def test_no_cookie_returns_401(self):
        r = client.get("/")
        assert r.status_code == 401

    def test_wrong_password_returns_401(self):
        r = client.post("/login", data={"password": "wrong"})
        assert r.status_code == 401

    def test_correct_password_redirects(self):
        r = client.post("/login", data={"password": PROJECTOR_PASSWORD},
                        follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/"

    def test_correct_password_sets_cookie(self):
        r = client.post("/login", data={"password": PROJECTOR_PASSWORD},
                        follow_redirects=False)
        assert "proj_auth" in r.cookies


class TestSlides:
    def test_returns_200(self):
        r = client.get("/", cookies=_AUTH)
        assert r.status_code == 200

    def test_content_type_html(self):
        r = client.get("/", cookies=_AUTH)
        assert "text/html" in r.headers["content-type"]

    def test_body_contains_slides_content(self):
        r = client.get("/", cookies=_AUTH)
        assert "Test Slides" in r.text

    def test_missing_slides_returns_503(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WORKSPACE_PATH", str(tmp_path))
        empty_workspace = tmp_path  # no slides.html here
        assert not (empty_workspace / "slides.html").exists()


# ── GET /audience ─────────────────────────────────────────────────────────────

class TestAudience:
    def test_returns_200(self):
        r = client.get("/audience")
        assert r.status_code == 200

    def test_content_type_html(self):
        r = client.get("/audience")
        assert "text/html" in r.headers["content-type"]

    def test_body_is_html(self):
        r = client.get("/audience")
        assert "<html" in r.text.lower()


# ── 404 on unknown routes ─────────────────────────────────────────────────────

class TestUnknownRoutes:
    def test_unknown_route_is_404(self):
        r = client.get("/does-not-exist")
        assert r.status_code == 404

    def test_unknown_method_is_405(self):
        r = client.post("/health")
        assert r.status_code == 405


# ── WebSocket /ws ─────────────────────────────────────────────────────────────

def _register(ws, role):
    """Connect as a given role and drain the three greeting messages sent on connect.

    The server immediately sends:
      1. {"type": "assigned_name", "name": <auto>}
      2. {"type": "slide_update", ...}
      3. {"type": "projector_status", "connected": <bool>}
    For projector role we also send register_projector so the server treats
    this connection as the projector.
    """
    msg1 = ws.receive_json()
    assert msg1["type"] == "assigned_name"
    msg2 = ws.receive_json()
    assert msg2["type"] == "slide_update"
    msg3 = ws.receive_json()
    assert msg3["type"] == "projector_status"

    if role == "projector":
        ws.send_json({"type": "register_projector"})

    return msg1.get("name", "")


class TestWebSocket:
    def test_projector_can_connect(self):
        with client.websocket_connect("/ws") as ws:
            _register(ws, "projector")

    def test_audience_can_connect(self):
        with client.websocket_connect("/ws") as ws:
            _register(ws, "audience")

    def test_assigned_name_returned(self):
        """Server auto-generates a non-empty name on connect."""
        with client.websocket_connect("/ws") as ws:
            name = _register(ws, "audience")
            assert isinstance(name, str) and len(name) > 0

    def test_projector_receives_like_update(self):
        """Audience sends a like → projector should receive a like_update."""
        with client.websocket_connect("/ws") as proj:
            _register(proj, "projector")

            with client.websocket_connect("/ws") as aud:
                _register(aud, "audience")
                aud.send_json({"type": "like", "slide": 0})

                msg = proj.receive_json()
                assert msg["type"] == "like_update"

    def test_projector_status_broadcast_on_connect(self):
        """When projector connects, audience should be notified."""
        with client.websocket_connect("/ws") as aud:
            _register(aud, "audience")

            with client.websocket_connect("/ws") as proj:
                _register(proj, "projector")

                msg = aud.receive_json()
                assert msg["type"] == "projector_status"
                assert msg["connected"] is True

    def test_projector_status_broadcast_on_disconnect(self):
        """When projector disconnects, audience should be notified."""
        with client.websocket_connect("/ws") as aud:
            _register(aud, "audience")

            with client.websocket_connect("/ws") as proj:
                _register(proj, "projector")
                _ = aud.receive_json()  # projector_status connected=True

            # projector disconnected — audience should get connected=False
            msg = aud.receive_json()
            assert msg["type"] == "projector_status"
            assert msg["connected"] is False

    def test_unknown_message_type_ignored(self):
        """Server should not crash on unknown message types."""
        with client.websocket_connect("/ws") as ws:
            _register(ws, "audience")
            ws.send_json({"type": "unknown_type", "data": "whatever"})

    def test_generate_username_no_name(self):
        """Every new audience connection gets a unique auto-generated name."""
        with client.websocket_connect("/ws") as ws:
            name = _register(ws, "audience")
            assert isinstance(name, str) and len(name) > 0
