"""列出"标题"那一半要改哪些地方。

用户规则：抬头里**第一个 `·` 之前是 pane 标题**。这一趟只找 title，不动 sub。

当前标题从源码里静态取（两条路）：
  * pane 函数体里的 `_kit(...)` / `_Kit(...)` 的标题实参；
  * `pane_exchange` 的 `TITLE` 表（按面板名）。

    python _dev/apply_titles_part2.py
"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
sys.path.insert(0, str(ROOT / "_dev"))
os.environ.setdefault("PV_VARIANT", "school")

import apply_titles as A  # noqa: E402

SCENES = ROOT / "player" / "_tools" / "school_scenes.py"
MOTIFS = ROOT / "player" / "_tools" / "school_motifs.py"
PANELS = ROOT / "player" / "_tools" / "school_panels.py"


def unesc(s: str) -> str:
    try:
        return s.encode("ascii", "backslashreplace").decode("unicode_escape")
    except Exception:
        return s


def pane_titles():
    """pane 名 -> (文件, 行号, 当前标题)。"""
    out = {}
    for path in (SCENES, MOTIFS):
        lines = path.read_text(encoding="utf8").split("\n")
        cur = None
        for i, l in enumerate(lines):
            m = re.match(r"def (\w+)\(", l)
            if m:
                cur = m.group(1)
            if "pane_" in (cur or "") or (cur or "").startswith("_ev_"):
                pass
            # `_kit(s, x0, y0, x1, y1, 0, "标题")` 或 `_Kit(s, x0, y0, x1, y1, "标题", 0, 0, u)`
            m2 = re.search(r'_(?:kit|Kit)\([^)]*?"((?:[^"\\]|\\.)*)"', l)
            if m2 and cur:
                out.setdefault(cur, (path.name, i + 1, unesc(m2.group(1))))
    # `pane_exchange` 的面板标题表
    lines = SCENES.read_text(encoding="utf8").split("\n")
    for i, l in enumerate(lines):
        m = re.match(r'\s*"(\w+)":\s*"((?:[^"\\]|\\.)*)",\s*$', l)
        if m and i > 2500 and i < 2650:
            pass
    return out


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    user = A.parse_table()
    titles = pane_titles()
    need, ok, unknown = [], 0, []
    for r in user:
        if r["head"] == "\u2014" or not r["new_title"]:
            continue
        pane = r["pane"].strip("`").split("(")[0]
        info = titles.get(pane)
        if not info:
            unknown.append((r["span"], pane, r["new_title"]))
            continue
        if info[2] == r["new_title"]:
            ok += 1
        else:
            need.append((r["span"], pane, info[0], info[1], info[2], r["new_title"]))
    print("标题已一致 %d 行；要改 %d 行；静态取不到当前标题 %d 行\n"
          % (ok, len(need), len(unknown)))
    print("=== 要改的（去重后每个 pane 一条）===")
    seen = set()
    for span, pane, f, ln, cur, want in need:
        if pane in seen:
            continue
        seen.add(pane)
        print("  %-22s %s:%d" % (pane, f, ln))
        print("        现在 %s" % cur)
        print("        改成 %s" % want)
    print("\n=== 静态取不到当前标题的 pane（要手工看）===")
    for span, pane, want in unknown[:26]:
        print("  %-13s %-24s 想要 %s" % (span, pane, want))


if __name__ == "__main__":
    main()
