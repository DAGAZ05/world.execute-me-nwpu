"""画面里的东西到底动了几步？数一个地标的**不同位置**，不数每帧变了多少格。

`probe_isolate_motion` 的结论是：变化格数在 24/48/96 fps 下几乎不变，而且**关掉全部后期也一样**。
那说明这不是后期噪声。剩下两个可能：

  * **位置连续**：地标每帧都在新的位置，只是每次挪得很小（<1 格），所以"变了多少格"看不出差别；
  * **位置被量化**：地标的位置只在少数几个值上跳（例如按 24 Hz 更新），提高速率只是把同一个
    位置画很多遍——那 `--fps-cap` 的帮助文本就是错的。

判据：拿屏幕上一块**确实在动**的区域（默认取整屏的墨迹质心，也可以指定一块矩形），
以某个速率采很多帧，数它的位置序列里**出现了多少个不同的值**。

  * 连续：不同值 ≈ 帧数（每个采样都在动）；
  * 量化到 24 Hz：在 0.6 s 的窗口里不同值 ≈ 15 个，与采样速率无关。

    python _dev/probe_motion_steps.py --at 15.0 --span 0.6
    python _dev/probe_motion_steps.py --box 8,20,120,44 --at 15.0
"""
from __future__ import annotations

import argparse
import gc
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


def ink_centroid(s, box):
    """墨迹的质心与墨迹格数：屏幕上"哪里亮着"的一个粗坐标。"""
    x0, y0, x1, y1 = box
    sx = sy = n = 0
    for y in range(max(0, y0), min(s.rows, y1 + 1)):
        row = s.buf[y]
        for x in range(max(0, x0), min(s.cols, x1 + 1)):
            if row[x][0] not in (" ", ""):
                sx += x
                sy += y
                n += 1
    if not n:
        return (0.0, 0.0, 0)
    return (sx / n, sy / n, n)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", type=float, default=15.0)
    ap.add_argument("--span", type=float, default=0.6)
    ap.add_argument("--rates", default="24,48,96,240")
    ap.add_argument("--box", help="X0,Y0,X1,Y1 of the region to watch (default: whole screen)")
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    rates = [float(v) for v in a.rates.split(",")]
    box = tuple(int(v) for v in a.box.split(",")) if a.box else (0, 0, cols - 1, rows - 1)

    gc.disable()
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()
    # 后期关掉：这一检验问的是排期本身动了几步，不是后期层抖了几下
    T.FX.update(on=False, reveal=False, mech=False, trail=False, vig=False, shake=False)

    lo, hi = a.at, a.at + a.span
    row = SP.row_at((lo + hi) / 2)
    print(f"窗口 {lo:.2f}-{hi:.2f} s   {row['name'] if row else '-'}   观察区 {box}")
    print()
    print(f"{'rate':>6} {'frames':>7} {'不同质心值':>11} {'不同墨迹数':>11} {'质心行程(格)':>13} "
          f"{'单步中位(格)':>13}")
    for fps in rates:
        n = max(2, int(a.span * fps))
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        for k in range(4):
            T.draw(s, data, eng, lo - 0.4 + k * 0.01, True, fps)
            s.render_diff(sink)
        cent, ink = [], []
        for k in range(n):
            T.draw(s, data, eng, lo + k * a.span / n, True, fps)
            s.render_diff(sink)
            cx, cy, m = ink_centroid(s, box)
            cent.append((round(cx, 4), round(cy, 4)))
            ink.append(m)
        steps = []
        for i in range(1, len(cent)):
            dx = abs(cent[i][0] - cent[i - 1][0])
            dy = abs(cent[i][1] - cent[i - 1][1])
            steps.append((dx * dx + dy * dy) ** 0.5)
        steps.sort()
        travel = sum(steps)
        median = steps[len(steps) // 2] if steps else 0.0
        print(f"{fps:6.0f} {n:7d} {len(set(cent)):11d} {len(set(ink)):11d} "
              f"{travel:13.2f} {median:13.4f}")


if __name__ == "__main__":
    main()
