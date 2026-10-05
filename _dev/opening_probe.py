"""How long is each frame of the opening seconds? The flash events grow from nothing, and `sprite` is
cached per size, so a flash that resizes every frame decodes the PNG every frame.

    python _dev/opening_probe.py             the first 4 s at 24 fps, frame times
    python _dev/opening_probe.py --to 8
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402

ap = argparse.ArgumentParser(description=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--to", type=float, default=4.0)
ap.add_argument("--size", default="197x52")
ap.add_argument("--warm", action="store_true", help="run school_fx.warm first, as the player does")
ap.add_argument("--dry", action="store_true",
                help="also walk the schedule's rows into a throwaway screen, as the player does")
a = ap.parse_args()
c, _, r = a.size.partition("x")
cols, rows = int(c), int(r)

T.VAR[0] = "school"
T.SP = SP
SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
import school_gate as G
G.assume()
eng = T.Engine()
d = T.Data()
T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)
if a.warm:
    import school_fx as FX
    t0 = time.perf_counter()
    n = FX.warm(cols, rows)
    print(f"warm: {n} events in {time.perf_counter() - t0:.2f} s")
if a.dry:
    t0 = time.perf_counter()
    sw, sinkw = T.Screen(cols, rows), io.StringIO()
    n = 0
    for r_ in SP.shot_rows():
        if not r_.get("name"):
            continue
        T.draw(sw, d, eng, r_["at"] + 0.02, True, 0.0, None)
        sw.render_diff(sinkw)
        n += 1
    print(f"dry run: {n} frames in {time.perf_counter() - t0:.2f} s")

s = T.Screen(cols, rows)
sink = io.StringIO()
rows_out = []
t = 0.0
while t < a.to:
    t0 = time.perf_counter()
    T.draw(s, d, eng, t, True, 24.0)
    s.render_diff(sink)
    rows_out.append(((time.perf_counter() - t0) * 1000, t))
    t += 1 / 24.0
worst = sorted(rows_out, reverse=True)[:6]
print(f"{len(rows_out)} frames of the opening {a.to:.1f} s, 197x52"
      f"{' (warmed)' if a.warm else ' (cold)'}:")
print(f"  mean {sum(x for x, _ in rows_out) / len(rows_out):6.1f} ms   "
      f"over 41.7 ms: {sum(1 for x, _ in rows_out if x > 41.7)}")
for ms, tt in sorted(worst):
    print(f"    {ms:7.1f} ms at t={tt:5.2f}")
