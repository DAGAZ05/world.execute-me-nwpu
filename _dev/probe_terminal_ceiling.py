"""**终端那一端的墙**：一帧要写多少字节，以及实际写进终端的吞吐是多少。

## 为什么这是决定性的

前面几步已经把 Python 侧的路基本走完：

  * `render_diff` 占一帧 29-49%（批 84 量过），它的成本是"屏幕上真的变了多少"的**下界**；
  * 写入时脏位图没用（批 85），因为 `draw()` 每帧整屏重写；
  * **去掉整屏 `fill` 只省 1.0 ms，却破坏 23/24 帧**（`_dev/probe_no_fill.py`）；
  * 每个热函数都已经很便宜（`_dev/probe_wide_micro.py`）：把 `_maybe_wide` 的两跳链换成
    查集合，每帧只省约 0.6 ms。

于是问题变成：**就算 Python 侧做到 0，这一帧还能多快？** 答案是终端能吞多少字节。
这个探针量两件事：

  1. **一帧的转义流有多大**（含全曲分布，不只是中位）；
  2. **真的写进一个终端时吞吐是多少**——用一个空壳 sink 测"格式化开销"，
     再用真的 stdout（管道 / conpty）测"端到端"。

一帧的字节数 × 终端吞吐 = 这一帧**不可能低于**的时间。如果这个下界已经超过 16.7 ms，
那么 60 fps 不是"再优化优化"就能到的，是这一代终端的物理限制。

    python _dev/probe_terminal_ceiling.py
    python _dev/probe_terminal_ceiling.py --write   # 真的往 stdout 写（会有大量输出）
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

BUDGET = {24: 1000 / 24, 30: 1000 / 30, 60: 1000 / 60}


class Counter(io.StringIO):
    """按帧统计字节数，但不留内容。"""

    def __init__(self):
        super().__init__()
        self.n = 0

    def write(self, text):
        self.n += len(text)
        return len(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--write", action="store_true",
                    help="也真的往 stdout 写一段（会有大量终端输出）")
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

    # ---- 1. 全曲一帧多少字节
    print(f"{cols}x{rows}  一帧的转义流字节数（全曲每 4 s 取一帧）")
    sizes = []
    t = 0.0
    while t < T.END - 0.1:
        s = T.Screen(cols, rows)
        sink = Counter()
        # 前一帧先渲染一次，让 render_diff 有个真实的 prev
        T.draw(s, data, eng, max(0.0, t - 1 / T.FPS), True, T.FPS)
        s.render_diff(io.StringIO())
        sink.n = 0
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
        sizes.append(sink.n)
        t += 4.0
    sizes_sorted = sorted(sizes)
    n = len(sizes_sorted)
    print(f"  帧数 {n}")
    print(f"  min {sizes_sorted[0]:,}  p50 {sizes_sorted[n // 2]:,}  "
          f"p90 {sizes_sorted[int(0.9 * (n - 1))]:,}  max {sizes_sorted[-1]:,}  字节/帧")
    tot = sum(sizes)
    print(f"  全曲合计 {tot / 1e6:.1f} MB（{n} 帧）")
    print()

    # ---- 2. 格式化开销（纯 Python 侧）
    s = T.Screen(cols, rows)
    sink = Counter()
    for _ in range(6):
        T.draw(s, data, eng, 61.0, True, T.FPS)
        s.render_diff(sink)
    ms = []
    for _ in range(15):
        sink.n = 0
        T.draw(s, data, eng, 61.0, True, T.FPS)
        t0 = time.perf_counter()
        s.render_diff(sink)
        ms.append((time.perf_counter() - t0) * 1000.0)
    print("=== 只格式化到内存（不写终端）===")
    print(f"  render_diff 中位 {statistics.median(ms):.1f} ms，"
          f"产生 {sink.n:,} 字节")
    med_ms = statistics.median(ms)
    print(f"  纯格式化吞吐 ≈ {sink.n / (med_ms / 1000) / 1e6:.1f} MB/s")
    print()

    # ---- 3. 真的写进终端
    if a.write:
        payload = []
        s2 = T.Screen(cols, rows)
        c2 = Counter()
        t = 0.0
        while t < 30.0:
            s2 = T.Screen(cols, rows)
            c2 = Counter()
            T.draw(s2, data, eng, t, True, T.FPS)
            s2.render_diff(c2)
            # Counter 不存内容，这里重新渲染一次拿到真字符串
            s3 = T.Screen(cols, rows)
            c3 = io.StringIO()
            T.draw(s3, data, eng, t, True, T.FPS)
            s3.render_diff(c3)
            payload.append(c3.getvalue())
            t += 1 / T.FPS
        total = sum(len(p) for p in payload)
        sys.stderr.write(f"\n（开始往 stdout 写 {total / 1e6:.2f} MB，"
                         f"{len(payload)} 帧，请稍候）\n")
        sys.stderr.flush()
        out = sys.stdout
        t0 = time.perf_counter()
        for p in payload:
            out.write(p)
        out.flush()
        dt = time.perf_counter() - t0
        print()
        print("=== 真的写进终端 ===")
        print(f"  {total / 1e6:.2f} MB，{len(payload)} 帧，耗时 {dt:.2f} s")
        print(f"  端到端吞吐 ≈ {total / dt / 1e6:.1f} MB/s")
        print(f"  每帧 {total / len(payload):,.0f} 字节 -> 光写这一项就要 "
              f"{dt / len(payload) * 1000:.1f} ms")
    else:
        print("（加 --write 会真的往终端写一段，量端到端吞吐；那会有大量输出。）")

    print()
    print("=== 结论口径 ===")
    med_bytes = sizes_sorted[n // 2]
    for mbps in (10, 20, 40, 80):
        print(f"  若终端吞吐 {mbps:3d} MB/s：中位帧 {med_bytes / mbps / 1000:6.2f} ms "
              f"-> 上限 {1000 / (med_bytes / mbps / 1000):6.1f} fps")
    print()
    print(f"  参考：24 fps 预算 {BUDGET[24]:.1f} ms · 30 fps {BUDGET[30]:.1f} ms · "
          f"60 fps {BUDGET[60]:.1f} ms")
    print("  一帧的字节数 × 终端吞吐 = 这一帧**不可能低于**的时间。")


if __name__ == "__main__":
    main()
