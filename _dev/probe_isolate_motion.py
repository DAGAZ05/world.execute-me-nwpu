"""`--fps-cap` 到底有没有用？把"运动"和"逐帧噪声"分开量。

背景：`tui_live.py` 的 `--fps-cap` 帮助文本写着"the film is authored at 24 fps and every effect is a
function of the song clock, so a higher cap is genuinely smoother motion and not repeated frames"。
`_dev/probe_fps_motion.py` 第一次检验了它，结论却相反：同一个时间窗里，24/48/96 fps 三种速率下
相邻帧的平均变化格数分别是 5638 / 5450 / 5163 —— **几乎不变**。如果画面是连续的，把时间步缩到
1/4，相邻帧的变化量应该也缩到约 1/4。

两种解释，必须分开：

  * **真运动 + 逐帧噪声**：几何确实在连续移动，但每帧都还叠了一层与时间无关的抖动
    （故障效果、抖动贴图、按帧步进的余晖），把变化量顶在一个与 dt 无关的地板上；
  * **时间被量化**：画面内部按某个固定步长（例如 1/24 s）取整，那么提高速率只是重复同一帧。

判据：**关掉所有后期（`--no-fx`）再量一次**。

  * 若变化量这时随 dt 缩小 → 运动是连续的，噪声来自后期层；
  * 若仍不缩小 → 排期本身被量化，高帧率只会重复帧（那么 `--fps-cap` 的说明需要改）。

    python _dev/probe_isolate_motion.py                     默认窗口，开关两遍
    python _dev/probe_isolate_motion.py --at 15.0 --span 1.0
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

WINDOWS = [(14.5, 15.5), (61.0, 62.0), (147.0, 148.0), (195.0, 196.0)]


def snapshot(s):
    return [row[:] for row in s.buf]


def diff_cells(a, b) -> int:
    n = 0
    for ra, rb in zip(a, b):
        for ca, cb in zip(ra, rb):
            if ca != cb:
                n += 1
    return n


def measure(T, SP, eng, data, cols, rows, lo, hi, fps, fx_on):
    import tui_live as _T
    _T.FX.update(on=fx_on, reveal=fx_on, mech=fx_on, trail=fx_on, vig=fx_on, shake=fx_on)
    span = hi - lo
    n = max(2, int(span * fps))
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    for k in range(4):                       # 预热：缓存与 ghost 状态
        T.draw(s, data, eng, lo - 0.4 + k * 0.01, True, fps)
        s.render_diff(sink)
    prev = None
    changed = []
    identical = 0
    for k in range(n):
        t = lo + k * span / n
        T.draw(s, data, eng, t, True, fps)
        s.render_diff(sink)
        cur = snapshot(s)
        if prev is not None:
            d = diff_cells(cur, prev)
            changed.append(d)
            if d == 0:
                identical += 1
        prev = cur
    return (statistics.fmean(changed) if changed else 0.0), identical, n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", type=float, help="one window of --span seconds around this time")
    ap.add_argument("--span", type=float, default=1.0)
    ap.add_argument("--rates", default="24,48,96")
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T

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
    total = cols * rows

    for lo, hi in windows:
        row = SP.row_at((lo + hi) / 2)
        print(f"=== {lo:.1f}-{hi:.1f} s   {row['name'] if row else '-'}")
        for fx_on in (False, True):
            tag = "后期开" if fx_on else "后期关"
            base = None
            for fps in rates:
                mean_c, ident, n = measure(T, SP, eng, data, cols, rows, lo, hi, fps, fx_on)
                if base is None:
                    base = mean_c
                ratio = (mean_c / base) if base else 0.0
                expect = rates[0] / fps
                print(f"   {tag}  {fps:5.0f} fps  step {1000 / fps:5.1f} ms  "
                      f"changed {mean_c:8.0f} ({100 * mean_c / total:4.1f} %)  "
                      f"identical {ident:4d}/{n:4d}  比基准 {ratio:5.2f} (连续画面应 {expect:5.2f})")
        print()


if __name__ == "__main__":
    main()
