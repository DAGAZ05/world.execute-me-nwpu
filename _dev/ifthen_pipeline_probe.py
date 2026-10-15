"""IF/THEN 框要活过整条管线：**整帧**（`tui_live.draw`，含转场）里都看得见。

另外两支探针都是直接调 `school_scenes` 画框；这一支走**完整的一帧**。批 112 的问题正出在这里——
框画对了，但 `fx_apply` 的 reveal 把旧格贴回来、盖住了它（用户说的"切换特效"）。
所以取样点故意选在**行开头之后不久**，那正是转场最可能吃掉框的时候。

    python _dev/ifthen_pipeline_probe.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ifthen_common import boot, frame_at, frame_rows, ifthen_intervals  # noqa: E402

MARK = "\u252c"


def main() -> None:
    d, eng = boot()
    spans = ifthen_intervals()
    #: 每段取两个点：一个是"刚进这一段"（转场边缘），一个是段中段。
    probes = []
    for a, b in spans:
        probes.append(a + min(0.30, (b - a) * 0.1))
        probes.append(a + (b - a) * 0.5)
    ok, bad = 0, []
    for t in probes:
        s = frame_at(d, eng, t)
        if MARK in frame_rows(s)[0]:
            ok += 1
        else:
            bad.append(round(t, 2))
    for t in bad:
        print(f"  FAIL t={t} 整帧里没有框")
    print(f"{'PASS' if not bad else 'FAIL'}\uff1a{ok}/{len(probes)} 个时刻的整帧里都有框")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()