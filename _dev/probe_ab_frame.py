"""Stable A/B: run the same frames N times, report the *median* of the medians.

`_dev/frame_budget.py` samples the whole song once, and `_dev/probe_frame_profile.py` wraps the
run in cProfile - both are fine for finding *where* time goes and useless for deciding whether a
change helped, because a single pass over this machine's frames varies by tens of percent (the
miniconda Python, a loaded desktop, a thermal ramp). Measured the hard way: the same unmodified
`put` reported 8.39 ms and 4.53 ms in two consecutive profile runs.

So this probe does one thing: it runs the same window `--rounds` times and prints the median, plus
the spread, so a claim like "put went from 8.4 to 4.5 ms" has something behind it.

    python _dev/probe_ab_frame.py --window 56.8,58.0 --rounds 7
    python _dev/probe_ab_frame.py --windows 14.0,16.0 61.0,62.0 147.0,148.0 195.0,196.0
"""
from __future__ import annotations

import argparse
import gc
import io
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

DEFAULT = ["14.0,16.0", "56.8,58.0", "61.0,62.0", "147.0,148.0", "195.0,196.0"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", help="LO,HI seconds")
    ap.add_argument("--windows", nargs="*", default=DEFAULT, help="several windows at once")
    ap.add_argument("--rounds", type=int, default=7)
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    windows = [a.window] if a.window else a.windows

    gc.disable()
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()

    print(f"{cols}x{rows}  {a.rounds} rounds, median of per-round medians")
    print()
    print(f"{'window':>14} {'frames':>7} {'median ms':>10} {'best ms':>9} {'worst ms':>9} "
          f"{'fps(med)':>9}  pane")
    for spec in windows:
        lo, hi = (float(v) for v in spec.split(","))
        frames = max(2, int((hi - lo) * T.FPS))
        times_per_round = []
        for _round in range(a.rounds):
            s = T.Screen(cols, rows)
            sink = io.StringIO()
            for k in range(frames):                 # warm this round
                t = lo + k * (hi - lo) / frames
                T.draw(s, data, eng, t, True, T.FPS)
                s.render_diff(sink)
            ms = []
            for k in range(frames):
                t = lo + k * (hi - lo) / frames
                t0 = time.perf_counter()
                T.draw(s, data, eng, t, True, T.FPS)
                s.render_diff(sink)
                ms.append((time.perf_counter() - t0) * 1000)
            times_per_round.append(statistics.median(ms))
        med = statistics.median(times_per_round)
        row = SP.row_at((lo + hi) / 2)
        print(f"{lo:6.1f}-{hi:6.1f} {frames:7d} {med:10.1f} {min(times_per_round):9.1f} "
              f"{max(times_per_round):9.1f} {1000 / med:9.1f}  {row['name'] if row else '-'}")


if __name__ == "__main__":
    main()
