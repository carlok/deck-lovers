# requirements: fastapi uvicorn[standard] websockets
# launch: uvicorn server:app --host 0.0.0.0 --port 8000

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

app = FastAPI(title="Presentation Server")

WORKSPACE = Path(os.getenv("WORKSPACE_PATH", "/app/workspace"))
SLIDES_HTML = WORKSPACE / "slides.html"
AUDIENCE_HTML = Path(__file__).parent / "audience.html"
AUDIENCE_SRC  = Path(__file__).parent / "src"
PROJECTOR_SECRET   = os.getenv("PROJECTOR_SECRET", "")    # Optional WS projector auth
PROJECTOR_PASSWORD = os.getenv("PROJECTOR_PASSWORD", "admin")  # Page password ("" = off)
LIKES_CAP = 1000  # Max recorded likes per slide (C3 fix)

# ── Server state ──────────────────────────────────────────────────────────────
current_slide: int = 0
slides_total: int = 0
clients: dict[WebSocket, str] = {}          # ws → username
projector_ws: Optional[WebSocket] = None
likes: dict[int, list[str]] = {}            # slide_idx → [username, ...]
slides_meta: list[dict] = []               # [{title, summary}, ...]
used_names: set[str] = set()

# ── Username generation ───────────────────────────────────────────────────────
ADJECTIVES = [
    "Silent", "Brave", "Swift", "Gentle", "Bold", "Calm", "Fierce", "Wise",
    "Nimble", "Stark", "Vivid", "Hollow", "Bright", "Dark", "Keen", "Pale",
    "Rough", "Smooth", "Sharp", "Blunt", "Cold", "Warm", "Deep", "Vast",
    "Still", "Loud", "Quick", "Slow", "High", "Low",
]
NOUNS = [
    "Pebble", "Storm", "River", "Cloud", "Ember", "Stone", "Wave", "Flame",
    "Frost", "Dusk", "Dawn", "Mist", "Gale", "Tide", "Spark", "Ridge",
    "Grove", "Creek", "Crest", "Bluff", "Glen", "Marsh", "Cape", "Reef",
    "Peak", "Vale", "Dell", "Fen", "Mere", "Knoll",
]
ANIMALS = [
    "🦊", "🐺", "🦅", "🐬", "🦁", "🐻", "🦋", "🐙",
    "🦜", "🐢", "🦩", "🐘", "🦒", "🐝", "🦈", "🐦",
    "🦌", "🐋", "🦚", "🐆",
]


def generate_username() -> str:
    """Generate collision-resistant username within session. Space: 30×30×20 = 18,000."""
    for _ in range(2000):
        name = (
            random.choice(ADJECTIVES)
            + random.choice(NOUNS)
            + random.choice(ANIMALS)
        )
        if name not in used_names:
            used_names.add(name)
            return name
    # Fallback: append random suffix if space exhausted
    name = (
        random.choice(ADJECTIVES)
        + random.choice(NOUNS)
        + random.choice(ANIMALS)
        + str(random.randint(1000, 9999))
    )
    used_names.add(name)
    return name


# ── Helpers ───────────────────────────────────────────────────────────────────
def _meta(idx: int) -> dict:
    if idx < len(slides_meta):
        return slides_meta[idx]
    return {"title": "", "summary": ""}


async def _broadcast_audience(msg: dict) -> None:
    """Send a message to all non-projector clients."""
    dead: list[WebSocket] = []
    payload = json.dumps(msg)
    for ws, _ in list(clients.items()):
        if ws is projector_ws:
            continue
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        used_names.discard(clients.pop(ws, ""))


async def _send_projector(msg: dict) -> None:
    global projector_ws
    if projector_ws is None:
        return
    try:
        await projector_ws.send_text(json.dumps(msg))
    except Exception:
        projector_ws = None


