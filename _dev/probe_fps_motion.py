"""Is above 24 fps genuinely new motion, or the same frame twice? Measure it, do not assume.

The player's `--fps-cap` docstring claims "the film is authored at 24 fps and every effect is a function
of the song clock, so a higher cap is genuinely smoother motion and not repeated frames". That claim is
the whole justification for the frame-rate half of the enhancement work, and it had never been measured.

This probe draws the film at a series of instants and compares the *cell buffers*:

  * at the film's own rate (1/24 s apart) - adjacent cells here are what a 24 fps player shows;
  * at 2x and 3x that rate (1/48, 1/72 s apart) - if the claim holds, these neighbours differ too, and
    by a shrinking but non-zero amount.

`changed` is the number of cells whose (char, fg, bg) differs from the previous instant. `distinct` is
whether the frame is literally the same buffer as its predecessor. A frame that is identical to its
neighbour is a repeat, and a higher cap would be showing it for nothing.

    python _dev/probe_fps_motion.py                        the default windows
    python _dev/probe_fps_motion.py --at 15.0 --span 2.0
    python _dev/probe_fps_motion.py --rates 24,48,96
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

# one window per kind of motion: the aircraft crossing, a course pane, the flood, her floating
WINDOWS = [(14.0, 15.0), (61.0, 62.0), (147.0, 148.0), (193.0, 194.0)]


def snapshot(screen):
    return [row[:] for row in screen.buf]


def diff_cells(a, b) -> int:
    n = 0
    for ra, rb in zip(a, b):
        for ca, cb in zip(ra, rb):
            if ca != cb:
                n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", type=float, help="one window of --span seconds around this time")
    ap.add_argument("--span", type=float, default=1.0)
    ap.add_argument("--rates", default="24,48,72",
                    help="frame rates to compare, comma separated (the film's own is 24)")
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    import tui_live as T
    import school_panels as SP
    import school_fx as FX
    import school_gate as G

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    rates = [float(v) for v in a.rates.split(",")]
    windows = [(a.at - a.span, a.at + a.span)] if a.at is not None else WINDOWS

    gc.disable()
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()
    s = T.Screen(cols, rows)
    cells_total = cols * rows

    print(f"{cols}x{rows} = {cells_total} cells; the film's own rate is 24 fps")
    print()
    print("每一行：在**同一个时间窗**里，以该速率画的 `frames` 帧之间，逐格比较的平均变化量。")
    print("如果画面是连续的，帧间隔缩小 N 倍，相邻帧的变化量也应该缩小约 N 倍；")
    print("如果变化量不随帧间隔缩小，说明画面在时间上被量化了（例如内部按 1/24 s 取整），")
    print("那么把 cap 提到 24 以上只会重复同一帧——这一检验就是为了证明它不会。")
    print()
    print(f"{'rate':>6} {'step ms':>8} {'frames':>7} {'changed/frame':>14} {'% of cells':>10} "
          f"{'identical':>10} {'mean ms':>8}")
    for lo, hi in windows:
        span = hi - lo
        print(f"--- {lo:.1f}-{hi:.1f} s  ({SP.row_at((lo + hi) / 2)['name']})")
        per_rate = {}
        for fps in rates:
            step = 1.0 / fps
            n = max(2, int(span * fps))          # 同一窗口、不同速率 → 帧数按比例变，步长按比例变
            # warm this window so caches and the previous-frame buffers are in the right state
            for k in range(3):
                T.draw(s, data, eng, lo - 0.5 + k * 0.01, True, fps)
                s.render_diff(io.StringIO())
            prev = None
            changed = []
            identical = 0
            ms = []
            for k in range(n):
                t = lo + k * span / n
                t0 = time.perf_counter()
                T.draw(s, data, eng, t, True, fps)
                s.render_diff(io.StringIO())
                ms.append((time.perf_counter() - t0) * 1000)
                cur = snapshot(s)
                if prev is not None:
                    d = diff_cells(cur, prev)
                    changed.append(d)
                    if d == 0:
                        identical += 1
                prev = cur
            mean_c = sum(changed) / len(changed) if changed else 0.0
            per_rate[fps] = mean_c
            print(f"{fps:6.0f} {step * 1000:8.1f} {n:7d} {mean_c:14.0f} "
                  f"{100 * mean_c / cells_total:9.1f}% {identical:10d} "
                  f"{sum(ms) / len(ms):8.1f}")
        base = rates[0]
        if base in per_rate and per_rate[base] > 0:
            for fps in rates[1:]:
                if fps not in per_rate:
                    continue
                ratio = per_rate[fps] / per_rate[base]
                expect = base / fps
                verdict = ("随帧间隔缩小（画面连续）" if ratio < 0.75
                           else "几乎不缩小 —— 可疑，值得再查")
                print(f"      {base:.0f}→{fps:.0f} fps: 变化量比 {ratio:.2f}"
                      f"（连续画面应约 {expect:.2f}）— {verdict}")
        print()


if __name__ == "__main__":
    main()
