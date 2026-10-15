"""批 170：收尾。先**定位**剩下的抬头串在哪，能确定的就改。

`--apply` 才写入；不带参数只报告。每条都会打出"在哪个文件哪一行、原文是什么"，
所以即使没匹上也能人工接手，不会静默跳过。
"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "player" / "_tools" / n
         for n in ("school_scenes.py", "school_motifs.py", "school_panels.py", "school_courses.py")]

#: (名字, 定位正则, 想改成什么（源码里的样子，None = 只看不改）)
JOBS = [
    ("chladni 标题", r'"12 \\u5c0f\\u65f6[^"]*"', '"12 \\u5c0f\\u65f6\\u949f\\u9762"'),
    ("gauge_final 标题", r'"\\u6bd5\\u4e1a\\u8bbe\\u8ba1[^"]*"', None),
    ("sw_project 标题", r'"\\u8f6f\\u4ef6\\u9879\\u76ee\\u7ba1\\u7406[^"]*"', None),
    ("exec_embedded 标题", r'"\\u5d4c\\u5165\\u5f0f[^"]*"', None),
    ("dijkstra 标题", r'"Dijkstra[^"]*"', None),
    ("fragments 标题", r'"\\u5220\\u9664[^"]*"', None),
    ("exec_c 标题", r'"\\u7a0b\\u5e8f\\u8bbe\\u8ba1[^"]*"', None),
    ("crest 行的 sub", r'dict\(at=17\.0[^\n]*', None),
]


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    cache: dict[Path, str] = {}
    for name, pat, new in JOBS:
        found = False
        for path in FILES:
            text = cache.get(path) or path.read_text(encoding="utf8")
            for m in re.finditer(pat, text):
                found = True
                ln = text[:m.start()].count("\n") + 1
                print("%-20s %s:%d" % (name, path.name, ln))
                print("     现在 %r" % m.group(0)[:96])
                if new and new != m.group(0):
                    text = text[:m.start()] + new + text[m.end():]
                    print("     改成 %r" % new)
                    cache[path] = text
                break
            if found:
                break
        if not found:
            print("%-20s **没找到**" % name)
        print()
    if "--apply" in sys.argv and cache:
        for path, t in cache.items():
            path.write_text(t, encoding="utf8")
        print("已写入 %d 个文件" % len(cache))


if __name__ == "__main__":
    main()
