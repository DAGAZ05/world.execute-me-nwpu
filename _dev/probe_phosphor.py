"""荧光余晖：同刻对照图 + 单帧成本。这是"加余晖"这个方向唯一的直接视觉证据。

跑同一条时间线两次，用**同一个** `Screen` 尺寸与同一批帧，唯一差别是 `school_phosphor` 开或关：

    关   每帧只有 `draw()`（现状：`fx_trail` 的同帧幽灵仍在，那是播放器本来就有的）
    开   每帧在 `draw()` 之前 `ph.ink(s)`，在之后 `ph.poke(s, dt)`

然后两件事各出一份：

  * **肉眼证据** `_dev/out/phosphor/<t>_off.png` 与 `_on.png`，用 `art_probe.draw_cells` 那套
    8x16 的格子栅格化（和项目里其他截图同一个字体、同一个尺寸，可以直接并排看）；
    再拼一张上下对照 `_dev/out/phosphor/<t>_compare.png`。
  * **成本数字**：开关两种情况下每帧的 `draw()` 毫秒数，以及 `ink`/`poke` 各自花掉多少。
    余晖要能进主线，就必须压在 2 ms 以内——这个项目里任何"每帧 10 ms"的装饰都会直接把
    24 fps 的预算吃掉（见 `_dev/probe_frame_profile.py`）。

    python _dev/probe_phosphor.py                     默认几个时刻
    python _dev/probe_phosphor.py --at 66.0 --frames 24
    python _dev/probe_phosphor.py --decay 0.55        更长的尾巴
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
sys.path.insert(0, str(ROOT / "_dev"))
os.environ.setdefault("PV_VARIANT", "school")

OUT = ROOT / "_dev" / "out" / "phosphor"

# 每个时刻选一段"正在动"的画面，这样余晖有东西可留
MOMENTS = [
    (62.0, "lyric_band"),        # 副歌，歌词在逐字打出来
    (147.4, "execution_cut"),    # 07 EXECUTION 的转场
    (195.0, "whale_fall"),       # 结尾她落下（终端流量最大的一段）
    (9.0, "pane_parameters"),    # 全场最慢的 pane 之一
]


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
    return T, SP, T.Engine(), T.Data()


def run(T, eng, data, cols, rows, t_end, frames, phosphor):
    """跑 `frames` 帧到 `t_end`。

    相位是 draw -> poke -> ink -> render_diff（见 `school_phosphor` 的模块文档）：
    `draw` 每帧整屏重画，`ink` 放在它之前会被涂掉；`poke` 读的是上一帧 `render_diff` 收好的
    `s.dirty`；`render_diff` 放在最后，`prev` 里就会带着余晖、只发出它真正变了的那几格。
    """
    dt = 1.0 / T.FPS
    t = t_end - frames * dt
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    draw_ms, ink_ms, poke_ms = [], [], []
    for k in range(frames):
        t0 = time.perf_counter()
        T.draw(s, data, eng, t, True, T.FPS)
        b = time.perf_counter()
        if phosphor is not None:
            phosphor.poke(s, dt)
        c = time.perf_counter()
        if phosphor is not None:
            phosphor.ink(s)
        d = time.perf_counter()
        s.render_diff(sink)
        e = time.perf_counter()
        # "开"这一列的 draw 时间含 ink：它们是一起构成这一帧画面的
        draw_ms.append((d - t0) * 1000 if phosphor is not None else (e - t0) * 1000)
        ink_ms.append((d - c) * 1000)
        poke_ms.append((c - b) * 1000)
        t += dt
    return draw_ms, ink_ms, poke_ms, s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", type=float, help="one moment instead of the default four")
    ap.add_argument("--frames", type=int, default=20, help="frames to run into the moment")
    ap.add_argument("--decay", type=float, default=None, help="override the per-1/24 s retention")
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args()

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    moments = [(a.at, f"t{a.at:.1f}")] if a.at is not None else MOMENTS

    gc.disable()
    T, SP, eng, data = setup(cols, rows)
    import school_phosphor as PH
    if a.decay is not None:
        PH.DECAY = a.decay

    print(f"{cols}x{rows}  余晖保留 decay={PH.DECAY}  (每 1/24 s)  "
          f"下限 MIN_LEVEL={PH.MIN_LEVEL}  {a.frames} 帧")
    print()
    print(f"{'时刻':>16} {'关: draw ms':>12} {'开: draw ms':>12} {'ink ms':>8} {'poke ms':>8} "
          f"{'余晖格数':>9} {'新点燃':>8}")

    for t_end, label in moments:
        off_ms, _, _, s_off = run(T, eng, data, cols, rows, t_end, a.frames, None)
        ph = PH.Phosphor(cols, rows)
        on_ms, ink_ms, poke_ms, s_on = run(T, eng, data, cols, rows, t_end, a.frames, ph)
        st = ph.stats()
        print(f"{label:>16} {statistics.fmean(off_ms):12.1f} {statistics.fmean(on_ms):12.1f} "
              f"{statistics.fmean(ink_ms):8.2f} {statistics.fmean(poke_ms):8.2f} "
              f"{st['residue']:9d} {st['lit']:8d}")

        if not a.no_png:
            import art_probe
            OUT.mkdir(parents=True, exist_ok=True)
            tag = f"{t_end:06.2f}_{label}"
            im_off = art_probe.draw_cells(s_off.buf, cols, rows)
            im_on = art_probe.draw_cells(s_on.buf, cols, rows)
            im_off.save(OUT / f"{tag}_off.png")
            im_on.save(OUT / f"{tag}_on.png")
            # 上下对照，中间一条分隔线
            from PIL import Image, ImageDraw
            gap = 6
            cmp_im = Image.new("RGB", (im_off.width, im_off.height * 2 + gap), (30, 30, 30))
            cmp_im.paste(im_off, (0, 0))
            cmp_im.paste(im_on, (0, im_off.height + gap))
            d = ImageDraw.Draw(cmp_im)
            d.text((8, im_off.height + 2), "above: WITHOUT phosphor   below: WITH phosphor",
                   fill=(230, 230, 120))
            cmp_im.save(OUT / f"{tag}_compare.png")

    if not a.no_png:
        print()
        print(f"对照图写到 {OUT}")


if __name__ == "__main__":
    main()
