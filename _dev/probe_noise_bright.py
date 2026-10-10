"""噪点实际画出来的亮度是多少？—— 量它，然后才决定调暗多少。

用户说"希望把噪点的颜色调暗"。`school_noise.field` 里颜色是
`(cr*k, cg*k, cb*k)`，`k = v * level`：`v` 是场值、`level` 是强度。所以"调暗"有两个旋钮
（基色 `colour` 与 `level`），而**改哪个、改多少**要看现在画出来是什么样。

这个探针把一帧里**所有噪点格**的前景色收集起来，报：
  * 最暗 / 中位 / 最亮的 RGB 与亮度；
  * 与背景 `BG`、正文 `UI` 的距离——因为"噪点太亮"的实质是"它离正文太近"，
    而不是它的绝对值大；
  * 按若干候选增益（乘在基色上）重算，看会落到哪里。

    python _dev/probe_noise_bright.py
"""
from __future__ import annotations

import argparse
import io
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

WINDOWS = ["61.0,62.0", "148.0,149.0", "184.4,186.0"]


def luma(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window")
    ap.add_argument("--windows", nargs="*", default=WINDOWS)
    ap.add_argument("--gains", nargs="*", type=float, default=[1.0, 0.7, 0.55, 0.4, 0.28])
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import school_fx as FX
    import school_gate as G
    import school_noise as NZ
    import school_panels as SP
    import tui_live as T

    cols, rows = 197, 52
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()

    print(f"背景 BG={T.BG} luma={luma(T.BG):.1f} · 正文 UI={T.UI} luma={luma(T.UI):.1f}")
    import school_noise as NZ
    base = NZ.BASE_COLOUR
    print(f"噪点基色 = {base} luma={luma(base):.1f}")
    print(f"当前噪声增益 = {T.NOISE_GAIN_RUNTIME[0]:g}"
          f"（来源：{'data/fx.json' if T._fx_read_gain() is not None else '默认'}）")
    print()

    # 认底噪的格：**不能靠固定色比**。第一版写死了 120:150:190 那个比，
    # 基色一改（批 94）就认不出来了，于是"噪点格"从 534 掉到 153——那是探针的形状，
    # 不是画面的变化。改成"从 `BASE_COLOUR` 按当前 gain 推出的色相比例"，两个旋钮都跟着走。
    ratio = (base[0] / base[2], base[1] / base[2])
    print(f"识别底噪用的色比 (r/b, g/b) = ({ratio[0]:.4f}, {ratio[1]:.4f})")
    print()

    for spec in ([a.window] if a.window else a.windows):
        lo, hi = (float(v) for v in spec.split(","))
        t = lo + (hi - lo) / 2
        row = SP.row_at(t)
        for level in (0.5, 1.0):
            T.NOISE[0] = NZ.Noise(cols, rows, seed=7, scale=14.0)
            s = T.Screen(cols, rows)
            sink = io.StringIO()
            T.draw(s, data, eng, t, True, T.FPS)      # 先让画面成型（底噪在 draw 里画）
            s.render_diff(sink)
            # 重画一次底噪，好把它的格子单独取出来：用一个只记不改的探针不行，
            # 所以直接对缓冲扫——底噪是唯一用基色 (120,150,190) 系调出来的层。
            cells = []
            for y in range(rows):
                for x in range(cols):
                    c = s.buf[y][x]
                    if c[0] == " ":
                        continue
                    r, g, b = c[1]
                    if b < 8:
                        continue
                    # 基色的色相比例，容差 3%——整数取整会让暗色偏离得多一点
                    if abs((r / b) - ratio[0]) < 0.03 and abs((g / b) - ratio[1]) < 0.03:
                        cells.append((r, g, b))
            if not cells:
                print(f"=== {spec} @{t:.1f}s level={level}  {row['name'] if row else '?'} ===")
                print("    没找到底噪格（未开启或全被内容盖住）")
                print()
                continue
            lum = sorted(luma(c) for c in cells)
            mx = max(cells, key=luma)
            print(f"=== {spec} @{t:.1f}s level={level}  {row['name'] if row else '?'} ===")
            print(f"    噪点格 {len(cells)} 个；亮度 min {lum[0]:5.1f}  "
                  f"p50 {lum[len(lum) // 2]:5.1f}  max {lum[-1]:5.1f}")
            print(f"    最亮的一格 RGB={mx}")
            print(f"    相对：比背景亮 {lum[-1] - luma(T.BG):5.1f}，"
                  f"比正文暗 {luma(T.UI) - lum[-1]:5.1f}")
            print("    若把基色乘上增益：")
            for g in a.gains:
                c = tuple(int(v * g) for v in mx)
                print(f"      gain {g:4.2f}  ->  最亮 RGB={str(c):>18}  luma {luma(c):5.1f}  "
                      f"（正文 {luma(T.UI):.0f} 的 {100 * luma(c) / luma(T.UI):4.1f}%）")
            print()


    print()
    print("=== `noise_gain` 扫描：它真的在起作用吗？（真跑一遍 draw，不是算比例）===")
    import school_noise as NZ2
    t = 61.5
    row = SP.row_at(t)
    print(f"  @{t:.1f}s  {row['name'] if row else '?'}")
    print(f"  {'gain':>6} {'噪点格':>8} {'min':>7} {'p50':>7} {'max':>7} {'最亮 = 正文的':>13}")
    prev = None
    monotone = True
    for g in (0.4, 0.6, 0.8, 1.0, 1.4, 2.0):
        T.NOISE_GAIN_RUNTIME[0] = g
        T.FX_STRENGTH[0] = (0.6, 0.4, 1.0) if T.FX_STRENGTH[0] else None
        T.FX_BUNDLE[0] = T._fx_bundle(T.FX_STRENGTH[0]) if T.FX_STRENGTH[0] else None
        T.FX_LEVEL[0] = 1.0
        T._fx_level_apply()
        if T.NOISE[0] is None:
            continue
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
        got = []
        for y in range(rows):
            for x in range(cols):
                c = s.buf[y][x]
                if c[0] == " " or c[1][2] < 8:
                    continue
                r, gg, b = c[1]
                if abs((r / b) - ratio[0]) < 0.03 and abs((gg / b) - ratio[1]) < 0.03:
                    got.append(luma(c[1]))
        if not got:
            print(f"  {g:6.2f}  （没有底噪格）")
            continue
        got.sort()
        mx = got[-1]
        if prev is not None and mx < prev - 0.5:
            monotone = False
        prev = mx
        print(f"  {g:6.2f} {len(got):8d} {got[0]:7.1f} {got[len(got) // 2]:7.1f} {mx:7.1f} "
              f"{100 * mx / luma(T.UI):12.1f}%")
    print()
    print(f"  最亮随 gain 单调不减：{'PASS' if monotone else 'FAIL'}")


if __name__ == "__main__":
    main()
