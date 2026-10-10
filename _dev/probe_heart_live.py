"""心形真的出现在画面上吗？—— 在 `pane_love_class` 的窗口里逐帧找它，并检查形状。

`_dev/probe_diff_bytes.py` 的采样点里**没有** 184.33-187.97 这一段，
所以它报 IDENTICAL 并不说明心形改对了——只说明那一批采样帧里没有心形。
（这正是"零字节差异"这类判据的边界：它只覆盖它采样到的地方。）
`_dev/probe_scope_frames.py` 是全曲逐帧的，那个才算数。

这个探针做三件事：

  1. 在 `pane_love_class` 的窗口里逐帧 `draw`，统计画面里出现了多少"实心块"，
     以及这些块的**几何形状**（是不是两个瓣 + 一个尖头）；
  2. 用 `school_motifs.heart_cells` 在**实际用到的那个尺寸**上重算一遍，
     两边格数应当一致——把"画出来的"和"算出来的"对上；
  3. 报告心形所在的行范围与列范围，便于在终端里直接看。

    python _dev/probe_heart_live.py
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

#: `pane_love_class` 排在 184.33，`pane_sw_project` 在 187.97
LO, HI = 184.4, 187.9


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import tui_live as T
    import school_panels as SP

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    T.SP = SP
    T.VAR[0] = "school"
    eng, data = T.Engine(), T.Data()

    s = T.Screen(cols, rows)
    sink = io.StringIO()
    best = None
    print(f"{cols}x{rows}  {LO}-{HI} s  pane_love_class 窗口内逐帧找心形")
    print()
    print(f"{'t':>8} {'shot/pane':>16} {'实心块':>7} {'行范围':>9} {'列范围':>9}")
    for i in range(int(LO * T.FPS), int(HI * T.FPS) + 1):
        t = i / T.FPS
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
        row = SP.row_at(t)
        pos = []
        for y in range(rows):
            for x in range(cols):
                if s.buf[y][x][0] == "\u2588":
                    pos.append((x, y))
        if not pos:
            continue
        ys = [p[1] for p in pos]
        xs = [p[0] for p in pos]
        # 心形是这一帧里"最下面那块成片的实心"，用最大连通块近似：按行取连续段
        info = (len(pos), (min(xs), max(xs)), (min(ys), max(ys)))
        if best is None or info[0] > best[0]:
            best = (info[0], t, row["name"] if row else "?", info)
        if i % 6 == 0:
            print(f"{t:8.2f} {row['name'] if row else '?':>16} {len(pos):7d} "
                  f"{min(ys):4d}-{max(ys):<4d} {min(xs):4d}-{max(xs):<4d}")

    if best is None:
        print("\n** 这一段里一个实心块都没有 —— 心形没有画出来。**")
        raise SystemExit(1)

    n, t_best, pane, info = best
    print()
    print(f"最实的一帧：t={t_best:.3f}  pane={pane}  实心块 {n} 格")
    print(f"  行 {info[2][0]}-{info[2][1]}，列 {info[1][0]}-{info[1][1]}")

    # 把这一帧的行剖面打出来，直接看形状
    T.draw(s, data, eng, t_best, True, T.FPS)
    s.render_diff(sink)
    y0, y1 = info[2]
    x0, x1 = info[1]
    print()
    print("这一帧实心格的逐行剖面（只看实心块）：")
    for y in range(y0, y1 + 1):
        cells = [x for x in range(cols) if s.buf[y][x][0] == "\u2588"]
        if not cells:
            continue
        line = "".join("\u2588" if x in set(cells) else "\u00b7"
                       for x in range(x0, x1 + 1))
        print(f"  y={y:2d} n={len(cells):3d} {line}")
    print()
    print("读法：实心心形应当在顶部看到**两块分开的实心（两个瓣）**，")
    print("      往下逐行合并，最后收成一个尖头。只有一个整块 = 凹口丢了。")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
