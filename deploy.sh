#!/usr/bin/env bash
# deck-lovers — convert + serve, locally or on a remote VPS.
#
# LOCAL:
#   ./deploy.sh                          # auto-detects runtime + WiFi IP
#   ./deploy.sh --convert-only           # convert only, no server
#   ./deploy.sh --serve-only             # skip conversion, start server
#   ./deploy.sh --cloudflare <url>       # rebake Cloudflare tunnel URL into QR code
#
# REMOTE (Hetzner or any SSH host):
#   VPS=root@1.2.3.4 ./deploy.sh
#   VPS=root@1.2.3.4 ./deploy.sh --setup       # first-time VPS bootstrap
#   VPS=root@1.2.3.4 ./deploy.sh --convert-only
#
# ENV VARS:
#   VPS          user@host  — if set, deploy to remote host
#   VPS_PORT     SSH port (default 22)
#   PORT         app port (default 8000)
#   COMPOSE      override compose runtime (default: auto-detect)
#   SERVER_HOST  override hostname baked into QR code (remote: auto-sslip.io)
#   WS_SCHEME    ws or wss (remote: auto wss; local --https: auto wss)
#
# CLOUDFLARE TUNNEL (public HTTPS from laptop, no port forwarding):
#   Terminal 1:  cloudflared tunnel --url http://localhost:8000
#                → prints https://silver-toast.trycloudflare.com
#   Terminal 2:  ./deploy.sh --cloudflare https://silver-toast.trycloudflare.com
#                → converts slides with CF host in QR code + starts server

set -euo pipefail

# ── Parse flags ───────────────────────────────────────────────────────────────
CONVERT=true
SERVE=true
SETUP=false
HTTPS=false
CF_URL=""     # --cloudflare <url>  e.g. https://silver-toast.trycloudflare.com

while [[ $# -gt 0 ]]; do
  case "$1" in
    --convert-only) SERVE=false;    shift ;;
    --serve-only)   CONVERT=false;  shift ;;
    --setup)        SETUP=true;     shift ;;
    --https)        HTTPS=true;     shift ;;
    --cloudflare)
      CF_URL="${2:?'--cloudflare requires a URL argument'}";  shift 2 ;;
    *) shift ;;
  esac
done

# --cloudflare: reconvert with public host baked in, don't restart the server
if [[ -n "$CF_URL" ]]; then
  # strip scheme and trailing slash:  https://foo.trycloudflare.com/ → foo.trycloudflare.com
  CF_HOST="${CF_URL#*://}"   # strip scheme (http:// or https://)
  CF_HOST="${CF_HOST%%/*}"  # strip any trailing path
  SERVER_HOST="$CF_HOST"
  WS_SCHEME="wss"
  # SERVE stays true — convert + (re)start server so a single command does everything
  echo "☁  Cloudflare mode — public host: $CF_HOST"
  echo
fi

PORT=${PORT:-8000}
VPS_SSH_PORT=${VPS_PORT:-22}
VPS=${VPS:-}
WS_SCHEME=${WS_SCHEME:-ws}

# ── Detect compose runtime (Podman only) ─────────────────────────────────────
if [[ -z "${COMPOSE:-}" ]]; then
  COMPOSE="podman compose"
fi
if ! command -v podman &>/dev/null || ! podman info &>/dev/null 2>&1; then
  echo "ERROR: Podman is required." >&2
  exit 1
fi
if ! podman compose version &>/dev/null 2>&1; then
  echo "ERROR: 'podman compose' is required." >&2
  exit 1
fi

# ── sslip.io helper: 1.2.3.4 → 1-2-3-4.sslip.io ─────────────────────────────
_to_sslip() { echo "${1//./-}.sslip.io"; }

# ── Detect mode + HOST ────────────────────────────────────────────────────────
if [[ -n "$VPS" ]]; then
  MODE="remote"
  VPS_IP=$(echo "$VPS" | cut -d@ -f2)
  # Auto-HTTPS: compute sslip.io hostname from VPS IP unless caller overrides.
  # Uses Caddyfile.prod (real ACME cert — ports 80/443 must be open on the VPS).
  if [[ -z "${SERVER_HOST:-}" ]]; then
    SERVER_HOST=$(_to_sslip "$VPS_IP")
    WS_SCHEME="wss"
  fi
  export CADDYFILE="./Caddyfile.prod"
  HOST="$SERVER_HOST"
