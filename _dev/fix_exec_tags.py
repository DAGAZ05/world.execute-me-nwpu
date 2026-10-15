"""清掉 `EXEC_SUB` 里被误写进去的 `EXEC nn/nn` 尾巴与填充空格。

批 165 我把探针读到的**整行**（`标题 · 说明 ... EXEC 03/16`）按第一个 `·` 切开、
把后半段当 sub 写了回去——而那个 tag 在渲染时**另外还会画一次**
（`school_courses._Kit._header` 的 `s.put(x1 - len(tag) - 1, ...)`）。
结果：tag 画了两遍，并且它占的宽度让 `title_room` 掉到 6 格下限、**标题被截成 3 个字**
（`软件工`、`数据结`、`计算机`）。

    python _dev/fix_exec_tags.py           # 只报告
    python _dev/fix_exec_tags.py --apply
"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = ROOT / "player" / "_tools" / "school_panels.py"

#: 行尾的 `EXEC 03/16`（前面可能有一大串填充空格）
TAIL = re.compile(r"\s*EXEC\s+\d+/\d+\s*$")


def esc(s: str) -> str:
    out = []
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif o < 128:
            out.append(ch)
        elif o <= 0xFFFF:
            out.append("\\u%04x" % o)
        else:
            out.append("\\U%08x" % o)
    return "".join(out)


def unesc(s: str) -> str:
    try:
        return s.encode("ascii", "backslashreplace").decode("unicode_escape")
    except Exception:
        return s


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    lines = PANELS.read_text(encoding="utf8").split("\n")
    hits = []
    for i, l in enumerate(lines):
        m = re.search(r'(["\u0020]*"pane_\w+":\s*)"((?:[^"\\]|\\.)*)"', l)
        if m is None:
            m = re.search(r'(sub=)"((?:[^"\\]|\\.)*)"', l)
            grp = 2
        else:
            grp = 2
        if m is None:
            continue
        val = unesc(m.group(grp))
        if not TAIL.search(val):
            continue
        new = TAIL.sub("", val)
        hits.append((i + 1, val[-40:], new[-40:]))
        lines[i] = l[:m.start(grp)] + esc(new) + l[m.end(grp):]
    print("要去掉 tag 的 %d 行\n" % len(hits))
    for ln, a, b in hits[:20]:
        print("  %5d  尾=%r  ->  %r" % (ln, a, b))
    if "--apply" in sys.argv:
        PANELS.write_text("\n".join(lines), encoding="utf8")
        print("\n已写入 %s" % PANELS)


if __name__ == "__main__":
    main()
