"""用"转义形态"搜学院部分抬头重复的来源，并定位 EXEC 计数器。"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")
import school_panels as SP  # noqa: E402


def esc(s: str) -> str:
    return "".join(c if ord(c) < 128 else "\\u%04x" % ord(c) for c in s)


FILES = {n: (ROOT / "player" / "_tools" / n).read_text(encoding="utf8").split("\n")
         for n in ("school_panels.py", "school_scenes.py", "school_motifs.py",
                   "school_courses.py", "school_lines.py")}


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for word in ("卷积神经网络", "特征图"):
        print("=== %s （转义形态 %s）===" % (word, esc(word)))
        for name, lines in FILES.items():
            for i, l in enumerate(lines, 1):
                if esc(word) in l or word in l:
                    print("  %s:%d| %s" % (name, i, l.strip()[:108]))
        print()

    print("=== 学院部分（125-166）行 sub 与钉子 sub 对照 ===")
    pins = {}
    for ts, pane, panel, sub in SP.THEME_PINS:
        pins.setdefault(round(ts, 2), (pane, panel, sub))
    for r in SP.shot_rows():
        if 125.0 <= r["at"] <= 166.0:
            p = pins.get(round(r["at"], 2))
            print("  %7.2f %-24s 行=%s" % (r["at"], r.get("name"), (r.get("sub") or "")[:44]))
            if p:
                print("            钉子=%s" % (p[2] or "")[:60])

    print("\n=== EXEC 计数器：搜 '/04' 与 f\"EXEC' ===")
    for name, lines in FILES.items():
        for i, l in enumerate(lines, 1):
            if re.search(r"/04|/0[0-9]\"|EXEC \{|00/", l):
                print("  %s:%d| %s" % (name, i, l.strip()[:108]))


if __name__ == "__main__":
    main()