else
  MODE="local"
  if [[ -z "${SERVER_HOST:-}" ]]; then
    if command -v ipconfig &>/dev/null; then
      SERVER_HOST=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)
    else
      SERVER_HOST=$(ip -4 addr show scope global 2>/dev/null \
                    | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1 || true)
    fi
    if [[ -z "$SERVER_HOST" ]]; then
      echo "⚠  Could not detect WiFi IP — QR code will use 'localhost'" >&2
      SERVER_HOST="localhost"
    fi
  fi
  # --https (local): presenter's browser only — targets localhost so Chrome
  # trusts it natively (no CA install needed).  Audience devices on the same
  # LAN use plain HTTP at the LAN IP; that's printed separately below.
  LAN_IP="$SERVER_HOST"   # keep LAN IP for the audience hint
  if $HTTPS && [[ "$WS_SCHEME" != "wss" ]]; then
    SERVER_HOST="localhost"
    WS_SCHEME="wss"
    export CADDYFILE="./Caddyfile"   # tls internal
    echo "ℹ  HTTPS (local) → https://localhost  [presenter's browser only]"
    echo "   Audience on same LAN → http://$LAN_IP:$PORT/audience  [HTTP, no cert needed]"
    echo
  fi
  HOST="$SERVER_HOST"
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo "┌─────────────────────────────────────────┐"
echo "│              deck-lovers deploy          │"
echo "├─────────────────────────────────────────┤"
printf "│  mode    : %-30s│\n" "$MODE"
printf "│  runtime : %-30s│\n" "$COMPOSE"
printf "│  host    : %-30s│\n" "$HOST"
printf "│  port    : %-30s│\n" "$PORT"
[[ "$MODE" == "remote" ]] && printf "│  vps     : %-30s│\n" "$VPS"
echo "└─────────────────────────────────────────┘"
echo

SSH="ssh -p $VPS_SSH_PORT"
SCP="scp -P $VPS_SSH_PORT"

# ── Shared: convert slides locally ───────────────────────────────────────────
_convert() {
  local host="$1"

  echo "▶ Building images…"
  $COMPOSE build --pull md2html server
  echo

  # Ensure the output dir exists and is writable by any container UID.
  # With rootless Podman the directory may have been created by a previous
  # container running as a different UID (e.g. old appuser/1000), making it
  # unwritable even by "root" inside the new container.
  mkdir -p output
  chmod 777 output

  if [[ -s source/slides.tex ]]; then
    echo "▶ 1/2  tex2md   slides.tex → output/slides.md"
    $COMPOSE run --rm --remove-orphans tex2md
    echo "  ✓ done"
  else
    echo "→ 1/2  tex2md   skipped"
    mkdir -p output
    if [[ -f slides.md ]]; then
      cp slides.md output/slides.md
      echo "  → copied slides.md → output/slides.md"
    elif [[ ! -f output/slides.md ]]; then
      echo "ERROR: no slides.md found at project root or output/" >&2
      exit 1
    fi
  fi
  echo

  echo "▶ 2/2  md2html  output/slides.md → output/slides.html"
  # Remove any stale file — previous runs may have left it with a different owner
  # (e.g. appuser/UID-1000 from an old image) that the current container can't overwrite.
  rm -f output/slides.html
  SERVER_HOST="$host" PORT="$PORT" WS_SCHEME="$WS_SCHEME" $COMPOSE run --rm --remove-orphans md2html
  echo "  ✓ output/slides.html ready"
  echo
}

# ── Shared: print endpoint table ─────────────────────────────────────────────
_endpoints() {
  local h="$1"
  local show_hint="${2:-false}"
  # Use scheme-aware URLs: https/wss when Caddy/TLS is active
  local WS="$WS_SCHEME"
  local HTTP="http"; [[ "$WS" == "wss" ]] && HTTP="https"
  local P=":$PORT";  [[ "$WS" == "wss" ]] && P=""   # standard port — omit from URL
  echo "┌─────────────────────────────────────────────────────────────┐"
  echo "│                      ENDPOINTS                              │"
  echo "├──────────────┬──────────────────────────────────────────────┤"
  printf "│  %-12s│  %-44s│\n" "Projector"  "$HTTP://$h$P"
  printf "│  %-12s│  %-44s│\n" "Audience"   "$HTTP://$h$P/audience"
  printf "│  %-12s│  %-44s│\n" "Health"     "$HTTP://$h$P/health"
  printf "│  %-12s│  %-44s│\n" "WebSocket"  "$WS://$h$P/ws"
  if [[ "$show_hint" == "true" ]]; then
    echo "├──────────────┴──────────────────────────────────────────────┤"
    echo "│  QR code bottom-left of projector view  ·  Ctrl-C to stop  │"
  fi
  echo "└─────────────────────────────────────────────────────────────┘"
  echo
}

