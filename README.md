# deck-lovers — Interactive AI Presentation System

Custom HTML slide deck with live audience engagement via WebSocket.
Audience members open a mobile companion page, follow along, and send likes
that animate in real time on the projector view.

No Reveal.js. No frameworks. Pure HTML/CSS/JS generated from Markdown.

---

## 1. Architecture

### Conversion pipeline

```dot
digraph pipeline {
  rankdir=LR
  node [shape=box style="filled,rounded" fillcolor="#f5f5f5" color="#888"]
  edge [color="#888"]
  md   [label="slides.md" shape=note fillcolor="#fff9c4"]
  tex  [label="slides.tex\n(optional)" shape=note fillcolor="#f5f5f5"]
  out  [label="slides.html" shape=cylinder fillcolor="#c8e6c9"]
  tex  -> md2html [label="tex_extract.py" style=dashed]
  md   -> md2html
  md2html -> out
}
```

### Runtime WebSocket topology

```dot
digraph runtime {
  rankdir=LR
  node [shape=box style="filled,rounded" color="#888"]
  P [label="Projector" fillcolor="#bbdefb"]
  S [label="Server :8000" fillcolor="#ffe0b2"]
  A [label="Audience\n(mobile)" fillcolor="#f8bbd0"]
  P -> S [label="slide_change"]
  S -> P [label="like_update"]
  S -> A [label="slide_update"]
  A -> S [label="like"]
}
```

---

## 2. Slide format (`slides.md`)

Slides are plain Markdown separated by `---` on its own line.

```markdown
# Title slide
**subtitle**
*Author · Date*

---

## Content slide

- Bullet with **bold** and _italic_
- Emoji work fine 🚀

> blockquote

---

## Table

| Col A | Col B |
|-------|-------|
| x     | y     |

---

## Checklist

- [x] Done item
- [ ] Todo item

---

## Code

    ```python
    print("hello")
    ```

---

## YouTube embed

!youtube[Video title](https://www.youtube.com/watch?v=VIDEO_ID)

---
```

**Slide types:**
- A slide starting with `# Heading` → title style (centered, gradient background)
- A slide starting with `## Heading` → content style (left-aligned, accent underline)

**Stats slide** is auto-appended as the last slide — shows a live bar chart of likes per slide.

---

## 3. Running

### Full workflow (auto-detects WiFi IP)

```bash
./deploy.sh
```

This:
1. Detects `podman compose` or `docker compose`
2. Detects your WiFi IP (macOS `en0`/`en1`, Linux `ip addr`) — bakes it into the QR code
3. Converts `slides.md` → `output/slides.html`
4. Starts the server

### Override IP or runtime

```bash
# Both in one command
COMPOSE="podman compose" SERVER_HOST=192.168.0.106 ./deploy.sh

# Convert only (no server)
./deploy.sh --convert-only

# Server only (skip conversion)
./deploy.sh --serve-only
```

### Re-convert without restarting the server

```bash
./deploy.sh --convert-only
# Server auto-reloads on next browser refresh (reads slides.html from ./output/)
```

### Rebuild images after code changes

```bash
podman compose build md2html
podman compose build server
```

---

## 4. Input: Markdown only (no LaTeX)

Put your content directly in `slides.md` at the project root.
Run `./deploy.sh` — the script copies it to `output/slides.md` automatically
when `source/slides.tex` is empty.

---

## 5. Input: LaTeX source

Place your Beamer file at `source/slides.tex`.
`deploy.sh` detects it is non-empty and runs `tex_extract.py` first,
writing `output/slides.md`, which `md2html.py` then converts.

**Expected cleanup** after `tex_extract.py`:

| LaTeX residual | Target Markdown |
|---|---|
| `\begin{itemize}` / `\item` | `- ` bullets |
| `\textbf{x}` / `\textit{x}` | `**x**` / `_x_` |
| `\begin{equation}` | `$$ … $$` |
| `\includegraphics{f}` | `![](f)` or remove |
| `\begin{frame}{Title}` | `## Title` |

---

## 6. Output files (`output/`)

All generated files land on the host in `./output/`:

```
output/
├── slides.md          ← intermediate Markdown (editable)
└── slides.html        ← final standalone deck (open directly in browser)
```

