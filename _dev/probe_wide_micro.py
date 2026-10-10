"""`_maybe_wide` 这条两跳的函数链到底值多少钱？—— 纯微基准，四个实现比一比。

## 为什么值得单独问

`_dev/probe_call_counts.py`（只数次数，可信）说这个窗口里每帧：
    `_wide_char`   20 982 次
    `_maybe_wide`  11 858 次
`_dev/probe_hot_functions.py`（包围计时，**单次开销可信**）说单次 0.281 us / 0.433 us。
单调相乘：`_wide_char` ≈ 5.9 ms、`_maybe_wide` ≈ 5.1 ms，**合计约 11 ms 一帧**——
而这一帧总共 23.8 ms。也就是说这条"判断这个字符是不是双宽"的链子，
可能占掉了一帧的四成。

## 但这个结论必须验，不能推

"次数 × 单次"是**上限**，不是净值：那些调用里有一部分本来也躲不掉
（总得知道一个字符有多宽），而且包围计时本身有开销。所以这里直接比四个实现：

  A  现状：`_maybe_wide(ch)` —— 函数调用 + 字符串比较 + `_wide_char` 函数调用 + dict 查
  B  内联比较：`bool(ch) and ch >= _WIDE_MIN` —— 一个字符串比较，不查表
  C  直接调 `_wide_char(ch)` —— 只剩函数调用 + dict 查（去掉 `_maybe_wide` 那一跳）
  D  **查预先算好的集合**：`ch in WIDE_SET` —— 集合是每帧按"这一帧用到的字符"建一次的

D 是唯一有结构变化的一个：它把"分类字符"这件事从**每格一遍**搬到**每帧一遍**。
值得注意它是否真的赢，以及赢多少。

    python _dev/probe_wide_micro.py
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

_WIDE_MIN = chr(0x1100)
_CACHE: dict = {}


def wide_char(ch: str) -> bool:
    hit = _CACHE.get(ch)
    if hit is None:
        hit = len(ch) == 1 and unicodedata.east_asian_width(ch) in "WF"
        if len(_CACHE) < 4096:
            _CACHE[ch] = hit
    return hit


def maybe_wide(ch: str) -> bool:
    return bool(ch) and ch >= _WIDE_MIN and wide_char(ch)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", type=int, default=9)
    ap.add_argument("--n", type=int, default=140000)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    # 造一份"像真实画面"的字符序列：绝大部分是 ASCII，夹杂 CJK 与占位符
    import random
    rnd = random.Random(7)
    pool = [" "] * 60 + list("abcdefghijklmnopqrstuvwxyz0123456789·-|>[](){}#*+=")
    cjk = ["\u4e2d", "\u897f", "\u5de5", "\u4e1a", "\u56fe", "\u4e66", "\u9986", "\u6821",
           "\u5fbd", "\u5251", "\u9e3f", "\u9505"]
    seq = []
    for i in range(a.n):
        if i % 7 == 0 and rnd.random() < 0.55:
            seq.append(rnd.choice(cjk))
        else:
            seq.append(rnd.choice(pool))
    wide_set = {c for c in set(seq) if maybe_wide(c)}
    # 只预热缓存
    for c in set(seq):
        wide_char(c)

    def run(fn):
        for _ in range(3):
            fn()
        out = []
        for _ in range(a.rounds):
            t0 = time.perf_counter()
            fn()
            out.append((time.perf_counter() - t0) * 1000.0)
        return statistics.median(out)

    def a_cur():
        n = 0
        for c in seq:
            if maybe_wide(c):
                n += 1
        return n

    def b_cmp():
        n = 0
        for c in seq:
            if c and c >= _WIDE_MIN:
                n += 1
        return n

    def c_direct():
        n = 0
        for c in seq:
            if wide_char(c):
                n += 1
        return n

    def d_set():
        n = 0
        s = wide_set
        for c in seq:
            if c in s:
                n += 1
        return n

    print(f"{a.n} 次判断，{a.rounds} 轮取中位数（序列里 {len(wide_set)} 个不同字符是宽的）")
    print()
    base = run(a_cur)
    rows = [("A 现状 _maybe_wide(ch)", a_cur),
            ("B 只做 ch >= _WIDE_MIN", b_cmp),
            ("C 直接 _wide_char(ch)", c_direct),
            ("D 查预先算好的集合", d_set)]
    print(f"{'实现':>26} {'ms':>8} {'相对 A':>9} {'折算到 11 858 次':>16}")
    for name, fn in rows:
        ms = run(fn)
        per = ms / a.n * 11858
        print(f"{name:>26} {ms:8.2f} {ms / base:8.2f}x {per:13.2f} ms")
    print()
    print("说明：'折算到 11 858 次'是把每帧 11 858 次 `_maybe_wide` 代进这个实现的耗时，")
    print("      用来估'换掉它'能省多少（不是承诺——真实帧里还有别的活）。")


if __name__ == "__main__":
    main()
