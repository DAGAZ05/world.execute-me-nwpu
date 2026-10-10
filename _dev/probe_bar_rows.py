"""进度条到底在哪一行、在哪些时刻？—— 逐帧扫全屏找 `\\d{3}%`。

背景：`_dev/probe_stuckbar.py` 的断言全过，但 `_dev/probe_scope_frames.py` 说
"差异只落在 205.54-207.46"，也就是**whale_fall 那 12 秒似乎没有变化**。
两个结论不能同时是真的（进度条应该在整段都有）。原因是断言只采样了几个时刻，
而范围扫描才是"全曲每一帧"。

这个脚本把"哪一帧、哪一行、哪个百分比、什么标签"全列出来，用来判定进度条到底
覆盖了哪些时刻——不猜，直接看。

    python _dev/probe_bar_rows.py
    python _dev/probe_bar_rows.py --from 193 --to 208
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
    ap.add_argument("--every", type=int, default=4, help="每 N 帧打印一行")
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

    i0, i1 = int(a.lo * T.FPS), int(a.hi * T.FPS)
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    covered = []
    print(f"{cols}x{rows}  {a.lo:.2f}-{a.hi:.2f} s")
    print()
    print(f"{'t':>8} {'shot':>20} {'row':>4} {'pct':>5} {'label':>10}")
    for i in range(i0, i1 + 1):
        t = i / T.FPS
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
        ent = eng.at(t)
        nm = ent[0].fn.__name__ if ent and ent[0] and ent[0].fn else "?"
        hit = None
        for y in range(rows):
            ln = "".join(c[0] for c in s.buf[y])
            m = re.search(r"(\d{3})%", ln)
            if m:
                lab = ("EXECUTION" if "EXECUTION" in ln
                       else "RUNNING" if "RUNNING" in ln
                       else "loading" if "loading" in ln else "-")
                hit = (y, m.group(1), lab)
                break
        if hit:
            covered.append(t)
        if (i - i0) % a.every == 0 or (hit and i == i0):
            if hit:
                print(f"{t:8.2f} {nm:>20} {hit[0]:4d} {hit[1]:>5} {hit[2]:>10}")
            else:
                print(f"{t:8.2f} {nm:>20} {'-':>4} {'-':>5} {'-':>10}")

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
            print(f"  {s0:8.2f} - {s1:8.2f}  ({(s1 - s0) * T.FPS + 1:.0f} 帧)")
    else:
        print("整段没有出现进度条。")


if __name__ == "__main__":
    main()
