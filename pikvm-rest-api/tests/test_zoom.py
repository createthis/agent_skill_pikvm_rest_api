#!/usr/bin/env python3
"""Unit tests for scripts/zoom.py (requires Pillow; stdlib `unittest`).

The CLI is exercised as a subprocess (`[sys.executable, SCRIPT, ...]`). A
single synthetic input image (100x60, left half pure red, right half pure
blue) is built once and reused, saved as both PNG and JPEG in a temp dir.
SCRIPT is resolved relative to this file, so the suite does not depend on
the CWD.
"""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "zoom.py"

Image = None
try:
    from PIL import Image
except ImportError:  # pragma: no cover
    pass

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def run_cli(*args):
    """Run the script in a subprocess; return the CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *[str(a) for a in args]],
        capture_output=True,
        text=True,
        timeout=30,
    )


def rgb_at(path, fx, fy):
    """Pixel (r, g, b) at fractional coords fx, fy (0..1) of the image."""
    with Image.open(path) as im:
        w, h = im.size
        px = im.convert("RGB").load()
        return px[round(fx * (w - 1)), round(fy * (h - 1))]


def assert_reddish(test, px, msg=""):
    r, g, b = px
    test.assertGreater(r, 150, "not red-ish: %s %s" % (px, msg))
    test.assertLess(g, 80, "not red-ish: %s %s" % (px, msg))
    test.assertLess(b, 80, "not red-ish: %s %s" % (px, msg))


def assert_bluish(test, px, msg=""):
    r, g, b = px
    test.assertGreater(b, 150, "not blue-ish: %s %s" % (px, msg))
    test.assertLess(r, 80, "not blue-ish: %s %s" % (px, msg))
    test.assertLess(g, 80, "not blue-ish: %s %s" % (px, msg))


@unittest.skipIf(Image is None, "Pillow required to build fixtures")
class TestZoom(unittest.TestCase):
    """One synthetic 100x60 fixture: left half red, right half blue."""

    W, H = 100, 60

    @staticmethod
    def _build_fixture():
        """The single shared fixture image, built once per process."""
        if getattr(TestZoom, "_fixture", None) is None:
            img = Image.new("RGB", (TestZoom.W, TestZoom.H), (255, 0, 0))
            img.paste((0, 0, 255), box=(TestZoom.W // 2, 0,
                                         TestZoom.W, TestZoom.H))
            TestZoom._fixture = img
        return TestZoom._fixture

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        # Save the one shared fixture as PNG and JPEG for this test.
        self.png = self.dir / "in.png"
        self.jpg = self.dir / "in.jpg"
        self._build_fixture().save(self.png, "PNG")
        self._build_fixture().save(self.jpg, "JPEG", quality=95)

    def _out(self, name):
        return self.dir / name

    def test_crop_half_scale_2(self):
        # box 0,0 50x30 crops only the RED left half -> the whole 100x60
        # output is red. (The spec also mentioned a "blue-ish right region"
        # here, but a box covering x in [0,50) never reaches the blue half;
        # see the task report for details.)
        out = self._out("z1.png")
        r = run_cli(self.png, out, "--box", 0, 0, 50, 30, "--scale", 2)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout.strip(),
                         r"^box 0,0 50x30 -> 100x60  \(scale 2\)  .*\.png$")
        with Image.open(out) as im:
            self.assertEqual(im.size, (100, 60))
        assert_reddish(self, rgb_at(out, 0.5, 0.5), "left/center of z1")

    def test_scale_1_right_half_all_blue(self):
        out = self._out("z2.png")
        r = run_cli(self.png, out, "--box", 50, 0, 50, 30, "--scale", 1)
        self.assertEqual(r.returncode, 0, r.stderr)
        with Image.open(out) as im:
            self.assertEqual(im.size, (50, 30))
        assert_bluish(self, rgb_at(out, 0.5, 0.5), "center of z2")

    def test_non_integer_scale(self):
        out = self._out("z3.png")
        r = run_cli(self.png, out, "--box", 10, 10, 33, 21, "--scale", 3)
        self.assertEqual(r.returncode, 0, r.stderr)
        with Image.open(out) as im:
            self.assertEqual(im.size, (99, 63))

    def test_partially_outside_box_clipped(self):
        # box 95,-5 20x20 on a 100x60 image clips to (95,0)-(100,15) = 5x15,
        # then scale 2 -> 10x30.
        out = self._out("z4.png")
        r = run_cli(self.png, out, "--box", 95, -5, 20, 20, "--scale", 2)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("-> 10x30", r.stdout)
        with Image.open(out) as im:
            self.assertEqual(im.size, (10, 30))

    def test_fully_outside_box_errors(self):
        out = self._out("z5.png")
        r = run_cli(self.png, out, "--box", 200, 200, 10, 10)
        self.assertEqual(r.returncode, 1)
        self.assertIn("outside", r.stderr)
        self.assertFalse(out.exists())

    def test_missing_box_errors(self):
        r = run_cli(self.png, self._out("z6.png"))
        self.assertEqual(r.returncode, 2)

    def test_nonexistent_input_errors(self):
        r = run_cli(self.dir / "nope.jpg", self._out("z7.png"),
                    "--box", 0, 0, 10, 10)
        self.assertEqual(r.returncode, 1)
        self.assertIn("cannot open", r.stderr)

    def test_jpeg_input_end_to_end(self):
        # Same geometry as the PNG case but reading from the JPEG source.
        out = self._out("z8.png")
        r = run_cli(self.jpg, out, "--box", 0, 0, 50, 30, "--scale", 2)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout.strip(),
                         r"^box 0,0 50x30 -> 100x60  \(scale 2\)  .*\.png$")
        with Image.open(out) as im:
            self.assertEqual(im.size, (100, 60))
        # JPEG is lossy but quality=95 keeps the halves clearly red.
        assert_reddish(self, rgb_at(out, 0.5, 0.5), "center of z8 (jpg)")

    def test_output_is_real_png(self):
        out = self._out("z9.png")
        r = run_cli(self.png, out, "--box", 0, 0, 20, 20, "--scale", 2)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(out.exists())
        self.assertEqual(out.read_bytes()[:8], PNG_MAGIC)


if __name__ == "__main__":
    unittest.main()
