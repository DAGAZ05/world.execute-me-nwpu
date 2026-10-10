"""这些强度**看起来**有没有东西？—— 把"差多少格"和"差在哪、差多亮"分开量。

`probe_fx_repro.py` 已经证明逻辑是通的（`x` 确实在循环、三层确实在落值、与全关差 5031 格）。
但用户说"一个特效都没有"，所以问题是**可见性**，不是逻辑。

这一层要区分三件不同的事，它们最容易被混为一谈：

  1. **对 `x=0`（面板全关）差多少格** —— 大，但那说明不了什么：全关时屏幕本来就是空的；
  2. **对默认（不做任何 fx 参数）差多少格** —— **这才是"有没有多出东西"的正确参照**；
  3. **那些多出来的格有多亮、在什么字符上** —— 终端里"有格"不等于"看得见"。

第 2 条是关键：如果"给 `--fx` 低值"与"不给 `--fx`"的画面几乎一样，那用户说"没特效"
就是**对的描述**，而不是 bug。

    python _dev/probe_fx_visibility.py
    python _dev/probe_fx_visibility.py --triples 1,1,1 0.6,0.4,1 0.2,0.1,0.05
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

WINDOWS = [("14.0-16.0", 14.5), ("61.0-62.0", 61.5), ("148.0-149.0", 148.5),
           ("184.4-186.0", 185.0), ("195.5-196.5", 196.0)]


def luma(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--triples", nargs="*", default=["1,1,1", "0.6,0.4,1", "0.2,0.1,0.05"])
    ap.add_argument("--level", type=float, default=1.0)
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
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()

    def render(t):
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
        return s

    def set_fx(triple, level):
        T.FX_STRENGTH[0] = triple
        T.FX_BUNDLE[0] = T._fx_bundle(triple) if triple is not None else None
        T.FX_LEVEL[0] = level
        T._fx_level_apply()
        return render

    # 参照：不给任何 fx 参数（三层全关）——**这是"有没有多出东西"的正确基线**
    print("参照 = 不给 --fx、也没有 fx.json（三层全关，但后期 FX 照旧开着）")
    print()
    base = {}
    T.FX_STRENGTH[0] = None
    T.FX_BUNDLE[0] = None
    T.FX_LEVEL[0] = 1.0
    T._fx_level_apply()
    for label, t in WINDOWS:
        base[t] = render(t)

    for spec in a.triples:
        triple = tuple(float(v) for v in spec.split(","))
        p = T._fx_params(triple)
        T.FX_STRENGTH[0] = triple
        T.FX_BUNDLE[0] = T._fx_bundle(triple)
        T.FX_LEVEL[0] = a.level
        T._fx_level_apply()
        nz = T.NOISE[0]
        print("=" * 76)
        print(f"--fx {spec}   ->  phosphor={p['phosphor']}  noise={p['noise']}"
              f"(stride {p['noise_stride']})  dissolve={p['dissolve']}"
              f"   底噪{'on' if nz else 'off'}")
        print("=" * 76)
        print(f"  {'窗口':>12} {'多出/变化的格':>13} {'占全屏':>7} "
              f"{'其中底噪格':>10} {'底噪峰值luma':>12} {'底噪占正文':>10}")
        for label, t in WINDOWS:
            s = render(t)
            b = base[t]
            changed = [(x, y) for y in range(rows) for x in range(cols)
                       if s.buf[y][x] != b.buf[y][x]]
            # 底噪格：空格上被画了字符（内容格不会因为底噪而变，底噪只填空格）
            noise_cells = [(x, y) for (x, y) in changed if b.buf[y][x][0] == " "]
            lum = [luma(s.buf[y][x][1]) for (x, y) in noise_cells]
            peak = max(lum) if lum else 0.0
            print(f"  {label:>12} {len(changed):13d} {100 * len(changed) / (cols * rows):6.1f}% "
                  f"{len(noise_cells):10d} {peak:12.1f} {100 * peak / luma(T.UI):9.1f}%")
        print()

    print("读法：")
    print("  `多出/变化的格` 是相对'不给 --fx'多出来的量——**这才是用户能看见的东西**。")
    print("  `其中底噪格` = 原本是空格、被底噪填上的格（底噪只填空格，不覆盖内容）。")
    print("  底噪峰值占正文的百分比决定它看不看得见：15% 左右是可见的底纹，10% 以下基本糊掉。")


if __name__ == "__main__":
    main()
