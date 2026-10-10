"""**不清屏**试一次：把 `draw()` 开头那次整屏 `fill` 去掉，看帧时间掉多少。

## 为什么这是唯一能抬高上限的一步

批 85 量出来的结论是：写入时脏位图**没用**，因为 `draw()` 每帧开头一次
`fill(0, 0, cols-1, rows-1, " ", ...)`，于是每一格都真的被写过，
`render_diff` 的代价就是"屏幕上真的变了多少"的下界，不是浪费。

所以要让帧率真正上一个台阶，前提只有一个：**让 `draw()` 不再整屏重写**。
问题是——那些 pane、文字、后期都是往缓冲里**写**的，没有"清理自己上一帧"的概念。
不清屏的直接后果是上一帧的残留留在那里。

**但残留是不是真的会发生，是个可以测的问题，不是一个信仰。** 这个探针：

  1. 直接 `import tui_live`，用 `unittest.mock` 把 `Screen.fill` **在 draw 期间**换成一个
     只截住"整屏调用"的版本（`x0==0 and y0==0 and x1==cols-1 and y1==rows-1` 时跳过，
     其余矩形照原样）——**不改仓库代码**；
  2. 每一帧 `draw → render_diff` 到**丢弃**的 sink（不给终端），只统计帧时间；
  3. 再单独跑一遍**每一帧新建 `Screen`** 的对照：新 Screen 天然没有残留，
     所以它的画面就是"正确的画面"。两者逐帧比对屏幕哈希——
     **相同 = 不清屏没有留下任何残留**（那这一改动就是纯赚），
     不同 = 有残留，差异就是代价。

三个结果都可能有用，所以三种都打印：
  * 帧时间掉了多少（收益）；
  * 有多少帧出现差异（代价）；
  * 差异集中在哪些时刻（能不能局部修）。

    python _dev/probe_no_fill.py
    python _dev/probe_no_fill.py --window 61.0,62.0 --rounds 5
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import io
import os
import statistics
import sys
import time
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

WINDOWS = ["14.0,16.0", "56.8,58.0", "61.0,62.0", "147.0,148.0", "184.4,186.0", "195.0,196.0"]


def setup():
    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(197, 52)
    return T, T.Engine(), T.Data()


def make_skipper(T):
    """一个只在"整屏"时跳过的 fill。其余矩形照原样调真的 `Screen.fill`。"""
    real = T.Screen.fill

    def fill(self, x0, y0, x1, y1, ch=" ", fg=None, bg=None):
        if x0 <= 0 and y0 <= 0 and x1 >= self.cols - 1 and y1 >= self.rows - 1:
            return
        if fg is None:
            fg = T.UI
        if bg is None:
            bg = T.BG
        return real(self, x0, y0, x1, y1, ch, fg, bg)

    return fill


def run_timed(T, eng, data, lo, hi, frames, rounds, skipless):
    """返回 (中位帧时间 ms, 每帧屏幕哈希)。`skipless=True` 时每帧新建 Screen（正确画面）。"""
    out_ms = []
    for _ in range(rounds):
        s = T.Screen(197, 52)
        sink = io.StringIO()
        ms = []
        for k in range(frames):
            t = lo + k * (hi - lo) / frames
            if skipless:
                s = T.Screen(197, 52)
                sink = io.StringIO()
            t0 = time.perf_counter()
            T.draw(s, data, eng, t, True, T.FPS)
            s.render_diff(sink)
            ms.append((time.perf_counter() - t0) * 1000.0)
        out_ms.append(statistics.median(ms))
    # 单独一遍取哈希（不计时）
    hs = []
    for k in range(frames):
        t = lo + k * (hi - lo) / frames
        s = T.Screen(197, 52)
        sink = io.StringIO()
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
        hs.append(hashlib.sha256(s.text_dump().encode("utf-8", "replace")).hexdigest()[:12])
    return statistics.median(out_ms), hs


def run_nofill(T, eng, data, lo, hi, frames, rounds):
    """不清屏：同一个 Screen 连跑，整屏 fill 被跳过。返回 (中位帧时间, 逐帧哈希)。"""
    out_ms = []
    fill = make_skipper(T)
    for _ in range(rounds):
        s = T.Screen(197, 52)
        sink = io.StringIO()
        ms = []
        with mock.patch.object(T.Screen, "fill", fill):
            for k in range(frames):
                t = lo + k * (hi - lo) / frames
                t0 = time.perf_counter()
                T.draw(s, data, eng, t, True, T.FPS)
                s.render_diff(sink)
                ms.append((time.perf_counter() - t0) * 1000.0)
        out_ms.append(statistics.median(ms))
    hs = []
    s = T.Screen(197, 52)
    sink = io.StringIO()
    with mock.patch.object(T.Screen, "fill", fill):
        for k in range(frames):
            t = lo + k * (hi - lo) / frames
            T.draw(s, data, eng, t, True, T.FPS)
            s.render_diff(sink)
            hs.append(hashlib.sha256(s.text_dump().encode("utf-8", "replace")).hexdigest()[:12])
    return statistics.median(out_ms), hs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window")
    ap.add_argument("--windows", nargs="*", default=WINDOWS)
    ap.add_argument("--rounds", type=int, default=3)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    gc.disable()
    T, eng, data = setup()
    windows = [a.window] if a.window else a.windows

    print("清屏 vs 不清屏（197x52；不清屏 = draw 里那次整屏 fill 被跳过）")
    print()
    print(f"{'window':>14} {'pane':>22} {'清屏 ms':>8} {'不清 ms':>8} {'省':>7} "
          f"{'差异帧':>7} {'差异时刻':>26}")
    worst = None
    for spec in windows:
        lo, hi = (float(v) for v in spec.split(","))
        frames = max(2, int((hi - lo) * T.FPS))
        import school_panels as SP
        row = SP.row_at((lo + hi) / 2)
        pane = row["name"] if row else "?"

        base_ms, base_h = run_timed(T, eng, data, lo, hi, frames, a.rounds, skipless=True)
        nofill_ms, nofill_h = run_nofill(T, eng, data, lo, hi, frames, a.rounds)

        diff = [k for k in range(frames) if base_h[k] != nofill_h[k]]
        ts = [f"{lo + k * (hi - lo) / frames:.1f}" for k in diff[:4]]
        saved = base_ms - nofill_ms
        print(f"{spec:>14} {pane:>22} {base_ms:8.1f} {nofill_ms:8.1f} "
              f"{saved:6.1f}  {len(diff):5d}/{frames:<3d} {','.join(ts):>26}")
        if diff and (worst is None or len(diff) > worst[1]):
            worst = (spec, len(diff), diff)

    print()
    if worst is None:
        print("**没有任何一帧不同** —— 不清屏在这个尺寸上没有留下残留。")
        print("那这一改动就是纯赚，下一步可以直接上写入时脏位图（批 85 那个被回退的方案）。")
    else:
        print(f"残留最重的是 {worst[0]}：{worst[1]} 帧不同。")
        print("有差异不等于不能用——要看差异是'上一帧的旧内容漏出来'还是别的，")
        print("而且要把范围与收益放在一起看：收益几百毫秒、差异只在几个转场帧上，是值得修；")
        print("收益很小而差异到处都有，就不值得。")


if __name__ == "__main__":
    main()
