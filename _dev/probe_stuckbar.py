"""卡在 99% 的进度条：它真的停在 99%、真的不越界、以及在最后那句 execution 时真的变红。

提示词文档第 06 条（`world.execute-me-ascii-main/docs/prompts/creation-prompts.md`）：
「03:12.5–03:31.9 加一个卡在99%的进度条动画，最后一句 execution 的时候进度条变成一个同风格的红色
execution」。在这个 cut 里那一段是 `shot_whale_fall`（193.54–205.54），最后一句 execution 落在
205.54 起的 `shot_last_execution`。

四件事必须成立，否则这个设计就是错的：

  1. **平台期精确等于 99%**——打印 `099%`，不是 98、更不是 100。打印 100 的话整个设计就没了；
  2. **有上涨过程**——出现过小于 99 的值，否则不是"涨到 99 然后卡住"而是"一直是 99"；
  3. **变红**——最后那句 execution 期间，条的颜色必须是红的那一支；
  4. **不被盖掉**——条所在的行上，`%03d%%` 与 `RUNNING` 都要真的读得到。

判据全部来自 `Screen.buf`（文本 + 颜色），不依赖视觉模型（本机两个读图通道都不可用）。

    python _dev/probe_stuckbar.py
    python _dev/probe_stuckbar.py --details        # 每帧打印条所在行与颜色
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

#: 进度条的平台期必须精确等于这个数
PLATEAU = 99


def sample(T, eng, data, t, cols, rows):
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    T.draw(s, data, eng, t, True, T.FPS)
    s.normalise()
    ent = eng.at(t)
    shot = ent[0].fn.__name__ if ent and ent[0] and ent[0].fn else "?"
    lines = s.text_dump().split("\n")
    pct = None
    bar_row = None
    for i, ln in enumerate(lines):
        m = re.search(r"\b(\d{3})%", ln)
        if m:
            pct = int(m.group(1))
            bar_row = i
            break
    label = "-"
    if bar_row is not None:
        ln = lines[bar_row]
        if "EXECUTION" in ln:
            label = "EXECUTION"
        elif "RUNNING" in ln:
            label = "RUNNING"
        elif "loading" in ln:
            label = "loading"
    # 条上 '█' 的颜色
    colour = None
    if bar_row is not None:
        for x in range(s.cols):
            if s.buf[bar_row][x][0] == "\u2588":
                colour = tuple(s.buf[bar_row][x][1])
                break
    return dict(t=t, shot=shot, pct=pct, label=label, row=bar_row, colour=colour,
                dump=s.text_dump())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--details", action="store_true")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import tui_live as T
    import school_panels as SP

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    T.SP = SP
    T.VAR[0] = "school"
    eng, data = T.Engine(), T.Data()

    times = (193.0, 193.6, 195.0, 197.0, 198.6, 200.0, 203.0, 205.0,
             205.6, 206.0, 206.6, 207.5)
    print(f"{cols}x{rows}  片尾进度条   RED={tuple(T.RED)}  ME_TEXT={tuple(T.ME_TEXT)}")
    print()
    print(f"{'t':>7} {'shot':>20} {'pct':>5} {'label':>8} {'colour':>18}")
    rows_out = []
    for t in times:
        r = sample(T, eng, data, t, cols, rows)
        rows_out.append(r)
        cs = str(r["colour"]) if r["colour"] else "-"
        print(f"{r['t']:7.1f} {r['shot']:>20} {str(r['pct']):>5} {r['label']:>8} {cs:>18}")
        if a.details and r["row"] is not None:
            print(f"         row {r['row']}: {r['dump'].split(chr(10))[r['row']][55:145]!r}")

    print()
    print("=== 断言 ===")
    ok = True
    whale = [r for r in rows_out if r["shot"] == "shot_whale_fall" and r["pct"] is not None]
    last = [r for r in rows_out if r["shot"] == "shot_last_execution"]
    pcts = [r["pct"] for r in whale]

    c1 = pcts and max(pcts) == PLATEAU and PLATEAU in pcts
    print(f"  1 平台期精确 {PLATEAU}%（且不超过）：{'PASS' if c1 else 'FAIL'}   {pcts}")
    ok &= c1

    c2 = any(p < PLATEAU for p in pcts)
    print(f"  2 有上涨过程（出现过 <{PLATEAU}）：{'PASS' if c2 else 'FAIL'}"
          f"   {sorted(set(p for p in pcts if p < PLATEAU))}")
    ok &= c2

    red = tuple(T.RED)
    # **不能用"颜色完全等于 RED"当判据**：条是在 `fx_apply`（影片自己的后期）之后画的，
    # 但整帧还要过一遍 vignette/扫描线，所以实测落在 (231, 53, 43) 而不是 (255, 59, 48)——
    # 那是红色被压暗一档，不是别的颜色。判据用"红通道占绝对主导"，这才是这个设计要的东西。
    def is_red(c):
        return c is not None and c[0] > 180 and c[0] > c[1] * 3 and c[0] > c[2] * 3

    c3 = bool(last) and all(is_red(r["colour"]) or r["colour"] is None for r in last)
    print(f"  3 execution 段变红（红通道主导）：{'PASS' if c3 else 'FAIL'}"
          f"   {[str(r['colour']) for r in last]}  桌面 RED={red}")
    ok &= c3

    c4 = all(r["pct"] is not None and r["label"] == "EXECUTION" for r in last)
    print(f"  4 execution 段条还在、标签换成 EXECUTION：{'PASS' if c4 else 'FAIL'}"
          f"   行号 {[r['row'] for r in last]} 标签 {[r['label'] for r in last]}")
    ok &= c4

    elsewhere = []
    for t in (100.0, 150.0, 175.0, 190.0, 208.5, 211.0):
        r = sample(T, eng, data, t, cols, rows)
        if r["pct"] is not None:
            elsewhere.append(t)
    c5 = not elsewhere
    print(f"  5 不在别的时刻出现：{'PASS' if c5 else 'FAIL'}   {elsewhere}")
    ok &= c5

    print()
    print("总体：", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
