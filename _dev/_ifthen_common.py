from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402
import school_scenes as _SC     # noqa: E402


def boot():
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G
    G.assume()
    return T.Data(), T.Engine()


def frame_at(d, eng, t, back=0.6, size=(197, 52)):
    T.fx_clear(T.Screen(*size))
    s = T.Screen(*size)
    sink = io.StringIO()
    n = max(1, int(back * 24))
    for k in range(n):
        T.draw(s, d, eng, t - back + k / 24.0, True, 24.0)
        s.render_diff(sink)
    return s


def row_text(s, y, x0, x1):
    return "".join(s.buf[y][x][0] or " " for x in range(x0, x1 + 1))


def frame_rows(s, top=None):
    top = _SC.IFTHEN_TOP_ROW if top is None else top
    x0, _, x1, _ = T.PANE_BOX
    return [row_text(s, top + i, x0, x1) for i in range(_SC.IFTHEN_ROWS + 1)]


def cells_lit(rows):
    """(left, right) non-space counts in the frame's two cells.

    **切点在上边框，不在中间那行**（实测：中间那行只有左右两根边框竖线，两格之间没有分隔符，
    分隔是用上边框的 `┬` 与下边框的 `┴` 表示的）。所以从 `rows[0]` 里找最靠近正中的
    `┬`/`┼` 当切点，再拿 `rows[1]` 在它两侧数非空格。
    """
    if len(rows) < 2:
        return (0, 0)
    top, mid = rows[0], rows[1]
    cands = [i for i, ch in enumerate(top) if ch in "┬┼"]
    if not cands:
        return (0, 0)
    centre = len(top) // 2
    cut = min(cands, key=lambda i: abs(i - centre))
    left = sum(1 for ch in mid[2:cut] if ch != " ")
    right = sum(1 for ch in mid[cut + 1:-2] if ch != " ")
    return (left, right)


def ifthen_intervals(lo=5.0, hi=210.0, step=0.2):
    out, t = [], lo
    while t < hi:
        if _SC._ifthen_wanted(t):
            start = t
            while t < hi and _SC._ifthen_wanted(t):
                t += step
            out.append((start, t - step))
        t += step
    return out


def ifthen_lines():
    """The scheduled rows whose lyric really is a conditional clause.

    `_ifthen_wanted(t)` yields only two continuous True spans in the whole song (29.40-44.00 and
    73.60-88.20) because adjacent conditional lines are contiguous. To name them one by one we walk the
    schedule instead and ask once per row, at its midpoint.
    """
    out = []
    for r in SP.shot_rows():
        if not r.get("name"):
            continue
        mid = r["at"] + (r["end"] - r["at"]) * 0.5
        if _SC._ifthen_wanted(mid):
            out.append((r["at"], r["end"], r.get("lyric") or ""))
    return out
