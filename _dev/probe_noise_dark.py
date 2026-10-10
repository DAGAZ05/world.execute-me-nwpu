"""底噪调暗的**语义**判据：跑当前代码两次，一次默认增益、一次旧基色，比前景色。

## 为什么不能用 `probe_scope_frames.py`

那个探针比的是 `text_dump()` 的**文本**——底噪调暗只改**颜色**，字符一个不变，
所以它对这次改动**天然看不见**（它报 0 帧不同是正确的，什么也没证明）。
颜色类改动要用颜色的判据。

## 这个探针怎么判

不比较两个 git 版本（那要切换代码，风险大），而是**在同一个进程里**：
  1. 用当前代码画一帧，记下所有"像底噪"的格子的前景色（色相按 `BASE_COLOUR` 的比例认）；
  2. 把 `school_noise.BASE_COLOUR` 在内存里改回旧值 `(120,150,190)`、增益设 1.0，
     再画同一帧，记一遍；
  3. 要求：**格子集合完全相同**（调暗不改"画哪些格"，只改颜色），
     而**最亮的那格显著变暗**（旧 > 新）。

"格子集合相同"是这次改动**不该**碰的东西，把它当判据能挡住"顺手改了 floor/stride"这类错误。

    python _dev/probe_noise_dark.py
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


def luma(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def collect(T, SP, eng, data, t, cols, rows):
    """(格子集合, 每个格子的前景色)"""
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    T.draw(s, data, eng, t, True, T.FPS)
    s.render_diff(sink)
    cells, colours = set(), {}
    for y in range(rows):
        for x in range(cols):
            c = s.buf[y][x]
            if c[0] == " ":
                continue
            cells.add((x, y))
            colours[(x, y)] = c[1]
    return cells, colours


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", type=float, default=61.5)
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

    # 用"文件里的三层都开"来跑，这样底噪一定在画
    T.FX_STRENGTH[0] = (0.6, 0.4, 1.0)
    T.FX_BUNDLE[0] = T._fx_bundle(T.FX_STRENGTH[0])
    T.FX_LEVEL[0] = 1.0

    new_base = NZ.BASE_COLOUR
    old_base = (120, 150, 190)
    gain = T.NOISE_GAIN_RUNTIME[0]

    # --- 第一次：当前代码（新基色 × 默认增益）
    T._fx_level_apply()
    cells_new, col_new = collect(T, SP, eng, data, a.at, cols, rows)

    # --- 第二次：把基色与增益改回旧行为
    NZ.BASE_COLOUR = old_base
    T.NOISE_GAIN_RUNTIME[0] = 1.0
    T._fx_level_apply()
    cells_old, col_old = collect(T, SP, eng, data, a.at, cols, rows)

    # --- 第三次：全部还原，确认可复现
    NZ.BASE_COLOUR = new_base
    T.NOISE_GAIN_RUNTIME[0] = gain
    T._fx_level_apply()
    cells_again, col_again = collect(T, SP, eng, data, a.at, cols, rows)

    print(f"@{a.at:.1f}s  新基色 {new_base} × gain {gain:g}   vs   旧基色 {old_base} × gain 1.0")
    print()
    print(f"  非空格子数      新 {len(cells_new)}   旧 {len(cells_old)}"
          f"   还原后 {len(cells_again)}")
    print(f"  格子集合相同（新 vs 旧）：{'PASS' if cells_new == cells_old else 'FAIL'}"
          f"   差异 {len(cells_new ^ cells_old)} 格")
    print(f"  可复现（新 vs 还原后）：{'PASS' if cells_new == cells_again else 'FAIL'}")
    print()

    # 只看**底噪**格：按各自基色的色相比认。
    # 不能拿"全屏最亮格"当判据——那是正文（luma 212.5），它本来就不该变；
    # 第一版就是这么写的，于是报"峰值下降 0.0"、FAIL，而实际上下面的 per-cell 比较
    # 已经显示 3932 格颜色变了。**判据要盯着被改的那个东西。**
    def noise_lum(colours, base):
        rb, gb = base[0] / base[2], base[1] / base[2]
        out = []
        for k, c in colours.items():
            r, g, b = c
            if b < 6:
                continue
            if abs(r / b - rb) < 0.05 and abs(g / b - gb) < 0.05:
                out.append(luma(c))
        return sorted(out)

    ln = noise_lum(col_new, new_base)
    lo = noise_lum(col_old, old_base)
    print(f"  底噪格（按各自基色色相认）：新 {len(ln)} 个，旧 {len(lo)} 个")
    if ln and lo:
        print(f"    新  峰值 luma {ln[-1]:6.1f}   中位 {ln[len(ln) // 2]:6.1f}")
        print(f"    旧  峰值 luma {lo[-1]:6.1f}   中位 {lo[len(lo) // 2]:6.1f}")
        print(f"    峰值下降 {lo[-1] - ln[-1]:.1f} luma"
              f"（{100 * (1 - ln[-1] / max(1e-9, lo[-1])):.0f}%）"
              f"   中位下降 {lo[len(lo) // 2] - ln[len(ln) // 2]:.1f}")
        print(f"    占正文亮度：新 {100 * ln[-1] / luma(T.UI):.1f}%   "
              f"旧 {100 * lo[-1] / luma(T.UI):.1f}%")
    print()
    darker = bool(ln and lo and ln[-1] < lo[-1] - 20)
    print(f"  底噪峰值确实变暗（>20 luma）：{'PASS' if darker else 'FAIL'}")
    print(f"  非空格子总数没变：{'PASS' if len(cells_new) == len(cells_old) else 'FAIL'}")
    print(f"  画了哪些格子没变：{'PASS' if cells_new == cells_old else 'FAIL'}")


if __name__ == "__main__":
    main()
