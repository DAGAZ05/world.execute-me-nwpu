"""噪声底噪的真实代价：**build + terminal stream 一起量**，多轮取中位数。

为什么必须是这个口径：这一层会把约 4,000 个原本是空格的格子变成有字符的格子，于是
`render_diff` 每一帧都要把它们写成转义流。只看 `draw()` 的毫秒数会漏掉这一半，
而用户的流畅度恰恰是两半之和（见 `tui_live` 顶部"两个预算"的说明、
`_dev/paint_probe.py` 的 docstring）。

    python _dev/probe_noise_total.py
    python _dev/probe_noise_total.py --period 0.5 --rounds 7
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

WINDOWS = ["14.0,16.0", "66.0,67.0", "195.0,196.0"]


class Counting(io.StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.bytes = 0
        self.cells = 0

    def write(self, text: str) -> int:
        self.bytes += len(text.encode("utf8"))
        return len(text)


def one_round(T, eng, data, cols, rows, lo, hi, frames, noise, period, stride):
    s = T.Screen(cols, rows)
    sink = Counting()
    T.NOISE[0] = noise
    T.NOISE_STRIDE = stride
    for k in range(frames):                     # 预热
        t = lo + k * (hi - lo) / frames
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
    ms, kb = [], []
    for k in range(frames):
        t = lo + k * (hi - lo) / frames
        sink.bytes = 0
        t0 = time.perf_counter()
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
        ms.append((time.perf_counter() - t0) * 1000)
        kb.append(sink.bytes / 1024)
    T.NOISE[0] = None
    return statistics.median(ms), statistics.median(kb)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", type=int, default=7)
    ap.add_argument("--period", type=float, default=0.25)
    ap.add_argument("--stride", type=int, default=1)
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
    T.NOISE_PERIOD = a.period

    print(f"{cols}x{rows}  period={a.period}s  stride={a.stride}  scale={a.scale}  {a.rounds} 轮取中位数")
    print(f"计的是 draw + render_diff 的合计（用户的流畅度就是这两半之和）")
    print()
    print(f"{'window':>14} {'关 ms':>8} {'开 ms':>8} {'Δms':>7} | {'关 KB':>8} {'开 KB':>8} {'ΔKB':>8}  pane")
    dms, dkb = [], []
    for spec in WINDOWS:
        lo, hi = (float(v) for v in spec.split(","))
        frames = max(2, int((hi - lo) * T.FPS))
        off_t, off_k = [], []
        on_t, on_k = [], []
        for _ in range(a.rounds):
            m, k = one_round(T, eng, data, cols, rows, lo, hi, frames, None, a.period, a.stride)
            off_t.append(m)
            off_k.append(k)
            nz = NZ.Noise(cols, rows, seed=7, scale=a.scale)
            m, k = one_round(T, eng, data, cols, rows, lo, hi, frames, nz, a.period, a.stride)
            on_t.append(m)
            on_k.append(k)
        o, n = statistics.median(off_t), statistics.median(on_t)
        ok, nk = statistics.median(off_k), statistics.median(on_k)
        row = SP.row_at((lo + hi) / 2)
        dms.append(n - o)
        dkb.append(nk - ok)
        print(f"{lo:6.1f}-{hi:6.1f} {o:8.1f} {n:8.1f} {n - o:+7.1f} | "
              f"{ok:8.1f} {nk:8.1f} {nk - ok:+8.1f}  {row['name'] if row else '-'}")
    print()
    print(f"平均：帧时间 {statistics.fmean(dms):+.2f} ms，终端流 {statistics.fmean(dkb):+.1f} KB/帧")


if __name__ == "__main__":
    main()
