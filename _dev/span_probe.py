"""Do the short panes have anything on them in the first frame they are shown?

The 12 "Execution" hits give a pane 0.83 s and the three countdown numbers give the six instruments
0.40-0.87 s, so twenty-four of the forty-nine schedule rows are shorter than 1.2 s. A drawing may
animate - most of them do - but a drawing whose *content* arrives with `u` shows an empty box for the
first frames of a sub-second slot, and at 24 fps that is what a viewer sees: a flash of black.

So this probes every row at the start of its life and at the end, and reports the panes that show
almost nothing at the start. It is the check behind the density decision recorded in
`05_歌词会话对照_v2.md` §6: keep twenty-five pictures in the first act, but make every picture legible
in the time it actually gets.

    python _dev/span_probe.py            every row, worst first
    python _dev/span_probe.py --min 0.5  only rows shorter than half a second
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402

# a pane that has less than this share of its finished ink at the first frame it is shown is a pane
# that starts black. Half is a generous floor: the drawings reveal members and curves, and half of
# them on frame one means the box is never empty.
FLOOR = 0.45

# ...but only for panes that *have* a substantial drawing. `pane_countdown` shows the digit "3" and
# nothing else on its first frame because it is a countdown, and its finished frame is one caption, a
# timer and a rule - a hundred and thirty lit cells in all. Reporting it would be reporting the design.
# The threshold is where "there is a drawing here" starts being true.
REPORT_FROM = 200

# Rows below the floor that were looked at and kept, with what the frame showed. The floor is a
# heuristic for "the box is empty on the frame it appears"; a drawing can be under it and still be
# legible, and then the number is telling the truth about the ink and nothing about the viewer.
KNOWN = {
    "pane_exec_dl": "the loss curve is drawn one bar at a time; frame one is the title, the value and "
                    "the first bar - _dev/out/dl/t0159_78.png",
}


def ink(s: T.Screen, x0: int, y0: int, x1: int, y1: int) -> int:
    n = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if s.buf[y][x][0] not in ("", " "):
                n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min", type=float, default=1.2, help="only rows shorter than this (default 1.2)")
    ap.add_argument("--size", default="113x33", help="the pane, in cells")
    a = ap.parse_args()
    c, _, r = a.size.partition("x")
    w, h = int(c), int(r)

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))

    bad, checked = [], 0
    for row in SP.shot_rows():
        name = row.get("name")
        if not name:
            continue
        span = row["end"] - row["at"]
        if span >= a.min:
            continue
        checked += 1
        shots = []
        for u in (0.02, 1.0):
            s = T.Screen(w + 6, h + 4)
            SP.draw_scene_pane(name, s, 2, 2, 2 + w - 1, 2 + h - 1, row["at"], span * u, span, u,
                               args=row.get("args"))
            shots.append(ink(s, 3, 4, 2 + w - 2, 2 + h - 2))
        first, last = shots
        share = first / last if last else 1.0
        if share < FLOOR and last >= REPORT_FROM:
            bad.append((share, span, row["at"], name, first, last))

    bad.sort()
    print(f"{checked} row(s) shorter than {a.min:.2f}s, drawn at {w}x{h}")
    for share, span, at, name, first, last in bad:
        note = KNOWN.get(name)
        print(f"  {share * 100:5.1f}%  span {span:4.2f}s  t={at:7.2f}  {name:22} "
              f"ink {first:4d} -> {last:4d}" + (f"   ({note})" if note else ""))
    unexplained = [b for b in bad if b[3] not in KNOWN]
    print(f"\n{len(bad)} of {checked} start below {FLOOR * 100:.0f}% of a drawing of "
          f"{REPORT_FROM}+ cells ({len(bad) - len(unexplained)} reviewed and accepted)")
    # Non-zero when a row starts empty and nobody has said why, so `check.cmd` can run this and look
    # at the exit code rather than at the wording.
    raise SystemExit(1 if unexplained else 0)


if __name__ == "__main__":
    main()
