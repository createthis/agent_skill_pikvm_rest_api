# Driving the target machine's GUI (click / type / read the screen)

This reference is the working procedure for operating a desktop (macOS, Linux,
Windows) behind the KVM: clicking buttons and menu items, typing into fields
and terminals, and reading what's on screen. It exists so you do **not** have
to re-derive the coordinate math or re-experiment — follow the loop and the
recipes.

The `info` / `power` / `hid` / `snapshot` commands are in [SKILL.md](../SKILL.md).
This file covers the *mouse + screen* workflow on top of them.

## The core loop (do this for every interaction)

```
1. snapshot        -> a fresh JPEG of the target screen
2. zoom + measure  -> crop the region of interest, upscale it, read the target's
                      exact pixel center (px, py)
3. coords          -> convert (px, py) to KVMD move coordinates
4. move + click    -> position the cursor, then click
5. snapshot        -> verify the expected thing happened
```

**Rules that matter most:**
- **Always take a fresh snapshot before you act.** Never reuse an old screenshot
  — window layout, focus, and scroll position all shift between captures. If you
  are about to click, the coordinates must come from a snapshot taken *just now*.
- **Measure the target center from a zoomed crop, not the full frame.** A full
  1080p/720p frame is too low-res to read small text or pin a small button.
  Cropping + upscaling 2–5× is the single biggest accuracy win.
- **Verify the click with a follow-up snapshot.** A click that misses looks
  identical to one that lands until you look. When the result matters, look.
- **Confirm *which app got focus* via the menu bar.** After clicking a window's
  title bar, the OS menu bar (top-left) shows the front app's name. If you meant
  to focus Chrome but it says something else, your click hit a different window.

## Coordinates: pixels → KVMD

`pikvm.sh move X Y` does **not** take screen pixels. KVMD absolute-mouse mode is
center-origin: `(0,0)` = screen center, X/Y span about `−32768..32767` and are
remapped onto the full display. The conversion (default range 65536):

```
to_x = round((px / W − 0.5) × 65536)
to_y = round((py / H − 0.5) × 65536)
```

where `W×H` is the snapshot size. **You almost never do this by hand** — use
`scripts/kvmcoords.py`, which auto-reads W/H from the JPEG header:

```bash
# pixel (75,42) from a snapshot -> "move" args (auto W/H from the file)
python3 scripts/kvmcoords.py snap.jpg 75 42
#   ->  move -30206 -30474   # pixel (75, 42) of 1920x1200

# fractional target (7.8% from left, 3.3% from top)
python3 scripts/kvmcoords.py snap.jpg --frac 0.078 0.033

# reverse: where did a KVMD coord land, in pixels? (debugging a mis-click)
python3 scripts/kvmcoords.py snap.jpg --from 205 437
```

Capture the args in a one-liner and drive `pikvm.sh` directly:

```bash
cd <skill-dir>
read to_x to_y < <(python3 scripts/kvmcoords.py snap.jpg 75 42 \
                    | sed -n 's/^move \([-0-9]*\) \([-0-9]*\).*/\1 \2/p')
scripts/pikvm.sh move "$to_x" "$to_y"
sleep 1
scripts/pikvm.sh click left
```

If a device maps the range differently, pass `--span` to `kvmcoords.py`
(default 65536 is the observed KVMD convention).

## Reading the screen: zoom

`scripts/zoom.py` crops a box from a snapshot and upscales it so you can read
small text or measure a button center. Requires **Pillow** (`pip install
pillow`); everything else in the skill is zero-dependency.

```bash
# crop 150x45 around pixel (890,590), zoom 5x -> readable PNG
python3 scripts/zoom.py snap.jpg more.png --box 890 590 150 45 --scale 5
```

Workflow: snapshot → zoom the candidate region → *view* the PNG → read the
target's pixel center in the **original** coordinates (the box origin + the
target's offset within the box) → feed that to `kvmcoords.py`.

## Recipes

These are the recurring desktop interactions, in terms of the loop above.

### Click an item in a menu (e.g. an OS application menu)
1. Snapshot. The menu glyph is at the top-left corner of the screen.
2. `kvmcoords.py snap.jpg <glyph_px> <glyph_py>` → `move` → `click left`.
3. Snapshot — the menu is open. Menu items stack vertically below the glyph;
   the first item is ~28–34px below it.
