"""进度条在**真实播放路径**下覆盖哪些帧？—— 每帧 `draw → render_diff`，与 `tui_live.main` 同序。

为什么要单独写一个：`_dev/probe_diff_at.py` 为了打印缓冲会连续 `draw` 多帧、
中间不 `render_diff`，于是"上一帧没被清掉的格子"会留在缓冲里，看起来像进度条跑到了黑屏上。
那是探针的残留，不是播放器的行为——**判据必须走和播放器一样的路径**：
每一帧 `draw()` 之后立刻 `render_diff()`（`tui_live.main` 就是这样），
并且每帧都用一个**新的** `Screen` 做交叉验证（新 Screen 里没有上一帧的任何东西）。

    python _dev/probe_bar_truth.py --from 193 --to 208
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="lo", type=float, default=193.0)
    ap.add_argument("--to", dest="hi", type=float, default=208.0)
    ap.add_argument("--size", default="197x52")
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

    def bar_at(t):
        s = T.Screen(cols, rows)          # 每帧全新，绝无残留
        sink = io.StringIO()
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
        for y in range(rows):
            ln = "".join(c[0] for c in s.buf[y])
            m = re.search(r"(\d{3})%", ln)
            if m:
                lab = ("EXECUTION" if "EXECUTION" in ln
                       else "RUNNING" if "RUNNING" in ln
                       else "loading" if "loading" in ln else "-")
                return y, int(m.group(1)), lab
        return None

    i0, i1 = int(a.lo * T.FPS), int(a.hi * T.FPS) + 1
    covered = []
    for i in range(i0, i1):
        t = i / T.FPS
        if bar_at(t):
            covered.append(t)
    print(f"{cols}x{rows}  {a.lo:.2f}-{a.hi:.2f}")
    print()
    if covered:
        runs = []
        start = prev = covered[0]
        for t in covered[1:]:
            if abs(t - prev - 1 / T.FPS) < 1e-6:
                prev = t
            else:
                runs.append((start, prev))
                start = prev = t
        runs.append((start, prev))
        print(f"进度条出现于 {len(covered)} 帧，{len(runs)} 段：")
        for s0, s1 in runs:
            print(f"  {s0:8.3f} - {s1:8.3f}   ({(s1 - s0) * T.FPS + 1:.0f} 帧)")
        print()
        print("前 3 帧与后 3 帧的读数：")
        for t in covered[:3] + covered[-3:]:
            print(f"  t={t:7.3f}  {bar_at(t)}")
    else:
        print("整段没有进度条。")


if __name__ == "__main__":
    main()
