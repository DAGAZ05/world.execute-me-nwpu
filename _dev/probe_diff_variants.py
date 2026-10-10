"""`render_diff` 的逐格比较能不能换成 C 层/向量化的比较？三种写法并排量。

背景（都是这个会话量出来的）：
  * `render_diff` 占一帧的 29-49%（`_dev/probe_renderdiff_split.py`）；
  * 脏行占 53-100% 的行 —— "整行跳过"最多省一半；
  * 行内变化格密度只有 0.22-0.58、每行 3-6 个簇（`_dev/probe_dirty_shape.py`）
    —— "收窄区间"也没多少可省。

所以省不下来的是**逐格比较本身**：52 行 × 197 格的纯 Python 循环。三种替代写法：

  A  现状：`for x in range(cols): if row[x] != old[x]`          （纯 Python，每格两次索引）
  B  C 层整行比较：`if row == old: continue`，否则再逐格找      （批 81 已经在用的短路）
  C  **扁平副本 + C 层比较**：把每一行存成一份扁平的 list，`row == flat_prev[y]` 是 C 层；
     只有整行不等时才去逐格找 —— 但"逐格找"仍然要 O(197)。
  D  **numpy 镜像**：每帧把缓冲抽成三个扁平数组（char/fg/bg），与上一帧做向量化比较，
     `np.nonzero` 直接给出"哪些格变了"。所有比较都在 C 里。

D 的代价在"每帧抽取"（10,244 格 × 3 个字段），B/C 的代价在"每帧仍然要逐格走一遍"。
这个探针量的是：哪种写法的**每帧总成本**最低。

    python _dev/probe_diff_variants.py
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


def variant_c_flat(buf, prev, cols, rows):
    """扁平副本 + C 层逐行比较。返回脏行列表。"""
    flat = [c for row in buf for c in row]
    flat_prev = [c for row in prev for c in row]
    dirty_rows = []
    for y in range(rows):
        a = y * cols
        b = a + cols
        if flat[a:b] != flat_prev[a:b]:
            dirty_rows.append(y)
    return dirty_rows, flat


def variant_d_numpy(buf, cols, rows):
    """把缓冲抽成三个扁平数组。这是一次整屏抽取，之后所有比较都在 C 里。"""
    import numpy as np
    n = cols * rows
    ch = np.empty(n, dtype="<U1")
    fg = np.empty((n, 3), dtype=np.uint8)
    bg = np.empty((n, 3), dtype=np.uint8)
    k = 0
    for row in buf:
        for cell in row:
            c = cell[0]
            ch[k] = c if c else " "
            fg[k] = cell[1]
            bg[k] = cell[2]
            k += 1
    return ch, fg, bg


def variant_d_flatonly(buf, cols, rows):
    """只抽"字符"一个字段（比较的最廉价近似），看抽取本身的下限。"""
    import numpy as np
    n = cols * rows
    ch = np.empty(n, dtype="<U1")
    k = 0
    for row in buf:
        for cell in row:
            c = cell[0]
            ch[k] = c if c else " "
            k += 1
    return ch


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", default="61.0,62.0")
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    import numpy as np
    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    lo, hi = (float(v) for v in a.window.split(","))
    frames = max(2, int((hi - lo) * T.FPS))
    gc.disable()
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()
    s = T.Screen(cols, rows)
    sink = io.StringIO()

    # 先画一帧，让 s.buf / s.prev 都是真实内容
    for k in range(frames):
        T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, T.FPS)
        s.render_diff(sink)

    print(f"{cols}x{rows}  window {a.window}  {a.rounds} 轮取中位数")
    print()
    res = {}

    # A：真实的 render_diff（现状）
    ms = []
    for _ in range(a.rounds):
        t0 = time.perf_counter()
        for k in range(frames):
            T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, T.FPS)
            t1 = time.perf_counter()
            s.render_diff(sink)
            ms.append((time.perf_counter() - t1) * 1000)
        del t0
    res["A 现状 render_diff"] = statistics.median(ms)

    # B/C/D：只量"找出脏格"这一段，不写转义流（写转义流的成本三者相同）
    for name, fn in (("C 扁平副本 + C 层比较", variant_c_flat),
                     ("D numpy 抽取(3 字段)", None),
                     ("D2 numpy 抽取(仅字符)", variant_d_flatonly)):
        ms = []
        for _ in range(a.rounds):
            for k in range(frames):
                T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, T.FPS)
                prev = s.prev
                t1 = time.perf_counter()
                if fn is not None:
                    fn(s.buf, prev, cols, rows) if fn is variant_c_flat else fn(s.buf, cols, rows)
                else:
                    variant_d_numpy(s.buf, cols, rows)
                ms.append((time.perf_counter() - t1) * 1000)
            s.render_diff(sink)
        res[name] = statistics.median(ms)

    # numpy 比较本身（在上一次抽取之上）的成本
    ch, fg, bg = variant_d_numpy(s.buf, cols, rows)
    ms = []
    for _ in range(a.rounds):
        for k in range(frames):
            T.draw(s, data, eng, lo + k * (hi - lo) / frames, True, T.FPS)
            t1 = time.perf_counter()
            ch2, fg2, bg2 = variant_d_numpy(s.buf, cols, rows)
            d = (ch2 != ch) | (fg2 != fg).any(axis=1) | (bg2 != bg).any(axis=1)
            idx = np.nonzero(d)[0]
            ms.append((time.perf_counter() - t1) * 1000)
            ch, fg, bg = ch2, fg2, bg2
        s.render_diff(sink)
    res["D+D 抽取+向量比较"] = statistics.median(ms)

    for name, v in sorted(res.items(), key=lambda kv: kv[1]):
        print(f"  {name:28s} {v:8.2f} ms/帧")
    print()
    print("注意：A 包含转义流拼装（用户看到的那一半），B/C/D 只是找脏格那一段。")
    print("三者都要再各自接上拼装。所以只有当 D（抽取+比较）明显低于 A 时改造才值得。")


if __name__ == "__main__":
    main()
