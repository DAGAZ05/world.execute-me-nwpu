"""批 169：收尾剩下的抬头 —— 逐条 job，命中就改、不命中就报出来。

每条 job 是 `(文件, 定位用正则, 要替换成的源码文本, 说明)`。替换**只改正则匹配到的那一段**，
所以不会像批165 那样误伤别的地方；每条都会报"命中/未命中"。
"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "player" / "_tools" / "school_scenes.py"
M = ROOT / "player" / "_tools" / "school_motifs.py"
P = ROOT / "player" / "_tools" / "school_panels.py"


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


#: (文件, 正则（第 1 组要被替换）, 新的源码文本, 说明)
JOBS = [
    # --- 标题：改为用户要的文本 ---
    (S, r'(_kit\(s, x0, y0, x1, y1, 0, )"YOLO"', '"YOLO \\u6253\\u6807"',
     "pane_yolo 标题 YOLO -> YOLO 打标"),
    (S, r'("venn":\s*)"[^"]*"', '"F \\u2229 M \\u96c6\\u5408"',
     "venn 标题 F ∩ M · 集合 -> F ∩ M 集合"),
    (M, r'(_kit\([^)]*?)"12 \\u5c0f\\u65f6[^"]*"', '"12 \\u5c0f\\u65f6\\u949f\\u9762"',
     "chladni 标题 -> 12 小时钟面"),
    (S, r'(_kit\(s, x0, y0, x1, y1, 0, )"\\u5220\\u9664"',
     '"\\u5220\\u9664 erase fragments"', "pane_fragments 标题 -> 删除 erase fragments"),
    # --- sub：探针读 (无) 的那几行，补上说明就画得出抬头 ---
    (P, r'(dict\(at=7\.19,[^\n]*\n[^\n]*?)sub="[^"]*"',
     'sub="\\u4e00\\u884c\\u884c\\u586b\\u53c2\\u6570\\uff0c\\u9f50\\u4e86\\u624d COMMIT"',
     "7.19 pane_parameters 补 sub（HEADERLESS 已有标题 参数表）"),
    (P, r'(dict\(at=17\.0,[^\n]*\n[^\n]*?)sub="[^"]*"',
     'sub="Northwestern Polytechnical University"',
     "17.00 pane_landmark_crest 补 sub"),
    (P, r'(dict\(at=80\.93,[^\n]*\n[^\n]*?)sub="[^"]*"',
     'sub="\\u53c8\\u751f\\u53c8\\u6b7b\\u7684\\u53e0\\u52a0\\u6001"',
     "80.93 pane_landmark_cat 补 sub"),
]


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    cache: dict[Path, str] = {}
    ok = bad = 0
    for path, pat, new, why in JOBS:
        text = cache.get(path) or path.read_text(encoding="utf8")
        m = re.search(pat, text)
        if m is None:
            bad += 1
            print("  未命中  %s" % why)
            continue
        # **替换整个匹配 `m.span(0)`，不是第 1 组**：这些正则的形状是 `(前缀)sub="…"`，
        # 第 1 组只是前缀；用 `span(1)` 会把新的 sub **追加在旧的后面**
        # （实测写出 `sub="新"sub="旧"` 直接语法错，已 git checkout 回滚）。
        span = m.span(0)
        text = text[:span[0]] + m.group(1) + new + text[span[1]:]
        cache[path] = text
        ok += 1
        print("  命中    %s" % why)
    print("\n命中 %d / 未命中 %d" % (ok, bad))
    if "--apply" in sys.argv:
        for path, text in cache.items():
            path.write_text(text, encoding="utf8")
        print("已写入 %d 个文件" % len(cache))


if __name__ == "__main__":
    main()
