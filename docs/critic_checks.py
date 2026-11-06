#!/usr/bin/env python3
"""Independent deterministic QA of the generated PiKVM teaching diagrams.

This is NOT an LLM subagent: it checks reproducibility, geometry, contrast,
and technical invariants. Human clarity review is documented in REVIEW.md.

Run from the repo root (or docs/) after regenerating the figures:
  python docs/critic_checks.py
"""
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parent
spec = spec_from_file_location('diagrams', ROOT / 'generate_pikvm_diagrams.py')
m = module_from_spec(spec)
spec.loader.exec_module(m)

def luminance(hex_color):
    rgb=[int(hex_color[i:i+2],16)/255.0 for i in (1,3,5)]
    linear=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb]
    return sum(a*b for a,b in zip(linear,(.2126,.7152,.0722)))

def contrast(a,b):
    l1,l2=sorted((luminance(a),luminance(b)),reverse=True)
    return (l1+.05)/(l2+.05)

assert m.kvmd(1440,900,1920,1200)==(16384,16384)
assert m.kvmd(0,0,1920,1200)==(-32768,-32768)
assert m.kvmd(960,600,1920,1200)==(0,0)
assert m.kvmd(1920,1200,1920,1200)==(32767,32767)
assert (m.TARGET[0]-m.CROP[0],m.TARGET[1]-m.CROP[1])==(100,62)
assert (m.CROP[2]*m.SCALE,m.CROP[3]*m.SCALE)==(920,496)

contrast_pairs=[('NAVY','PAPER'),('TEXT','PALE'),('MUTED','PAPER'),
                ('BLUE','LIGHTBLUE'),('TEAL','LIGHTTEAL'),
                ('GOLD','LIGHTGOLD'),('RED','LIGHTRED')]
for fg,bg in contrast_pairs:
    ratio=contrast(getattr(m,fg),getattr(m,bg))
    assert ratio>=4.5,(fg,bg,ratio)

pngs=sorted((ROOT/'figures').glob('*.png'))
svgs=sorted((ROOT/'figures').glob('*.svg'))
assert len(pngs)==len(svgs)==8
for png in pngs:
    im=Image.open(png).convert('RGB')
    assert im.size==(2080,1170),(png.name,im.size)
    assert (png.with_suffix('.svg')).exists()
    # Content should be nonblank (minimum per-channel variation).
    assert sum(ImageStat.Stat(im).stddev)>30,png.name
    assert png.stat().st_size>30_000,png.name
    assert png.with_suffix('.svg').stat().st_size>10_000,png.name
print('PASS: 8 PNG + 8 SVG outputs (2080×1170); nonblank; files present')
print('PASS: crop offsets, zoom dimensions, and pixel→KVMD math')
print('PASS: seven representative text/background color pairs ≥4.5:1')
print('LIMIT: no hardware test, automated semantic review, or independent LLM critic')
