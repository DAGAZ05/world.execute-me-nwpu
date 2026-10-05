"""What the transitions actually do to a frame, as text, one phase at a time.

The transitions are post-processes on a finished frame, so a bug in one of them is invisible in the
player until the half second it runs. This draws a deliberately readable frame - a grid with labelled
borders - and then runs one transition on it at a series of `q` values, printing the buffer. It is how
the shatter's two-pass bug was found: the frame came out black with cracks in it, which the PNG at
player resolution showed as "the shards are missing" and nothing more specific.

    python _dev/trans_probe.py shatter
    python _dev/trans_probe.py slide zoom skew page
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_fx as FX          # noqa: E402

W, H = 96, 30


def canvas() -> T.Screen:
    """A frame with something on it everywhere: a grid, so a shard that moves takes evidence with it."""
    s = T.Screen(W, H)
    for y in range(H):
        for x in range(W):
            if y in (0, H - 1) or x in (0, W - 1):
                s.put(x, y, "#", (200, 220, 255))
            elif y % 5 == 0:
                s.put(x, y, "=", (120, 150, 200))
            elif x % 12 == 0:
                s.put(x, y, "|", (110, 140, 190))
            else:
                s.put(x, y, ".", (70, 90, 120))
    for i, lab in enumerate(range(0, W, 12)):
        s.put(lab + 1, 2, f"c{lab:02d}", (230, 200, 120))
    return s


def show(s: T.Screen, tag: str) -> None:
    print(f"--- {tag}")
    for y in range(H):
        print("".join(c[0] if c[0] else " " for c in s.buf[y]).rstrip())


def check_cells(s: T.Screen) -> str:
    """The invariant a transition must not break: every cell's character is at most one character.

    `Screen.put` writes a *filler* - an empty character with `wide=True` - after every double-width
    character, and the PNG rasteriser skips those by testing the flag. A transition that moves cells
    around can move a filler without its flag, and then `east_asian_width("")` raises inside the
    rasteriser, three modules away from the transition that caused it. That is exactly what happened,
    so the check lives here, next to the code that can break it.
    """
    for y in range(s.rows):
        for x in range(s.cols):
            ch, _fg, _bg = s.buf[y][x]
            if not isinstance(ch, str) or len(ch) > 1 or (ch == "" and not s.wide[y][x]):
                return f"({x},{y}) holds {ch!r} with wide={s.wide[y][x]}"
    return ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kinds", nargs="*", default=["shatter"])
    ap.add_argument("--cells", action="store_true", help="only run the cell-invariant check")
    a = ap.parse_args()
    bad = 0
    for kind in a.kinds:
        for q in (0.15, 0.35, 0.45, 0.6, 0.85):
            s = canvas()
            if kind == "shatter":
                FX._SHARDS.clear()
                FX._shatter(s, W, H, 0.0, q)
            else:
                {"slide": FX._slide, "zoom": FX._zoom, "skew": FX._skew, "page": FX._page}[kind](
                    s, W, H, q)
            if not a.cells:
                show(s, f"{kind} q={q}")
            problem = check_cells(s)
            if problem:
                bad += 1
                print(f"CELLS {kind} q={q}: {problem}")
    print(f"{bad} cell problem(s) across {len(a.kinds)} transition(s)")
    # Non-zero on a real problem so `check.cmd` can run this and look at the exit code rather than at
    # the wording.
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