# ── Auth helpers ──────────────────────────────────────────────────────────────
_LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Projector login</title>
<style>
  body{{background:#111;color:#eee;font-family:sans-serif;
        display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
  form{{display:flex;flex-direction:column;gap:12px;width:260px}}
  input{{padding:10px;font-size:1rem;border-radius:6px;border:1px solid #444;background:#222;color:#eee}}
  button{{padding:10px;font-size:1rem;border-radius:6px;border:none;
          background:#4a9eff;color:#fff;cursor:pointer}}
  .err{{color:#f66;font-size:.9rem;text-align:center}}
</style></head>
<body>
<form method="post" action="/login">
  <h2 style="margin:0 0 4px;text-align:center">🎤 Projector</h2>
  <input type="password" name="password" placeholder="Password" autofocus>
  <button type="submit">Enter</button>
  {error}
</form>
</body></html>"""

def _auth_ok(request: Request) -> bool:
    """Return True if password protection is off or cookie matches."""
    if not PROJECTOR_PASSWORD:
        return True
    return request.cookies.get("proj_auth") == PROJECTOR_PASSWORD


# ── HTTP routes ───────────────────────────────────────────────────────────────
@app.get("/")
async def serve_slides(request: Request):
    if not _auth_ok(request):
        return HTMLResponse(_LOGIN_HTML.format(error=""), status_code=401)
    if not SLIDES_HTML.exists():
        return JSONResponse(
            status_code=503,
            content={
                "error": "slides.html not found in workspace.",
                "hint": (
                    "Run the conversion pipeline first:\n"
                    "  docker compose --profile convert up --abort-on-container-exit"
                ),
            },
        )
    return FileResponse(SLIDES_HTML, media_type="text/html")


@app.get("/mirror")
async def serve_mirror():
    """Serve slides in read-only mirror mode — used by the audience iframe, no auth."""
    if not SLIDES_HTML.exists():
        return JSONResponse(status_code=503, content={"error": "slides.html not found"})
    return FileResponse(SLIDES_HTML, media_type="text/html")


@app.get("/print")
async def serve_print():
    """Serve slides in print/PDF mode — no auth (audience can download PDF)."""
    if not SLIDES_HTML.exists():
        return JSONResponse(status_code=503, content={"error": "slides.html not found"})
    return FileResponse(SLIDES_HTML, media_type="text/html")


@app.post("/login")
async def login(password: str = Form(...)):
    if PROJECTOR_PASSWORD and password != PROJECTOR_PASSWORD:
        err = '<p class="err">Wrong password.</p>'
        return HTMLResponse(_LOGIN_HTML.format(error=err), status_code=401)
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie("proj_auth", PROJECTOR_PASSWORD, httponly=True, samesite="strict")
    return resp


_NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}


@app.get("/audience")
async def serve_audience():
    if not AUDIENCE_HTML.exists():
        return JSONResponse(status_code=503, content={"error": "audience.html missing"})
    return FileResponse(AUDIENCE_HTML, media_type="text/html", headers=_NO_CACHE)


@app.get("/audience.css")
async def serve_audience_css():
    f = AUDIENCE_SRC / "audience.css"
    if not f.exists():
        return JSONResponse(status_code=503, content={"error": "audience.css missing"})
    return FileResponse(f, media_type="text/css", headers=_NO_CACHE)


@app.get("/audience.js")
async def serve_audience_js():
    f = AUDIENCE_SRC / "audience.js"
    if not f.exists():
        return JSONResponse(status_code=503, content={"error": "audience.js missing"})
    return FileResponse(f, media_type="application/javascript", headers=_NO_CACHE)


@app.get("/health")
async def health():
    """Used by Docker healthcheck and monitoring."""
    return {
        "status": "ok",
        "slides_ready": SLIDES_HTML.exists(),
        "projector_connected": projector_ws is not None,
        "connected_clients": len(clients),
        "current_slide": current_slide,
        "total_slides": slides_total,
    }


# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global current_slide, slides_total, projector_ws, slides_meta

    await ws.accept()
    is_projector = False
    username = generate_username()
    clients[ws] = username

    # Greet immediately with assigned name + current slide state + projector status
    await ws.send_text(json.dumps({"type": "assigned_name", "name": username}))
    m = _meta(current_slide)
    await ws.send_text(json.dumps({
        "type": "slide_update",
        "index": current_slide,
        "total": slides_total,
        "title": m["title"],
        "summary": m["summary"],
    }))
    await ws.send_text(json.dumps({
        "type": "projector_status",
        "connected": projector_ws is not None,
    }))

    try:
        async for raw in ws.iter_text():
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            mtype = msg.get("type", "")

            if mtype == "register_projector":
                # Optional secret auth (C1 fix: opt-in, doc'd in README)
                if PROJECTOR_SECRET and msg.get("secret") != PROJECTOR_SECRET:
                    await ws.send_text(json.dumps({"type": "error", "message": "Unauthorized"}))
                    continue
                is_projector = True
                projector_ws = ws
                await _broadcast_audience({"type": "projector_status", "connected": True})
                # Replay all existing like state to reconnected projector (S2 fix)
                for slide_idx, like_list in likes.items():
                    if like_list:
                        await ws.send_text(json.dumps({
                            "type": "like_update",
                            "slide": slide_idx,
                            "count": len(like_list),
                            "recent": like_list[-5:],
                        }))

            elif mtype == "slides_meta" and is_projector:          # C1: projector-only
                incoming = msg.get("slides", [])
                if incoming:
                    # Merge/replace — safe to re-send on reconnect (S2 fix)
                    slides_meta = incoming
                    slides_total = len(slides_meta)

            elif mtype == "slide_change" and is_projector:
                idx = int(msg.get("index", 0))                     # I2: bounds-check
                current_slide = max(0, min(idx, max(slides_total - 1, 0)))
                m = _meta(current_slide)
                await _broadcast_audience({
                    "type": "slide_update",
                    "index": current_slide,
                    "total": slides_total,
                    "title": m["title"],
                    "summary": m["summary"],
                })

            elif mtype == "like":
                slide_idx = int(msg.get("slide", current_slide))
                user = username                                     # I1: ignore spoofable client field
                bucket = likes.setdefault(slide_idx, [])
                if len(bucket) < LIKES_CAP:  # C3 fix: cap at 1000
                    bucket.append(user)
                await _send_projector({
                    "type": "like_update",
                    "slide": slide_idx,
                    "count": len(bucket),
                    "recent": bucket[-5:],
                })

            elif mtype == "request_state":
                # Audience client reconnected — resend current state (S1 fix)
                m = _meta(current_slide)
                await ws.send_text(json.dumps({
                    "type": "slide_update",
                    "index": current_slide,
                    "total": slides_total,
                    "title": m["title"],
                    "summary": m["summary"],
                }))

    except WebSocketDisconnect:
        pass
    finally:
        if is_projector and projector_ws is ws:
            projector_ws = None
            await _broadcast_audience({"type": "projector_status", "connected": False})
        used_names.discard(clients.pop(ws, ""))
