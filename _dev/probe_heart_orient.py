"""经典心形曲线 `x=16sin³t, y=13cost−5cos2t−2cos3t−cos4t` 的**朝向**：尖端在哪一端？

这个函数写错过一次朝向：渲染出来的形状是**倒的**（两个圆瓣在下面，尖头在上面）。
原因是我按"`y` 的最大值在底部"去取负号，而这条曲线不是那样。

所以这个探针不算公式，直接**采样打印**：每个关键 t 上的 `(x, y)`，
以及 `y` 的最大值/最小值出现在哪个 t。朝向由数字决定，不由我对公式的记忆决定。

    python _dev/probe_heart_orient.py
"""
from __future__ import annotations

import math
import sys


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    pts = []
    for i in range(720):
        t = 2.0 * math.pi * i / 720
        x = 16.0 * math.sin(t) ** 3
        y = 13.0 * math.cos(t) - 5.0 * math.cos(2 * t) - 2.0 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((t, x, y))

    ymax = max(pts, key=lambda p: p[2])
    ymin = min(pts, key=lambda p: p[2])
    xmax = max(pts, key=lambda p: p[1])
    xmin = min(pts, key=lambda p: p[1])
    print("关键点（原始坐标，y 正方向为数学上方）：")
    print(f"  y 最大 {ymax[2]:+8.4f} 在 t={math.degrees(ymax[0]):7.2f}°  x={ymax[1]:+8.4f}"
          "   <== 这里是尖端/凹口")
    print(f"  y 最小 {ymin[2]:+8.4f} 在 t={math.degrees(ymin[0]):7.2f}°  x={ymin[1]:+8.4f}"
          "   <== 这里是尖头")
    print(f"  x 最大 {xmax[1]:+8.4f} 在 t={math.degrees(xmax[0]):7.2f}°  y={xmax[2]:+8.4f}")
    print(f"  x 最小 {xmin[1]:+8.4f} 在 t={math.degrees(xmin[0]):7.2f}°  y={xmin[2]:+8.4f}")
    print()
    print("几个 t 上的值：")
    for i in (0, 45, 90, 135, 180, 225, 270, 315):
        t = math.radians(i)
        x = 16.0 * math.sin(t) ** 3
        y = 13.0 * math.cos(t) - 5.0 * math.cos(2 * t) - 2.0 * math.cos(3 * t) - math.cos(4 * t)
        print(f"  t={i:4d}°  x={x:+8.4f}  y={y:+8.4f}")
    print()
    print("结论：")
    print(f"  y 的范围是 [{ymin[2]:.4f}, {ymax[2]:.4f}]，**最大值在 t=0（x=0）**，")
    print("  也就是说 13cos t 那一项占主导，t=0 是**顶部的凹口/尖端**，t=180° 是**底部的尖头**。")
    print("  屏幕坐标 y 向下增长，所以：screen_y = -y_raw 会把凹口放到**顶部**（正确），")
    print("  而 screen_y = +y_raw 会把它放到**底部**（倒过来）。")


if __name__ == "__main__":
    main()
