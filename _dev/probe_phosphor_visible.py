"""余晖是**时间上的**效果——单帧比不出来，必须连着跑几帧看"字走了有没有留痕"。

`probe_x_visible.py` 是单帧比较，它能看到余晖与底噪**叠在一起**的总差异，
但分不出"余晖到底起了多少作用"。而余晖恰恰是三个里最容易被看见的那个
（它让字在移开之后还亮一会儿），所以它值不值得单独量：值。

做法：同一个 `Screen` 连跑 N 帧（余晖靠累积，不能每帧新建屏幕），
对照两次——开余晖 / 关余晖——比**同一帧**的缓冲差，并且看**空档里的残留**
（上一帧有内容、这一帧没有的格子）。

    python _dev/probe_phosphor_visible.py
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", type=float, default=61.5)
    ap.add_argument("--frames", type=int, default=12)
    ap.add_argument("--readme", default="0.2,0.1,0.05")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import school_phosphor as PH
    import tui_live as T

    cols, rows = 197, 52
    total = cols * rows
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()
    triple = tuple(float(v) for v in a.readme.split(","))

    def run(decay, frames):
        """连跑 frames 帧，返回逐帧缓冲快照（余晖需要同一块屏累积）。"""
        T.FX_STRENGTH[0] = triple
        T.FX_BUNDLE[0] = T._fx_bundle(triple)
        T.FX_LEVEL[0] = 1.0
        T._fx_level_apply()
        ph = None if decay is None else PH.Phosphor(cols, rows, decay=decay, enabled=True)
        T.FX_PHOSPHOR[0] = ph
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        snaps = []
        prev_t = None
        for k in range(frames):
            t = a.at + k / T.FPS
            dt = (t - prev_t) if prev_t is not None else 1.0 / T.FPS
            prev_t = t
            T.draw(s, data, eng, t, True, T.FPS)
            if ph is not None:
                ph.poke(s, dt)
                ph.ink(s)
            s.render_diff(sink)
            snaps.append([row[:] for row in s.buf])
        return snaps

    # 当前代码在 fx.json=0.2,0.1,0.05 下余晖的 decay 是 0.48；对照 0.72（最大手调）
    for label, decay in (("余晖关（对照）", None),
                         ("decay 0.48（--fx 0.2 的余晖）", 0.48),
                         ("decay 0.72（--fx 1.0 的余晖）", 0.72)):
        snaps = run(decay, a.frames)
        print(f"=== {label} ===")
        # 与"余晖关"的同一帧比
        ref = run(None, a.frames) if decay is not None else snaps
        for k in (3, 6, 11):
            if k >= len(snaps):
                continue
            d = sum(1 for y in range(rows) for x in range(cols)
                    if snaps[k][y][x] != ref[k][y][x])
            # 残留：这一帧是空格、而参考帧同一格有内容或颜色更亮
            extra = [luma(snaps[k][y][x][1]) for y in range(rows) for x in range(cols)
                     if snaps[k][y][x] != ref[k][y][x]]
            peak = max(extra) if extra else 0.0
            print(f"  第 {k:2d} 帧  与关余晖差 {d:6d} 格（{100 * d / total:5.1f}%）"
                  f"  峰值 luma {peak:6.1f}")
        print()

    print("读法：余晖关时三次都应报 0 格（同一份代码、同一帧，本来就该一样）。")
    print("      有差就说明余晖真的往缓冲里留了东西；差值大不大、峰值多亮，决定看不看得见。")


if __name__ == "__main__":
    main()
