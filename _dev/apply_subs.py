"""把用户表格里的 sub 套用回 `school_panels.py`。

只改 **`dict(at=X, ...)` 里的 `sub="..."`**；标题（pane 自己的 `_kit` title）下一步单独做。

    python _dev/apply_titles.py --apply     # 改源码
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

SRC = ROOT / "player" / "_tools" / "school_panels.py"


def esc(s: str) -> str:
    """写回源码时用 `\\uXXXX` 转义非 ASCII——这个文件通篇是这个风格。"""
    return s.encode("unicode_escape").decode("ascii").replace('"', '\\"')


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    rows = A.parse_table()
    text = SRC.read_text(encoding="utf8")
    lines = text.split("\n")

    # 找每个 `dict(at=X,` 的位置；sub 可能在同一行、也可能在往后几行
    starts = {}
    for i, l in enumerate(lines):
        m = re.search(r"dict\(at=([\d.]+),", l)
        if m:
            starts.setdefault(float(m.group(1)), i)

    # **另一条路：按 pane 名索引的字典**。`pane_exec_*` 那十几行不是 `dict(at=...)` 形式——
    # 它们的 sub 在 `EXEC_SUB`（`school_panels.py:144`）里按 pane 名查：
    #     "pane_exec_c": "一次执行：main 里的语句一条条走",
    # 所以光按 `at` 找会漏掉 23 行。这里把「按名字写的那些」也建成一张行号表。
    by_name = {}
    for i, l in enumerate(lines):
        m = re.match(r'\s*"(pane_\w+)":\s*"', l)
        if m:
            by_name.setdefault(m.group(1), i)

    changed, missing, same = [], [], []
    for r in rows:
        if r["head"] == "\u2014":
            continue
        pane = r["pane"].strip("`").split("(")[0]
        at = float(r["span"].split("\u2013")[0])
        j = starts.get(at)
        if j is None:
            j = by_name.get(pane)
        if j is None:
            missing.append((at, "at 与 pane 名都没找到（%s）" % pane))
            continue
        # 从这一行往下找 sub 值（最多 8 行），碰到下一个条目就停。
        #
        # **两条路要用两套正则**（批 165 修；上一版就是在这里写坏了）：
        #   * `"pane_exec_c": "一次执行：…"` —— 这一行有**两个**引号串，
        #     第一个是**键**（pane 名）、第二个才是 sub。上一版用 `(sub=)?"(...)"` 去抓，
        #     抓到的是**键**，于是把 pane 名替换成了 sub——生成的表里"动画框"那一列
        #     整列变成抬头文字，已 `git checkout` 回滚；
        #   * `dict(at=…, …, sub="…")` —— 用 `sub="(...)"` 抓。
        found = None
        for k in range(j, min(j + 8, len(lines))):
            if k != j and (re.match(r"\s*dict\(at=", lines[k]) or re.match(r'\s*"pane_\w+":', lines[k])):
                break
            m = re.search(r'"pane_\w+":\s*"((?:[^"\\]|\\.)*)"', lines[k]) if k == j else None
            if m is None:
                m = re.search(r'sub="((?:[^"\\]|\\.)*)"', lines[k])
            if m is None:
                continue
            raw = m.group(1)
            try:
                cur_txt = raw.encode("ascii", "backslashreplace").decode("unicode_escape")
            except Exception:
                cur_txt = raw
            found = (k, m, 1, cur_txt)
            break
        if found is None:
            missing.append((at, "这一段里没有 sub="))
            continue
        k, m, grp, cur_txt = found
        if cur_txt == r["new_sub"]:
            same.append(at)
        else:
            lines[k] = lines[k][:m.start(grp)] + esc(r["new_sub"]) + lines[k][m.end(grp):]
            changed.append((at, cur_txt[:26], r["new_sub"][:26]))

    print("会改 %d 行；已经是目标值 %d 行；没找到 %d 行\n" % (len(changed), len(same), len(missing)))
    for at, a, b in changed[:30]:
        print("  %7.2f  %-28s -> %s" % (at, a, b))
    if missing:
        print("\n=== 没找到（要手工看）===")
        for at, why in missing:
            print("  %7.2f  %s" % (at, why))

    if "--apply" in sys.argv:
        SRC.write_text("\n".join(lines), encoding="utf8")
        print("\n已写入 %s" % SRC)


if __name__ == "__main__":
    main()
