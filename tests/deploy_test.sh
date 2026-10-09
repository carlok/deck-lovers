#!/usr/bin/env bash
# Tests for helper functions in deploy.sh (no bats needed).
#
#   ./tests/deploy_test.sh            # run with the default bash
#   /bin/bash tests/deploy_test.sh    # macOS ships bash 3.2; deploy.sh must work there
#
# Inner shells get </dev/null: bash sources ~/.bashrc when stdin is a socket.
#
# Each helper is cut out of deploy.sh and exercised in a scratch directory with a
# fake `podman`, so nothing here needs a container runtime. The port tests do bind
# one real localhost port. Requires lsof and python3.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'kill "${HTTP_PID:-}" 2>/dev/null; rm -rf "$TMP"' EXIT

PASS=0; FAIL=0
ok()   { echo "PASS  $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL  $1"; [[ -n "${2:-}" ]] && echo "      $2"; FAIL=$((FAIL + 1)); }

# extract <function-name>  → writes $TMP/<name>.sh containing just that function
extract() {
  sed -n "/^$1() {/,/^}/p" "$ROOT/deploy.sh" > "$TMP/$1.sh"
  [[ -s "$TMP/$1.sh" ]] || { echo "FAIL  $1 not found in deploy.sh"; exit 1; }
}
extract _check_ports_free
extract _load_env_file
extract _export_pdf

# ── _check_ports_free ─────────────────────────────────────────────────────────
mkdir -p "$TMP/bin"
cat > "$TMP/bin/podman" <<'EOF'
#!/usr/bin/env bash
# fake podman: `ps` prints $FAKE_PS (rows of  name|compose-project|ports)
[[ "${1:-}" == "ps" ]] && printf '%b' "${FAKE_PS:-}"
exit 0
EOF
chmod +x "$TMP/bin/podman"

FREE=18765
while lsof -nP -iTCP:$FREE -sTCP:LISTEN >/dev/null 2>&1; do FREE=$((FREE + 1)); done

# ports <FAKE_PS> <port>...  → sets RC and OUT, under deploy.sh's shell options
ports() {
  local ps="$1"; shift
  OUT=$(FAKE_PS="$ps" COMPOSE_PROJECT_NAME=deck-lovers PATH="$TMP/bin:$PATH" \
        bash -c 'set -euo pipefail; source "$1"; shift; _check_ports_free "$@"' _ "$TMP/_check_ports_free.sh" "$@" 2>&1 </dev/null)
  RC=$?
}
expect() {  # <name> <rc> [text the output must contain]
  if [[ $RC -eq $2 && ( -z "${3:-}" || "$OUT" == *"$3"* ) ]]; then ok "$1"
  else fail "$1" "rc=$RC (want $2); needle='${3:-}'; output: $OUT"; fi
}

ports "" "$FREE";                                                      expect "ports: free port passes" 0
ports "other-1|other|0.0.0.0:$FREE->8000/tcp\n" "$FREE";               expect "ports: foreign compose container is named" 1 "other-1"
ports "other-1|other|0.0.0.0:$FREE->8000/tcp\n" "$FREE";               expect "ports: error mentions the port" 1 "host port $FREE"
ports "other-1|other|0.0.0.0:$FREE->8000/tcp\n" "$FREE";               expect "ports: error names the compose project" 1 "compose project 'other'"
ports "lone||0.0.0.0:$FREE->80/tcp\n" "$FREE";                         expect "ports: plain podman-run container (empty label) is named" 1 "lone"
ports "deck-lovers-server-1|deck-lovers|0.0.0.0:$FREE->8000/tcp\n" "$FREE"; expect "ports: own project container is ignored" 0
ports "x|other|0.0.0.0:${FREE}0->80/tcp\n" "$FREE";                    expect "ports: ${FREE}0 does not match $FREE" 0
ports "x|other|0.0.0.0:80->80/tcp\n" "$FREE" 80;                       expect "ports: second port can clash" 1 "host port 80"

python3 -m http.server "$FREE" --bind 127.0.0.1 >/dev/null 2>&1 &
HTTP_PID=$!
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  lsof -nP -iTCP:$FREE -sTCP:LISTEN >/dev/null 2>&1 && break; sleep 0.25
done
ports "" "$FREE";                                                      expect "ports: host process is reported as in use" 1 "in use"
ports "" "$FREE";                                                      expect "ports: host process pid is named" 1 "pid $HTTP_PID"
kill "$HTTP_PID" 2>/dev/null; wait "$HTTP_PID" 2>/dev/null; HTTP_PID=""

# ── _load_env_file ────────────────────────────────────────────────────────────
# envload <env-file-content> [VAR=value ...]  → prints "KEY=value" lines after loading
envload() {
  local content="$1"; shift
  printf '%b' "$content" > "$TMP/dot.env"
  env -i PATH="$PATH" "$@" bash -c '
    set -euo pipefail
    source "$1"
    _load_env_file "$2"
    for k in PORT PALETTE FONT EMOJI LOGO FRAME LOGO_ON PDF_MODE PDF_NAME PDF_QUALITY SERVER_HOST WS_SCHEME PROJECTOR_PASSWORD; do
      if [[ -n "${!k+x}" ]]; then echo "$k=${!k}"; fi
    done' _ "$TMP/_load_env_file.sh" "$TMP/dot.env" 2>&1 </dev/null
}
same() { [[ "$2" == "$3" ]] && ok "$1" || fail "$1" "got: [$2]  want: [$3]"; }

