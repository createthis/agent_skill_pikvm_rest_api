# Worked example (illustrative only)

The concrete scenario behind all eight walkthrough figures in the root
[`README.md`](../README.md) and in [`figures/`](figures/). The simulated screen
and every number below are **illustrative only** — the example machine and its
UI are simulated, not a hardware capture. The commands, endpoints, and
coordinate math match this repository's `pikvm-rest-api/scripts/` and
`pikvm-rest-api/references/`.

## The scenario

The simulated screen is **1920×1200**. The "Details" button center is at pixel
**(1440, 900)**. The optional crop starts at **(1340, 838)** and is
**230×124** pixels. Its crop-local target center is therefore **(100, 62)**.
A 4× upscale produces a **920×496** view.

## The command sequence

```bash
# Run from the installed pikvm-rest-api skill directory, once configured.
scripts/pikvm.sh info
scripts/pikvm.sh hid
scripts/pikvm.sh snapshot snap.jpg
python3 scripts/zoom.py snap.jpg crop.png --box 1340 838 230 124 --scale 4
python3 scripts/kvmcoords.py snap.jpg 1440 900
# => move 16384 16384   # pixel (1440, 900) of 1920x1200
scripts/pikvm.sh move 16384 16384
scripts/pikvm.sh click left
scripts/pikvm.sh snapshot after.jpg
# The agent visually checks after.jpg; if no effect, get a fresh image and re-measure.
```

## The coordinate transform

Native KVMD absolute-mouse transform with the default 65536 span:

```text
to_x = clamp(round((px / W - 0.5) * 65536), -32768, 32767)
to_y = clamp(round((py / H - 0.5) * 65536), -32768, 32767)
```

Worked through with the scenario numbers:

```text
to_x = round((1440 / 1920 - 0.5) * 65536) = round(16384) = 16384
to_y = round((900  / 1200 - 0.5) * 65536) = round(16384) = 16384
```

Sanity points (checked by `critic_checks.py`): the screen center (960, 600)
maps to KVMD (0, 0); the top-left corner (0, 0) maps to (−32768, −32768); the
bottom-right corner (1920, 1200) clamps to (32767, 32767).

## Notes on what the example demonstrates

- The diagrams depict a *possible* workflow, not a guarantee that every agent
  follows it. A fresh screenshot is needed for each click-sensitive action and
  each focus-changing event.
- The remote OS is not semantically inspected by this REST skill; it is
  operated from pixels and HID. A real target may have display scaling,
  cursor/mouse-mode issues, latency, or a locked screen.
- The simulated "Details" button is a harmless teaching example; real actions
  on a real machine can be irreversible.