4. Zoom if the label is ambiguous, measure the item's center, `move` → `click`.
5. Snapshot — verify.

### Close a window
The close control is the leftmost of the three traffic-light buttons at the
top-left of the window's title bar (macOS) or the × at the top-right
(Windows/Linux). Zoom the title-bar corner, measure the control's center,
`move` → `click left`, snapshot to confirm it's gone.

### Focus an app whose window is mostly covered
Do **not** click a spot you can't see is that window's title bar — it will
focus whatever is on top at that pixel. Instead: click a *visible* part of the
window, or use the OS's app switcher / the dock, then check the menu-bar app
name in a snapshot.

### Open the OS "About / System Information" panel
Open the OS app menu (recipe above) → click the "About This <computer>" item.
For the exact model identifier, prefer the terminal over the GUI (below) —
the "More Info…" button that leads to the identifier is small and the GUI path
is a long chain of tiny targets.

### Type into a terminal or text field
`pikvm.sh type "<text>"` sends real characters to the focused field — it is
reliable for commands and text. Use `key Enter` to submit, and `shortcut`
(`MetaLeft KeyA` = select-all on macOS, `ControlLeft KeyA` on Linux) for
chords. Always click the target field first and confirm focus with a snapshot.

### Get a fact about the machine — prefer the terminal
Opening a GUI panel and then a sub-panel and then a tiny "More Info…" button is
fragile. Opening a terminal and typing one command is deterministic:
- macOS: `system_profiler SPHardwareDataType | grep -E 'Model Identifier|Model Name|Serial'`
- Linux: `cat /etc/os-release; hostnamectl; lscpu | grep 'Model name'`

Read the output from a zoomed crop of the terminal.

## Hard-won lessons (why the rules are the rules)

- **The `power` endpoint can be wrong about "is it on".** On some setups the ATX
  power cable is not wired, so `power` reports the LED off and no actions — yet
  the machine is running. **The screen snapshot is the ground truth** for what
  state the target is in. Don't make decisions from `power` alone.
- **The target OS auto-locks after idle.** If a task involves long read/write
  pauses, macOS (and desktops generally) will lock the screen — the snapshot
  then shows a lock/login screen instead of the desktop. **If you see a lock
  screen, stop and tell the user.** Do not attempt to unlock it: you generally
  don't have the login credential, and trying to type a guess is both futile and
  disruptive. A locked machine is the safe state; finish what you can and report
  that the target is locked.
- **`snapshot` can 503 when the video stream is offline** (no active viewer /
  display asleep). See the SKILL.md note: open the KVM web UI once to wake the
  stream, then retry with a longer `--timeout`.
- **Measure from the fresh frame every time.** The same button moves when a
  window is dragged, a menu opens, or a window takes focus and re-lays-out.
  Re-derive coordinates from the current snapshot, not a previous one.
- **One off-by-a-few-pixels mis-derivation will click the window behind.** When
  several windows share a title-bar row, or a floating panel overlaps the target,
  a 5–10px error in your pixel estimate lands on the wrong window. Zoom to
  confirm the exact center before clicking small controls.
- **Small UI targets need the zoom step.** Buttons, menu items, and window
  controls are 10–20px tall at full-frame resolution — easy to mis-estimate by
  enough to miss. Always zoom small targets.
- **Send real input to a real machine.** Every `type`/`key`/`click`/`move` acts
  on whatever is focused. Prefer read-only first, act deliberately, verify after.

## Worked example (generic)

Goal: click a window's close button, on a 1920×1200 capture.

1. `snapshot screen.jpg`
2. The window's title bar top-left is at roughly pixel (120, 90). Zoom it:
   `zoom.py screen.jpg close.png --box 100 78 90 34 --scale 6`
3. View `close.png`; the red close button center sits ~18px right and ~17px down
   from the box origin → pixel (118, 95).
4. `kvmcoords.py screen.jpg 118 95` → `move −13025 −26364`
5. `move −13025 −26364` → `sleep 1` → `click left`
6. `snapshot after.jpg` → confirm the window is gone.