same "env: reads PORT"                      "$(envload 'PORT=9000\n')" "PORT=9000"
same "env: missing file is not an error"    "$(env -i PATH="$PATH" bash -c 'set -euo pipefail; source "$1"; _load_env_file /nonexistent && echo fine' _ "$TMP/_load_env_file.sh" </dev/null)" "fine"
same "env: environment beats .env"          "$(envload 'PORT=9000\n' PORT=7000)" "PORT=7000"
same "env: empty environment value beats .env" "$(envload 'FONT=Montserrat\n' FONT=)" "FONT="
same "env: skips comments and blank lines"  "$(envload '# PORT=1\n\n   # x\nPORT=9001\n')" "PORT=9001"
same "env: double-quoted value"             "$(envload 'FONT="Open Sans"\n')" "FONT=Open Sans"
same "env: single-quoted value"             "$(envload "FONT='Open Sans'\n")" "FONT=Open Sans"
same "env: trailing comment, unquoted"      "$(envload 'PORT=9002   # custom\n')" "PORT=9002"
same "env: # kept inside quotes"            "$(envload 'FONT="A # B"\n')" "FONT=A # B"
same "env: trailing comment after quotes"   "$(envload 'FONT="Lato"  # why\n')" "FONT=Lato"
same "env: CRLF line endings"               "$(envload 'PORT=9003\r\nFONT=Lato\r\n')" "$(printf 'PORT=9003\nFONT=Lato')"
same "env: export prefix"                   "$(envload 'export PORT=9004\n')" "PORT=9004"
same "env: spaces around ="                 "$(envload 'PORT = 9005\n')" "PORT=9005"
same "env: last line without newline"       "$(envload 'PORT=9006')" "PORT=9006"
same "env: empty value"                     "$(envload 'PALETTE=\n')" "PALETTE="
same "env: SERVER_HOST is not loaded"       "$(envload 'SERVER_HOST=localhost\nWS_SCHEME=wss\n')" ""
same "env: unrelated keys are not loaded"   "$(envload 'PROJECTOR_PASSWORD=hunter2\n')" ""
same "env: a value cannot run code"         "$(envload 'PORT=$(touch '"$TMP"'/pwned)\n')" 'PORT=$(touch '"$TMP"'/pwned)'
[[ ! -e "$TMP/pwned" ]] && ok "env: no command was executed" || fail "env: no command was executed"

# ── _export_pdf: audience.pdf copy ────────────────────────────────────────────
cat > "$TMP/bin/fakecompose" <<'EOF'
#!/usr/bin/env bash
# fake `compose run --rm --remove-orphans pdf <html> /workspace/<name>`: writes output/<name>
out="${!#}"; printf 'PDF-BYTES' > "output/${out##*/}"
EOF
chmod +x "$TMP/bin/fakecompose"

# export_pdf <PDF_ONLY> <MODE> <PDF_NAME> [pre-existing audience.pdf content]
export_pdf() {
  local work="$TMP/work"; rm -rf "$work"; mkdir -p "$work/output"
  [[ -n "${4:-}" ]] && printf '%s' "$4" > "$work/output/audience.pdf"
  ( cd "$work" && PDF_ONLY="$1" MODE="$2" PDF_NAME="$3" COMPOSE="$TMP/bin/fakecompose" \
      bash -c 'set -euo pipefail; source "$1"; _export_pdf' _ "$TMP/_export_pdf.sh" >/dev/null 2>&1 </dev/null )
  RC=$?
}
has()  { [[ -e "$TMP/work/output/$1" ]]; }

export_pdf true local deck.pdf
[[ $RC -eq 0 ]] && has deck.pdf && ! has audience.pdf && ok "pdf: local --pdf-only makes only the named PDF" || fail "pdf: local --pdf-only makes only the named PDF" "rc=$RC"

export_pdf true local deck.pdf OLD-AUDIENCE
[[ "$(cat "$TMP/work/output/audience.pdf" 2>/dev/null)" == "OLD-AUDIENCE" ]] && ok "pdf: local --pdf-only leaves an existing audience.pdf alone" || fail "pdf: local --pdf-only leaves an existing audience.pdf alone"

export_pdf false local deck.pdf
[[ $RC -eq 0 ]] && has deck.pdf && has audience.pdf && ok "pdf: normal run also writes audience.pdf" || fail "pdf: normal run also writes audience.pdf" "rc=$RC"

export_pdf false local deck.pdf OLD-AUDIENCE
[[ "$(cat "$TMP/work/output/audience.pdf" 2>/dev/null)" == "PDF-BYTES" ]] && ok "pdf: normal run refreshes a stale audience.pdf" || fail "pdf: normal run refreshes a stale audience.pdf"

export_pdf true remote deck.pdf
[[ $RC -eq 0 ]] && has audience.pdf && ok "pdf: remote --pdf-only still writes audience.pdf (it is pushed to the VPS)" || fail "pdf: remote --pdf-only still writes audience.pdf" "rc=$RC"

export_pdf false local audience.pdf
[[ $RC -eq 0 ]] && has audience.pdf && ok "pdf: --pdf-name audience.pdf needs no self-copy" || fail "pdf: --pdf-name audience.pdf needs no self-copy" "rc=$RC"

echo
echo "passed=$PASS failed=$FAIL"
[[ $FAIL -eq 0 ]]
