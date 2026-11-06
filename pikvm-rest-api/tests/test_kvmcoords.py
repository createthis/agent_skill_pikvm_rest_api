#!/usr/bin/env python3
"""Unit tests for scripts/kvmcoords.py.

stdlib `unittest` only. The CLI is exercised as a subprocess
(`[sys.executable, SCRIPT, ...]`) so exit codes, stdout and stderr are
observed exactly as a shell user would see them. SCRIPT is resolved
relative to this file, so the suite does not depend on the CWD.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "kvmcoords.py"

# Pillow is only used here to *build* the fixture images; the script under
# test reads PNG/JPEG/GIF headers itself and never imports PIL. It is
# imported lazily inside setUpClass so a missing Pillow skips (not errors)
# only the image-based tests.
Image = None
try:
    from PIL import Image
except ImportError:  # pragma: no cover
    pass


def load_kvmcoords():
    """Import kvmcoords.py by path (it is not an importable package)."""
    spec = importlib.util.spec_from_file_location("kvmcoords", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cli(*args):
    """Run the script in a subprocess; return the CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *[str(a) for a in args]],
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestFracToKvmHelper(unittest.TestCase):
    """Direct tests of the importable frac_to_kvm() helper."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_kvmcoords()

    def test_quadrant_offsets(self):
        self.assertEqual(self.mod.frac_to_kvm(0.75, 0.25, 65536), (16384, -16384))

    def test_center_is_zero(self):
        self.assertEqual(self.mod.frac_to_kvm(0.5, 0.5, 65536), (0, 0))

    def test_other_corners_and_quadrants(self):
        self.assertEqual(self.mod.frac_to_kvm(0.0, 0.0, 65536), (-32768, -32768))
        self.assertEqual(self.mod.frac_to_kvm(1.0, 1.0, 65536), (32768, 32768))
        self.assertEqual(self.mod.frac_to_kvm(0.25, 0.75, 65536), (-16384, 16384))

    def test_custom_span(self):
        self.assertEqual(self.mod.frac_to_kvm(1.0, 0.0, 32768), (16384, -16384))


class TestPixelMath(unittest.TestCase):
    """Pixel -> KVMD conversion on an explicit 1920x1200 frame (span 65536)."""

    def _move(self, x, y, *extra):
        r = run_cli(x, y, "--width", 1920, "--height", 1200, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_center(self):
        self.assertEqual(self._move(960, 600),
                         "move 0 0   # pixel (960, 600) of 1920x1200")

    def test_upper_left_quadrant(self):
        self.assertEqual(self._move(75, 42),
                         "move -30208 -30474   # pixel (75, 42) of 1920x1200")

    def test_near_center_quadrant(self):
        self.assertEqual(self._move(118, 95),
                         "move -28740 -27580   # pixel (118, 95) of 1920x1200")

    def test_lower_right_quadrant(self):
        self.assertEqual(self._move(1440, 900),
                         "move 16384 16384   # pixel (1440, 900) of 1920x1200")

    def test_top_left_corner_clamps_to_neg_range(self):
        self.assertEqual(self._move(0, 0),
                         "move -32768 -32768   # pixel (0, 0) of 1920x1200")

    def test_fractional_input(self):
        r = run_cli(0.75, 0.75, "--frac", "--width", 1920, "--height", 1200)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(),
                         "move 16384 16384   # pixel (0.75, 0.75) of 1920x1200")

    def test_reverse_from_kvmd(self):
        r = run_cli(16384, 16384, "--from", "--width", 1920, "--height", 1200)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("pixel (1440, 900)", r.stdout)
        self.assertIn("of 1920x1200", r.stdout)
        self.assertIn("KVMD (16384, 16384)", r.stdout)

    def test_json_output(self):
        r = run_cli(1440, 900, "--width", 1920, "--height", 1200, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        # Required keys.
        for key in ("to_x", "to_y", "pixel", "frame"):
            self.assertIn(key, data)
        self.assertEqual(data["to_x"], 16384)
        self.assertEqual(data["to_y"], 16384)
        # pixel/frame are emitted as JSON lists.
        self.assertEqual(list(data["pixel"]), [1440.0, 900.0])
        self.assertEqual(list(data["frame"]), [1920, 1200])
        self.assertEqual(data["span"], 65536.0)

    def test_out_of_range_pixel_errors(self):
        r = run_cli(1920, 0, "--width", 1920, "--height", 1200)
        self.assertEqual(r.returncode, 1)
        self.assertIn("outside", r.stderr)

    def test_span_override(self):
        r = run_cli(1440, 900, "--width", 1920, "--height", 1200, "--span", 32768)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(),
                         "move 8192 8192   # pixel (1440, 900) of 1920x1200")


class TestAutoSizeFromImage(unittest.TestCase):
    """W/H auto-detected from a real image file header (no --width/--height)."""

    def setUp(self):
        if Image is None:
            self.skipTest("Pillow not available to build fixtures")
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        Image.new("RGB", (1920, 1200), (120, 40, 200)).save(self.dir / "full.png", "PNG")
        Image.new("RGB", (1920, 1200), (120, 40, 200)).save(self.dir / "full.jpg", "JPEG")
        Image.new("RGB", (320, 240), (0, 200, 100)).save(self.dir / "small.png", "PNG")

    def _move(self, x, y, image):
        r = run_cli(image, x, y)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_png_size_detected(self):
        self.assertEqual(self._move(1440, 900, self.dir / "full.png"),
                         "move 16384 16384   # pixel (1440, 900) of 1920x1200")

    def test_jpeg_size_detected(self):
        self.assertEqual(self._move(1440, 900, self.dir / "full.jpg"),
                         "move 16384 16384   # pixel (1440, 900) of 1920x1200")

    def test_small_png_size_detected(self):
        self.assertEqual(self._move(160, 120, self.dir / "small.png"),
                         "move 0 0   # pixel (160, 120) of 320x240")


class TestArgErrors(unittest.TestCase):
    def test_no_args(self):
        r = run_cli()
        self.assertEqual(r.returncode, 2)

    def test_x_y_but_no_dimensions(self):
        r = run_cli(100, 100)
        self.assertEqual(r.returncode, 2)

    def test_non_numeric_junk(self):
        r = run_cli("abc", "def", "--width", 1920, "--height", 1200)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
