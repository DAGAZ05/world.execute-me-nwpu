"""隐含心形 `(x²+y²-1)³ - x²y³ ≤ 0` 到底是什么形状？—— 直接算，不用搜索函数。

`school_motifs._heart_y_extent` 第一版用"轴上是否在内部"当判据，得到高 1.0（把心压成三角）；
第二版用三分搜索求 `min over x`，得到高 3.0（又反过来，而且形状上下颠倒）。
两次都不是形状的问题，是**我的搜索写错了**。所以这里不再搜索：直接把格点扫一遍，
打印每个 y 上有解的 x 范围与最小函数值——形状是什么样，一眼就看得出。

同时给出离线校正：对若干参考形状，用**密集采样**求出的内部集合当"真值"，
再和 `heart_cells` 比覆盖率，这样即便我对公式的理解有偏差也能被数字抓住。

    python _dev/probe_heart_shape.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


def expr(x: float, y: float) -> float:
    return (x * x + y * y - 1.0) ** 3 - x * x * y * y * y


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("沿 y 扫描：每个 y 上 x∈[-2,2] 内满足 <=0 的 x 区间，以及最小函数值")
    print(f"{'y':>7} {'最小 f':>12} {'有解?':>6}  x 范围")
    for i in range(-24, 13):
        y = i / 12.0
        # 密集采样
        best = None
        xs_in = []
        N = 4000
        for k in range(N + 1):
            x = -2.0 + 4.0 * k / N
            v = expr(x, y)
            if best is None or v < best:
                best = v
            if v <= 0.0:
                xs_in.append(x)
        rng = f"[{min(xs_in):+.3f}, {max(xs_in):+.3f}]" if xs_in else "-"
        print(f"{y:7.3f} {best:12.5f} {'YES' if xs_in else 'no':>6}  {rng}")

    print()
    print("=== 与 heart_cells 对照（用密集采样当真值）===")
    import school_motifs as M
    print(f"_heart_y_extent() = {M._heart_y_extent()}")
    for (w, h) in ((28, 13), (20, 9)):
        # 真值：对每个格的中心点算 f，<=0 即内部
        ytop, ybot = 1.0, -1.3          # 先用"标准"心形范围试
        truth = set()
        for gy in range(h):
            uy = ytop - (gy + 0.5) * (ytop - ybot) / h
            for gx in range(w):
                ux = 2.0 * ((gx + 0.5) / w) - 1.0
                if expr(ux, uy) <= 0.0:
                    truth.add((gx, gy))
        got = M.heart_cells(w, h)
        print(f"  {w}x{h}: heart_cells {len(got)} 格, 参考 {len(truth)} 格, "
              f"交集 {len(got & truth)}")
        if truth:
            print(f"        差异 {len(got ^ truth)} 格")
            miss = sorted(truth - got)[:6]
            extra = sorted(got - truth)[:6]
            print(f"        参考有而我没画: {miss}")
            print(f"        我画了而参考没有: {extra}")


if __name__ == "__main__":
    main()
