#!/usr/bin/env bash
# Integration tests for scripts/pikvm.sh, driven against tests/mock_kvm_server.py.
#
# Runs fully offline: a local mock KVMD HTTP server on 127.0.0.1, a copied
# client in a throwaway skill dir, and an isolated fake HOME. No real KVM,
# network, or credentials are needed; the caller's PIKVM_* env is ignored.
#
#   bash pikvm-rest-api/tests/test_pikvm.sh
#
# Prints PASS/FAIL per assertion and exits non-zero if any fail.
set -u

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$TESTS_DIR/.." && pwd)"
REAL_CLIENT="$SKILL_DIR/scripts/pikvm.sh"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/pikvm-tests.XXXXXX")"
SERVER_PID=""
cleanup() {
  [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null
  [[ -n "$SERVER_PID" ]] && wait "$SERVER_PID" 2>/dev/null
  rm -rf "$WORK"
}
trap cleanup EXIT

# --- isolated client copy + fake home --------------------------------------
CLIENT_DIR="$WORK/skill/scripts"
mkdir -p "$CLIENT_DIR" "$WORK/home"
cp "$REAL_CLIENT" "$CLIENT_DIR/pikvm.sh"
CLIENT="$CLIENT_DIR/pikvm.sh"
FAKE_HOME="$WORK/home"
CONFIG_FILE="$WORK/skill/pikvm.local"
TEST_PATH="/usr/local/bin:/usr/bin:/bin"
USER_AGENT="agent-skill-pikvm-rest-api/1.0"

# --- mock server ------------------------------------------------------------
PORT_FILE="$WORK/port"
REQ_LOG="$WORK/reqs.jsonl"
python3 "$TESTS_DIR/mock_kvm_server.py" --port 0 --portfile "$PORT_FILE" \
  --logfile "$REQ_LOG" --expected-user testuser --expected-password 'test pass' \
  --reset >"$WORK/server.log" 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 50); do
  [[ -s "$PORT_FILE" ]] && break
  sleep 0.1
done
if [[ ! -s "$PORT_FILE" ]] || ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "FATAL: mock server failed to start:" >&2
  cat "$WORK/server.log" >&2
  exit 1
fi
PORT="$(cat "$PORT_FILE")"
BASE="http://127.0.0.1:$PORT"
GOOD_URL="$BASE"; GOOD_USER="testuser"; GOOD_PASS='test pass'
expected_auth="Basic $(printf '%s' "$GOOD_USER:$GOOD_PASS" | base64 | tr -d '\n')"

# --- test machinery ---------------------------------------------------------
PASS=0; FAIL=0
# assert <name> <exit code 0=ok> [detail]  — call as:  <condition>; assert "name" "$?"
assert() {
  local name="$1" code="$2" detail="${3:-}"
  if [[ "$code" -eq 0 ]]; then
    PASS=$((PASS+1)); printf 'PASS  %s\n' "$name"
  else
    FAIL=$((FAIL+1)); printf 'FAIL  %s\n' "$name"
    [[ -n "$detail" ]] && printf '        %s\n' "$detail"
  fi
}
section() { printf '\n-- %s\n' "$1"; }

# Run the client with a fully controlled environment (no PIKVM_* leaks from
# the surrounding shell). Global options, if any, go before the command.
# After a call: RC (exit code), OUT (stdout), ERR (stderr) are set.
RC=0; OUT=""; ERR=""
run_client() {
  local env=()
  [[ -n "${T_URL:-}" ]]      && env+=("PIKVM_URL=$T_URL")
  [[ -n "${T_USER:-}" ]]     && env+=("PIKVM_USER=$T_USER")
  [[ -n "${T_PASS:-}" ]]     && env+=("PIKVM_PASSWORD=$T_PASS")
  [[ -n "${T_INSECURE:-}" ]] && env+=("PIKVM_INSECURE=$T_INSECURE")
  [[ -n "${T_CA:-}" ]]       && env+=("PIKVM_CA=$T_CA")
  OUT="$(env -i PATH="$TEST_PATH" HOME="$FAKE_HOME" "${env[@]}" \
          bash "$CLIENT" "$@" 2>"$WORK/err")"
  RC=$?
  ERR="$(cat "$WORK/err" 2>/dev/null)"
}

