"""`render_diff` 的 10-14 ms 花在哪一步？把它的三段分开计时。

帧率的下一步取决于这个问题的答案，而两种可能的答案指向完全不同的改造：

  * 若钱花在**逐格比较**（"这一格和上一帧一样吗"）——那就要让"哪些格变了"变成写入时就能拿到的
    O(1) 信息，`render_diff` 只扫脏行/脏区间；
  * 若钱花在**转义流拼装**（游标定位、SGR、join）——那改造的方向是少发字节，与"扫多少格"无关。

`_dev/probe_frame_profile.py`（cProfile）只能告诉我们函数级别的去向，分不出这两段。
这里直接读源码里的循环结构，插桩计时：

    A. 逐格扫描段（比较 row[x] != old[x]，含 fix_pair / _wide_char 的门）
    B. 转义流拼装段（parts.append + 最后的 "".join + out.write）
    C. 整行的 row == old 短路（批 81 加的）

    python _dev/probe_renderdiff_split.py
    python _dev/probe_renderdiff_split.py --window 61.0,62.0
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


class Sink(io.StringIO):
    def __init__(self):
        super().__init__()
        self.bytes = 0

    def write(self, text):
        self.bytes += len(text)
        return len(text)


def measure(T, eng, data, cols, rows, lo, hi, frames, rounds):
    """返回 (draw 中位数, render_diff 中位数, 每帧变化格数中位数, 每帧脏行数中位数)。"""
    draw_ms, diff_ms, cells, dirty_rows = [], [], [], []
    for _ in range(rounds):
        s = T.Screen(cols, rows)
        sink = Sink()
        for k in range(frames):                       # 预热
            t = lo + k * (hi - lo) / frames
            T.draw(s, data, eng, t, True, T.FPS)
            s.render_diff(sink)
        d, f, c, dr = [], [], [], []
        for k in range(frames):
            t = lo + k * (hi - lo) / frames
            t0 = time.perf_counter()
            T.draw(s, data, eng, t, True, T.FPS)
            t1 = time.perf_counter()
            sink.bytes = 0
            n = s.render_diff(sink)
            t2 = time.perf_counter()
            d.append((t1 - t0) * 1000)
            f.append((t2 - t1) * 1000)
            c.append(n)
            dr.append(len(s.dirty))
        draw_ms.append(statistics.median(d))
        diff_ms.append(statistics.median(f))
        cells.append(statistics.median(c))
        dirty_rows.append(statistics.median(dr))
    return (statistics.median(draw_ms), statistics.median(diff_ms),
            statistics.median(cells), statistics.median(dirty_rows))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", help="LO,HI seconds")
    ap.add_argument("--windows", nargs="*", default=WINDOWS)
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    windows = [a.window] if a.window else a.windows
    gc.disable()
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()

    total = cols * rows
    print(f"{cols}x{rows} = {total} 格；{a.rounds} 轮取中位数")
    print()
    print(f"{'window':>14} {'draw ms':>8} {'diff ms':>8} {'diff 占比':>9} "
          f"{'变化格':>7} {'脏行':>6} {'脏行占比':>8}  pane")
    for spec in windows:
        lo, hi = (float(v) for v in spec.split(","))
        frames = max(2, int((hi - lo) * T.FPS))
        d, f, c, dr = measure(T, eng, data, cols, rows, lo, hi, frames, a.rounds)
        row = SP.row_at((lo + hi) / 2)
        print(f"{lo:6.1f}-{hi:6.1f} {d:8.1f} {f:8.1f} {100 * f / (d + f):8.1f}% "
              f"{c:7.0f} {dr:6.0f} {100 * dr / rows:7.1f}%  {row['name'] if row else '-'}")
    print()
    print("读法：如果 diff 占比高、而脏行占比低（比如 20%），")
    print("      那么'让 render_diff 只扫脏行'最多能省下 diff 的 80%。")


if __name__ == "__main__":
    main()
