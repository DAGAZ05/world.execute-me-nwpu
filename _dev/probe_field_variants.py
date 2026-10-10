"""`field` 那 2.2 ms 花在哪？三种写法并排量。

直觉上"整屏向量化"一定更快，但这一层不是：最终必须把 10,244 个**元组**写进
`list[list[tuple]]`，那一步必然是 Python 循环，而 numpy 侧的掩码、argsort、分组
反而是在它之上再加的开销。这个探针把三种写法放在同一批场上量：

  A  逐格 Python（最朴素：`for y: for x:`，一个 `if` 一个元组）
  B  向量化 + 按行切片写（当前实现）
  C  逐格 Python，但只遍历"够亮的格"（`np.nonzero` 得到的稀疏坐标）

    python _dev/probe_field_variants.py --rounds 15
"""
from __future__ import annotations

import argparse
import gc
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


class FakeScreen:
    """和 `tui_live.Screen` 同形状的缓冲，避开 vignette 与 CLEAR 的干扰。"""

    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.buf = [[(" ", (200, 200, 200), (4, 7, 15))] * cols for _ in range(rows)]


def variant_a(f, s, ramp, colour, level, floor):
    """逐格。"""
    import numpy as np
    n = len(ramp) - 1
    drawn = 0
    for y in range(s.rows):
        row = s.buf[y]
        frow = f[y]
        for x in range(s.cols):
            if row[x][0] != " ":
                continue
            v = float(frow[x])
            if v < floor:
                continue
            ch = ramp[int(v * n)]
            if ch == " ":
                continue
            k = v * level
            row[x] = (ch, (int(colour[0] * k), int(colour[1] * k), int(colour[2] * k)),
                      row[x][2])
            drawn += 1
    return drawn


def variant_b(f, s, ramp, colour, level, floor):
    """向量化 + 按行切片写（school_noise.field 的当前实现）。"""
    import numpy as np
    n = len(ramp) - 1
    idx = np.clip((f * np.float32(n)).astype(np.int32), 0, n)
    chars = np.array(list(ramp), dtype="<U1")[idx]
    hit = (f >= np.float32(floor)) & (chars != " ")
    if not hit.any():
        return 0
    ys, xs = np.nonzero(hit)
    levels = f[ys, xs]
    order = np.argsort(ys, kind="stable")
    ys, xs, levels = ys[order], xs[order], levels[order]
    drawn = 0
    r0 = 0
    rows_n = ys.shape[0]
    while r0 < rows_n:
        r1 = r0
        yv = int(ys[r0])
        while r1 < rows_n and int(ys[r1]) == yv:
            r1 += 1
        row = s.buf[yv]
        for k in range(r0, r1):
            xv = int(xs[k])
            cell = row[xv]
            if cell[0] != " ":
                continue
            v = float(levels[k])
            kk = v * level
            row[xv] = (str(chars[ys[k], xs[k]]),
                       (int(colour[0] * kk), int(colour[1] * kk), int(colour[2] * kk)),
                       cell[2])
            drawn += 1
        r0 = r1
    return drawn


def variant_c(f, s, ramp, colour, level, floor):
    """只遍历够亮的格（稀疏），不做 argsort 分组。"""
    import numpy as np
    n = len(ramp) - 1
    ys, xs = np.nonzero(f >= np.float32(floor))
    drawn = 0
    for k in range(ys.shape[0]):
        y = int(ys[k])
        x = int(xs[k])
        row = s.buf[y]
        cell = row[x]
        if cell[0] != " ":
            continue
        v = float(f[y, x])
        ch = ramp[int(v * n)]
        if ch == " ":
            continue
        kk = v * level
        row[x] = (ch, (int(colour[0] * kk), int(colour[1] * kk), int(colour[2] * kk)),
                  cell[2])
        drawn += 1
    return drawn


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", type=int, default=15)
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()
    import numpy as np
    import school_noise as NZ

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    nz = NZ.Noise(cols, rows, seed=7, scale=14.0, octaves=2)
    gc.disable()
    ramp, colour, level, floor = NZ.RAMP, (120, 150, 190), 0.55, 0.12

    print(f"{cols}x{rows}  {a.rounds} 轮   floor={floor} level={level}")
    print()
    print(f"{'variant':>34} {'median ms':>10} {'min':>7} {'max':>7} {'画出格数':>9}")
    for name, fn in (("A 逐格（全屏）", variant_a),
                     ("B 向量化 + 按行分组（当前）", variant_b),
                     ("C 稀疏逐格（只遍历够亮的）", variant_c)):
        ms = []
        drawn = 0
        for r in range(a.rounds):
            nz.tick(r * 0.37)
            s = FakeScreen(cols, rows)
            t0 = time.perf_counter()
            drawn = fn(nz.cur, s, ramp, colour, level, floor)
            ms.append((time.perf_counter() - t0) * 1000)
        print(f"{name:>34} {statistics.median(ms):10.2f} {min(ms):7.2f} {max(ms):7.2f} "
              f"{drawn:9d}")


if __name__ == "__main__":
    main()
