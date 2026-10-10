"""`--dissolve` 真的生效了吗？在真实的转场上量它改了多少格、花多少时间。

三件事：

  1. **它必须真的改画面**——否则就是一段没接上的开关（这个仓库里踩过一次：`period` 写了却
     因为缓存每帧被清而完全不起作用，是探针抓出来的）；
  2. **它不能把 `CLEAR` 矩形（歌词条、左侧窗口）也溶掉**——那两处是"要读的字，不是看的画"，
     `fx_reveal` 特意在最后整块拷回新帧。溶解必须尊重那条边界；
  3. **成本**——每次转场一次约 0.7 ms，之后每帧应当近乎零。

    python _dev/probe_dissolve.py
    python _dev/probe_dissolve.py --at 62.5
"""
from __future__ import annotations

import argparse
import gc
import io
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

OUT = ROOT / "_dev" / "out" / "dissolve"
# 几个已知有转场的时刻（`shot` 边界）
CUTS = [12.5, 61.0, 66.0, 147.4, 195.0]


def setup(cols, rows):
    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    return T, T.Engine(), T.Data()


def run(T, eng, data, cols, rows, t0, frames, dissolve):
    """从 t0 起跑 frames 帧，返回 (最后的屏, 每帧 ms)。"""
    T.DISSOLVE[0] = dissolve
    dt = 1.0 / T.FPS
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    ms = []
    for k in range(frames):
        t = t0 + k * dt
        a = time.perf_counter()
        T.draw(s, data, eng, t, True, T.FPS)
        b = time.perf_counter()
        s.render_diff(sink)
        c = time.perf_counter()
        ms.append((c - a) * 1000)
        del b
    return s, ms


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", type=float, help="one moment only")
    ap.add_argument("--frames", type=int, default=16)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args()
    cols, rows = (int(v) for v in a.size.lower().split("x"))
    moments = [a.at] if a.at is not None else CUTS

    gc.disable()
    T, eng, data = setup(cols, rows)
    try:
        import tui_live as _T
        CLEAR = _T.CLEAR
    except Exception:
        CLEAR = ()

    print(f"{cols}x{rows}  {a.frames} 帧/时刻")
    print()
    print(f"{'t0':>7} {'改动格':>8} {'占全屏':>7} {'落在 CLEAR 内':>13} {'开 ms':>7} {'关 ms':>7}  pane")
    for t0 in moments:
        s_off, ms_off = run(T, eng, data, cols, rows, t0, a.frames, False)
        s_on, ms_on = run(T, eng, data, cols, rows, t0, a.frames, True)

        # 只比较"转场还开着"的那些帧：最后一帧可能两边都已收敛
        changed = in_clear = 0
        for y in range(rows):
            ro, rn = s_off.buf[y], s_on.buf[y]
            for x in range(cols):
                if ro[x] == rn[x]:
                    continue
                changed += 1
                for (cx0, cy0, cx1, cy1) in CLEAR:
                    if cy0 <= y <= cy1 and cx0 <= x <= cx1:
                        in_clear += 1
                        break
        import school_panels as SP
        row = SP.row_at(t0)
        print(f"{t0:7.1f} {changed:8d} {100 * changed / (cols * rows):6.1f}% "
              f"{in_clear:13d} {statistics.median(ms_on):7.1f} {statistics.median(ms_off):7.1f}  "
              f"{row['name'] if row else '-'}")

        if not a.no_png and a.at is not None:
            import art_probe
            from PIL import Image, ImageDraw
            OUT.mkdir(parents=True, exist_ok=True)
            io_ = art_probe.draw_cells(s_off.buf, cols, rows)
            in_ = art_probe.draw_cells(s_on.buf, cols, rows)
            gap = 6
            cmp_im = Image.new("RGB", (io_.width, io_.height * 2 + gap), (30, 30, 30))
            cmp_im.paste(io_, (0, 0))
            cmp_im.paste(in_, (0, io_.height + gap))
            ImageDraw.Draw(cmp_im).text((8, io_.height + 2),
                                        "above: normal reveal   below: fbm dissolve",
                                        fill=(230, 230, 120))
            cmp_im.save(OUT / f"cmp_{t0:06.2f}.png")
            print(f"        对照图 {OUT / f'cmp_{t0:06.2f}.png'}")
    print()
    print("读法：'改动格' 必须明显大于 0（否则开关没接上）；")
    print("      '落在 CLEAR 内' 应当为 0 —— 歌词条与左侧窗口是'要读的字'，不该被溶解。")


if __name__ == "__main__":
    main()
