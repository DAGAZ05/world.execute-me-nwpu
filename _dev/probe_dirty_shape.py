"""一行的变化格是聚在一起还是铺满整行？这决定"收窄扫描区间"有没有用。

`_dev/probe_renderdiff_split.py` 的结论是脏行占 53-100%，所以"整行跳过"最多省一半、通常省不到。
剩下唯一的收窄办法是**行内只扫变化区间**（min..max 脏列），而这只有在变化格**聚簇**时才有意义。
这个探针直接量：每行变化格的数量、跨度、以及"格数 / 跨度"（密度）。

  * 密度接近 1.0 → 变化格连续铺开，收窄区间没用（区间就是整行）；
  * 密度很低（比如 0.2）→ 变化格散布在小簇里，收窄区间能省很多，但也说明"区间"并不是
    好的抽象，应该改用**簇**（runs）。

    python _dev/probe_dirty_shape.py
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

WINDOWS = ["14.0,16.0", "61.0,62.0", "147.0,148.0", "195.0,196.0"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--windows", nargs="*", default=WINDOWS)
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

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

    print(f"{cols}x{rows}；每行的变化格形状")
    print()
    print(f"{'window':>14} {'行/帧':>6} {'变化格/行':>9} {'跨度':>7} {'密度':>6} "
          f"{'簇数/行':>8} {'簇总长':>7} {'簇内密度':>8}  pane")
    for spec in WINDOWS:
        lo, hi = (float(v) for v in spec.split(","))
        frames = max(2, int((hi - lo) * T.FPS))
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        for k in range(frames):
            T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, T.FPS)
            s.render_diff(sink)

        ncell, span, runs_n, runs_len = [], [], [], []
        for k in range(frames):
            T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, T.FPS)
            # 在 render_diff 之前，自己算一遍每行的变化格形状（只看，不改）
            prev = s.prev
            for y in range(rows):
                row, old = s.buf[y], prev[y]
                xs = [x for x in range(cols) if row[x] != old[x]]
                if not xs:
                    continue
                ncell.append(len(xs))
                span.append(xs[-1] - xs[0] + 1)
                # 连续簇：gap > 1 就断开
                r = 1
                total = 1
                for i in range(1, len(xs)):
                    if xs[i] == xs[i - 1] + 1:
                        total += 1
                    else:
                        r += 1
                        total += 1
                runs_n.append(r)
                runs_len.append(total)
            s.render_diff(sink)

        if not ncell:
            print(f"{lo:6.1f}-{hi:6.1f} {'-':>6}")
            continue
        nc = statistics.median(ncell)
        sp = statistics.median(span)
        row = SP.row_at((lo + hi) / 2)
        print(f"{lo:6.1f}-{hi:6.1f} {len(ncell) / frames:6.0f} {nc:9.0f} {sp:7.0f} "
              f"{nc / sp:6.2f} {statistics.median(runs_n):8.0f} "
              f"{statistics.median(runs_len):7.0f} "
              f"{statistics.median(runs_len) / sp if sp else 0:8.2f}  {row['name'] if row else '-'}")
    print()
    print("密度 = 变化格数 / 跨度。接近 1 说明变化连续铺满，收窄区间无用；")
    print("簇数/行高说明变化是散的，那么该按簇跳而不是按区间扫。")


if __name__ == "__main__":
    main()
