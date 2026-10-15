"""不许有"擦出来"的空白带：一条空白带在相邻两帧之间**突然出现或消失**。

批 108-117 修 IF/THEN 框时我用过一版"擦除"：某些帧把框那三行抹成空格。它的签名不是"版面上有空白"
——稀疏的 pane 本来就有大片空白（实测某几帧 pane 中间本来就有 9~18 行是空的）——而是
**一条空白带在相邻两帧之间凭空出现或消失**：上一帧那块地方有画，下一帧没了。

所以判据是**帧间差**，不是静态空白：同一格位置，一帧有墨、紧邻的下一帧 0 墨（或反过来），
且这样的行**连续 >= 2 行**。单行的进出是正常的逐帧重绘（光标、闪烁的 `%`、走过的点）。

擦除机制本身在批 118 已整套删掉（用户明确要求"后续所有实现禁止擦除"），这个探针守的是它不再回来。

    python _dev/blank_row_probe.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ifthen_common import boot, frame_at  # noqa: E402

import tui_live as T            # noqa: E402

#: 采样时刻，铺满学校段与学院段。
TIMES = (15.0, 22.0, 30.4, 38.0, 44.0, 52.0, 58.0, 68.0, 76.0, 84.0,
         96.0, 118.0, 140.0, 165.0, 196.0)


def _row_ink(s, x0, x1, y):
    return sum(1 for x in range(x0 + 1, x1) if (s.buf[y][x][0] or " ").strip())


def _bands(prev_ink, cur_ink, y0, min_run=2):
    """连续 >= min_run 行，上一帧有墨、这一帧空（或反过来）。"""
    out, i = [], 0
    n = len(cur_ink)
    while i < n:
        a, b = prev_ink[i] > 0, cur_ink[i] == 0
        rev = prev_ink[i] == 0 and cur_ink[i] > 0
        if a == b and not a:
            i += 1
            continue
        if not (a or rev):
            i += 1
            continue
        j = i
        while j < n:
            aa = prev_ink[j] > 0 and cur_ink[j] == 0
            rr = prev_ink[j] == 0 and cur_ink[j] > 0
            if (a and aa) or (rev and rr):
                j += 1
            else:
                break
        if j - i >= min_run:
            out.append((y0 + i, j - i))
        i = max(j, i + 1)
    return out


def main() -> None:
    d, eng = boot()
    ok, bad = 0, []
    for t in TIMES:
        s1 = frame_at(d, eng, t)
        s2 = frame_at(d, eng, t + 1.0 / 24.0)
        x0, y0, x1, y1 = T.PANE_BOX
        ys = list(range(y0 + 2, y1))
        i1 = [_row_ink(s1, x0, x1, y) for y in ys]
        i2 = [_row_ink(s2, x0, x1, y) for y in ys]
        hit = _bands(i1, i2, y0 + 2)
        if hit:
            bad.append((t, hit))
        else:
            ok += 1
    for t, hit in bad:
        print(f"  FAIL t={t:.1f} 帧间凭空进出的空白带 {hit}")
    print(f"{'PASS' if not bad else 'FAIL'}\uff1a{ok}/{len(TIMES)} 对相邻帧没有凭空进出的空白带")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()