`slides.html` is fully self-contained — open it with `file://` for offline use,
or serve it via the FastAPI server for live audience features.

---

## 7. QR code and network

| Scenario | `SERVER_HOST` | `WS_SCHEME` |
|---|---|---|
| Local dev | `localhost` (default) | `ws` (default) |
| LAN / in-person | `192.168.x.x` (auto-detected) | `ws` |
| VPS + Caddy, no domain | `1-2-3-4.sslip.io` | `wss` |
| VPS + Caddy, custom domain | `slides.example.com` | `wss` |

Find your LAN IP manually:

```bash
# macOS
ipconfig getifaddr en0

# Linux
ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127
```

---

## 8. HTTPS in production

The FastAPI server speaks plain HTTP on port 8000 internally. In production
**never expose 8000 publicly** — put Caddy in front, which handles TLS
termination, certificate renewal, WebSocket upgrade headers, and HTTP→HTTPS
redirects automatically. Set `WS_SCHEME=wss` so the baked-in WebSocket URL
uses `wss://`.

### No domain? Use sslip.io

`sslip.io` resolves any hostname of the form `1-2-3-4.sslip.io` to the IP
`1.2.3.4`. Caddy can obtain a real Let's Encrypt certificate for it — no DNS
purchase or configuration required.

```
VPS IP:  1.2.3.4
Host:    1-2-3-4.sslip.io   ← dots replaced with dashes
```

### Caddy setup (recommended)

SSH into the VPS and install Caddy:

```bash
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy
```

Create `/etc/caddy/Caddyfile` (replace `1-2-3-4` with your actual IP dashes,
or use your own domain):

```caddyfile
1-2-3-4.sslip.io {
    reverse_proxy localhost:8000
}
```

```bash
systemctl enable --now caddy
```

Deploy with HTTPS:

```bash
WS_SCHEME=wss SERVER_HOST=1-2-3-4.sslip.io VPS=root@1.2.3.4 ./deploy.sh
```

Audience URL: `https://1-2-3-4.sslip.io/audience`

> **Firewall:** open ports **80 and 443** only. Port 8000 stays closed — Caddy
> reaches the server over `localhost`. See section 14 for Hetzner-specific steps.

### nginx (alternative)

```nginx
server {
    listen 443 ssl;
    server_name 1-2-3-4.sslip.io;   # or your domain

    ssl_certificate     /etc/letsencrypt/live/1-2-3-4.sslip.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/1-2-3-4.sslip.io/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

---

## 9. Running bare (no containers)

```bash
pip install -r converter/requirements.txt
pip install -r server/requirements.txt

# Convert
mkdir -p output && cp slides.md output/slides.md
SERVER_HOST=localhost python converter/md2html.py \
  --input output/slides.md \
  --output output/slides.html

# Serve
WORKSPACE_PATH=./output uvicorn server.server:app --host 0.0.0.0 --port 8000
```

---

## 10. SELinux (Fedora / RHEL)

On SELinux-enforcing systems add `:Z` to bind mounts in `docker-compose.yml`:

```yaml
tex2md:
  volumes:
    - ./source:/source:ro,Z
    - ./output:/workspace:Z
```

---

## 11. Auto-start with systemd — Quadlet (Podman ≥ 4.4)

`~/.config/containers/systemd/presentation.container`:

```ini
[Container]
Image=localhost/deck-lovers_server:latest
PublishPort=8000:8000
Volume=%h/deck-lovers/output:/app/workspace:Z
Environment=WORKSPACE_PATH=/app/workspace

[Service]
Restart=always

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now presentation.container
```

---

## 12. Presenter workflow

1. Edit `slides.md` (or put `slides.tex` in `source/`)
2. `./deploy.sh` — converts + starts server, shows all endpoints
3. Open `http://<IP>:8000` on projector machine → F11 fullscreen
4. Show QR code (bottom-left) to audience
5. Navigate with ← → arrow keys
6. Watch likes sidebar on the right
7. Navigate to last slide for the engagement bar chart

---

## 13. Extending

### Add a slide

Add a new `---` section to `slides.md`, then `./deploy.sh --convert-only`.

### Change the like mechanic

In `server/audience.html`, add a cooldown to the click handler:

```javascript
var lastLike = 0;
likeBtn.addEventListener('click', function () {
    if (Date.now() - lastLike < 2000) return;
    lastLike = Date.now();
    // ... rest of handler
});
```

