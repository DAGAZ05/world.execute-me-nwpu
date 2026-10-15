"""把用户改过的抬头表解析成 (标题, sub)，并对照当前源码，算出要改哪些地方。

规则（用户 2026-10 定）：抬头里**第一个 ` · ` 之前是 pane 标题、之后是 sub**，不再拆第二刀。

**必须先洗掉"汉字之间的空格"**：表是我把每格字符拼出来的，而 CJK 在本渲染器里占两格
（第二格是占位），所以表里每个汉字后面都跟着一个空格——那不是标题的一部分。

    python _dev/apply_titles.py            # 只报告
"""
from __future__ import annotations

import io
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

TABLE = ROOT / "动画框抬头对照表.md"


def is_wide(ch: str) -> bool:
    return unicodedata.east_asian_width(ch) in ("W", "F")


def clean(s: str) -> str:
    """洗掉"宽字符之间的那个占位空格"，但**保留**混合文本里真正的空格。

    本渲染器里一个 CJK 占两格（第二格是占位），所以表里汉字之间会多出一个空格。
    但**不能见空格就删**：`VCC 与 5V` 里 `与` 与 `5` 之间的空格是真的。
    判据：**这个空格的左右（跳过连续空格）都是宽字符**才删。

    第一版只删"紧跟在宽字符之后"的空格，于是 `这 是` 这种（表里被写成两个空格）
    留下了；而 `VCC 与 5V` 里的又会被误删。
    """
    chars = list(s)
    n = len(chars)
    for i, ch in enumerate(chars):
        if ch != " ":
            continue
        j = i - 1
        while j >= 0 and chars[j] in (" ", ""):     # `""` 是**已被删掉的**空格，也要跳过
            j -= 1
        k = i + 1
        while k < n and chars[k] in (" ", ""):
            k += 1
        if j >= 0 and k < n and chars[j] and chars[k] and is_wide(chars[j]) and is_wide(chars[k]):
            chars[i] = ""
    return "".join(chars).strip()


def split_cells(line: str):
    """按 markdown 表格切格，**尊重 `\\|` 转义**。

    第一版直接 `split("|")`，于是 21.00-25.14 那一行的副标题
    （`\\|x\\|^n + \\|y\\|^n = r^n`）被从第一个 `|` 处切断，
    解析出来只剩 `设定不同，胖瘦有异· \\`——**生成表时没转义、解析时又不认转义**，两处都错。
    """
    line = line.strip().strip("|")
    out, cur, i = [], [], 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            cur.append("|")
            i += 2
            continue
        if line[i] == "|":
            out.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(line[i])
        i += 1
    out.append("".join(cur))
    return [c.strip() for c in out]


def split_head(head: str):
    """按用户的规则切：**第一个 `·` 之前是 pane 标题、之后是 sub**。

    但"第一个 `·`"不能一刀切，实测表里有三种写法：

      * `2^53 · IEEE-754 double 的边界 · …`——`·` **两边都有空格**，是分界；
      * `参数表· 一行行填参数…`——`·` **只在后面有空格**，也是分界；
      * `矩阵 A·x · 点集乘一下…`——**标题自己含 `·`**（A·x 是逐元素乘），
        那一个 `·` 两边都没有空格，**不是分界**，切它会把标题切坏。

    所以判据是：**第一个 前有空格 或 后有空格 的 `·`**。返回 `(标题, sub)`；
    找不到分界就返回 `(None, 整串)`——那是"这一格没有 pane 标题，整串都是 sub"。
    """
    for i, ch in enumerate(head):
        if ch != "\u00b7" or i == 0:
            continue
        if head[i - 1] == " " or (i + 1 < len(head) and head[i + 1] == " "):
            return head[:i].strip(), head[i + 1:].strip()
    return None, head


def parse_table():
    rows = []
    for line in TABLE.read_text(encoding="utf8").split("\n"):
        if not line.startswith("| ") or line.startswith("| 时刻"):
            continue
        cells = split_cells(line)
        if len(cells) < 6:
            continue
        span, lyric, pane, sect, sub, ops = cells[:6]
        head = clean(sub)
        title, s = split_head(head)
        rows.append(dict(span=span, lyric=lyric, pane=pane, sect=sect,
                         head=head, new_title=title, new_sub=s, ops=ops))
    return rows


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    rows = parse_table()
    print("表里读到 %d 行\n" % len(rows))
    n_t = sum(1 for r in rows if r["new_title"])
    print("  有分界（前=标题 / 后=sub）: %d 行" % n_t)
    print("  没分界（整串当 sub）      : %d 行" % (len(rows) - n_t))
    print("  探针当时读不出抬头的（`—`）: %d 行（跳过，不动它们）\n"
          % sum(1 for r in rows if r["head"] == "\u2014"))
    print("=== 逐行解析（前 26 行）===")
    for r in rows[:26]:
        print("  %-13s │ 标题=%-20s │ sub=%s"
              % (r["span"], (r["new_title"] or "（无）")[:20], (r["new_sub"] or "")[:50]))
    print("\n=== 标题含 `·` 的行（检查有没有被切错）===")
    for r in rows:
        if r["new_title"] and "\u00b7" in r["new_title"]:
            print("  %-13s │ 标题=%s" % (r["span"], r["new_title"]))
    print("\n=== `—` 的行（跳过）===")
    for r in rows:
        if r["head"] == "\u2014":
            print("  %-13s │ %s" % (r["span"], r["pane"][:40]))


if __name__ == "__main__":
    main()
