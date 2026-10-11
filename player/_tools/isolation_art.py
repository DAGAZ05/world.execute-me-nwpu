r"""`isolation` 这九个字母的字符画（清单第 48 条）。

用户："动画孤立框内加上字符画 isolation（目前只有点的纹样，有点单调）"、"isolation 又不是校园标识物，
我让你画 isolation 这几个字母的字符画"。

**不走 `assets/校园标识物/` 那条管线**：那是给校园里的实物（何尊 / 猫学长 / NWPU 字标）用的。
这里就是这九个字母本身，直接写在这里。

**四版经过（都踩过，所以记下来）**：

1. 5 行 `#` 位图、放在 `assets/校园标识物/`、走 `banner_cells` —— 错在把字母当成了实物资产；
2. 把位图**自动翻译成笔画**（上下→`_`、左右→`|`、其余→`/`）—— 出来是
   `____  ___  __  _     __  ____ ...`，**读不出字母**；
3. 手写 **3 行**的竖条风格 —— 太矮，`###`/`##` 分组后读不出"ISOLATION"（用户看了实图：
   "感觉不太对"）；
4. **本版**：**逐字母定形**——每个字母一张 5 行 × 4 宽的位图，字母之间留一格。
   5 行才放得下 `S` 的上下弯、`A` 的横杠、`N` 的对角，4 宽才放得下 `M`/`N` 的两条竖。

    python _dev/isolation_art.py      # 打印出来看
"""
from __future__ import annotations

#: 每个字母 5 行 × 4 列（`#` = 这一格是实心）。`ISOLATION` 用到 I S O L A T N 七个。
GLYPHS: dict[str, tuple[str, ...]] = {
    "I": ("####", " ## ", " ## ", " ## ", "####"),
    "S": (" ###", "#   ", " ## ", "   #", "### "),
    "O": (" ## ", "#  #", "#  #", "#  #", " ## "),
    "L": ("#   ", "#   ", "#   ", "#   ", "####"),
    "A": (" ## ", "#  #", "####", "#  #", "#  #"),
    "T": ("####", " ## ", " ## ", " ## ", " ## "),
    "N": ("#  #", "## #", "# ##", "#  #", "#  #"),
}

#: 字母之间空几格。一格就够——每一列上字母自己的边界（`####` / `#  #`）已经把间距说清楚了。
GAP = 1


def art(word: str = "ISOLATION") -> list[str]:
    """`word` 的字符画；行数 = 5，列数 = `(4 + GAP) * len(word) - GAP`。"""
    rows = [""] * 5
    for i, ch in enumerate(word.upper()):
        g = GLYPHS.get(ch)
        if g is None:
            continue
        for r in range(5):
            rows[r] += g[r] + (" " * GAP if i + 1 < len(word) else "")
    return [r.rstrip() for r in rows]


def cells(word: str = "ISOLATION") -> tuple[list[list[str | None]], int, int]:
    """`(cells, w, h)`，`cells[r][c]` 是字符或 `None`（与调用处那几行的形状一致）。"""
    rows = art(word)
    w = max(len(r) for r in rows)
    grid: list[list[str | None]] = [[(c if c != " " else None) for c in r.ljust(w)]
                                    for r in rows]
    return grid, w, len(rows)


def main() -> None:
    lines = art()
    print(f"{max(len(r) for r in lines)}x{len(lines)}")
    for line in lines:
        print("|" + line + "|")


if __name__ == "__main__":
    main()
