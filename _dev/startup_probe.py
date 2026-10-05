"""How long between "the music starts" and "the first picture is on screen"?

The user's report: "执行程序后，最开头画面还未加载出来，但音乐已经开始播放了". The player starts the audio and then
does its one-time sprite decode *inside* the first frame of the loop, so the gap is however long that
decode takes - and the song clock is running throughout it, which means the first frame drawn is not the
first frame of the song either. This measures the stages in the order `tui_live.main` runs them.

    python _dev/startup_probe.py                 the interactive start-up, 197x52
    python _dev/startup_probe.py --size 120x34
"""
from __future__ import annotations

import argparse
import gc
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
ap.add_argument("--size", default="197x52")
ap.add_argument("--start", type=float, default=0.0)
a = ap.parse_args()
c, _, r = a.size.partition("x")
cols, rows = int(c), int(r)
t0 = time.perf_counter()


def mark(label: str) -> float:
    global t0
    now = time.perf_counter()
    ms = (now - t0) * 1000
    print(f"  {ms:8.1f} ms   {label}")
    t0 = now
    return ms


mark("the process starts")
T.VAR[0] = "school"
T.SP = SP
SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
mark("tui_live + the variant are imported (already done by now)")
d = T.Data()
mark(f"Data() - the lyric timeline, {len(d.lines)} lines")
print("loading the film's shot table...")
eng = T.Engine()
mark("Engine() - the film's 97-shot table")
gc.disable()
s = T.Screen(cols, rows)
sink = io.StringIO()
import school_fx as FX
mark("Screen()")
n = FX.warm(cols, rows)
mark(f"school_fx.warm() - {n} sprites + the basketball animation")
T.draw(s, d, eng, a.start, True, 24.0)
s.render_diff(sink)
mark("the first draw() + rasterise")
print(f"\ntotal: from the import of the modules to the first finished frame, "
      f"the user sees a blank screen for everything above 'the first draw()'")
