"""噪声场的成本与长相：≤ 2 ms/帧是硬指标，另外出一张 PNG 供人眼判断。

两件事必须分开量：

  * **成本**——`tick`（整屏向量化）+ `field`（画进缓冲）。文档里承诺 ≤ 2 ms/帧，
    所以任何一次超过它的实现都得改，不能靠"看起来还行"；
  * **长相**——这个会话里没有可用的视觉模型，所以对照图只能交给人看。
    探针把它写到 `_dev/out/noise/`。

    python _dev/probe_noise_cost.py
    python _dev/probe_noise_cost.py --rounds 15 --scale 10
"""
from __future__ import annotations

import argparse
import gc
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

OUT = ROOT / "_dev" / "out" / "noise"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", type=int, default=11)
    ap.add_argument("--scale", type=float, default=14.0)
    ap.add_argument("--octaves", type=int, default=3)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args()

    import numpy as np
    import school_noise as NZ

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    gc.disable()

    print(f"{cols}x{rows}  {a.rounds} 轮 / 每个组合。`tick` 是整屏向量化，"
          f"`field` 是把字符写进缓冲（每格一个元组，这部分必然是 Python）。")
    print()
    print(f"{'octaves':>8} {'scale':>7} {'tick ms':>9} {'field ms':>9} {'合计':>7} "
          f"{'值域':>15}  判定")
    # octaves 与 scale 是仅有的两个旋钮：倍频数线性影响 tick 的哈希次数，
    # scale 只改变场的"块大小"、不影响成本，所以它是可以自由选的那个。
    combos = [(1, 14.0), (2, 14.0), (3, 14.0), (2, 8.0), (2, 22.0), (3, 8.0)]
    best = None
    for oct_n, scale in combos:
        nz = NZ.Noise(cols, rows, seed=7, scale=scale, octaves=oct_n)
        tick_ms = []
        for r in range(a.rounds):
            t = r * 0.37
            t0 = time.perf_counter()
            nz.tick(t)
            tick_ms.append((time.perf_counter() - t0) * 1000)

        import tui_live as T
        s = T.Screen(cols, rows)
        field_ms = []
        for r in range(a.rounds):
            nz.tick(r * 0.37)
            t0 = time.perf_counter()
            nz.field(s, level=0.55)
            field_ms.append((time.perf_counter() - t0) * 1000)

        tk, fd = statistics.median(tick_ms), statistics.median(field_ms)
        st = nz.stats()
        total = tk + fd
        ok = "OK" if total <= 2.0 else "超预算"
        print(f"{oct_n:8d} {scale:7.1f} {tk:9.2f} {fd:9.2f} {total:7.2f} "
              f"{st['mn']:6.3f}..{st['mx']:<7.3f} {ok}")
        if best is None or total < best[0]:
            best = (total, oct_n, scale)

    print()
    print(f"最省的是 octaves={best[1]} scale={best[2]}：{best[0]:.2f} ms")
    print("注：scale 不改变成本，只改变场的块大小，所以它是可以按观感自由选的那个；"
          "倍频数才是成本的旋钮。")

    # 等频化（threshold 用的那张分位表）是额外的一次 argsort，单独量
    nz = NZ.Noise(cols, rows, seed=7, scale=14.0, octaves=2)
    q_ms = []
    for r in range(a.rounds):
        nz.tick(r * 0.37)
        t0 = time.perf_counter()
        nz.quantile_field()
        q_ms.append((time.perf_counter() - t0) * 1000)
    print(f"  quantile_field (等频化, 只在场重算后做一次)  median "
          f"{statistics.median(q_ms):6.2f} ms")

    if a.no_png:
        return
    import art_probe
    OUT.mkdir(parents=True, exist_ok=True)
    import tui_live as T
    for name, kwargs in (
        ("A_bare", None),
        ("B_oct3_scale14", dict(scale=14.0, octaves=3)),
        ("C_oct2_scale14", dict(scale=14.0, octaves=2)),
        ("D_oct1_scale14", dict(scale=14.0, octaves=1)),
        ("E_oct2_scale22", dict(scale=22.0, octaves=2)),
        ("F_oct2_scale8", dict(scale=8.0, octaves=2)),
    ):
        scr = T.Screen(cols, rows)
        if kwargs is not None:
            n = NZ.Noise(cols, rows, seed=7, **kwargs)
            n.tick(3.3)
            n.field(scr, level=0.6)
        art_probe.draw_cells(scr.buf, cols, rows).save(OUT / f"{name}.png")
    print()
    print(f"预览写到 {OUT}（A 是不画噪声的对照，B–F 是同一时刻的不同组合）")

    # 阈值 mask 的形状：给"溶解/显影"用，打印成字符让人看形状
    nz = NZ.Noise(cols, rows, seed=7)
    nz.tick(3.3)
    for p in (0.25, 0.45, 0.65):
        m = nz.threshold(p)
        print(f"  threshold({p}): 覆盖 {100 * m.mean():5.1f}% 的格子")
        if p == 0.45:
            for y in range(0, rows, 3):
                print("    " + "".join("#" if m[y][x] else "." for x in range(0, cols, 2)))


if __name__ == "__main__":
    main()
