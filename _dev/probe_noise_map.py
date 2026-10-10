"""把"底噪到底画在哪、长什么样"直接画出来——一张终端里的 ASCII 地图。

逻辑已经证明是通的（`run.cmd --fx 0.2,0.1,0.05` 三层都报 on、每帧多出 3400-6400 格），
但用户仍然说"一个特效都没有"。所以要看**画出来的东西**，而不是看计数。

这个探针输出两样：

  1. **底噪分布图**：屏幕上哪些格是底噪（`#`）、哪些是内容（`.`）、哪些是空（空格）。
     底噪只画在**空格**上，所以如果内容本来就铺满屏幕，底噪就无处可画——
     这一张图能一眼看出是不是这个原因。
  2. **字形直方图**：底噪用的 ramp 字符分布。底噪的 ramp 首字符是空格，
     所以"画了多少格"与"看起来有多少东西"是两回事。

    python _dev/probe_noise_map.py
    python _dev/probe_noise_map.py --fx 0.2,0.1,0.05 --at 61.5
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fx", default="0.2,0.1,0.05")
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

    triple = tuple(float(v) for v in a.fx.split(","))
    T.FX_STRENGTH[0] = triple
    T.FX_BUNDLE[0] = T._fx_bundle(triple)
    T.FX_LEVEL[0] = 1.0
    T._fx_level_apply()
    print(f"--fx {a.fx}  底噪={T.NOISE[0].scale if T.NOISE[0] else 'off'}"
          f"(stride {T._fx_params(triple)['noise_stride']})   @{a.at}s")
    print()

    def draw():
        s = T.Screen(cols, rows)
        T.draw(s, data, eng, a.at, True, T.FPS)
        s.render_diff(io.StringIO())
        return s

    # 带底噪
    s_on = draw()
    # 不带底噪（同一帧，只关底噪）
    keep = T.NOISE[0]
    T.NOISE[0] = None
    s_off = draw()
    T.NOISE[0] = keep

    # 底噪格 = 只有底噪时才有的字符
    noise = set()
    for y in range(rows):
        for x in range(cols):
            if s_on.buf[y][x] != s_off.buf[y][x]:
                noise.add((x, y))

    # 内容格：不带底噪时就不是空格
    content = set()
    for y in range(rows):
        for x in range(cols):
            if s_off.buf[y][x][0] not in (" ", ""):
                content.add((x, y))

    print(f"底噪格 {len(noise)}   内容格 {len(content)}   全屏 {cols * rows}")
    # 底噪的 box 是 (0,1,cols-1,rows-5)，看它在这个框里占多少空格
    bx0, by0, bx1, by1 = 0, 1, cols - 1, rows - 5
    box_cells = (bx1 - bx0 + 1) * (by1 - by0 + 1)
    box_content = sum(1 for (x, y) in content if bx0 <= x <= bx1 and by0 <= y <= by1)
    print(f"底噪允许的框 {bx0},{by0}..{bx1},{by1} = {box_cells} 格，"
          f"其中内容占 {box_content} 格（{100 * box_content / box_cells:.0f}%），"
          f"空格 {box_cells - box_content} 格")
    print(f"框内的空格里有 {len(noise)} 格被底噪填上"
          f"（{100 * len(noise) / max(1, box_cells - box_content):.0f}%）")
    print()

    # 字形直方图
    from collections import Counter
    hist = Counter(s_on.buf[y][x][0] for (x, y) in noise)
    print("底噪用的字形分布（ramp = %r）：" % NZ.RAMP)
    for ch in NZ.RAMP:
        n = hist.get(ch, 0)
        bar = "#" * min(60, n // 20)
        print(f"  {ch!r:>5}  {n:5d}  {bar}")
    other = {k: v for k, v in hist.items() if k not in NZ.RAMP}
    if other:
        print(f"  （其他 {sum(other.values())} 格：{list(other)[:6]}）")
    print()

    # 分布图：每 2 列取 1（宽 197 -> 99），行全要
    print("分布图（# = 底噪  · = 内容  空格 = 空）  每 2 列取 1：")
    for y in range(rows):
        line = []
        for x in range(0, cols, 2):
            if (x, y) in noise:
                line.append("#")
            elif (x, y) in content:
                line.append("·")
            else:
                line.append(" ")
        print("  " + "".join(line).rstrip())
    print()
    print("读法：底噪只填空格。如果一屏里内容本来就占满（· 多），底噪就没有位置可画——")
    print("      那种时候调 `noise` 强度是没用的，要调的是**画什么内容**。")


if __name__ == "__main__":
    main()
