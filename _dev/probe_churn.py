"""一帧里**有多少格是真的需要重写的**？—— 这决定了"只写变化"能省多少。

## 为什么这是最后一块拼图

前面已经排除了：终端吞吐（一帧 23 KB，约 1-2 ms，不是瓶颈）、numpy 抽取（更慢）、
整屏 `fill`（去掉只省 1.0 ms 且破坏画面）、热函数微优化（每帧只值 0.6 ms）、
写入时脏位图（负收益）。

剩下的唯一方向是"**别整屏重画**"。但这条路的收益完全取决于一个数字：
**相邻两帧之间，屏幕上真正变化的格子占多少**。

  * 如果只变 10%，那么"只写变化"理论上能把这一帧的绘制成本砍到十分之一；
  * 如果变 80%，那这条路省不了多少，不值得动 24 个 pane。

这个探针量它，而且**分开量两件事**：
  1. **帧与帧之间**的差异（相邻 1/24 s），这是"不清屏"要面对的；
  2. **`fill` 抹掉的量**：整屏 10 244 格，其中上一帧本来是多少格**非空**——
     也就是"被 fill 白白重写、然后又用同样内容写回去"的格数。

第 2 项是关键：如果上一帧有 8 000 格非空，而这一帧的 8 000 格里 7 000 格内容一样，
那"整屏重写"就是在做 7 000 次无效劳动，而那些劳动正是 `render_diff` 要逐格比对的量。

    python _dev/probe_churn.py
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

WINDOWS = ["14.0,16.0", "61.0,62.0", "148.0,149.0", "184.4,186.0", "196.0,197.0"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window")
    ap.add_argument("--windows", nargs="*", default=WINDOWS)
    ap.add_argument("--size", default="197x52")
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
    total = cols * rows
    gc.disable()
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()
    windows = [a.window] if a.window else a.windows

    print(f"{cols}x{rows} = {total} 格")
    print()
    print(f"{'window':>14} {'pane':>22} {'相邻帧变格':>10} {'占全屏':>7} "
          f"{'上帧非空':>9} {'同格同内容':>10} {'重写但没变':>10}")
    for spec in windows:
        lo, hi = (float(v) for v in spec.split(","))
        frames = max(2, int((hi - lo) * T.FPS))
        row = SP.row_at((lo + hi) / 2)

        s = T.Screen(cols, rows)
        sink = io.StringIO()
        T.draw(s, data, eng, lo, True, T.FPS)
        s.render_diff(sink)

        churn, nonblank, same = [], [], []
        for k in range(1, frames):
            t = lo + k * (hi - lo) / frames
            prev = [r[:] for r in s.buf]
            T.draw(s, data, eng, t, True, T.FPS)
            s.render_diff(sink)
            diff = sum(1 for y in range(rows) for x in range(cols)
                       if s.buf[y][x] != prev[y][x])
            churn.append(diff)
            nb = sum(1 for y in range(rows) for x in range(cols)
                     if prev[y][x][0] not in (" ", ""))
            nonblank.append(nb)
            # 上一帧非空的格里，这一帧内容完全相同的（= 被整屏重写却白写）
            same.append(sum(1 for y in range(rows) for x in range(cols)
                            if prev[y][x][0] not in (" ", "")
                            and s.buf[y][x] == prev[y][x]))
        c = statistics.median(churn)
        nb = statistics.median(nonblank)
        sm = statistics.median(same)
        print(f"{spec:>14} {row['name'] if row else '?':>22} {c:10.0f} "
              f"{100 * c / total:6.1f}% {nb:9.0f} {sm:10.0f} {sm:10.0f}")
    print()
    print("读法：'相邻帧变格' 是真正需要重画的量。它占全屏的比例决定'只写变化'的上限——")
    print("      比例越低，这条路越值得走。'重写但没变' 就是现在白白做掉的那部分工作量，")
    print("      也正是 `render_diff` 必须逐格比对的那部分。")


if __name__ == "__main__":
    main()
