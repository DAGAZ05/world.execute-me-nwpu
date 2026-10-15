"""批 177：四处抬头/对话文本按用户要求改。"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "player" / "_tools"


def esc(s: str) -> str:
    return "".join(c if ord(c) < 128 else "\\u%04x" % ord(c) for c in s)


#: (文件, 原文, 新文) —— **原始中文形态**（这个仓库里两种写法都有，所以两种都试）
JOBS = [
    ("school_panels.py", "\u56db\u5f20\u56fe\u6536\u8fdb\u4e00\u4e2a\u7c7b",
     "\u591a\u5f20\u56fe\u6536\u8fdb\u4e00\u4e2a\u7c7b"),
    ("school_lines_act2.py", "\u5d4c\u5165\u5f0f\u5fae\u7535\u5b50\u7cfb\u7edf",
     "\u5d4c\u5165\u5f0f\u7535\u5b50\u5fae\u7cfb\u7edf"),
]


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    cache: dict[Path, str] = {}
    for name, old, new in JOBS:
        p = TOOLS / name
        t = cache.get(p) or p.read_text(encoding="utf8")
        forms = [(old, new), (esc(old), esc(new))]
        done = False
        for a, b in forms:
            if a in t:
                print("  命中 %-22s %s -> %s  (%s)" % (name, old, new, "原始" if a == old else "转义"))
                t = t.replace(a, b)
                done = True
        if not done:
            print("  未命中 %s  %s" % (name, old))
        cache[p] = t

    # sw_project 的 ops 与标题重复 -> 换成框内那三个词（`敏捷 · 冲刺 · 看板`）
    p = TOOLS / "school_panels.py"
    t = cache.get(p) or p.read_text(encoding="utf8")
    old_ops = 'ops=["\\u8f6f\\u4ef6\\u9879\\u76ee\\u7ba1\\u7406", "\\u8f6f\\u4ef6\\u5f00\\u53d1\\u7efc\\u5408\\u8bad\\u7ec3"]'
    new_ops = 'ops=["\\u654f\\u6377", "\\u51b2\\u523a", "\\u770b\\u677f"]'
    if old_ops in t:
        print("  命中 school_panels.py  sw_project 的 ops -> 敏捷/冲刺/看板")
        t = t.replace(old_ops, new_ops)
        cache[p] = t
    else:
        print("  未命中 sw_project 的 ops")

    if "--apply" in sys.argv:
        for p, t in cache.items():
            p.write_text(t, encoding="utf8")
        print("已写入 %d 个文件" % len(cache))


if __name__ == "__main__":
    main()
