"""Rasterise the school variant's frames to PNG - the check that has to be done by looking.

`tui_shot.py` does this for the film's own frames, but it reads `T.FP.dsh_window` and
`T._avatar_block` to build its avatar sheet, and it loads the film's engine before every run. This
is the school variant's own equivalent, and it is deliberately separate: it renders the frames the
*batch* is about (the ten shots of `03_批次设计/batch_01.md`) and nothing else.

    python _dev/school_shot.py                    the batch-1 times, into _dev/out/school/
    python _dev/school_shot.py 0.5 3.6 9.8        specific times
    python _dev/school_shot.py --size 120x34      a narrow window, to check the layout degrades
    python _dev/school_shot.py --no-engine        panes off: chat window and chrome only
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "player" / "_tools"
sys.path.insert(0, str(TOOLS))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
from tui_shot import Painter    # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "school"

# the ten shots of batch 1, at the moment their pane has something to show: one second in, so the
# pane's own animation has run and a still frame is representative rather than a first frame.
BATCH1 = [0.9, 2.2, 4.4, 6.0, 8.0, 10.5, 11.6, 12.9, 20.0, 30.0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("times", nargs="*", type=float, default=None)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-engine", action="store_true", help="no shot table: no pane, no ops ticker")
    ap.add_argument("--no-title", action="store_true")
    ap.add_argument("--var", default="school", choices=["school", "original"])
    ap.add_argument("--major", help="pre-answer the college gate (default: assume it, i.e. render past "
                                    "02:11.9 with the question answered - see the note in main())")
    args = ap.parse_args()

    T.VAR[0] = args.var
    if args.var == "school":
        import school_panels as SP
        T.SP = SP
        SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
        # The college gate must be answered before any frame is rendered, and *how* it is answered is a
        # property of the render, not of the frame: `--major` pre-answers it, and without one the gate
        # would hold the playhead at 02:11.9 for every requested time (the clock is pinned while it is
        # armed, so a probe at 02:50 would be a probe at 02:11.9 with the question on screen - which is
        # correct behaviour and useless as a check). Passing no `--major` therefore assumes the default,
        # the same thing the player does when the bar is dragged past the gate.
        import school_gate as G
        if args.major:
            G.reset(args.major)
        else:
            G.assume()
    c, _, r = args.size.partition("x")
    cols, rows = int(c), int(r)

    eng = None
    if not args.no_engine:
        print("loading the shot table...", file=sys.stderr, flush=True)
        eng = T.Engine()

    d = T.Data()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)
    p = Painter()
    times = args.times if args.times else (BATCH1 if args.var == "school" else [30.0])
    for t in times:
        T.fx_clear()
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        # a warm-up pass from the *previous* shot, so a cut is real rather than a first frame; the
        # school overlay's cuts land on lyric lines, so the 1.5 s before the target is the outgoing
        # shot for every row in the table.
        #
        # The loop ends *at* `t`, and the count matters: 24*2 frames from `t - 1.5` end at `t + 0.458`,
        # so the PNG was labelled `t` and showed half a second later. Every frame this tool has ever
        # produced was shifted by that much - it is how the torpedo leap was "missing" while the shatter
        # it causes was on screen. 1.5 s at 24 fps is 36 steps, so 37 frames land on the target.
        for k in range(int(1.5 * 24) + 1):
            T.draw(s, d, eng, max(0.0, t - 1.5 + k / 24.0), True, 24.0)
            s.render_diff(sink)
        ent = T.SP.school_entry(t, eng.entry_at(t)) if (eng is not None and T.SP is not None) else None
        label = (f"t={t:6.2f}  {ent['name'] if ent else '-'}  ops={'/'.join(ent['ops']) if ent else '-'}"
                 if not args.no_title else "")
        T.fx_clear()
        out = Path(args.out) / (f"t{t:07.2f}".replace(".", "_") + ".png")
        print(p.paint(s, out, label))


if __name__ == "__main__":
    main()
