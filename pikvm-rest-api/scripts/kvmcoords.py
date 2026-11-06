#!/usr/bin/env python3
r"""kvmcoords.py — convert between screenshot pixels and KVMD absolute-mouse
coordinates. Zero dependencies (stdlib only).

Background
----------
`pikvm.sh move X Y` does NOT take screen pixels. KVMD absolute-mouse mode uses a
center-origin coordinate space: (0,0) is the screen center and X/Y span roughly
-32768..32767, remapped onto the full display. To click the point you identified
in a snapshot, convert the pixel to a fraction of the frame (0 = left/top edge,
1 = right/bottom edge), center it, and scale:

    to_x = round((px / W - 0.5) * span)
    to_y = round((py / H - 0.5) * span)

with the default span of 65536 (the observed KVMD convention; override with
--span if you are calibrating a device whose mapping differs).

W/H are the snapshot dimensions. This tool auto-detects them from the JPEG/PNG
file header (no Pillow needed) — or pass --width/--height.

Examples
--------
  # pixel (75,42) on a 1920x1200 capture -> "move" arguments
  kvmcoords.py snap.jpg 75 42
  # fractional coordinates (7.8% from left, 3.3% from top)
  kvmcoords.py snap.jpg --frac 0.078 0.033
  # inverse: what pixel does KVMD (205,437) land on? (verify a mis-click)
  kvmcoords.py snap.jpg --from 205 437

Output is a single machine-readable line on stdout, e.g.
  move 205 437   # pixel (966, 608) of 1920x1200
so it can be parsed:

  args=$(python3 scripts/kvmcoords.py snap.jpg 75 42 | sed -n 's/^move \([-0-9]*\) \([-0-9]*\).*/\1 \2/p')
  scripts/pikvm.sh move $args
"""

import argparse
import json
import struct
import sys

DEFAULT_SPAN = 65536


def img_size(path):
    """Return (width, height) of a PNG, JPEG, or GIF file, or (None, None)."""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
            if head.startswith(b"\x89PNG\r\n\x1a\n"):
                w, h = struct.unpack(">II", head[16:24])
                return w, h
            if head[:3] == b"\xff\xd8\xff":
                f.seek(2)
                while True:
                    b = f.read(1)
                    if not b:
                        return None, None
                    if b != b"\xff":
                        continue
                    marker = f.read(1)[0]
                    if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                        f.read(3)
                        h, w = struct.unpack(">HH", f.read(4))
                        return w, h
                    if marker == 0xD9:
                        return None, None
                    if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                        continue
                    if marker == 0xDA:  # start of scan, no SOF seen
                        return None, None
                    ln = struct.unpack(">H", f.read(2))[0]
                    f.seek(ln - 2, 1)
            if head[:4] == b"GIF8":
                w, h = struct.unpack("<HH", head[6:10])
                return w, h
    except OSError:
        pass
    return None, None


def frac_to_kvm(fx, fy, span):
    return (round((fx - 0.5) * span), round((fy - 0.5) * span))


def main():
    ap = argparse.ArgumentParser(
        description="Convert screenshot pixels (or fractions) to KVMD "
                    "absolute-mouse coordinates for `pikvm.sh move`.")
    ap.add_argument("image", nargs="?",
                    help="snapshot image (JPEG/PNG/GIF) whose size gives W/H")
    ap.add_argument("x", nargs="?", type=float)
    ap.add_argument("y", nargs="?", type=float)
    ap.add_argument("--frac", action="store_true",
                    help="treat x y as fractions of the frame (0..1) instead of pixels")
    ap.add_argument("--from", dest="from_kvmd", action="store_true",
                    help="reverse: x y are KVMD coords; print the target pixel")
    ap.add_argument("--span", type=float, default=DEFAULT_SPAN,
                    help="full-range size of the KVMD space (default: 65536)")
    ap.add_argument("--width", type=int, help="frame width (overrides image)")
    ap.add_argument("--height", type=int, help="frame height (overrides image)")
    ap.add_argument("--json", action="store_true", help="JSON output")
    a = ap.parse_args()

    if a.x is None or a.y is None:
        ap.error("x and y are required")

    # Resolve frame dimensions: explicit flags win, else read from the image.
    w, h = a.width, a.height
    if (w is None or h is None) and a.image:
        iw, ih = img_size(a.image)
        if iw is None:
            sys.exit("error: could not read dimensions of %s (unknown format); "
                     "pass --width/--height explicitly" % a.image)
        w, h = w or iw, h or ih
    if w is None or h is None:
        ap.error("need frame dimensions: give an image and/or --width/--height")

    if a.from_kvmd:
        px = (a.x / a.span + 0.5) * w
        py = (a.y / a.span + 0.5) * h
        out = {"to_x": a.x, "to_y": a.y, "pixel": (round(px), round(py)),
               "frame": [w, h]}
        human = "KVMD (%d, %d) -> pixel (%d, %d) of %dx%d" % (
            a.x, a.y, out["pixel"][0], out["pixel"][1], w, h)
    else:
        if a.frac:
            fx, fy = a.x, a.y
        else:
            fx, fy = a.x / w, a.y / h
            if not (0.0 <= fx < 1.0 and 0.0 <= fy < 1.0):
                sys.exit("error: pixel (%g, %g) is outside a %dx%d frame; "
                         "re-measure from a fresh snapshot" % (a.x, a.y, w, h))
        tx, ty = frac_to_kvm(fx, fy, a.span)
        # Clamp to the signed 16-bit space KVMD accepts.
        tx = max(-32768, min(32767, tx))
        ty = max(-32768, min(32767, ty))
        out = {"to_x": tx, "to_y": ty, "pixel": (a.x, a.y), "frame": [w, h],
               "span": a.span}
        human = "move %d %d   # pixel (%g, %g) of %dx%d" % (tx, ty, a.x, a.y, w, h)

    if a.json:
        print(json.dumps(out))
    else:
        print(human)


if __name__ == "__main__":
    main()
