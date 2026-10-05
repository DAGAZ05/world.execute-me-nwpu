"""Ad-hoc: measure the illustration's own geometry (ink box, head, shoulders, face).

    python _dev/measure_art.py

Prints the alpha ink box and the per-row ink extent, so a crop can be written down from
measurements instead of guessed from "a head is the top quarter".
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "player" / "_tools"))
import mascot_glyphs as MG      # noqa: E402

im = MG.rgba()
w, h = im.size
a = im.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
print(f"canvas {w}x{h}   ink box {MG.ink_box()}   face_region {MG.face_region()}")
print(f"skin tone {MG.skin_tone()}")

data = a.load()
print("\nrow    x0   x1  width   (every 10th row, to 60 % of the canvas)")
prev = None
for y in range(0, int(h * 0.60), 10):
    xs = [x for x in range(w) if data[x, y]]
    if not xs:
        print(f"{y:4}     -    -      -")
        continue
    wdt = xs[-1] - xs[0]
    jump = "" if prev is None or abs(wdt - prev) < 40 else f"   <- width jumps by {wdt - prev:+d}"
    print(f"{y:4} {xs[0]:5} {xs[-1]:4} {wdt:6}{jump}")
    prev = wdt

# the head's own columns only, to find where the chin is: the shoulders arrive at y~200 and make the
# full-row extent useless for that question
print("\nhead columns only (x 90..370): row  x0   x1  width")
for y in range(120, 320, 8):
    xs = [x for x in range(90, 371) if data[x, y]]
    print(f"{y:4} {xs[0]:5} {xs[-1]:4} {xs[-1] - xs[0]:6}" if xs else f"{y:4}  (none)")