# ══════════════════════════════════════════════════════════════════════════════
# REMOTE MODE
# ══════════════════════════════════════════════════════════════════════════════
if [[ "$MODE" == "remote" ]]; then

  # ── First-time VPS bootstrap ───────────────────────────────────────────────
  if $SETUP; then
    echo "▶ Bootstrapping VPS…"
    $SSH "$VPS" bash <<'REMOTE'
set -euo pipefail

# ── Package manager helper ────────────────────────────────
_apt() { apt-get install -y --no-install-recommends "$@"; }
_dnf() { dnf install -y "$@"; }

# ── podman ────────────────────────────────────────────────
if ! command -v podman &>/dev/null; then
  if command -v apt-get &>/dev/null; then
    apt-get update -qq && _apt podman
  elif command -v dnf &>/dev/null; then
    _dnf podman
  else
    echo "ERROR: cannot install podman — do it manually" >&2; exit 1
  fi
fi

# ── podman compose (prefer built-in plugin v4+, fall back to pip package) ─
if ! podman compose version &>/dev/null 2>&1; then
  if command -v apt-get &>/dev/null; then
    # python3-podman-compose is in Ubuntu repos; avoids PEP-668 pip restrictions
    apt-get update -qq && _apt python3-podman-compose 2>/dev/null \
      || { _apt python3-pip 2>/dev/null; \
           pip3 install podman-compose --break-system-packages -q 2>/dev/null \
           || pip3 install podman-compose -q; }
  elif command -v dnf &>/dev/null; then
    _dnf python3-pip && pip3 install podman-compose -q
  fi
fi

# ── rsync (required for project file sync from local machine) ─────────────
if ! command -v rsync &>/dev/null; then
  if command -v apt-get &>/dev/null; then
    _apt rsync
  elif command -v dnf &>/dev/null; then
    _dnf rsync
  fi
fi

# ── firewall ──────────────────────────────────────────────
if command -v ufw &>/dev/null; then
  ufw allow 80/tcp   comment 'Caddy HTTP'  >/dev/null
  ufw allow 443/tcp  comment 'Caddy HTTPS' >/dev/null
  ufw deny  8000/tcp comment 'app internal only' >/dev/null
  ufw --force enable >/dev/null
  echo "  ufw: 80/443 open, 8000 blocked"
fi

mkdir -p /root/deck-lovers/output
chmod 755 /root/deck-lovers/output   # root-owned; converter containers run as root too
echo "VPS ready."
REMOTE
    echo "  ✓ VPS bootstrapped"
    echo

    echo "▶ Syncing project files to VPS…"
    command -v rsync &>/dev/null || { echo "ERROR: rsync not found locally (brew install rsync)" >&2; exit 1; }
    rsync -az --progress \
      -e "$SSH" \
      --exclude='.git' \
      --exclude='output/' \
      --exclude='__pycache__' \
      --exclude='*.pyc' \
      . "$VPS:/root/deck-lovers/"
    echo "  ✓ files synced"
    echo

    echo "▶ Building images on VPS…"
    $SSH "$VPS" "cd /root/deck-lovers && ${COMPOSE} build md2html server"  # C6: use detected runtime
    echo "  ✓ images built"
    echo
  fi

  # ── Convert locally, push HTML to VPS ─────────────────────────────────────
  if $CONVERT; then
    _convert "$HOST"
    echo "▶ Pushing slides.html to VPS…"
    $SCP output/slides.html "$VPS:/root/deck-lovers/output/slides.html"
    echo "  ✓ pushed"
    echo
  fi

  # ── Start / restart server + Caddy on VPS ────────────────────────────────
  if $SERVE; then
    echo "▶ Restarting server on VPS…"
    $SSH "$VPS" "cd /root/deck-lovers && ${COMPOSE} --profile tls up server caddy -d --remove-orphans"
    echo "  ✓ server + Caddy running (https)"
    echo
  fi

  _endpoints "$HOST"

# ══════════════════════════════════════════════════════════════════════════════
# LOCAL MODE
# ══════════════════════════════════════════════════════════════════════════════
else

  if $CONVERT; then
    _convert "$HOST"
  fi

  if $SERVE; then
    _endpoints "$HOST" true
    if [[ "$WS_SCHEME" == "wss" ]]; then
      $COMPOSE --profile tls up caddy server   # local --https mode
    else
      $COMPOSE up server                        # plain HTTP (default local)
    fi
  else
    _endpoints "$HOST"
  fi

fi