reset_env()      { T_URL=""; T_USER=""; T_PASS=""; T_INSECURE=""; T_CA=""; }
configured_env() { T_URL="$GOOD_URL"; T_USER="$GOOD_USER"; T_PASS="$GOOD_PASS"; }

# last_req <field> : value of a field in the most recent logged request.
last_req() {
  python3 - "$REQ_LOG" "$1" <<'PY'
import json, sys
path, field = sys.argv[1], sys.argv[2]
rec = None
for line in open(path):
    line = line.strip()
    if line:
        rec = json.loads(line)
if rec is None:
    print("\x00<no request logged>")
else:
    v = rec.get(field)
    print("" if v is None else str(v))
PY
}

# ===========================================================================
section "config resolution"

reset_env
run_client --base-url "$GOOD_URL" --user "$GOOD_USER" --password "$GOOD_PASS" info
[[ $RC -eq 0 ]];                                   assert "flags resolve; info works" "$?" "rc=$RC err=$ERR"
grep -q mock-kvm <<<"$OUT";                        assert "info output mentions mock-kvm" "$?" "out=$OUT"
[[ $(last_req method) == GET ]];                   assert "info sends GET" "$?"
[[ $(last_req path) == /api/info ]];               assert "info hits /api/info" "$?" "got: $(last_req path)"
[[ $(last_req authorization) == "$expected_auth" ]]; assert "info sends correct Basic auth" "$?" "got: $(last_req authorization)"
[[ $(last_req user_agent) == "$USER_AGENT" ]];     assert "info sends expected user-agent" "$?" "got: $(last_req user_agent)"

reset_env; configured_env
run_client power
[[ $RC -eq 0 ]];                                   assert "env vars resolve; power works" "$?" "rc=$RC err=$ERR"
grep -q reset_hard <<<"$OUT";                      assert "power output mentions reset_hard" "$?" "out=$OUT"
[[ $(last_req path) == /api/atx ]];                assert "power hits /api/atx" "$?" "got: $(last_req path)"

reset_env; configured_env
run_client hid
[[ $RC -eq 0 ]];                                   assert "hid works" "$?" "rc=$RC err=$ERR"
grep -q absolute <<<"$OUT";                        assert "hid output mentions absolute" "$?" "out=$OUT"
[[ $(last_req path) == /api/hid ]];                assert "hid hits /api/hid" "$?" "got: $(last_req path)"

reset_env
printf '# a comment\nPIKVM_URL=%s\nPIKVM_USER=%s\nPIKVM_PASSWORD=%s\n' \
  "$GOOD_URL" "$GOOD_USER" "$GOOD_PASS" > "$CONFIG_FILE"
run_client info
[[ $RC -eq 0 ]];                                   assert "pikvm.local in skill dir resolves" "$?" "rc=$RC err=$ERR"
[[ $(last_req path) == /api/info ]];               assert "skill-dir config actually used" "$?"
rm -f "$CONFIG_FILE"

reset_env
mkdir -p "$FAKE_HOME/.config/pikvm"
printf 'PIKVM_URL=%s\nPIKVM_USER=%s\nPIKVM_PASSWORD=%s\n' \
  "$GOOD_URL" "$GOOD_USER" "$GOOD_PASS" > "$FAKE_HOME/.config/pikvm/endpoint"
run_client info
[[ $RC -eq 0 ]];                                   assert "~/.config/pikvm/endpoint resolves" "$?" "rc=$RC err=$ERR"
rm -rf "$FAKE_HOME/.config"

reset_env; configured_env
printf 'PIKVM_URL=http://127.0.0.1:1\nPIKVM_USER=x\nPIKVM_PASSWORD=x\n' > "$CONFIG_FILE"
run_client info
[[ $RC -eq 0 ]];                                   assert "env overrides pikvm.local (env wins)" "$?" "rc=$RC err=$ERR"
rm -f "$CONFIG_FILE"

reset_env
T_URL="http://127.0.0.1:1"
run_client --base-url "$GOOD_URL" --user "$GOOD_USER" --password "$GOOD_PASS" info
[[ $RC -eq 0 ]];                                   assert "flag overrides env for base-url (flag wins)" "$?" "rc=$RC err=$ERR"

# ===========================================================================
section "unconfigured / invalid config"

