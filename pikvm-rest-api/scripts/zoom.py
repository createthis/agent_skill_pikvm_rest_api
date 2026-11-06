#!/usr/bin/env python3
"""zoom.py — crop a region of a PiKVM snapshot and upscale it so small UI
targets (buttons, menu items, window controls, terminal text) are readable.

Why this exists: a full-frame 1920x1200 snapshot is too low-resolution to
reliably read small text or pin the exact center of a small button. Cropping
and upscaling 2-4x is the most effective way to measure a click target
accurately.

Dependency: Pillow (import PIL). Install with:
    pip install pillow

Usage
-----
  zoom.py in.jpg out.png --box X Y W H [--scale 3]

X, Y are the top-left pixel of the crop (from the full snapshot); W, H are the
crop size in pixels. The crop is resized by --scale (integer >= 1, default 3)
using LANCZOS and saved as PNG.

Example: the "More Info..." button in an About This Mac panel was around
pixel (966, 608). Crop a box around it and zoom 5x:
  zoom.py snap.jpg more.png --box 890 590 150 45 --scale 5

Output (stdout) is a single line with the source box and the zoomed
dimensions, so it can be logged:
  box 890,590 150x45 -> 750x225  (scale 5)  more.png
"""

import argparse
import sys


def main():
    ap = argparse.ArgumentParser(
        description="Crop + upscale a region of a snapshot image (Pillow).")
    ap.add_argument("in_image", help="source snapshot (JPEG/PNG/...)")
    ap.add_argument("out_image", help="output image (PNG recommended)")
    ap.add_argument("--box", type=int, nargs=4, metavar=("X", "Y", "W", "H"),
                    help="crop rectangle: left, top, width, height (pixels)")
    ap.add_argument("--scale", type=float, default=3.0,
                    help="upscale factor (default: 3)")
    a = ap.parse_args()

    if not a.box or len(a.box) != 4:
        ap.error("--box X Y W H is required")

    try:
        from PIL import Image
    except ImportError:
        sys.exit("error: Pillow is required (pip install pillow)")

    x, y, w, h = a.box
    try:
        img = Image.open(a.in_image)
    except OSError as e:
        sys.exit("error: cannot open %s: %s" % (a.in_image, e))

    W, H = img.size
    x0, y0 = max(0, x), max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        sys.exit("error: box (%d, %d, %d, %d) is outside the %dx%d image" %
                 (x, y, w, h, W, H))
    crop = img.crop((x0, y0, x1, y1))
    crop = crop.resize((max(1, round(crop.width * a.scale)),
                        max(1, round(crop.height * a.scale))), Image.LANCZOS)
    crop.save(a.out_image)
    print("box %d,%d %dx%d -> %dx%d  (scale %g)  %s" %
          (x, y, w, h, crop.width, crop.height, a.scale, a.out_image))


if __name__ == "__main__":
    main()
