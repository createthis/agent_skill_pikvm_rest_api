#!/usr/bin/env bash
# pikvm.sh — a zero-dependency (bash + curl) client for the PiKVM / KVMD REST API.
#
# The base URL and credentials are resolved at runtime; nothing sensitive is
# hardcoded. See the usage text for the resolution order.
set -euo pipefail

PROG="$(basename "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

BASE_URL=""
USER_NAME=""
PASSWORD=""
INSECURE=0
CA_BUNDLE=""
TIMEOUT=30
BINARY_OUT_FILE=""
RESP_FILE="$(mktemp "${TMPDIR:-/tmp}/pikvm-resp.XXXXXX")"
# Only clean up the temp response file; a file the user asked for via --out is kept.
trap 'rm -f "$RESP_FILE"' EXIT

usage() {
  cat >&2 <<EOF
$PROG — PiKVM (KVMD) REST API client. Zero dependencies beyond bash + curl.

Usage: $PROG [global options] <command> [args]

Global options (before the command):
  --base-url URL     One-off KVM base URL (overrides all other config).
  --user USER        One-off username (overrides config).
  --password PASS    One-off password (overrides config).
  --insecure         Skip TLS certificate verification (self-signed cert).
  --ca PATH          Trust a specific CA bundle for the KVM's cert.
  --timeout SECS     Request timeout in seconds (default: 30).
  --out FILE         For 'raw' binary responses: save the bytes to FILE instead
                     of a temporary file (the temp file is deleted on exit).
  -h, --help         Show this help.

Base URL / credential resolution (first match wins per value):
  1. --base-url / --user / --password flags
  2. \$PIKVM_URL / \$PIKVM_USER / \$PIKVM_PASSWORD environment variables
  3. pikvm.local in the skill dir (or ~/.config/pikvm/endpoint)

Commands:
  info                          GET  /api/info        (KVM/system info)
  power                         GET  /api/atx         (ATX power state)
  hid                           GET  /api/hid         (keyboard/mouse state)
  key KEY                       tap one key, e.g. key Escape
  shortcut KEY [KEY...]         press a key chord, e.g. shortcut MetaLeft KeyA
  type TEXT                     type text (POST /api/hid/print)
  click [BUTTON]                mouse click; BUTTON in left|right|middle (default left)
  move X Y                      absolute mouse move in native KVMD coords
                                  (X,Y in -32768..32767; 0,0 = screen center)
  wheel DX DY                   scroll the wheel by delta
  power-on | power-off | power-reset
                                ATX power control (POST /api/atx/power)
  snapshot [FILE]               capture the screen as JPEG (default: temp file)
  raw METHOD PATH [K=V ...]     generic request, e.g. raw POST /api/hid/reset

Key names follow the KVMD web keymap (KeyA, Digit1, Enter, Escape, Tab, Space,
F1..F12, MetaLeft, ControlLeft, AltLeft, ShiftLeft, NumpadEnter, ...).
Full reference: ../SKILL.md and ../references/KEYMAP.md.
EOF
}

die() { echo "error: $*" >&2; exit "${2:-1}"; }

# --- parse global options ---------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE_URL="${2:?--base-url requires a URL}"; shift 2 ;;
    --user)     USER_NAME="${2:?--user requires a value}"; shift 2 ;;
    --password) PASSWORD="${2:?--password requires a value}"; shift 2 ;;
    --insecure) INSECURE=1; shift ;;
    --ca)       CA_BUNDLE="${2:?--ca requires a path}"; shift 2 ;;
    --timeout)  TIMEOUT="${2:?--timeout requires a number}"; shift 2 ;;
    --out)      BINARY_OUT_FILE="${2:?--out requires a path}"; shift 2 ;;
    -h|--help)  usage; exit 0 ;;
    -*)         die "unknown global option: $1 (see --help)" 2 ;;
    *)          break ;;
  esac
done