reset_env
run_client info
[[ $RC -eq 3 ]];                                   assert "no config -> exit 3" "$?" "rc=$RC"
grep -q 'no KVM base URL' <<<"$ERR";               assert "no config -> explains how to configure" "$?" "err=$ERR"

reset_env
T_URL="$GOOD_URL"
run_client info
[[ $RC -eq 3 ]];                                   assert "url but no credentials -> exit 3" "$?" "rc=$RC"
grep -q 'username and password are required' <<<"$ERR"; assert "missing creds message" "$?" "err=$ERR"

reset_env
T_URL="ftp://nope"; T_USER="$GOOD_USER"; T_PASS="$GOOD_PASS"
run_client info
[[ $RC -eq 2 ]];                                   assert "non-http(s) base url -> exit 2" "$?" "rc=$RC"
grep -q 'must be an http(s) URL' <<<"$ERR";        assert "bad-scheme message" "$?" "err=$ERR"

# ===========================================================================
section "usage / help"

reset_env
run_client --help
[[ $RC -eq 0 ]];                                   assert "--help -> exit 0" "$?" "rc=$RC"
# usage() writes to stderr by design
grep -q 'Usage:' <<<"$ERR";                        assert "--help prints Usage (to stderr)" "$?" "err=$ERR"

reset_env
run_client
[[ $RC -eq 2 ]];                                   assert "no command -> exit 2" "$?" "rc=$RC"
grep -q 'Usage:' <<<"$ERR";                        assert "no command prints usage to stderr" "$?" "err=$ERR"

# must be configured: with no config the client exits 3 before it even
# inspects the command word
configured_env
run_client frobnicate
[[ $RC -eq 2 ]];                                   assert "unknown command -> exit 2" "$?" "rc=$RC"
grep -q 'unknown command' <<<"$ERR";               assert "unknown command message" "$?" "err=$ERR"

reset_env; configured_env
run_client --bogus info
[[ $RC -eq 2 ]];                                   assert "unknown global option -> exit 2" "$?" "rc=$RC"
grep -q 'unknown global option' <<<"$ERR";         assert "unknown option message" "$?" "err=$ERR"

# ===========================================================================
section "input commands (exact method / path / query / body)"

reset_env; configured_env
run_client key Escape
[[ $RC -eq 0 ]];                                   assert "key -> rc=0" "$?" "rc=$RC err=$ERR"
grep -q 'tapped key: Escape' <<<"$ERR";            assert "key stderr 'tapped key: Escape'" "$?" "err=$ERR"
[[ $(last_req method) == POST ]];                  assert "key sends POST" "$?"
[[ $(last_req path) == /api/hid/events/send_key ]]; assert "key hits send_key" "$?" "got: $(last_req path)"
[[ $(last_req query) == "key=Escape" ]];           assert "key query key=Escape" "$?" "got: $(last_req query)"

run_client shortcut MetaLeft KeyA
[[ $RC -eq 0 ]];                                   assert "shortcut -> rc=0" "$?" "rc=$RC err=$ERR"
[[ $(last_req path) == /api/hid/events/send_shortcut ]]; assert "shortcut hits send_shortcut" "$?" "got: $(last_req path)"
[[ $(last_req query) == "keys=MetaLeft,KeyA" ]];   assert "shortcut comma-joins keys" "$?" "got: $(last_req query)"
grep -q 'MetaLeft,KeyA' <<<"$ERR";                 assert "shortcut stderr lists keys" "$?" "err=$ERR"

run_client type hello world
[[ $RC -eq 0 ]];                                   assert "type -> rc=0" "$?" "rc=$RC err=$ERR"
[[ $(last_req path) == /api/hid/print ]];          assert "type hits /api/hid/print" "$?" "got: $(last_req path)"
[[ $(last_req query) == "limit=11" ]];             assert "type query limit=11" "$?" "got: $(last_req query)"
[[ $(last_req body) == "hello world" ]];           assert "type body is 'hello world'" "$?" "got: $(last_req body)"
grep -q 'typed 11 characters' <<<"$ERR";           assert "type stderr 'typed 11 characters'" "$?" "err=$ERR"

run_client type '@literal not a file'
[[ $(last_req body) == "@literal not a file" ]];   assert "type '@...' sent literally" "$?" "got: $(last_req body)"

