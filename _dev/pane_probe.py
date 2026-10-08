"""Draw every course and instrument pane at several pane sizes, and report what goes wrong.

The twelve drawings in `school_courses` are written for a rectangle of *some* size and the player
hands them whatever the window leaves - at 197x52 that is about eleven rows by a hundred-odd columns,
but `draw_body` gives less on a short window and the narrowest layouts give a third of that. A drawing
that silently writes outside its rect is invisible in the player (the pane is clipped by the box
around it) and only shows up as a course that looks empty or a box that looks broken.

So this is the cheap version of that check: render each pane at four sizes, from the real one down to
one where it is expected to degrade to nearly nothing, and report two things - an exception, and ink
outside the rect. Nothing here is part of the player.

    python _dev/pane_probe.py              all panes, four sizes, summary only
    python _dev/pane_probe.py --shots      also write the middle size to _dev/out/panes/
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402
import school_courses as CO     # noqa: E402

SIZES = [(118, 11), (118, 9), (60, 7), (34, 5),   # the pane as it was, then three degrading ones
         (113, 36), (113, 20)]                     # and the pane as the layout now gives it


def _ink_outside(s: T.Screen, x0: int, y0: int, x1: int, y1: int) -> int:
    """Cells with any ink at all outside the rect, ignoring the box the player draws around it."""
    n = 0
    for y in range(s.rows):
        for x in range(s.cols):
            ch = s.buf[y][x][0]
            if ch in ("", " "):
                continue
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                n += 1
    return n


def _bad_colours(s: T.Screen):
    """The first cell whose fg/bg is not an RGB tuple, and what it holds instead.

    This check exists because of a real defect that the two checks above could not see. A pane called
    `s.put(x, y, text, fg, 1.0)` - five arguments, where the fifth is the *background colour* - and the
    float went into the buffer and travelled to `render_diff` before anything raised. From this file's
    point of view the pane had drawn fine: it had not thrown, and every cell it wrote was inside its
    rect. The failure was in the *shape* of what it wrote.

    A pane that paints the buffer directly is the only caller `Screen` has that can do this, so the
    check belongs here: the player never writes a bare float, and if the variant does, the pane probe is
    where it should be caught rather than `render_diff`, one call frame further away.
    """
    for y in range(s.rows):
        for x in range(s.cols):
            cell = s.buf[y][x]
            if not isinstance(cell, tuple) or len(cell) != 3:
                return (x, y, repr(cell))
            for k, name in ((1, "fg"), (2, "bg")):
                c = cell[k]
                if not (isinstance(c, tuple) and len(c) == 3 and all(isinstance(v, int) for v in c)):
                    return (x, y, f"{name}={c!r} in {cell!r}")
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shots", action="store_true")
    a = ap.parse_args()

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    out = Path(__file__).resolve().parent / "out" / "panes"
    if a.shots:
        out.mkdir(parents=True, exist_ok=True)
        from tui_shot import Painter
        painter = Painter()

    # every pane the schedule ever draws, at the argument its row carries: a pane drawn six different
    # ways (`pane_memory` on the five "You have left") is six different drawings and each has to fit
    panes: list[tuple[str, dict | None]] = []
    seen = set()
    for r in SP.shot_rows():
        if not r.get("name"):
            continue
        key = (r["name"], tuple(sorted((r.get("args") or {}).items())))
        if key not in seen:
            seen.add(key)
            panes.append((r["name"], r.get("args")))
    bad = 0
    # ...and every pane must *show* the row's one-line explanation (batch 58, the user: "抬头部分，标题后
    # 加上' · '+简短说明文字"). A pane that draws its own first row has no header for it to sit after -
    # that is what `school_scenes.HEADERLESS` is for - so a new pane added without either is a header the
    # viewer never sees. The marker is two characters no drawing prints, which makes "is it on screen" a
    # buffer test rather than a look at the picture.
    MARK = "\u25c7\u6807"
    for pane, args in panes:
        tag = f"{pane}({','.join(f'{k}={v}' for k, v in (args or {}).items())})"
        line = []
        for k, (w, h) in enumerate(SIZES):
            s = T.Screen(w + 6, h + 4)
            try:
                SP.draw_scene_pane(pane, s, 2, 2, 2 + w - 1, 2 + h - 1, 100.0, 1.0, 2.0, 0.85,
                                   args=args, sub=MARK if k == 0 else "")
            except Exception as exc:
                line.append(f"{w}x{h}: RAISED {type(exc).__name__}: {exc}")
                bad += 1
                if k == 0:
                    traceback.print_exc()
                continue
            leak = _ink_outside(s, 2, 2, 2 + w - 1, 2 + h - 1)
            bad_col = _bad_colours(s)
            if leak:
                note, bad = f"LEAK {leak}", bad + 1
            elif bad_col:
                note, bad = f"COLOUR {bad_col[2]}", bad + 1
            elif k == 0 and not any(MARK in "".join(s.buf[y][x][0] for x in range(s.cols))
                                    for y in range(s.rows)):
                note, bad = "NO HEADER SUB", bad + 1
            else:
                note = "ok"
            line.append(f"{w}x{h}:{note}")
            if a.shots and k == 0:
                painter.paint(s, out / (tag.replace(",", "_").replace("=", "") + ".png"), tag)
        print(f"{tag:<40} " + "  ".join(line))
    print(f"\n{bad} problem(s) across {len(panes)} panes x {len(SIZES)} sizes")
    if a.shots:
        print(f"shots in {out}")
    # Non-zero on a real problem so `check.cmd` can run this and look at the exit code rather than at
    # the wording. A check that cannot fail a script is a check nobody runs.
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
