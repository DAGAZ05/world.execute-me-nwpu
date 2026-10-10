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
    print(f"噪点基色 = (120, 150, 190) luma={luma((120, 150, 190)):.1f}")
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
                    # 基色比例 120:150:190，用它认底噪（其他层不走这个比）
                    if b > r and g > r and abs((g / max(1, r)) - 150 / 120) < 0.02 \
                            and abs((b / max(1, g)) - 190 / 150) < 0.02:
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


if __name__ == "__main__":
    main()
