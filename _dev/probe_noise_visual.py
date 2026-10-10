"""把噪声底噪接进真实画面：它出现了吗？它改动多大？它花多少帧时间？

三件事，缺一件这个层就不能上：

  * **出现了**——`field` 报告的落笔格数 > 0，且落在"空旷处"而不是压在内容上；
  * **不覆盖内容**——对比开关两版，**只有原本是空格的格子**发生了变化；
    这一条是硬约束，破了就是"底噪把字盖了"；
  * **成本**——用 `_dev/probe_ab_frame.py` 那套多轮中位数，别用 cProfile。

    python _dev/probe_noise_visual.py
    python _dev/probe_noise_visual.py --scale 22 --at 66.0
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

OUT = ROOT / "_dev" / "out" / "noise"
# 每个时刻挑一段"有明显留白"的画面，底噪才有地方显示
MOMENTS = [(66.0, "satisfaction"), (9.0, "pane_parameters"), (195.0, "whale_fall"),
           (147.4, "execution_cut")]


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


def run(T, eng, data, cols, rows, t_end, frames, noise):
    """跑 `frames` 帧，返回 (屏, 每帧 draw 毫秒, 每帧 noise 毫秒)。"""
    import school_noise as NZ
    dt = 1.0 / T.FPS
    t = t_end - frames * dt
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    draw_ms, noise_ms = [], []
    for k in range(frames):
        T.NOISE[0] = noise
        t0 = time.perf_counter()
        T.draw(s, data, eng, t, True, T.FPS)
        draw_ms.append((time.perf_counter() - t0) * 1000)
        noise_ms.append(0.0 if noise is None else 0.0)
        T.NOISE[0] = None
        s.render_diff(sink)
        if noise is not None:
            noise.tick(t)                # 下一帧的场（draw 里会再 tick 一次，这里只为计时）
        t += dt
    return s, draw_ms, noise_ms


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=float, default=14.0)
    ap.add_argument("--at", type=float, help="one moment only")
    ap.add_argument("--frames", type=int, default=20)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args()

    import numpy as np
    import school_noise as NZ

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    moments = [(a.at, f"t{a.at:.1f}")] if a.at is not None else MOMENTS
    gc.disable()
    T, eng, data = setup(cols, rows)

    print(f"{cols}x{rows}  scale={a.scale}  octaves={NZ.OCTAVES}  {a.frames} 帧/时刻")
    print()
    print(f"{'时刻':>18} {'改动的格':>9} {'其中原本是空格':>14} {'压在非空格上':>13} "
          f"{'占全屏':>7} {'draw 开 ms':>11} {'draw 关 ms':>11}")
    for t_end, label in moments:
        s_off, ms_off, _ = run(T, eng, data, cols, rows, t_end, a.frames, None)
        # 成本用多轮中位数，别用单次
        off_med = statistics.median(ms_off)
        noise = NZ.Noise(cols, rows, seed=7, scale=a.scale)
        s_on, ms_on, _ = run(T, eng, data, cols, rows, t_end, a.frames, noise)
        on_med = statistics.median(ms_on)

        changed = on_blank = 0
        onto_ink = 0
        for y in range(rows):
            ro, rn = s_off.buf[y], s_on.buf[y]
            for x in range(cols):
                if ro[x] == rn[x]:
                    continue
                changed += 1
                if ro[x][0] == " ":
                    on_blank += 1
                else:
                    onto_ink += 1
        flag = "" if onto_ink == 0 else "   <-- 覆盖了内容！"
        print(f"{label:>18} {changed:9d} {on_blank:14d} {onto_ink:13d} "
              f"{100 * changed / (cols * rows):6.1f}% {on_med:11.1f} {off_med:11.1f}{flag}")

        if not a.no_png and a.at is not None:
            import art_probe
            from PIL import Image, ImageDraw
            OUT.mkdir(parents=True, exist_ok=True)
            im_off = art_probe.draw_cells(s_off.buf, cols, rows)
            im_on = art_probe.draw_cells(s_on.buf, cols, rows)
            gap = 6
            cmp_im = Image.new("RGB", (im_off.width, im_off.height * 2 + gap), (30, 30, 30))
            cmp_im.paste(im_off, (0, 0))
            cmp_im.paste(im_on, (0, im_off.height + gap))
            ImageDraw.Draw(cmp_im).text(
                (8, im_off.height + 2),
                "above: WITHOUT noise backdrop   below: WITH it", fill=(230, 230, 120))
            cmp_im.save(OUT / f"cmp_{t_end:06.2f}_{label}.png")
            print(f"      对照图 {OUT / f'cmp_{t_end:06.2f}_{label}.png'}")


if __name__ == "__main__":
    main()