[[ $# -ge 1 ]] || { usage; exit 2; }
COMMAND="$1"; shift

# --- config file resolution -------------------------------------------------
# config_get FILE KEY  -> print the value of KEY= from FILE (last wins, # comments ok)
config_get() {
  local f="$1" key="$2" line val=""
  [[ -f "$f" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"
    line="$(printf '%s' "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [[ "$line" == "$key"=* ]] || continue
    val="${line#*=}"
  done < "$f"
  [[ -n "$val" ]] || return 1
  printf '%s' "$val"
}

CONFIG_FILE=""
for cand in "$SKILL_DIR/pikvm.local" "$SCRIPT_DIR/pikvm.local" "${HOME:-/nonexistent}/.config/pikvm/endpoint"; do
  [[ -f "$cand" ]] && { CONFIG_FILE="$cand"; break; }
done

if [[ -z "$BASE_URL" && -n "${PIKVM_URL:-}" ]]; then BASE_URL="$PIKVM_URL"; fi
if [[ -z "$USER_NAME" && -n "${PIKVM_USER:-}" ]]; then USER_NAME="$PIKVM_USER"; fi
if [[ -z "$PASSWORD" && -n "${PIKVM_PASSWORD:-}" ]]; then PASSWORD="$PIKVM_PASSWORD"; fi
case "${PIKVM_INSECURE:-}" in true|1|yes|on) INSECURE=1 ;; esac
if [[ -z "$CA_BUNDLE" && -n "${PIKVM_CA:-}" ]]; then CA_BUNDLE="$PIKVM_CA"; fi

if [[ -n "$CONFIG_FILE" ]]; then
  [[ -n "$BASE_URL" ]]  || BASE_URL="$(config_get "$CONFIG_FILE" PIKVM_URL || true)"
  [[ -n "$USER_NAME" ]] || USER_NAME="$(config_get "$CONFIG_FILE" PIKVM_USER || true)"
  [[ -n "$PASSWORD" ]]  || PASSWORD="$(config_get "$CONFIG_FILE" PIKVM_PASSWORD || true)"
  [[ -n "$CA_BUNDLE" ]] || CA_BUNDLE="$(config_get "$CONFIG_FILE" PIKVM_CA || true)"
  case "$(config_get "$CONFIG_FILE" PIKVM_INSECURE || true)" in true|1|yes|on) INSECURE=1 ;; esac
fi

if [[ -z "$BASE_URL" ]]; then
  cat >&2 <<EOF
error: no KVM base URL configured.

Configure one of (first match wins):
  1. pass --base-url http(s)://your-kvm
  2. export PIKVM_URL=http(s)://your-kvm
  3. cp pikvm.example pikvm.local   (in the skill dir, then edit)
  4. create ~/.config/pikvm/endpoint
EOF
  exit 3
fi
if [[ -z "$USER_NAME" || -z "$PASSWORD" ]]; then
  die "username and password are required (use --user/--password, PIKVM_USER/PIKVM_PASSWORD, or pikvm.local) (see --help)" 3
fi
case "$BASE_URL" in
  http://*|https://*) ;;
  *) die "base URL must be an http(s) URL, got: $BASE_URL" 2 ;;
esac
BASE_URL="${BASE_URL%/}"

# --- request helpers --------------------------------------------------------
CURL_ARGS=()

auth_curl_args() {
  if [[ -n "$USER_NAME" ]]; then CURL_ARGS+=(-u "${USER_NAME}:${PASSWORD}"); fi
  if [[ -n "$CA_BUNDLE" ]]; then
    CURL_ARGS+=(--cacert "$CA_BUNDLE")
  elif [[ "$INSECURE" == 1 ]]; then
    CURL_ARGS+=(-k)
  fi
}

print_json() {
  # pretty-print a JSON body if jq is available, otherwise raw
  if command -v jq >/dev/null 2>&1 && head -c1 "$RESP_FILE" | grep -q '[{]'; then
    jq . "$RESP_FILE" 2>/dev/null || cat "$RESP_FILE"
  else
    cat "$RESP_FILE"
  fi
}

# do_request METHOD PATH [QUERY] [EXTRA CURL ARGS...]
# The QUERY arg is consumed if *supplied* (even when empty); only a non-empty
# query is appended to the URL. Extra args after QUERY are curl flags.
do_request() {
  local method="$1" path="$2" query="${3:-}"
  shift 2
  if [[ $# -gt 0 ]]; then shift; fi
  local url="${BASE_URL}${path}"
  if [[ -n "$query" ]]; then url="${url}?${query}"; fi
  CURL_ARGS=()
  CURL_ARGS+=(-sS --max-time "$TIMEOUT" -A 'agent-skill-pikvm-rest-api/1.0' -o "$RESP_FILE" -w '%{http_code} %{content_type}')
  auth_curl_args
  local meta
  if ! meta="$(curl -X "$method" "${CURL_ARGS[@]}" "$@" "$url" 2>&1)"; then
    die "request ${method} ${path} failed (network unreachable, KVM down, or timeout after ${TIMEOUT}s): $meta" 4
  fi
  HTTP_CODE="${meta%% *}"
  CONTENT_TYPE="${meta#* }"
  if [[ "$HTTP_CODE" != "200" ]]; then
    echo "error: ${method} ${path} returned HTTP $HTTP_CODE" >&2
    cat "$RESP_FILE" >&2
    echo >&2
    exit 4
  fi
}

# --- commands ---------------------------------------------------------------
case "$COMMAND" in
  info)     do_request GET /api/info;   print_json ;;
  power)    do_request GET /api/atx;    print_json ;;
  hid)      do_request GET /api/hid;    print_json ;;

  key)
    [[ $# -ge 1 ]] || { usage; exit 2; }
    do_request POST /api/hid/events/send_key "key=$1"
    echo "tapped key: $1" >&2
    ;;

  shortcut)
    [[ $# -ge 1 ]] || { usage; exit 2; }
    keys=""
    for k in "$@"; do keys="${keys:+$keys,}$k"; done
    do_request POST /api/hid/events/send_shortcut "keys=$keys"
    echo "sent shortcut: $keys" >&2
    ;;

  type)
    [[ $# -ge 1 ]] || { usage; exit 2; }
    text="$*"
    limit="${#text}"
    [[ "$limit" -lt 1 ]] && limit=1024
    # --data-raw (not --data-binary): a leading '@' in the text is sent
    # literally instead of being interpreted by curl as a file to upload.
    do_request POST /api/hid/print "limit=$limit" -H 'Content-Type: text/plain' --data-raw "$text"
    echo "typed ${#text} characters" >&2
    ;;

  click)
    btn="${1:-left}"
    case "$btn" in left|right|middle) ;; *) die "button must be left, right, or middle (got: $btn)" 2 ;; esac
    do_request POST /api/hid/events/send_mouse_button "button=$btn"
    echo "clicked: $btn" >&2
    ;;

  move)
    [[ $# -eq 2 ]] || { usage; exit 2; }
    do_request POST /api/hid/events/send_mouse_move "to_x=$1&to_y=$2"
    echo "moved mouse to ($1, $2)" >&2
    ;;

  wheel)
    [[ $# -eq 2 ]] || { usage; exit 2; }
    do_request POST /api/hid/events/send_mouse_wheel "delta_x=$1&delta_y=$2"
    echo "wheeled ($1, $2)" >&2
    ;;

  power-on|power-off|power-reset)
    action="${COMMAND#power-}"
    case "$action" in
      on)    action=on ;;
      off)   action=off ;;
      reset) action=reset_hard ;;
    esac
    do_request POST /api/atx/power "action=$action"
    echo "ATX power: $action" >&2
    ;;

  snapshot)
    out="${1:-}"
    [[ -n "$out" ]] || out="$(mktemp "${TMPDIR:-/tmp}/pikvm-snap.XXXXXX").jpg"
    CURL_ARGS=()
    CURL_ARGS+=(-sS --max-time "$TIMEOUT" -A 'agent-skill-pikvm-rest-api/1.0' -o "$out" -w '%{http_code} %{content_type}')
    auth_curl_args
    if ! meta="$(curl -X GET "${CURL_ARGS[@]}" "${BASE_URL}/api/streamer/snapshot" 2>&1)"; then
      die "snapshot request failed (KVM down or timeout after ${TIMEOUT}s): $meta" 4
    fi
    code="${meta%% *}"
    if [[ "$code" == "200" ]]; then
      size="$(wc -c < "$out" | tr -d ' ')"
      echo "saved JPEG snapshot to: $out (${size} bytes)"
    else
      echo "error: snapshot returned HTTP $code (the video stream may be offline — open the PiKVM web UI once to wake the stream, or retry)" >&2
      cat "$out" >&2
      rm -f "$out"
      exit 4
    fi
    ;;

  raw)
    [[ $# -ge 2 ]] || { usage; exit 2; }
    method="$1"; path="$2"; shift 2
    query=""
    for kv in "$@"; do query="${query:+$query&}$kv"; done
    do_request "$method" "$path" "$query"
    case "${CONTENT_TYPE:-}" in
      image/*|application/octet-stream)
        # Binary response: RESP_FILE is deleted on exit, so copy it to a file
        # the caller keeps. --out is honored; otherwise a fresh temp file.
        out="${BINARY_OUT_FILE:-$(mktemp "${TMPDIR:-/tmp}/pikvm-bin.XXXXXX")}"
        cp "$RESP_FILE" "$out"
        echo "saved binary to: $out ($(wc -c < "$out" | tr -d ' ') bytes)"
        ;;
      *)       print_json ;;
    esac
    ;;

  *)
    die "unknown command: $COMMAND (see --help)" 2 ;;
esac