run_client click
[[ $RC -eq 0 ]];                                   assert "click default -> rc=0" "$?" "rc=$RC err=$ERR"
[[ $(last_req path) == /api/hid/events/send_mouse_button ]]; assert "click hits send_mouse_button" "$?" "got: $(last_req path)"
[[ $(last_req query) == "button=left" ]];          assert "click default is left" "$?" "got: $(last_req query)"

run_client click right
[[ $(last_req query) == "button=right" ]];         assert "click right" "$?" "got: $(last_req query)"
run_client click middle
[[ $(last_req query) == "button=middle" ]];        assert "click middle" "$?" "got: $(last_req query)"

run_client click sideways
[[ $RC -eq 2 ]];                                   assert "click bad button -> exit 2" "$?" "rc=$RC"
grep -q 'button must be' <<<"$ERR";                assert "bad button message" "$?" "err=$ERR"

run_client move 123 -456
[[ $RC -eq 0 ]];                                   assert "move -> rc=0" "$?" "rc=$RC err=$ERR"
[[ $(last_req path) == /api/hid/events/send_mouse_move ]]; assert "move hits send_mouse_move" "$?" "got: $(last_req path)"
[[ $(last_req query) == "to_x=123&to_y=-456" ]];   assert "move query to_x/to_y" "$?" "got: $(last_req query)"

run_client move 1
[[ $RC -eq 2 ]];                                   assert "move with 1 arg -> exit 2" "$?" "rc=$RC"
run_client move 1 2 3
[[ $RC -eq 2 ]];                                   assert "move with 3 args -> exit 2" "$?" "rc=$RC"

run_client wheel 5 -7
[[ $RC -eq 0 ]];                                   assert "wheel -> rc=0" "$?" "rc=$RC err=$ERR"
[[ $(last_req path) == /api/hid/events/send_mouse_wheel ]]; assert "wheel hits send_mouse_wheel" "$?" "got: $(last_req path)"
[[ $(last_req query) == "delta_x=5&delta_y=-7" ]]; assert "wheel query deltas" "$?" "got: $(last_req query)"

# ===========================================================================
section "power control"

reset_env; configured_env
run_client power-on
[[ $RC -eq 0 ]];                                   assert "power-on -> rc=0" "$?" "rc=$RC err=$ERR"
[[ $(last_req path) == /api/atx/power ]];          assert "power hits /api/atx/power" "$?" "got: $(last_req path)"
[[ $(last_req query) == "action=on" ]];            assert "power-on -> action=on" "$?" "got: $(last_req query)"

run_client power-off
[[ $(last_req query) == "action=off" ]];           assert "power-off -> action=off" "$?" "got: $(last_req query)"

run_client power-reset
[[ $(last_req query) == "action=reset_hard" ]];    assert "power-reset -> action=reset_hard" "$?" "got: $(last_req query)"
grep -q 'reset_hard' <<<"$ERR";                    assert "power-reset stderr names the action" "$?" "err=$ERR"

# ===========================================================================
section "snapshot"

reset_env; configured_env
SNAP="$WORK/screen.jpg"
run_client snapshot "$SNAP"
[[ $RC -eq 0 ]];                                   assert "snapshot -> rc=0" "$?" "rc=$RC err=$ERR"
[[ -s "$SNAP" ]];                                  assert "snapshot writes a non-empty file" "$?" "size=$(stat -c %s "$SNAP" 2>/dev/null)"
grep -q 'saved JPEG snapshot' <<<"$OUT";           assert "snapshot stdout 'saved JPEG snapshot'" "$?" "out=$OUT"
[[ $(last_req path) == /api/streamer/snapshot ]];  assert "snapshot hits streamer endpoint" "$?" "got: $(last_req path)"
head -c 2 "$SNAP" | od -An -tx1 | grep -q 'ff d8'; assert "snapshot file is a JPEG (magic)" "$?"

