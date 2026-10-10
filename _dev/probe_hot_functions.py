"""热函数真实耗时——用**包围计时**而不是 `sys.setprofile`。

## 为什么不能用 setprofile 的数

`_dev/probe_draw_attribution.py` 用 `sys.setprofile` 报出 `_wide_char` 19 ms/帧、`_maybe_wide` 8.9 ms。
那些数**不能信**：同一个窗口从 22.6 ms 变成 108 ms，多出来的 85 ms 全是探针开销，
而开销按**调用次数**摊——调用最多的函数必然被算成最贵的。那是探针的形状。

这个探针把目标函数包一层 `time.perf_counter()`，只测那几个函数，其余代码不受影响。
被包的是**真函数**，所以得到的是"这些函数本身花掉多少"，代价是每次调用多两次 `perf_counter`
（约 0.1-0.2 us），对 21 000 次的量级是 2-4 ms 的探针开销——**要把这个开销也报出来**，
不然又会犯同一个错。

    python _dev/probe_hot_functions.py
    python _dev/probe_hot_functions.py --window 61.0,62.0
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

WINDOWS = ["61.0,62.0", "148.0,149.0", "184.4,186.0"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window")
    ap.add_argument("--windows", nargs="*", default=WINDOWS)
    ap.add_argument("--rounds", type=int, default=3)
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

    # 有没有包过：保存原函数，量完恢复
    originals = {}
    stats = {}

    def instrument(obj, name, label):
        fn = getattr(obj, name, None)
        if fn is None or label in originals:
            return
        originals[label] = (obj, name, fn)
        stats[label] = [0.0, 0]          # [总秒数, 次数]

        def wrapper(*args, **kw):
            t0 = time.perf_counter()
            r = fn(*args, **kw)
            st = stats[label]
            st[0] += time.perf_counter() - t0
            st[1] += 1
            return r

        setattr(obj, name, wrapper)

    print(f"{cols}x{rows}  {a.rounds} 轮（包围计时；perf_counter 开销约 0.1-0.2 us/次）")
    print()
    for spec in windows:
        lo, hi = (float(v) for v in spec.split(","))
        frames = max(2, int((hi - lo) * T.FPS))
        row = SP.row_at((lo + hi) / 2)

        # 先量"没包任何东西"的基线帧时间
        base_ms = []
        for _ in range(a.rounds):
            s = T.Screen(cols, rows)
            sink = io.StringIO()
            ms = []
            for k in range(frames):
                t = lo + k * (hi - lo) / frames
                t0 = time.perf_counter()
                T.draw(s, data, eng, t, True, T.FPS)
                s.render_diff(sink)
                ms.append((time.perf_counter() - t0) * 1000.0)
            base_ms.append(statistics.median(ms))
        base = statistics.median(base_ms)

        # 再包上目标函数量
        for n in ("_wide_char", "_maybe_wide", "dw"):
            instrument(T, n, f"tui_live.{n}")
        for n in ("put", "fix_pair", "_unpair", "_clear_spans", "render_diff"):
            instrument(T.Screen, n, f"Screen.{n}")
        for st in stats.values():
            st[0] = 0.0
            st[1] = 0

        wrapped_ms = []
        nframes = 0
        for _ in range(a.rounds):
            s = T.Screen(cols, rows)
            sink = io.StringIO()
            ms = []
            for k in range(frames):
                t = lo + k * (hi - lo) / frames
                t0 = time.perf_counter()
                T.draw(s, data, eng, t, True, T.FPS)
                s.render_diff(sink)
                ms.append((time.perf_counter() - t0) * 1000.0)
            wrapped_ms.append(statistics.median(ms))
            nframes += frames
        wrapped = statistics.median(wrapped_ms)

        print(f"=== {spec}  {row['name'] if row else '?'} ===")
        print(f"    基线帧时间（未包任何东西）  {base:6.1f} ms")
        print(f"    包上目标函数之后            {wrapped:6.1f} ms   "
              f"（差 {wrapped - base:+.1f} ms = 探针开销 + 这些函数的耗时）")
        print()
        print(f"    {'函数':>24} {'次/帧':>9} {'ms/帧':>8} {'us/次':>7}")
        tot_ms = 0.0
        for label, (secs, cnt) in sorted(stats.items(), key=lambda kv: -kv[1][0]):
            if cnt == 0:
                continue
            per_frame = cnt / nframes
            per_frame_ms = secs / nframes * 1000.0
            us = secs / cnt * 1e6
            tot_ms += per_frame_ms
            print(f"    {label:>24} {per_frame:9.0f} {per_frame_ms:8.2f} {us:7.3f}")
        print(f"    {'合计':>24} {'':9} {tot_ms:8.2f}   占基线的 {100 * tot_ms / base:.0f}%")
        print()

    for label, (obj, name, fn) in originals.items():
        setattr(obj, name, fn)
    print("（原函数已恢复）")


if __name__ == "__main__":
    main()
