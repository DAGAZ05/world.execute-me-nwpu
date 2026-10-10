"""一帧 23 ms 到底花在哪？—— 按**函数**归因，而不是只看 `draw` / `render_diff` 两半。

已知（本会话量过）：
  * 一帧中位数 21-33 ms（多数窗口 22-24 ms），`FPS_CAP = 60` 但机器给不了；
  * `render_diff` 占 29-49%；
  * `draw` 占剩下的大头，**但从没被按函数拆开量过**。

这个探针用 `sys.setprofile` 做**调用级归因**（不是 cProfile 的百分比，而是
"每个函数的**自身**耗时之和 / 帧数"），因为 cProfile 在这个项目里已经被证明会误导
（同一段代码两轮报 8.39 ms 与 4.53 ms）。这里的原则是：**多轮取中位数**，且
把 `clock` 的开关当成一次 A/B。

    python _dev/probe_draw_attribution.py
    python _dev/probe_draw_attribution.py --rounds 5 --window 61.0,62.0
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

WINDOWS = ["14.0,16.0", "56.8,58.0", "61.0,62.0", "147.0,148.0", "184.4,186.0", "195.0,196.0"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window")
    ap.add_argument("--windows", nargs="*", default=WINDOWS)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--top", type=int, default=12)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    gc.disable()
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()
    windows = [a.window] if a.window else a.windows

    print(f"{cols}x{rows}  {a.rounds} 轮")
    print()
    for spec in windows:
        lo, hi = (float(v) for v in spec.split(","))
        frames = max(2, int((hi - lo) * T.FPS))
        row = SP.row_at((lo + hi) / 2)
        pane = row["name"] if row else "?"

        # ---- 逐函数归因：sys.setprofile 记每个函数"进入→退出"的自身时间
        best = None
        for r in range(a.rounds):
            s = T.Screen(cols, rows)
            sink = io.StringIO()
            for k in range(min(6, frames)):          # 预热
                T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, T.FPS)
                s.render_diff(sink)
            self_ms = {}
            depth = [0]
            stack = []

            def prof(frame, event, arg):
                if event == "call":
                    stack.append([frame.f_code.co_qualname, time.perf_counter(), 0.0])
                    depth[0] += 1
                elif event == "return":
                    if stack:
                        name, t0, kids = stack.pop()
                        depth[0] -= 1
                        dt = (time.perf_counter() - t0) * 1000.0
                        self_ms[name] = self_ms.get(name, 0.0) + (dt - kids)
                        if stack:
                            stack[-1][2] += dt
                return prof

            total = []
            sys.setprofile(prof)
            try:
                for k in range(frames):
                    t = lo + k * (hi - lo) / frames
                    t0 = time.perf_counter()
                    T.draw(s, data, eng, t, True, T.FPS)
                    s.render_diff(sink)
                    total.append((time.perf_counter() - t0) * 1000.0)
            finally:
                sys.setprofile(None)
            med = statistics.median(total)
            scaled = {k: v / len(total) for k, v in self_ms.items()}
            if best is None or med < best[0]:
                best = (med, scaled, len(total))

        med, per, n = best
        cover = sum(v for k, v in per.items()
                    if not k.startswith(("tui_live.draw", "probe_", "<")))
        print(f"=== {lo:.1f}-{hi:.1f} s  {pane}   中位帧 {med:.1f} ms  ({n} 帧) ===")
        print(f"    归因覆盖 {cover:.1f} ms / 帧；逐函数自身耗时 top {a.top}：")
        for name, v in sorted(per.items(), key=lambda kv: -kv[1])[:a.top]:
            if v < 0.15:
                break
            print(f"      {v:8.2f} ms   {name}")
        print()


if __name__ == "__main__":
    main()
