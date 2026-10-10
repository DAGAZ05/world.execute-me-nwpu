"""余晖到底改变了画面多少？把它量出来，不靠眼睛。

这个会话里没有可用的视觉模型，所以对照图只能写给用户看；**结论**必须由数字给。这个探针跑同一条
时间线两次（`school_phosphor` 开 / 关），然后逐格比较两个缓冲：

  * `changed`     两版的 (char, fg, bg) 有几格不同——改变了多少画面；
  * `only_bg`     其中只有背景色不同的格数——余晖本质上就是在改背景；
  * `mean_delta`  被改动的格子上，背景亮度平均变了多少（0..255）；
  * `max_delta`   最大的一格变了多少；
  * `darker`/`lighter`  变暗 / 变亮的格数。余晖落在浅色纸面上是压暗、落在深色底上是提亮，
    两个方向都应该出现，只剩一个方向就是参数错了。

    python _dev/probe_phosphor_delta.py
    python _dev/probe_phosphor_delta.py --frames 24 --decay 0.62
"""
from __future__ import annotations

import argparse
import gc
import io
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

MOMENTS = [(62.0, "lyric_band"), (66.5, "satisfaction"), (147.4, "execution_cut"),
           (195.0, "whale_fall"), (9.0, "pane_parameters")]


def setup(cols, rows):
    import tui_live as T
    import school_panels as SP
    import school_fx as FX
    import school_gate as G

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    return T, T.Engine(), T.Data()


def run(T, eng, data, cols, rows, t_end, frames, phosphor):
    dt = 1.0 / T.FPS
    t = t_end - frames * dt
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    for _ in range(frames):
        # **相位**：draw -> poke -> ink -> render_diff。见 school_phosphor 的模块文档：
        # draw 整屏重画，ink 放在它之前会被涂掉（实测 2,811 处写入活下来 0 处）。
        T.draw(s, data, eng, t, True, T.FPS)
        if phosphor is not None:
            phosphor.poke(s, dt)
            phosphor.ink(s)
        s.render_diff(sink)
        t += dt
    return s


def lum(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames", type=int, default=20)
    ap.add_argument("--decay", type=float, default=None)
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()
    cols, rows = (int(v) for v in a.size.lower().split("x"))

    gc.disable()
    T, eng, data = setup(cols, rows)
    import school_phosphor as PH
    if a.decay is not None:
        PH.DECAY = a.decay

    print(f"{cols}x{rows}  decay={a.decay if a.decay is not None else PH.DECAY}  "
          f"min_level={PH.MIN_LEVEL}  fg_share={PH.FG_SHARE}  {a.frames} 帧 / 时刻")
    print()
    print(f"{'时刻':>17} {'changed':>8} {'仅背景':>8} {'仅前景':>7} {'meanΔ':>7} {'maxΔ':>6} "
          f"{'darker':>7} {'lighter':>8}   变化最多的行")
    for t_end, label in MOMENTS:
        s_off = run(T, eng, data, cols, rows, t_end, a.frames, None)
        # 注意：`--decay` 必须显式传进构造函数。改模块常量 `PH.DECAY` 是没用的——
        # Python 在 `def __init__(..., decay=DECAY)` 时就把默认值绑死了（这里踩过一次，
        # 三个不同的 decay 量出了三个一模一样的结果）。
        ph = PH.Phosphor(cols, rows, decay=a.decay if a.decay is not None else PH.DECAY)
        s_on = run(T, eng, data, cols, rows, t_end, a.frames, ph)
        changed = only_bg = darker = lighter = 0
        deltas = []
        by_row: dict[int, int] = {}
        fg_only = 0
        for y in range(rows):
            ro, rn = s_off.buf[y], s_on.buf[y]
            for x in range(cols):
                co, cn = ro[x], rn[x]
                if co == cn:
                    continue
                changed += 1
                by_row[y] = by_row.get(y, 0) + 1
                if co[0] == cn[0] and co[1] == cn[1]:
                    only_bg += 1
                elif co[0] == cn[0] and co[2] == cn[2]:
                    fg_only += 1
                d = lum(cn[2]) - lum(co[2]) if co[0] == " " else lum(cn[1]) - lum(co[1])
                if d < 0:
                    darker += 1
                elif d > 0:
                    lighter += 1
                deltas.append(abs(d))
        top = sorted(by_row.items(), key=lambda kv: -kv[1])[:3]
        print(f"{label:>17} {changed:8d} {only_bg:8d} {fg_only:8d} "
              f"{statistics.fmean(deltas) if deltas else 0:7.1f} "
              f"{max(deltas) if deltas else 0:6.1f} {darker:7d} {lighter:8d}   "
              f"top rows {top}")


if __name__ == "__main__":
    main()
