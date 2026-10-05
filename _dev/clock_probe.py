"""Does every drawing in the right-hand pane still move once it has finished being revealed?

The variant tells the song's story in one pane, and the pane is *revealed* by `u` - its own progress
through the slot it was given. `u` alone is a monotone animation: the drawing assembles and then sits
there, so a 20-second slot is a still image for 19 of its seconds and the act reads as a slide show.
The fix, applied pane by pane since batch 14, is the second clock: the drawing also reads `k.t` (the
song clock) or `lt` (its own elapsed time within the slot) and moves something on it - a cursor walking
a row, a packet crossing a wire, a level breathing - independently of how far the reveal has got.

A pane is easy to write without that and it is invisible in a still frame, so the PNG review cannot see
it: the drawing looks finished either way. This probe is the check. It draws the row at full reveal
(`u = 1.0`, so nothing is left to assemble) at three moments spread across the slot the row really
has, and counts the cells that change. Three identical frames mean the pane, as a viewer sees it, is a
photograph for the whole time it is on screen.

It samples the row's *own* span rather than a fixed window on purpose: a pane whose clock moves once
every two seconds is not moving in a 0.82 s slot, and a fixed four-second window would call it alive.

Some panes are meant to be still - the campus and character plates are photographs - and they are named
in `STILL_OK` with the reason. Everything else has to move.

    python _dev/clock_probe.py               every row, worst first
    python _dev/clock_probe.py --size 95x33  the pane as the production layout gives it
    python _dev/clock_probe.py --selftest    draw each row twice with identical arguments
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
import school_panels as SP      # noqa: E402

# Where in the slot the three frames are taken. They are not `0.0` and `1.0` because a few drawings key
# their last stage to exactly `u == 1.0` and would read as moving when they are not.
FRACTIONS = (0.15, 0.55, 1.0)

# A pane that is still and has less ink than this is not worth reporting: `pane_countdown` holds one
# digit, and a caption that does not blink is the design.
MIN_INK = 60

# Panes that are still on purpose: photographs and plates out of `assets/`, drawn by `school_scenes`
# and `school_fx` rather than by a `school_courses` routine. There is nothing in them to animate, and
# while they are on screen the left window, a flight or a motif band is carrying the motion.
STILL_OK = {
    # the five campus plates and the two character plates
    "pane_landmark_hezun", "pane_landmark_dialogue", "pane_landmark_cat", "pane_landmark_crest",
    "pane_landmark_sword", "pane_class", "pane_knowledge",
    # the film's own left-hand window is the picture here; the pane only holds the backlog table
    "pane_backlog", "pane_hello_world", "pane_thread", "pane_converge", "pane_love_class",
}


def _diff(a: T.Screen, b: T.Screen) -> int:
    """Cells that differ in glyph or in either colour."""
    n = 0
    for y in range(a.rows):
        for x in range(a.cols):
            if a.buf[y][x] != b.buf[y][x]:
                n += 1
    return n


def _ink(s: T.Screen, x0: int, y0: int, x1: int, y1: int) -> int:
    n = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if s.buf[y][x][0] not in ("", " "):
                n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default="113x33", help="the pane, in cells (default 113x33)")
    ap.add_argument("--selftest", action="store_true",
                    help="draw each row twice with identical arguments; all must read identical")
    a = ap.parse_args()
    c, _, r = a.size.partition("x")
    w, h = int(c), int(r)

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))

    def draw(name, args, at, lt, span):
        s = T.Screen(w + 6, h + 4)
        SP.draw_scene_pane(name, s, 2, 2, 2 + w - 1, 2 + h - 1, at, lt, span, 1.0, args=args)
        return s

    if a.selftest:
        # Two draws with the same arguments *must* be identical. If they are not, the difference does
        # not come from either clock - it is unseeded randomness or state kept between draws - and no
        # number this probe prints for that row is evidence of anything.
        rows = [(r_["name"], r_.get("args"), r_["at"], r_["end"] - r_["at"])
                for r_ in SP.shot_rows() if r_.get("name")]
        bad = []
        for name, args, at, span in rows:
            two = [draw(name, args, at, span * FRACTIONS[2], span) for _ in range(2)]
            if _diff(two[0], two[1]):
                bad.append((name, _diff(two[0], two[1])))
        if bad:
            print("SELFTEST FAILED - these rows differ between two identical draws:")
            for name, n in bad:
                print(f"  {name:<32} {n} cell(s)")
            raise SystemExit(1)
        print(f"SELFTEST ok - all {len(rows)} rows read identical when drawn twice the same way")
        raise SystemExit(0)

    out, still = [], []
    for row in SP.shot_rows():
        name = row.get("name")
        if not name:
            continue
        span = row["end"] - row["at"]
        args = row.get("args")
        tag = f"{name}({','.join(f'{k}={v}' for k, v in (args or {}).items())})"
        shots = [draw(name, args, row["at"] + span * f, span * f, span) for f in FRACTIONS]
        best = max(_diff(shots[i], shots[j]) for i in range(3) for j in range(i + 1, 3))
        ink = _ink(shots[-1], 3, 4, 2 + w - 2, 2 + h - 2)
        out.append((best, ink, span, row["at"], tag))
        if not best and ink >= MIN_INK and name not in STILL_OK:
            still.append((best, ink, span, row["at"], tag))

    out.sort()
    print(f"every row on the song clock, still ones first ({len(out)} rows at {w}x{h}):")
    for best, ink, span, at, tag in out:
        note = "STILL" if not best else f"moves {best:5d}"
        mark = ""
        if not best:
            mark = "  <- by design" if tag.split("(")[0] in STILL_OK else "  <- NEEDS A CLOCK"
            if ink < MIN_INK:
                mark = "  <- almost empty, not reported"
        print(f"  {tag:<44} {note}  span {span:5.2f}s  ink {ink:4d}{mark}")
    print(f"\n{len(out)} rows at {w}x{h}: {len(still)} still with no reason recorded")
    if still:
        print("  FAIL: " + ", ".join(t for _b, _i, _s, _a, t in still))
    raise SystemExit(1 if still else 0)


if __name__ == "__main__":
    main()
