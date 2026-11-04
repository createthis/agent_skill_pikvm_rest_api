---
name: pikvm-rest-api
description: "Control a PiKVM / KVMD (PiKVM Mini) hardware KVM over its REST API — read system/power state, send keyboard and mouse input, type text, take screen snapshots, and control ATX power. Use when a task needs to drive a remote machine through a PiKVM: typing into a target machine, clicking its screen, checking its power or health, grabbing a screen capture, or recovering a locked/unresponsive machine by sending input or power-cycling it. Resolves the KVM's base URL, username, and password at runtime from environment variables or a local config file; nothing is hardcoded in the skill."
compatibility: "Requires bash and curl (and ideally jq, for pretty output) and network access to a PiKVM/KVMD instance. No other dependencies."
metadata:
  author: createthis
  version: "1.0"
---

# PiKVM / KVMD REST API control

Drive a hardware KVM (PiKVM Mini 4 / any KVMD-based device) from the command line: inspect the KVM and the machine behind it, send real keyboard/mouse input, type text, capture the screen, and control ATX power. This skill wraps the KVMD HTTP REST API with a zero-dependency bash client so an agent can operate the target machine without a browser.

## Endpoint & credential resolution

Nothing is hardcoded. The base URL, username, and password are resolved at runtime, first match wins per value:

1. `--base-url URL`, `--user USER`, `--password PASS` flags (one-off override)
2. `PIKVM_URL`, `PIKVM_USER`, `PIKVM_PASSWORD` environment variables
3. `pikvm.local` in the skill directory (see `pikvm.example`), or `~/.config/pikvm/endpoint`

Extra TLS options (also env-overridable): `PIKVM_INSECURE=true` (or `--insecure`) to skip cert verification for self-signed certs; `PIKVM_CA=/path/bundle` (or `--ca`) to trust a specific CA. `PIKVM_TIMEOUT` is not read — use `--timeout SECS`.

The base URL is the KVM's origin only — e.g. `https://your-kvm-host` — with no trailing slash and no `/api` path. If the script reports "no KVM base URL configured" or "username and password are required", check this machine's AGENTS.md or memory for the KVM's address and pass them via the flags or env vars. There is deliberately **no default instance**: the KVM address and credentials are private to the user's network.

## Usage

Run the client from the skill directory; relative examples below assume you `cd` into it. Pass global options before the command.

```bash
# read-only
scripts/pikvm.sh info                 # KVM + host system info (KVMD version, platform, uptime, health)
scripts/pikvm.sh power                # ATX power state (enabled, busy, LED state, available actions)
scripts/pikvm.sh hid                  # keyboard/mouse state (online, absolute/relative, LED state)

# input (real events on the target machine)
scripts/pikvm.sh key Escape                          # tap one key
scripts/pikvm.sh shortcut MetaLeft KeyA               # press a key chord (⌘A on macOS)
scripts/pikvm.sh type "echo hello"                    # type text via /api/hid/print
scripts/pikvm.sh click left                           # mouse click: left | right | middle
scripts/pikvm.sh move 512 384                         # absolute mouse move to pixel (x, y)
scripts/pikvm.sh wheel 0 -3                           # scroll wheel by (delta_x, delta_y)

# power control
scripts/pikvm.sh power-on
scripts/pikvm.sh power-off
scripts/pikvm.sh power-reset                         # hard reset

# screen capture
scripts/pikvm.sh snapshot /tmp/screen.jpg            # JPEG of the target screen

# generic escape hatch
scripts/pikvm.sh raw POST /api/hid/reset             # any method + path + query params
```

Override endpoint/creds for a one-off call:

```bash
scripts/pikvm.sh --base-url https://your-kvm --user admin --password '...' --insecure info
```

JSON endpoints print to stdout pretty-printed (when `jq` is available); confirmation messages and errors go to stderr. Non-zero exit codes: `2` usage, `3` not configured, `4` HTTP/network failure.

## Field notes (hard-won)

- **TLS is usually self-signed.** PiKVM ships a self-signed cert by default, so HTTPS needs `--insecure` (env `PIKVM_INSECURE=true`) unless the user has installed a CA-signed or internal-CA cert (then use `--ca`). If you get an `SSL certificate problem`, this is why — it is expected on a LAN KVM, not a security failure.
- **The API uses query params, not a form body.** e.g. `POST /api/hid/events/send_key?key=Escape`, `POST /api/hid/events/send_shortcut?keys=MetaLeft,KeyA`. The only endpoint that takes a body is `POST /api/hid/print` (raw text, with a `?limit=` cap). The client handles this; use `raw` if you hand-roll a request and it 400s.
- **Key names are the KVMD web keymap, not evdev/X11 names.** `KeyA`…`KeyZ`, `Digit1`…`Digit0`, `Enter`, `Escape`, `Tab`, `Space`, `F1`–`F24`, `MetaLeft`/`MetaRight` (⌘/Super), `ControlLeft`/`ControlRight`, `AltLeft`/`AltRight` (⌥/Option), `ShiftLeft`/`ShiftRight`, `NumpadEnter`, `ArrowUp`… etc. A full table is in [references/KEYMAP.md](references/KEYMAP.md). evdev-style names like `Super_L`, `Meta_L`, or `KEY_A` are **rejected** with a `ValidatorError`.
- **Shortcuts need modifier+key, comma-joined.** `shortcut MetaLeft KeyV` = ⌘V. Order is press-first, release-reverse, so it reads as a real chord.
- **Mouse is absolute on this class of device.** `move X Y` targets a pixel in the stream resolution (check `hid` → `mouse.absolute` and the streamer resolution). `wheel` deltas are signed (positive = up/right).
- **The video stream may be offline → `snapshot` 503s.** `/api/streamer/snapshot` returns `UnavailableError` (HTTP 503) when the streamer is not running (no active viewer, or the target display is asleep). Input and state endpoints still work. To recover: connect a viewer once (the PiKVM web UI) to wake the stream, ensure the target's display is on, then retry. `--timeout` up to ~60s helps on a busy Pi-based KVM.
- **Pi-based KVMs (CM4/CM5) are sometimes slow.** A PiKVM Mini can intermittently time out on `/api/hid/*` under load. The default 30s timeout is usually fine; bump it with `--timeout 60` if you see curl error 28.
- **Read state before you act.** `power` tells you if the machine is on (`leds.power`) and which ATX actions are enabled (`acts`); `hid` tells you keyboard/mouse are online before you send input. `info` confirms you reached the right KVM (check `system.kvmd.version` and `hw.platform.model`).

## Safety

You are sending **real input and power events to a real machine**. Before destructive actions:
- `power-off` / `power-reset` will interrupt whatever the target is doing — confirm intent first.
- `type` and `key`/`shortcut` act on the focused element of the target OS; a stray click or keystroke can modify the target. Prefer read-only (`info`, `power`, `hid`, `snapshot`) to observe, then act deliberately.
- Prefer `key`/`shortcut` for discrete actions and `type` for text; verify with a `snapshot` afterward when the result matters.

## Privacy

The base URL, username, and password are private to the user's network and are never hardcoded in this skill — they come from env vars or the user's local, gitignored config. This skill makes network calls only to the resolved KVM and never to any default or third-party host.
