"""心形的凹口（两个圆瓣之间的凹口）到底有多深？—— 逐行宽度剖面，与参考心形对照。

`(x²+y²-1)³ = x²y³` 那条隐含曲线被证明**根本没有凹口**（顶部 x 区间仍是 ±1.00），
所以本文件的心形改用经典参数曲线 `x=16sin³t, y=13cost−5cos2t−2cos3t−cos4t`。
但参数曲线也不一定够深：`_dev/probe_heart.py` 打出 26x22 的形状后，
顶部看起来仍是"圆冠"而不是"两个瓣 + 中间一个凹口"。

所以这里量两件事：

  1. **逐行宽度剖面**：每一行填充格的左右跨度。心形应当在靠近顶部出现
     "跨度先宽、中间窄"的特征（两个瓣），也就是**顶部的宽度不是单调收窄**；
  2. **凹口深度**：`y=0`（两瓣之间的最深点）与两瓣峰顶之间的高度差，
     换算成"在 w×h 的格子上占几行"。占不到一行就看不见，那就是分辨率问题而不是形状问题；
  3. **与参考形状对照**：直接用圆的并集减掉一个楔形造一个"标准心形"，
     比较两者在同样格子数下的宽度剖面，看差异有多大。

    python _dev/probe_heart_notch.py
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


def rows_of(cells, w, h):
    out = []
    for y in range(h):
        xs = [x for x in range(w) if (x, y) in cells]
        out.append((min(xs), max(xs), len(xs)) if xs else None)
    return out


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    # ---- 曲线自身的凹口深度（原始单位）
    def cy(t):
        return 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)

    t_notch = 0.0
    # 瓣峰：`cy(t) > cy(0)` 的那个解，取 `t ∈ (0, π)` 内使 `cy` 最大的一点。
    # **第一版把搜索写反了**（在 `cy(mid) > cy(0)` 为真时收窄右界），于是收敛到
    # "cy 恰好回到凹口高度" 的那一点，算出凹口深度 = 0.0000 —— 一个一眼就可疑的数。
    # 正确做法是直接对 `cy` 求极大：先粗扫再在极值邻域细分。
    N = 4000
    t_peak = max((math.pi * i / N for i in range(1, N)), key=cy)
    print("曲线自身：")
    print(f"  凹口底部 t={math.degrees(t_notch):.1f}°  y={cy(t_notch):+.4f}")
    print(f"  瓣峰     t={math.degrees(t_peak):.1f}°  y={cy(t_peak):+.4f}")
    depth = cy(t_peak) - cy(t_notch)
    print(f"  凹口深度 = {depth:.4f}（曲线总高 29.0）→ 占 {depth / 29.0 * 100:.1f}%")
    print()

    import school_motifs as M
    for (w, h) in ((26, 22), (26, 12), (14, 7), (40, 18)):
        cells = M.heart_cells(w, h)
        prof = rows_of(cells, w, h)
        print(f"参数心形 {w}x{h}：凹口深度占 {depth / 29.0 * h:.2f} 行")
        # 顶部几行的跨度
        head = [f"{p[2]}" if p else "-" for p in prof[:6]]
        print(f"  顶部 6 行填充格数：{head}")
        wide = [p[2] if p else 0 for p in prof]
        # 凹口是否可见：首行的宽度应当小于"最大值"的 60%
        if prof and prof[0]:
            w0, wmax = prof[0][2], max(wide)
            print(f"  首行 {w0} 格 / 最宽 {wmax} 格 = {w0 / max(1, wmax) * 100:.0f}%"
                  f"   （凹口可见需要明显 < 100%）")

    # ---- 参考心形：两个圆 ∪ 一个三角形尖，中间留一条楔形缝
    def ref_cells(w, h, notch_rows):
        """圆瓣 + 尖角，两瓣之间留出 `notch_rows` 行深的缝。"""
        out = set()
        for gy in range(h):
            # 归一化到 [0,1]x[0,1]
            u = gy / max(1, h - 1)
            v_len = 0.0
            for gx in range(w):
                v = (gx + 0.5) / w
                ux, uy = (v - 0.5) * 2.0, (u - 0.5) * 2.0
                # 上两个圆
                in_top = (ux + 0.5) ** 2 + (uy - 0.42) ** 2 <= 0.52 ** 2 or \
                         (ux - 0.5) ** 2 + (uy - 0.42) ** 2 <= 0.52 ** 2
                # 下三角
                in_bot = uy <= 0.42 and abs(ux) <= 0.5 * (uy + 1.0) / 1.42
                if in_top or in_bot:
                    v_len += 1
                    out.add((gx, gy))
        return out

    # ---- 把两条曲线在**相同格子数**下的顶部剖面并排打出来
    print()
    print("对照：同样 26x12 的格子，参数心形 vs 一个手工「标准心形」（两圆+尖角）")
    a = M.heart_cells(26, 12)
    b = ref_cells(26, 12, 2)
    pa, pb = rows_of(a, 26, 12), rows_of(b, 26, 12)
    print(f"{'行':>3} {'参数心形 左-右(格数)':>22} {'手工心形 左-右(格数)':>22}")
    for y in range(12):
        sa = f"{pa[y][0]:2d}-{pa[y][1]:2d} ({pa[y][2]:2d})" if pa[y] else "-"
        sb = f"{pb[y][0]:2d}-{pb[y][1]:2d} ({pb[y][2]:2d})" if pb[y] else "-"
        print(f"{y:3d} {sa:>22} {sb:>22}")


if __name__ == "__main__":
    main()
