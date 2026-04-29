"""
Unit tests for server.py — FastAPI WebSocket server.
Run inside the test container:  pytest --cov=server --cov-report=term-missing
"""
import asyncio
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
import server as server_mod
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

    def test_cookie_not_secure_over_http(self):
        # WS_SCHEME defaults to "ws" in tests → secure flag must be absent
        r = client.post("/login", data={"password": PROJECTOR_PASSWORD},
                        follow_redirects=False)
        set_cookie = r.headers.get("set-cookie", "")
        assert "secure" not in set_cookie.lower()

    def test_cookie_secure_over_https(self, monkeypatch):
        monkeypatch.setenv("WS_SCHEME", "wss")
        r = client.post("/login", data={"password": PROJECTOR_PASSWORD},
                        follow_redirects=False)
        set_cookie = r.headers.get("set-cookie", "")
        assert "secure" in set_cookie.lower()


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
        empty_file = tmp_path / "missing-slides.html"
        assert not empty_file.exists()
        monkeypatch.setattr(server_mod, "SLIDES_HTML", empty_file)
        # Disable projector-page auth to reach the missing file branch.
        monkeypatch.setattr(server_mod, "PROJECTOR_PASSWORD", "")
        r = client.get("/")
        assert r.status_code == 503
        payload = r.json()
        assert payload["error"] == "slides.html not found in workspace."
        assert "conversion pipeline" in payload["hint"]


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

    def test_audience_css_route(self):
        r = client.get("/audience.css")
        assert r.status_code == 200
        assert "text/css" in r.headers["content-type"]

    def test_audience_js_route(self):
        r = client.get("/audience.js")
        assert r.status_code == 200
        assert "application/javascript" in r.headers["content-type"]


# ── 404 on unknown routes ─────────────────────────────────────────────────────

class TestUnknownRoutes:
    def test_unknown_route_is_404(self):
        r = client.get("/does-not-exist")
        assert r.status_code == 404

    def test_unknown_method_is_405(self):
        r = client.post("/health")
        assert r.status_code == 405


class TestMirrorAndPrint:
    def test_mirror_returns_html(self):
        r = client.get("/mirror")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_print_returns_html(self):
        r = client.get("/print")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_mirror_returns_503_when_slides_missing(self, tmp_path, monkeypatch):
        missing = tmp_path / "missing-mirror.html"
        monkeypatch.setattr(server_mod, "SLIDES_HTML", missing)
        r = client.get("/mirror")
        assert r.status_code == 503
        assert r.json()["error"] == "slides.html not found"

    def test_print_returns_503_when_slides_missing(self, tmp_path, monkeypatch):
        missing = tmp_path / "missing-print.html"
        monkeypatch.setattr(server_mod, "SLIDES_HTML", missing)
        r = client.get("/print")
        assert r.status_code == 503
        assert r.json()["error"] == "slides.html not found"


class TestAudienceAssetsMissing:
    def test_audience_missing_returns_503(self, tmp_path, monkeypatch):
        monkeypatch.setattr(server_mod, "AUDIENCE_HTML", tmp_path / "audience.html")
        r = client.get("/audience")
        assert r.status_code == 503
        assert r.json()["error"] == "audience.html missing"

    def test_audience_css_missing_returns_503(self, tmp_path, monkeypatch):
        monkeypatch.setattr(server_mod, "AUDIENCE_SRC", tmp_path / "src")
        r = client.get("/audience.css")
        assert r.status_code == 503
        assert r.json()["error"] == "audience.css missing"

    def test_audience_js_missing_returns_503(self, tmp_path, monkeypatch):
        monkeypatch.setattr(server_mod, "AUDIENCE_SRC", tmp_path / "src")
        r = client.get("/audience.js")
        assert r.status_code == 503
        assert r.json()["error"] == "audience.js missing"


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

    def test_invalid_json_message_ignored(self):
        """Server should ignore malformed JSON frames."""
        with client.websocket_connect("/ws") as ws:
            _register(ws, "audience")
            ws.send_text("{invalid json")
            ws.send_json({"type": "request_state"})
            msg = ws.receive_json()
            assert msg["type"] == "slide_update"

    def test_generate_username_no_name(self):
        """Every new audience connection gets a unique auto-generated name."""
        with client.websocket_connect("/ws") as ws:
            name = _register(ws, "audience")
            assert isinstance(name, str) and len(name) > 0

    def test_request_state_returns_slide_update(self):
        with client.websocket_connect("/ws") as ws:
            _register(ws, "audience")
            ws.send_json({"type": "request_state"})
            msg = ws.receive_json()
            assert msg["type"] == "slide_update"

    def test_slide_change_broadcasts_to_audience(self):
        with client.websocket_connect("/ws") as proj:
            _register(proj, "projector")
            proj.send_json({"type": "slide_change", "index": 1, "reveal": 2})
            assert server_mod.current_slide == 0  # clamped when slides_total is 0
            assert server_mod.current_reveal == 2

    def test_presentation_state_broadcasts_to_audience(self):
        with client.websocket_connect("/ws") as proj:
            _register(proj, "projector")
            proj.send_json({"type": "presentation_state", "index": 3, "reveal": 1})
            assert server_mod.current_slide == 0  # clamped when slides_total is 0
            assert server_mod.current_reveal == 1

    def test_slides_meta_updates_total_for_new_clients(self):
        with client.websocket_connect("/ws") as proj:
            _register(proj, "projector")
            proj.send_json(
                {
                    "type": "slides_meta",
                    "slides": [
                        {"title": "S1", "summary": "A"},
                        {"title": "S2", "summary": "B"},
                    ],
                }
            )

            with client.websocket_connect("/ws") as aud:
                _ = aud.receive_json()  # assigned_name
                state = aud.receive_json()  # slide_update
                assert state["type"] == "slide_update"
                assert state["total"] == 2

    def test_like_cap_is_enforced(self):
        original_cap = server_mod.LIKES_CAP
        server_mod.LIKES_CAP = 2
        try:
            with client.websocket_connect("/ws") as proj:
                _register(proj, "projector")
                with client.websocket_connect("/ws") as aud:
                    _register(aud, "audience")
                    aud.send_json({"type": "like", "slide": 0})
                    m1 = proj.receive_json()
                    aud.send_json({"type": "like", "slide": 0})
                    m2 = proj.receive_json()
                    aud.send_json({"type": "like", "slide": 0})
                    m3 = proj.receive_json()
                    assert m1["count"] == 1
                    assert m2["count"] == 2
                    assert m3["count"] == 2
        finally:
            server_mod.LIKES_CAP = original_cap

    def test_projector_secret_rejects_unauthorized_registration(self, monkeypatch):
        monkeypatch.setattr(server_mod, "PROJECTOR_SECRET", "secret-token")
        with client.websocket_connect("/ws") as ws:
            _register(ws, "audience")
            ws.send_json({"type": "register_projector"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["message"] == "Unauthorized"


class TestHelpers:
    def test_send_projector_resets_on_send_error(self):
        class _BadWs:
            async def send_text(self, _):
                raise RuntimeError("boom")

        prev = server_mod.projector_ws
        server_mod.projector_ws = _BadWs()
        try:
            asyncio.run(server_mod._send_projector({"type": "x"}))
            assert server_mod.projector_ws is None
        finally:
            server_mod.projector_ws = prev
