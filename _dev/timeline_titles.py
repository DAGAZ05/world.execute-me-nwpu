"""批 173：把两个时间线动画的抬头改成用户在表里写的那两句。"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


#: (行首 at, 新 sub)
JOBS = [
    ("50.95", "\u5982\u679c\u80fd\u56de\u5230 1938"),
    ("52.99", "\u4ece\u53e4\u90fd\u56de\u7738\u5f80\u4e8b\u6570\u5343\u5e74"),
]


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    lines = P.read_text(encoding="utf8").split("\n")
    for at, new in JOBS:
        idx = next((i for i, l in enumerate(lines) if ("at=%s," % at) in l), None)
        if idx is None:
            print("  未命中 at=%s" % at)
            continue
        hit = None
        for j in range(idx, min(idx + 6, len(lines))):
            m = re.search(r'sub="((?:[^"\\]|\\.)*)"', lines[j])
            if m:
                hit = (j, m)
                break
        if hit is None:
            print("  未命中 at=%s 这一段里没有 sub=" % at)
            continue
        j, m = hit
        old = m.group(1)
        lines[j] = lines[j][:m.start(1)] + esc(new) + lines[j][m.end(1):]
        print("  OK  at=%s  %r -> %r" % (at, old, esc(new)))
    if "--apply" in sys.argv:
        P.write_text("\n".join(lines), encoding="utf8")
        print("已写入")


if __name__ == "__main__":
    main()
