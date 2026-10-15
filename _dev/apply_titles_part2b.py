"""套用第二批标题：把 8 处 pane 标题里用户不要的那截后缀去掉。

逐条按 `(文件, 行号)` 定位，**行内只替换那一个引号串**，替换前先核对现在的内容对得上，
对不上就拒绝并报告——不做"盲替换"。
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENES = ROOT / "player" / "_tools" / "school_scenes.py"

#: (行号, 现在的标题, 改成) —— 行号来自 `_dev/apply_titles_part2.py` 的扫描结果
JOBS = [
    (2503, "\u8d85\u692d\u5706 \u00b7 n \u4ece 1 \u5230 6", "\u8d85\u692d\u5706"),
    (2528, "\u5085\u91cc\u53f6\u5206\u6790 \u00b7 \u97f3\u4e50\u5206\u89e3", "\u5085\u91cc\u53f6\u5206\u6790"),
    (2003, "YOLO \u00b7 \u6253\u6807", "YOLO"),
    (2254, "Spinoza \u00b7 E! 1", "Spinoza"),
    (2331, "\u76d1\u5bdf\u535a\u5f08 \u00b7 S / M", "\u76d1\u5bdf\u535a\u5f08"),
    (3090, "\u5b64\u7acb \u00b7 in isolation", "\u5b64\u7acb"),
    (3199, "\u5220\u9664 \u00b7 erase fragments", "\u5220\u9664"),
    (993, "\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406 / \u8f6f\u4ef6\u5f00\u53d1",
     "\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406  / \u8f6f\u4ef6\u5f00\u53d1\u7efc\u5408\u8bad\u7ec3"),
]


def esc(s: str) -> str:
    """转成源码里那种 `\\uXXXX` 转义。

    **不能用 `unicode_escape`**：它把 `·`（U+00B7）写成 `\\xb7`（latin-1 风格），
    而这个文件通篇是 `\\u00b7`——于是 7 条全都"对不上"。
    （那 7 条没有写进去，是脚本里"有一条对不上就整批不写"的守卫拦住的；
    如果当时是逐条盲替换，就会把 `\\u00b7` 换成 `\\xb7`、或者干脆什么都没换。）
    """
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


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    lines = SCENES.read_text(encoding="utf8").split("\n")
    done = failed = 0
    for ln, old, new in JOBS:
        i = ln - 1
        src = lines[i]
        enc = esc(old)
        if enc in src:
            lines[i] = src.replace(enc, esc(new), 1)
            done += 1
            print("  OK   %d  %s  ->  %s" % (ln, old, new))
            continue
        # 有些是原始 UTF-8 直写（非转义）
        if old in src:
            lines[i] = src.replace(old, new, 1)
            done += 1
            print("  OK   %d  %s  ->  %s  (直写)" % (ln, old, new))
            continue
        failed += 1
        print("  跳过 %d  行里没有 %r；实际是：%s" % (ln, old, src.strip()[:96]))
    if "--apply" in sys.argv and failed == 0:
        SCENES.write_text("\n".join(lines), encoding="utf8")
        print("\n已写入 %s（%d 条）" % (SCENES, done))
    elif "--apply" in sys.argv:
        print("\n有 %d 条对不上，**没有写入**" % failed)


if __name__ == "__main__":
    main()
