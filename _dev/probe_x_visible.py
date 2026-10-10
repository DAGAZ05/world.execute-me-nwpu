"""用户那两个抱怨的**直接**判据：
  (1) `--fx 0.2,0.1,0.05` 相比"不给 --fx"，屏幕上多出多少格？
  (2) 按 `x` 的四个档位之间差多少格？

`probe_fx_visibility.py` 已经量过"相对全关"的量（很大），但那个参照是错的——
全关时屏幕本来就空，差多少格说明不了"看得见"。这里的参照是**不给 --fx 的默认画面**，
也就是用户平时的画面。

另外两件之前没做的：
  * **在真实转场时刻取帧**（dissolve 只在转场时起作用，在静止画面上测它永远是 0）；
  * 把 `x` 的相邻档位**两两**比，而不只是与全关比——用户按一次 `x` 看到的正是相邻差。

    python _dev/probe_x_visible.py
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T

    cols, rows = 197, 52
    total = cols * rows
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()

    # 找真实的转场时刻（切点），dissolve 在那里才起作用
    cuts = []
    prev = None
    t = 55.0
    while t < 70.0:
        row = SP.row_at(t)
        nm = row["name"] if row else None
        if prev is not None and nm != prev:
            cuts.append(t)
        prev = nm
        t += 1 / T.FPS
    print(f"55-70 s 之间的切点：{[round(c, 2) for c in cuts[:8]]}")
    print()

    def frame(t, triple, level):
        if triple is None:
            T.FX_STRENGTH[0] = None
            T.FX_BUNDLE[0] = None
        else:
            T.FX_STRENGTH[0] = triple
            T.FX_BUNDLE[0] = T._fx_bundle(triple)
        T.FX_LEVEL[0] = level
        T._fx_level_apply()
        s = T.Screen(cols, rows)
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(io.StringIO())
        return s

    def n_diff(a, b):
        return sum(1 for y in range(rows) for x in range(cols)
                   if a.buf[y][x] != b.buf[y][x])

    def split_diff(a, b):
        """把差异拆成"多出的字符"（底噪/余晖这类新增）与"只是颜色不同"。"""
        new_ch = col_only = 0
        for y in range(rows):
            for x in range(cols):
                ca, cb = a.buf[y][x], b.buf[y][x]
                if ca == cb:
                    continue
                if ca[0] != cb[0]:
                    new_ch += 1
                else:
                    col_only += 1
        return new_ch, col_only

    for label, triple in (("命令行 --fx 0.2,0.1,0.05", (0.2, 0.1, 0.05)),
                          ("fx.json 里那组 0.2,0.1,0.05", (0.2, 0.1, 0.05)),
                          ("中等 0.5,0.5,0.5", (0.5, 0.5, 0.5)),
                          ("全开 1,1,1", (1.0, 1.0, 1.0))):
        print("=" * 74)
        print(f"(1) {label}   vs   不给 --fx（默认）")
        print("=" * 74)
        print(f"  {'时刻':>8} {'性质':>6} {'差异格':>8} {'其中多出字符':>13} {'只是颜色':>9} {'占全屏':>7}")
        for label2, t in ([("静止", 61.5), ("静止", 148.5)] +
                          [("切点", c) for c in cuts[:2]]):
            fa, fb = frame(t, triple, 1.0), frame(t, None, 1.0)
            d = n_diff(fa, fb)
            new_ch, col_only = split_diff(fa, fb)
            print(f"  {t:8.2f} {label2:>6} {d:8d} {new_ch:13d} {col_only:9d} "
                  f"{100 * d / total:6.1f}%")
        print()

    print("=" * 74)
    print("(2) 按 x 的相邻档位（用 fx.json 那组 0.2,0.1,0.05）")
    print("=" * 74)
    triple = (0.2, 0.1, 0.05)
    frames = {}
    for lv in T.FX_LEVELS:
        frames[lv] = frame(61.5, triple, lv)
    names = [T._fx_level_name(v) for v in T.FX_LEVELS]
    for i in range(len(T.FX_LEVELS) - 1):
        d = n_diff(frames[T.FX_LEVELS[i]], frames[T.FX_LEVELS[i + 1]])
        new_ch, col_only = split_diff(frames[T.FX_LEVELS[i]], frames[T.FX_LEVELS[i + 1]])
        print(f"  {names[i]:>4} -> {names[i + 1]:<4}  差 {d:6d} 格"
              f"（{100 * d / total:5.1f}%）  其中多出字符 {new_ch:5d}，只是颜色 {col_only:5d}")
    print()
    print("  **判读**：`多出字符` 才是肉眼最容易看见的那一类（屏幕上凭空多了字）；")
    print("            `只是颜色` 在小色差下几乎看不出来——这一栏小就等于看不见。")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
