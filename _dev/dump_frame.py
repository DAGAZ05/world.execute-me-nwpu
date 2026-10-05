"""Ad-hoc: one frame of the variant, as text - for reading geometry when a PNG shows something you
cannot name (a dot in the wrong place, a line that stops early).

    python _dev/dump_frame.py 155.0                 the whole frame at 197x52
    python _dev/dump_frame.py 155.0 --cols 100-197  one column range
    python _dev/dump_frame.py 155.0 --rows 4-20     one row range
    python _dev/dump_frame.py 155.0 --find ●        where a glyph is, as coordinates and colours

The dump goes to `_dev/out/frame.txt` as UTF-8 because the console's codepage is GBK and box drawing
characters raise there rather than printing. Read the file with an editor, not with `type`.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402


def _frame(t: float, cols: int, rows: int) -> T.Screen:
    """The frame the player would be showing at `t`, warmed up the way it would be."""
    T.VAR[0] = "school"
    import school_panels as SP       # noqa: E402
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G          # noqa: E402
    G.assume()
    eng = T.Engine()
    d = T.Data()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    for k in range(int(1.5 * 24) + 1):
        T.draw(s, d, eng, max(0.0, t - 1.5 + k / 24.0), True, 24.0)
        s.render_diff(sink)
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("t", type=float)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--cols", default="")
    ap.add_argument("--rows", default="")
    ap.add_argument("--find", default="", help="a single glyph to locate instead of dumping")
    a = ap.parse_args()
    c, _, r = a.size.partition("x")
    cols, rows = int(c), int(r)
    s = _frame(a.t, cols, rows)

    def bounds(text: str, n: int) -> tuple[int, int]:
        if not text:
            return 0, n - 1
        lo, _, hi = text.partition("-")
        return int(lo), (int(hi) if hi else n - 1)

    x0, x1 = bounds(a.cols, cols)
    y0, y1 = bounds(a.rows, rows)
    x1, y1 = min(x1, cols - 1), min(y1, rows - 1)
    out = []
    if a.find:
        out.append(f"t={a.t:.2f}  {a.find!r} in {cols}x{rows}, cols {x0}..{x1}, rows {y0}..{y1}")
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if s.buf[y][x][0] == a.find:
                    out.append(f"  x={x:3} y={y:2}  fg={s.buf[y][x][1]}")
        out.append(f"  {sum(1 for line in out if line.startswith('  x='))} cell(s)")
    else:
        out.append(f"t={a.t:.2f}  {cols}x{rows}  cols {x0}..{x1}  rows {y0}..{y1}")
        out.append("      " + "".join(str(x // 10 % 10) for x in range(x0, x1 + 1)))
        for y in range(y0, y1 + 1):
            out.append(f"{y:4}  " + "".join(s.buf[y][x][0] for x in range(x0, x1 + 1)))
    dest = Path(__file__).resolve().parent / "out" / "frame.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out) + "\n", encoding="utf8")
    print(f"{len(out)} line(s) written to {dest}")


if __name__ == "__main__":
    main()
