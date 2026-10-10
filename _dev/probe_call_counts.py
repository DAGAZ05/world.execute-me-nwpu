"""热路径上每个函数**一帧被调用几次**——只数次数，不测时间（时间在别处量）。

## 为什么只数次数

`_dev/probe_draw_attribution.py` 用 `sys.setprofile` 得到过"每个函数自身耗时"，
但那个数**不可信**：探针本身的开销让同一个窗口从 22.6 ms 变成 108 ms，
而开销是按**调用次数**摊的，于是"调用最多的函数"必然被算成"最贵的函数"——
那是探针的形状，不是程序的形状。

**但调用次数本身是可信的、也是可用的**：它是解释器真实的动作次数，
与计时开销无关。而优化一个每格每帧都被调用的函数，收益上限就是
`次数 × 单次开销`，所以次数决定了"哪条路值得走"。

用 `sys.settrace`? 不——那更慢。这里用最轻的办法：把目标函数包一层计数器，
只加一次 `list.__setitem__`（整数自增），对 22 ms 的帧来说可以忽略。

    python _dev/probe_call_counts.py
    python _dev/probe_call_counts.py --window 61.0,62.0
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

WINDOWS = ["14.0,16.0", "61.0,62.0", "148.0,149.0", "184.4,186.0", "196.0,197.0"]

#: 要数的函数 / 方法，按"是否在每格路径上"分组
TARGETS_MODULE = ["_wide_char", "_maybe_wide", "dw", "_fit_cells", "mix", "ui",
                  "beat_level", "_glitch", "block_word"]
TARGETS_SCREEN = ["put", "set_cell", "fill", "box", "hbar", "render_diff",
                  "fix_pair", "normalise", "_unpair", "_clear_spans"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window")
    ap.add_argument("--windows", nargs="*", default=WINDOWS)
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
    windows = [a.window] if a.window else a.windows

    counts = {}

    def wrap(obj, name, label):
        fn = getattr(obj, name, None)
        if fn is None:
            return
        counts[label] = 0

        def wrapper(*args, **kw):
            counts[label] += 1
            return fn(*args, **kw)

        setattr(obj, name, wrapper)

    class Mod:
        pass

    m = Mod()
    for n in TARGETS_MODULE:
        if hasattr(T, n):
            wrap(T, n, f"tui_live.{n}")
    for n in TARGETS_SCREEN:
        wrap(T.Screen, n, f"Screen.{n}")
    del m

    print(f"{cols}x{rows}  每帧调用次数（只数次数，不测时间）")
    print()
    for spec in windows:
        lo, hi = (float(v) for v in spec.split(","))
        frames = max(2, int((hi - lo) * T.FPS))
        row = SP.row_at((lo + hi) / 2)
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        for k in range(4):                       # 预热
            T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, T.FPS)
            s.render_diff(sink)
        for key in counts:
            counts[key] = 0
        t0 = time.perf_counter()
        for k in range(frames):
            T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, T.FPS)
            s.render_diff(sink)
        dt = (time.perf_counter() - t0) / frames * 1000.0
        print(f"=== {spec}  {row['name'] if row else '?'}   {dt:.1f} ms/帧（含计数开销）===")
        for label, c in sorted(counts.items(), key=lambda kv: -kv[1]):
            if c == 0:
                continue
            per = c / frames
            mark = ""
            if per >= 200:
                mark = "   <== 每格量级"
            elif per >= 50:
                mark = "   <== 每行/每元素量级"
            print(f"    {per:9.0f} 次/帧   {label}{mark}")
        print()


if __name__ == "__main__":
    main()