### Persist likes across sessions

In `server/server.py` on startup/shutdown:

```python
LIKES_FILE = WORKSPACE / "likes.json"

def save_likes():
    LIKES_FILE.write_text(json.dumps(likes))

def load_likes():
    global likes
    if LIKES_FILE.exists():
        likes = {int(k): v for k, v in json.loads(LIKES_FILE.read_text()).items()}
```

### Custom slide backgrounds

Add an HTML comment to any slide in `slides.md`:

```markdown
## My Slide

<!-- style="background: linear-gradient(135deg,#1a2333,#2c3e50)" -->

Content here.
```

Then extend `converter/md2html.py` to parse and apply the comment as an inline style on the slide `<div>`.

---

## 14. Remote deployment (Hetzner VPS)

Use `deploy.sh` to present from a public server — no venue WiFi dependency.

### First-time VPS setup

```bash
# Bootstrap: installs podman, syncs project files, builds images
VPS=root@YOUR_SERVER_IP ./deploy.sh --setup
```

### Deploy and present

```bash
# Convert locally (bakes VPS IP into QR), push slides.html, restart server
VPS=root@YOUR_SERVER_IP ./deploy.sh
```

### Flags

```bash
# Push slides only — no server restart
VPS=root@YOUR_SERVER_IP ./deploy.sh --convert-only

# Restart server only — no re-conversion
VPS=root@YOUR_SERVER_IP ./deploy.sh --serve-only

# Custom SSH port
VPS_PORT=2222 VPS=root@YOUR_SERVER_IP ./deploy.sh
```

Local mode still works without `VPS`:

```bash
./deploy.sh          # auto-detects WiFi IP, converts + serves
```

### Hetzner firewall

Open **ports 80 and 443** in the **Hetzner Cloud Console** → your server →
**Firewalls → Add Rule**. Do **not** expose port 8000 publicly — Caddy
handles all public traffic.

| Direction | Protocol | Port | Source      |
|-----------|----------|------|-------------|
| Inbound   | TCP      | 80   | `0.0.0.0/0` |
| Inbound   | TCP      | 443  | `0.0.0.0/0` |

Or via `ufw` on the server:

```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 8000/tcp   # keep the app server internal
ufw reload
```

Then follow the [Caddy setup in section 8](#8-https-in-production) to get
automatic TLS. With `sslip.io` you don't need to buy a domain:

```bash
# Your IP 1.2.3.4 → free hostname 1-2-3-4.sslip.io
WS_SCHEME=wss SERVER_HOST=1-2-3-4.sslip.io VPS=root@1.2.3.4 ./deploy.sh
```

Audience URL: `https://1-2-3-4.sslip.io/audience`

---

## 15. Dependencies & credits

> **No Reveal.js.** The slide deck is plain HTML/CSS/JS generated by `converter/md2html.py`.

### Python

Split per service — no shared root `requirements.txt`.

| File | Package | Role |
|------|---------|------|
| `converter/requirements.txt` | [Markdown](https://python-markdown.github.io) | Markdown → HTML in `md2html.py` |
| `server/requirements.txt` | [FastAPI](https://fastapi.tiangolo.com) | HTTP + WebSocket server |
| `server/requirements.txt` | [uvicorn](https://www.uvicorn.org) | ASGI runner |
| `server/requirements.txt` | [websockets](https://websockets.readthedocs.io) | WebSocket transport |

### JavaScript (CDN, no `package.json` needed)

| Library | Version | CDN | Role |
|---------|---------|-----|------|
| [Font Awesome](https://fontawesome.com) | 6.5.2 | cdnjs | Icon set (`<i class="fa-...">`) |
| [QRCode.js](https://github.com/davidshimjs/qrcodejs) | 1.0.0 | cdnjs | QR code in projector view |
| [highlight.js](https://highlightjs.org) | 11.9.0 | cdnjs | Syntax highlighting for code blocks |
| [MathJax](https://www.mathjax.org) | 3.x | jsDelivr | LaTeX math via `$...$` / `$$...$$` |
| [viz.js](https://github.com/mdaines/viz-js) | 2.1.2 | cdnjs | Graphviz `dot` diagrams → inline SVG |