run_client raw POST /api/test/snapshot-fail value=1
[[ $RC -eq 0 ]];                                   assert "mock snapshot-fail on -> rc=0" "$?" "rc=$RC err=$ERR"
SNAP503="$WORK/fail.jpg"
run_client snapshot "$SNAP503"
[[ $RC -eq 4 ]];                                   assert "snapshot 503 -> exit 4" "$?" "rc=$RC"
grep -q 'returned HTTP 503' <<<"$ERR";             assert "snapshot 503 -> 'returned HTTP 503'" "$?" "err=$ERR"
grep -qi 'web UI\|wake' <<<"$ERR";                 assert "snapshot 503 -> hints at waking the stream" "$?" "err=$ERR"
[[ ! -f "$SNAP503" ]];                             assert "snapshot 503 -> no partial file left behind" "$?" "file still present"
run_client raw POST /api/test/snapshot-fail value=0
[[ $RC -eq 0 ]];                                   assert "mock snapshot-fail off -> rc=0" "$?" "rc=$RC err=$ERR"

# ===========================================================================
section "raw escape hatch"

reset_env; configured_env
run_client raw POST /api/hid/reset
[[ $RC -eq 0 ]];                                   assert "raw POST /api/hid/reset -> rc=0" "$?" "rc=$RC err=$ERR"
[[ $(last_req method) == POST ]];                  assert "raw forwards method" "$?"
[[ $(last_req path) == /api/hid/reset ]];          assert "raw forwards path" "$?" "got: $(last_req path)"
[[ -z $(last_req query) ]];                        assert "raw: no K=V -> empty query" "$?" "got: [$(last_req query)]"

run_client raw GET /api/info a=1 b=2
[[ $RC -eq 0 ]];                                   assert "raw multi-param -> rc=0" "$?" "rc=$RC err=$ERR"
[[ $(last_req query) == "a=1&b=2" ]];              assert "raw joins K=V with &" "$?" "got: $(last_req query)"

BINO="$WORK/bin.out"
run_client --out "$BINO" raw GET /api/streamer/snapshot
[[ $RC -eq 0 ]];                                   assert "raw binary --out -> rc=0" "$?" "rc=$RC err=$ERR"
[[ -s "$BINO" ]];                                  assert "raw binary file written" "$?" "size=$(stat -c %s "$BINO" 2>/dev/null)"
grep -q 'saved binary to:' <<<"$OUT";              assert "raw binary stdout 'saved binary to:'" "$?" "out=$OUT"
head -c 2 "$BINO" | od -An -tx1 | grep -q 'ff d8'; assert "raw binary is a JPEG (magic)" "$?"

run_client raw GET /api/doesnotexist
[[ $RC -eq 4 ]];                                   assert "raw 404 -> exit 4" "$?" "rc=$RC"
grep -q 'returned HTTP 404' <<<"$ERR";             assert "raw 404 -> 'returned HTTP 404'" "$?" "err=$ERR"

# ===========================================================================
section "auth & network failures"

reset_env
T_URL="$GOOD_URL"; T_USER="$GOOD_USER"; T_PASS='wrong password'
run_client info
[[ $RC -eq 4 ]];                                   assert "bad password -> exit 4" "$?" "rc=$RC"
grep -q 'returned HTTP 401' <<<"$ERR";             assert "bad password -> 'returned HTTP 401'" "$?" "err=$ERR"

reset_env
T_URL="http://127.0.0.1:1"; T_USER="$GOOD_USER"; T_PASS="$GOOD_PASS"
run_client --timeout 2 info
[[ $RC -eq 4 ]];                                   assert "connection refused -> exit 4" "$?" "rc=$RC"
grep -q 'failed' <<<"$ERR";                        assert "network failure -> 'failed'" "$?" "err=$ERR"

reset_env; configured_env
run_client --timeout 1 raw GET /api/info slow=1
[[ $RC -eq 4 ]];                                   assert "slow endpoint + 1s timeout -> exit 4" "$?" "rc=$RC err=$ERR"

# ===========================================================================
section "trailing-slash base URL"

reset_env
run_client --base-url "$GOOD_URL/" --user "$GOOD_USER" --password "$GOOD_PASS" info
[[ $RC -eq 0 ]];                                   assert "trailing-slash base url; info works" "$?" "rc=$RC err=$ERR"
[[ $(last_req path) == /api/info ]];               assert "no double slash in request path" "$?" "got: $(last_req path)"

# ===========================================================================
printf '\n=====================================\n'
printf '  pikvm.sh integration: %d passed, %d failed\n' "$PASS" "$FAIL"
printf '=====================================\n'
[[ $FAIL -eq 0 ]]
