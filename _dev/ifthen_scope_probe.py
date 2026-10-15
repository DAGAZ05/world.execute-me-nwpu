"""歌词是条件句的那几处，IF/THEN 框在不在、两格是不是都有内容。

批 108 把框做成"贯穿全曲的装置"，它有两半：左格填 `If ...`、右格填 `Then ...`。最容易出的毛病是
**只有左格**——IF 那句画了框，THEN 那句换了 pane、框跟着没了（用户："动画中只演出了 IF 的内容，
在 scene14 矩阵 没有演出 THEN 的内容"）。

逐"句"点名用 `_ifthen_common.ifthen_lines()`（按排期行问 `school_scenes._ifthen_wanted`，
与画框、与让位是同一个函数）。每一句在**整帧**里看框在不在、两格是不是都有字。

    python _dev/ifthen_scope_probe.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ifthen_common import boot, cells_lit, frame_at, frame_rows, ifthen_lines  # noqa: E402

#: 每一格右边至少要有这么多字才算"填了"。
MIN_CELL = 3


def main() -> None:
    d, eng = boot()
    rows = ifthen_lines()
    ok, bad = 0, []
    for a, b, lyric in rows:
        t = a + (b - a) * 0.6
        s = frame_at(d, eng, t)
        left, right = cells_lit(frame_rows(s))
        if left >= MIN_CELL and right >= MIN_CELL:
            ok += 1
        else:
            bad.append((round(t, 2), lyric[:28], left, right))
    for t, lyric, l, r in bad:
        print(f"  FAIL t={t}  {lyric!r}  左格 {l} 字 / 右格 {r} 字")
    print(f"{'PASS' if not bad else 'FAIL'}\uff1a{ok}/{len(rows)} 条条件句上框都在、两格都有内容")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()