#!/usr/bin/env bash
# deck-lovers — convert + serve, locally or on a remote VPS.
#
# LOCAL:
#   ./deploy.sh                          # auto-detects runtime + WiFi IP
#   ./deploy.sh --convert-only           # convert only, no server
#   ./deploy.sh --serve-only             # skip conversion, start server
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

set -euo pipefail

# ── Parse flags ───────────────────────────────────────────────────────────────
CONVERT=true
SERVE=true
SETUP=false
HTTPS=false
for arg in "$@"; do
  case "$arg" in
    --convert-only) SERVE=false ;;
    --serve-only)   CONVERT=false ;;
    --setup)        SETUP=true ;;
    --https)        HTTPS=true ;;
  esac
done

PORT=${PORT:-8000}
VPS_SSH_PORT=${VPS_PORT:-22}
VPS=${VPS:-}
WS_SCHEME=${WS_SCHEME:-ws}

# ── Detect compose runtime ────────────────────────────────────────────────────
if [[ -z "${COMPOSE:-}" ]]; then
  if command -v podman &>/dev/null && podman info &>/dev/null 2>&1; then
    COMPOSE="podman compose"
  elif command -v docker &>/dev/null && docker compose version &>/dev/null 2>&1; then
    COMPOSE="docker compose"
  else
    echo "ERROR: neither 'podman compose' nor 'docker compose' found." >&2
    exit 1
  fi
fi

# ── sslip.io helper: 1.2.3.4 → 1-2-3-4.sslip.io ─────────────────────────────
_to_sslip() { echo "${1//./-}.sslip.io"; }

# ── Detect mode + HOST ────────────────────────────────────────────────────────
if [[ -n "$VPS" ]]; then
  MODE="remote"
  VPS_IP=$(echo "$VPS" | cut -d@ -f2)
  # Auto-HTTPS: compute sslip.io hostname from VPS IP unless caller overrides
  if [[ -z "${SERVER_HOST:-}" ]]; then
    SERVER_HOST=$(_to_sslip "$VPS_IP")
    WS_SCHEME="wss"
  fi
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
  # --https: get public IP → sslip.io (requires port 80/443 forwarded to this machine)
  if $HTTPS && [[ "$WS_SCHEME" != "wss" ]]; then
    _PUB=$(curl -sf --connect-timeout 3 https://api.ipify.org 2>/dev/null || true)
    if [[ -n "$_PUB" ]]; then
      SERVER_HOST=$(_to_sslip "$_PUB")
      WS_SCHEME="wss"
      echo "ℹ  HTTPS mode → $SERVER_HOST  (needs ports 80/443 forwarded to this machine)"
    else
      echo "⚠  Could not detect public IP — falling back to HTTP" >&2
    fi
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
  $COMPOSE build md2html server
  echo

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
  SERVER_HOST="$host" PORT="$PORT" $COMPOSE run --rm --remove-orphans md2html
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
if ! command -v podman &>/dev/null; then
  if command -v apt-get &>/dev/null; then
    apt-get update -qq && apt-get install -y podman
  elif command -v dnf &>/dev/null; then
    dnf install -y podman
  else
    echo "ERROR: cannot install podman — do it manually" >&2; exit 1
  fi
fi
if ! command -v podman-compose &>/dev/null; then
  pip3 install podman-compose -q 2>/dev/null || pip install podman-compose -q
fi
mkdir -p /root/deck-lovers/output
echo "VPS ready."
REMOTE
    echo "  ✓ VPS bootstrapped"
    echo

    echo "▶ Syncing project files to VPS…"
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
