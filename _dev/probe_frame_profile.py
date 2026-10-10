"""Where does a frame's 20-odd milliseconds actually go? cProfile, per pane.

`paint_probe` says *that* the loop is over budget; this says *why*. It draws one pane's window with
cProfile around it and prints the top consumers by cumulative time, plus the calls that are pure
functions of things that do not change between frames (the usual shape of the answer: a mask, a ramp,
a cell table recomputed every frame for a pane that is on screen for four seconds).

    python _dev/probe_frame_profile.py --pane pane_parameters
    python _dev/probe_frame_profile.py --window 6,10 --top 25
    python _dev/probe_frame_profile.py --all --top 6      every pane, six lines each
"""
from __future__ import annotations

import argparse
import cProfile
import gc
import io
import os
import pstats
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


def build(cols, rows):
    import tui_live as T
    import school_panels as SP
    import school_fx as FX
    import school_gate as G

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    return T, SP, T.Engine(), T.Data(), T.Screen(cols, rows)


def profile_window(T, SP, eng, data, s, lo, hi, frames, top, label):
    sink = io.StringIO()
    for k in range(frames):                      # warm, so caches are not what we are measuring
        T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, 60.0)
        s.render_diff(sink)
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    for k in range(frames):
        T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, 60.0)
        s.render_diff(sink)
    pr.disable()
    wall = (time.perf_counter() - t0) * 1000
    print(f"=== {label}: {frames} frames in {wall:.0f} ms = {wall / frames:.1f} ms/frame")
    st = pstats.Stats(pr)
    st.sort_stats("tottime")
    rows = []
    for (fn, line, name), (cc, nc, tt, ct, callers) in st.stats.items():
        if name in ("<method 'disable' of '_lsprof.Profiler' objects>",):
            continue
        rows.append((tt * 1000 / frames, ct * 1000 / frames, nc // frames, name, Path(fn).name, line))
    rows.sort(reverse=True)
    print(f"    {'tottime':>9} {'cumtime':>9} {'calls/f':>9}  function")
    for tt, ct, nc, name, f, line in rows[:top]:
        print(f"    {tt:9.2f} {ct:9.2f} {nc:9d}  {name}  ({f}:{line})")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pane", help="profile the window of the row that draws this pane")
    ap.add_argument("--window", help="LO,HI seconds - profile this literal window")
    ap.add_argument("--all", action="store_true", help="one block per distinct pane")
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    gc.disable()
    T, SP, eng, data, s = build(cols, rows)

    jobs: list[tuple[float, float, str]] = []
    if a.window:
        lo, hi = (float(v) for v in a.window.split(","))
        jobs.append((lo, hi, f"window {lo}-{hi}s"))
    if a.pane:
        for r in SP.shot_rows():
            if r.get("name") == a.pane:
                lo, hi = r["at"] + 0.05, r["at"] + 0.05 + max(0.6, r.get("dur", 1.0))
                jobs.append((lo, hi, a.pane))
                break
        else:
            raise SystemExit(f"no row draws {a.pane}")
    if a.all:
        seen = set()
        for r in SP.shot_rows():
            name = r.get("name")
            if not name or name in seen:
                continue
            seen.add(name)
            jobs.append((r["at"] + 0.05, r["at"] + 0.05 + max(0.6, r.get("dur", 1.0)), name))
    if not jobs:
        # the panes the full-song sweep found slowest
        for name in ("pane_creation", "pane_parameters", "pane_deeply", "pane_challenge_god"):
            for r in SP.shot_rows():
                if r.get("name") == name:
                    jobs.append((r["at"] + 0.05, r["at"] + 0.05 + max(0.6, r.get("dur", 1.0)), name))
                    break

    for lo, hi, label in jobs:
        if lo >= hi:
            hi = lo + 0.6
        profile_window(T, SP, eng, data, s, lo, hi, a.frames, a.top, label)


if __name__ == "__main__":
    main()
