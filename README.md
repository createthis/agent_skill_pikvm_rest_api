# pikvm-rest-api — an Agent Skill

An [Agent Skills spec](https://agentskills.io/specification) skill that gives AI agents control over a PiKVM / KVMD (PiKVM Mini) hardware KVM through its REST API: read system and power state, send real keyboard/mouse input, type text, capture the screen, and control ATX power — with a zero-dependency bash + curl client.

## Why

Agents that need to operate a remote machine (a lab Mac, a server, a locked-down workstation) through a hardware KVM have no built-in path: the PiKVM web UI is a browser app, not an API. The KVMD daemon, however, exposes a clean JSON REST API (`/api/info`, `/api/atx`, `/api/hid/*`, `/api/streamer/snapshot`). This skill wraps it so an agent can type into the target machine, click its screen, take a snapshot, power-cycle it, and recover from lock screens — all from the shell.

The skill in one sentence: **drive the machine behind your PiKVM via the KVMD REST API, with endpoint and credentials resolved at runtime — never hardcoded, never a default host.**

## Configuration (the portable part)

The skill is fully parameterized and ships **no URL and no credentials of any kind**. Everything is resolved at runtime, first match wins:

1. `--base-url` / `--user` / `--password` flags (one-off)
2. `PIKVM_URL` / `PIKVM_USER` / `PIKVM_PASSWORD` environment variables
3. `pikvm.local` next to the skill (gitignored; see `pikvm.example`), or `~/.config/pikvm/endpoint`

TLS: PiKVM usually ships a self-signed cert. Set `PIKVM_INSECURE=true` (or `--insecure`) to skip verification, or point `PIKVM_CA` at a CA bundle.

That is what keeps the repo public-safe: your KVM's internal DNS name and password live in your env vars or your gitignored local file, and the public copy works for anyone who points it at their own PiKVM.

## Contents

```
pikvm-rest-api/
├── SKILL.md              # the skill (frontmatter + endpoint resolution + field notes)
├── pikvm.example         # committed config template (copy to pikvm.local)
├── scripts/
│   └── pikvm.sh          # zero-dependency bash + curl KVMD REST API client
└── references/
    └── KEYMAP.md         # full table of accepted key names (KVMD web keymap)
```

**How it activates:** the description is written so the agent invokes the skill whenever a task needs to drive a remote machine through a PiKVM — typing into it, clicking its screen, checking power/health, grabbing a screen capture, or power-cycling it. This is description-based model invocation per the Agent Skills spec, so the skill stays portable to any spec-compliant client. (OpenHands `triggers:` frontmatter is intentionally not used — it isn't part of the spec.)

## Install

### Project scope (applies to one repo)

```bash
cp -r pikvm-rest-api /path/to/your/repo/.agents/skills/
```

### User scope (applies to all your repos)

```bash
cp -r pikvm-rest-api ~/.agents/skills/
```

Then start a new agent conversation so the skill catalog is rebuilt. In OpenHands you can also verify under **Customize > Skills** — `pikvm-rest-api` should appear and be enabled.

### Point it at your KVM

```bash
export PIKVM_URL=https://your-kvm-host
export PIKVM_USER=admin
export PIKVM_PASSWORD='your-password'
export PIKVM_INSECURE=true        # self-signed cert (the PiKVM default)
```

…or in the skill directory:

```bash
cp pikvm-rest-api/pikvm.example pikvm-rest-api/pikvm.local
# edit PIKVM_URL / PIKVM_USER / PIKVM_PASSWORD
```

## The rules (short version)

- State: `info`, `power`, `hid` — read the KVM/host and check before acting.
- Input: `key`, `shortcut`, `type`, `click`, `move`, `wheel` — real HID events on the target. Key names are the KVMD *web* keymap (`KeyA`, `MetaLeft`, `Digit1`, …), not evdev or X11 names — see `references/KEYMAP.md`.
- Power: `power-on`, `power-off`, `power-reset` — confirm intent first; these are destructive.
- Screen: `snapshot /tmp/screen.jpg` — JPEG of the target; 503s while the video stream is offline (open the PiKVM web UI once to wake it).
- Escape hatch: `raw METHOD PATH K=V ...` for any KVMD endpoint. The API uses **query params**, not form bodies (except `POST /api/hid/print`).
- **No default host.** If nothing is configured, say so and ask for the KVM's address and credentials — never assume a host.

## Spec compliance

Valid against the Agent Skills spec: `name` matches the parent directory, lowercase-hyphen naming, required `name` + `description` frontmatter, description ≤ 1024 chars, body well under 500 lines. Optional spec fields used: `compatibility` (requires bash/curl + network) and `metadata` (author, version). No non-spec fields, so the skill is portable to any Agent Skills client. Validate with `skills-ref validate ./pikvm-rest-api`.
