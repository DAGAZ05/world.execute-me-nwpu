"""余晖会不会把前景色越叠越白？量一个格子 20 帧里的漂移。

`ink` 把余晖混进**前景色**（有字符的格子）。因为是"混进当前值"，同一个格子如果每帧都被重画、
每帧都被混一次，理论上会一路漂向余晖的颜色——像反复复印同一张纸。这个探针把这件事量出来：
跑一段动画强烈的窗口，记录每个格子的前景色亮度在第 1 帧和第 N 帧的差，
再和"整段里真正被画过的最亮颜色"比一比。

判据很直接：**漂移必须远小于"画面上真实存在的颜色范围"**。若某个格子在 20 帧里从 107 漂到 200，
那读者看到的就是一片越来越白的糊影，这个效果就不能上。

    python _dev/probe_phosphor_drift.py
    python _dev/probe_phosphor_drift.py --frames 40 --decay 0.62
"""
from __future__ import annotations

import argparse
import gc
import io
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

WINDOWS = [(61.0, "lyric_band"), (66.2, "satisfaction"), (14.5, "y20_crossing")]


def lum(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def snapshot(s):
    return [[(ch, fg, bg) for (ch, fg, bg) in row] for row in s.buf]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames", type=int, default=20)
    ap.add_argument("--decay", type=float, default=None)
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()
    cols, rows = (int(v) for v in a.size.lower().split("x"))

    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import school_phosphor as PH
    import tui_live as T

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()
    if a.decay is not None:
        PH.DECAY = a.decay
    dt = 1.0 / T.FPS

    print(f"{cols}x{rows}  decay={PH.DECAY}  {a.frames} 帧")
    print()
    print(f"{'窗口':>14} {'格数(亮)':>9} {'漂移中位':>9} {'漂移p95':>9} {'漂移max':>9} "
          f"{'真实色域':>9}")
    for t0, label in WINDOWS:
        for use in (False, True):
            s = T.Screen(cols, rows)
            ph = PH.Phosphor(cols, rows) if use else None
            sink = io.StringIO()
            t = t0
            first = None
            for k in range(a.frames):
                T.draw(s, data, eng, t, True, T.FPS)
                if ph is not None:
                    ph.ink(s)
                s.render_diff(sink)
                if k == 0:
                    first = snapshot(s)
                if ph is not None:
                    ph.poke(s, dt)
                t += dt
            last = snapshot(s)
            # 只统计"两帧都亮着"的格子，这才是漂移会累积的地方
            drift = []
            for y in range(rows):
                for x in range(cols):
                    ch0, fg0, _ = first[y][x]
                    ch1, fg1, _ = last[y][x]
                    if ch0 not in (" ", "") and ch1 not in (" ", ""):
                        drift.append(lum(fg1) - lum(fg0))
            # 整段里真实出现过的前景亮度跨度，作为"多少漂移才看得见"的标尺
            lo = min(lum(c[1]) for r in last for c in r)
            hi = max(lum(c[1]) for r in last for c in r)
            tag = "有余晖" if use else "无余晖"
            if drift:
                ds = sorted(abs(d) for d in drift)
                print(f"{label + '/' + tag:>14} {len(drift):9d} {statistics.median(ds):9.1f} "
                      f"{ds[int(len(ds) * .95)]:9.1f} {max(ds):9.1f} {hi - lo:9.1f}")
            else:
                print(f"{label + '/' + tag:>14} {0:9d}         -         -         - "
                      f"{hi - lo:9.1f}")
        print()


if __name__ == "__main__":
    main()
