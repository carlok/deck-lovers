# requirements: fastapi uvicorn[standard] websockets
# launch: uvicorn server:app --host 0.0.0.0 --port 8000

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="Presentation Server")

WORKSPACE = Path(os.getenv("WORKSPACE_PATH", "/app/workspace"))
SLIDES_HTML = WORKSPACE / "slides.html"
AUDIENCE_HTML = Path(__file__).parent / "audience.html"
PROJECTOR_SECRET = os.getenv("PROJECTOR_SECRET", "")  # Optional; set to require auth
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


# ── HTTP routes ───────────────────────────────────────────────────────────────
@app.get("/")
async def serve_slides():
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


@app.get("/audience")
async def serve_audience():
    if not AUDIENCE_HTML.exists():
        return JSONResponse(status_code=503, content={"error": "audience.html missing"})
    return FileResponse(AUDIENCE_HTML, media_type="text/html")


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

    # Greet immediately with assigned name + current slide state
    await ws.send_text(json.dumps({"type": "assigned_name", "name": username}))
    m = _meta(current_slide)
    await ws.send_text(json.dumps({
        "type": "slide_update",
        "index": current_slide,
        "total": slides_total,
        "title": m["title"],
        "summary": m["summary"],
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

            elif mtype == "slides_meta":
                incoming = msg.get("slides", [])
                if incoming:
                    # Merge/replace — safe to re-send on reconnect (S2 fix)
                    slides_meta = incoming
                    slides_total = len(slides_meta)

            elif mtype == "slide_change" and is_projector:
                current_slide = int(msg.get("index", 0))
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
                user = msg.get("user") or username
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
