"""IF/THEN 框：该有的时候两格都亮，不该有的时候一格都不许有。

与 `ifthen_scope_probe` 的分工：那一支逐句点名"框在不在、两格有没有字"；这一支同时守**反面**——
在**不是**条件句的时刻，框必须**完全不出来**。批 111 的毛病正是这个：框被固定住了，
`Switch my current` 那种非条件句的歌词上也挂着一个框。

    python _dev/ifthen_frame_probe.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ifthen_common import (boot, cells_lit, frame_at, frame_rows,  # noqa: E402
                            ifthen_lines)

import school_scenes as _SC     # noqa: E402

MIN_CELL = 3
#: 判"框在不在这里"用的字符：上边框的 `\u252c`（两格之间的丁字口）。
MARK = "\u252c"
#: 反面判据用的时刻：都不是条件句。
QUIET = (20.0, 27.0, 47.0, 60.0, 70.0, 95.0, 110.0, 130.0, 150.0, 175.0, 190.0, 203.0)


def main() -> None:
    d, eng = boot()
    rows = ifthen_lines()
    ok, bad = 0, []
    for a, b, lyric in rows:
        t = a + (b - a) * 0.6
        s = frame_at(d, eng, t)
        fr = frame_rows(s)
        left, right = cells_lit(fr)
        if MARK in fr[0] and left >= MIN_CELL and right >= MIN_CELL:
            ok += 1
        else:
            bad.append((round(t, 2), lyric[:26], left, right, MARK in fr[0]))
    for t, lyric, l, r, m in bad:
        print(f"  FAIL t={t} {lyric!r} 上边框={m} 左{l}/右{r}")
    quiet_ok, quiet_bad = 0, []
    for t in QUIET:
        if _SC._ifthen_wanted(t):
            continue                  # 这个时刻其实是条件句，跳过（不是反面样本）
        s = frame_at(d, eng, t)
        if MARK not in frame_rows(s)[0]:
            quiet_ok += 1
        else:
            quiet_bad.append(t)
    for t in quiet_bad:
        print(f"  FAIL t={t} 不是条件句却画了框")
    total, nbad = ok + quiet_ok, len(bad) + len(quiet_bad)
    print(f"{'PASS' if not nbad else 'FAIL'}\uff1a{ok}/{len(rows)} 对两格都亮；"
          f"{quiet_ok}/{quiet_ok + len(quiet_bad)} 个无关时段不画框")
    raise SystemExit(1 if nbad else 0)


if __name__ == "__main__":
    main()