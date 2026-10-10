"""现在的帧率预算到底是多少，以及 `--no-fx` 能省多少？

`_dev/frame_budget.py` 已经在报"多少帧进不了 24 fps"，但它只覆盖它自己那几个窗口。
这个探针做两件在别处没做过的事：

  1. **沿全曲扫一圈**（每 4 秒取一个窗口），给出帧时间的分布：中位、p90、最差，
     以及"进得去 24 fps（≤41.7 ms）的比例"。这才是"画面流畅不流畅"的真实答案——
     平均值会骗人，卡的是尾部。
  2. **`--no-fx` 的 A/B**：关掉后期（余晖/溶解/转场/暗角/抖动）能省多少。
     这是观众手里唯一一个"一句开关就变快"的杠杆，所以它的数字值得单独量。

口径与项目一致：`draw + render_diff` 一轮的墙上时间，多轮取中位数（不是平均值，也不是 cProfile）。

    python _dev/probe_song_budget.py
    python _dev/probe_song_budget.py --rounds 5 --no-fx
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

BUDGET_24 = 1000.0 / 24.0      # 41.67 ms
BUDGET_30 = 1000.0 / 30.0
BUDGET_60 = 1000.0 / 60.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--step", type=float, default=4.0, help="每隔多少秒取一个窗口")
    ap.add_argument("--span", type=float, default=0.5, help="每个窗口多长")
    ap.add_argument("--no-fx", action="store_true", help="关掉后期再量一遍（A/B）")
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import school_fx as FX
    import school_gate as G
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

    def measure(post_on: bool):
        # `FX` 是 `tui_live` 自己的字典（`on/reveal/mech/trail/vig/shake`），不是 `school_fx` 的。
        # 默认值就是全 True，见 `tui_live.py` 里 `FX = dict(...)` 那一行。
        if not post_on:
            T.FX.update(on=False, reveal=False, mech=False, trail=False, vig=False)
        else:
            T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True)
        frames_ms = {}
        t = 0.0
        while t < T.END - a.span:
            frames = max(2, int(a.span * T.FPS))
            per_round = []
            for _ in range(a.rounds):
                s = T.Screen(cols, rows)
                sink = io.StringIO()
                ms = []
                for k in range(frames):
                    tt = t + k * a.span / frames
                    t0 = time.perf_counter()
                    T.draw(s, data, eng, tt, True, T.FPS)
                    s.render_diff(sink)
                    ms.append((time.perf_counter() - t0) * 1000.0)
                per_round.append(statistics.median(ms))
            frames_ms[round(t, 2)] = statistics.median(per_round)
            t += a.step
        return frames_ms

    print(f"{cols}x{rows}  全曲扫描（每 {a.step:g} s 一个窗口，每窗 {a.span:g} s，"
          f"{a.rounds} 轮取中位数）")
    print()
    base = measure(True)
    vals = list(base.values())
    med = statistics.median(vals)
    p90 = sorted(vals)[int(0.9 * (len(vals) - 1))]
    worst_t = max(base, key=lambda k: base[k])
    ok24 = sum(1 for v in vals if v <= BUDGET_24)
    ok30 = sum(1 for v in vals if v <= BUDGET_30)
    ok60 = sum(1 for v in vals if v <= BUDGET_60)
    n = len(vals)
    print("=== 后期全开（默认）===")
    print(f"  中位 {med:6.1f} ms    p90 {p90:6.1f} ms    最差 {base[worst_t]:6.1f} ms @ {worst_t:.1f} s")
    print(f"  进得了 24 fps: {ok24:3d}/{n} ({100 * ok24 / n:.0f}%)    "
          f"30 fps: {ok30:3d}/{n} ({100 * ok30 / n:.0f}%)    "
          f"60 fps: {ok60:3d}/{n} ({100 * ok60 / n:.0f}%)")
    print()

    if a.no_fx:
        off = measure(False)
        ov = list(off.values())
        print("=== 后期全关（--no-fx）===")
        print(f"  中位 {statistics.median(ov):6.1f} ms    "
              f"最差 {max(ov):6.1f} ms @ {max(off, key=lambda k: off[k]):.1f} s")
        ok24b = sum(1 for v in ov if v <= BUDGET_24)
        ok30b = sum(1 for v in ov if v <= BUDGET_30)
        print(f"  进得了 24 fps: {ok24b:3d}/{n} ({100 * ok24b / n:.0f}%)    "
              f"30 fps: {ok30b:3d}/{n} ({100 * ok30b / n:.0f}%)")
        print()
        saved = [(k, base[k] - off[k]) for k in base]
        saved.sort(key=lambda kv: -kv[1])
        print("  省得最多的 8 个窗口：")
        for k, v in saved[:8]:
            print(f"    {k:7.1f} s   {base[k]:6.1f} -> {off[k]:6.1f} ms  省 {v:5.1f}")
        print(f"  全曲平均省 {statistics.mean(v for _, v in saved):.1f} ms/帧")
        print()

    print("=== 最费的 8 个窗口 ===")
    for k, v in sorted(base.items(), key=lambda kv: -kv[1])[:8]:
        row = SP.row_at(k)
        print(f"  {k:7.1f} s  {v:6.1f} ms  ({1000 / v:5.1f} fps)  {row['name'] if row else '?'}")
    print()
    print(f"参考预算：24 fps = {BUDGET_24:.1f} ms · 30 fps = {BUDGET_30:.1f} ms · "
          f"60 fps = {BUDGET_60:.1f} ms")


if __name__ == "__main__":
    main()
