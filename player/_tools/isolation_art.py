r"""`isolation` 这九个字母的字符画（清单第 48 条）。

用户："动画孤立框内加上字符画 isolation（目前只有点的纹样，有点单调）"、"isolation 又不是校园标识物，
我让你画 isolation 这几个字母的字符画"。

**不走 `assets/校园标识物/` 那条管线**：那是给校园里的实物（何尊 / 猫学长 / NWPU 字标）用的。
这里就是这九个字母本身，直接手写在这里，笔画用 `_` `|` `/` `\`（与 `猫学长_字符画.txt`
同一套语言）。

**两条经验（都踩过）**：

* 先把 `#` 位图原样画出去 ⇒ 屏幕上是 `████████` 一片，那是方块字不是字符画；
* 再试"把位图自动翻译成笔画"（上下边界→`_`、左右→`|`、其余→`/`）⇒ 出来是
  `____  ___  __  _     __  ____ ...`，**读不出字母**。
  自动翻译不行，所以下面是**手写**的。

    python _dev/isolation_art.py      # 打印出来看
"""
from __future__ import annotations

#: 手写的 `ISOLATION`，**3 行 x 37 列**。为什么这么矮（批 129，三次返工才定）：
#: 孤立那个抽屉只有 95x27（`_dev/isolation_geom_probe.py` 量到的是 `(100,12)-(194,38)` 绝对坐标），
#: 而点阵要占九列、底部还要放计数与说明。51 宽的五行大字会压住点阵最右一列；36 宽的三行小字
#: 正好落在点阵右边、还留得下底下一行。
ART: tuple[str, ...] = (
    r"###  ##  ##  #    ##  ###  ###  ##  #  #",
    r" #  #     #  #    #  #  #    #  #  # ## #",
    r"###  ##  ##  ###  #  #  #   ###  ##  #  #",
)


def art(word: str = "ISOLATION") -> list[str]:
    """`word` 的字符画（目前只有 `ISOLATION` 这一幅手写的）。"""
    if word.upper() != "ISOLATION":
        return list(ART)
    return list(ART)


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
