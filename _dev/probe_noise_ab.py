"""噪声底噪接进真实管线后的成本：多轮中位数，这是唯一能下结论的测法。

`probe_noise_visual.py` 用单次 draw 计时，读出来是 4.9-8.3 ms；换成多轮中位数之后是 +0.4 ms。
同一段代码、同一个窗口，差别全在被测方法——这正是批 82 加 `probe_ab_frame.py` 的原因，
所以这一层也要按它的规矩量。

    python _dev/probe_noise_ab.py
    python _dev/probe_noise_ab.py --rounds 9 --scale 6
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

WINDOWS = ["14.0,16.0", "56.8,58.0", "61.0,62.0", "147.0,148.0", "195.0,196.0"]


def median_draw(T, eng, data, cols, rows, lo, hi, frames, rounds, noise):
    out = []
    for _ in range(rounds):
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        for k in range(frames):                       # 预热这一轮
            t = lo + k * (hi - lo) / frames
            T.NOISE[0] = noise
            T.draw(s, data, eng, t, True, T.FPS)
            T.NOISE[0] = None
            s.render_diff(sink)
        ms = []
        for k in range(frames):
            t = lo + k * (hi - lo) / frames
            T.NOISE[0] = noise
            t0 = time.perf_counter()
            T.draw(s, data, eng, t, True, T.FPS)
            ms.append((time.perf_counter() - t0) * 1000)
            T.NOISE[0] = None
            s.render_diff(sink)
        out.append(statistics.median(ms))
    return statistics.median(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", type=int, default=7)
    ap.add_argument("--scale", type=float, default=14.0)
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    import school_fx as FX
    import school_gate as G
    import school_noise as NZ
    import school_panels as SP
    import tui_live as T

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    gc.disable()
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()

    print(f"{cols}x{rows}  scale={a.scale} octaves={NZ.OCTAVES}  "
          f"{a.rounds} 轮取中位数（与 _dev/probe_ab_frame.py 同一套方法）")
    print()
    print(f"{'window':>14} {'关 ms':>8} {'开 ms':>8} {'差值':>8} {'差值 %':>8}  pane")
    deltas = []
    for spec in WINDOWS:
        lo, hi = (float(v) for v in spec.split(","))
        frames = max(2, int((hi - lo) * T.FPS))
        off = median_draw(T, eng, data, cols, rows, lo, hi, frames, a.rounds, None)
        nz = NZ.Noise(cols, rows, seed=7, scale=a.scale)
        on = median_draw(T, eng, data, cols, rows, lo, hi, frames, a.rounds, nz)
        row = SP.row_at((lo + hi) / 2)
        deltas.append(on - off)
        print(f"{lo:6.1f}-{hi:6.1f} {off:8.1f} {on:8.1f} {on - off:+8.1f} "
              f"{100 * (on - off) / off:+7.1f}%  {row['name'] if row else '-'}")
    print()
    print(f"平均增量 {statistics.fmean(deltas):+.2f} ms  "
          f"(中位 {statistics.median(deltas):+.2f})")


if __name__ == "__main__":
    main()
