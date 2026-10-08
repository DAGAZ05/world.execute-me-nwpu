"""Replay the *interactive loop* and dump the frame it would really be showing at `t`.

Why this exists, and why `school_shot.py` is not enough:

  * `school_shot.py` (and any "look back 1.5 s and draw those frames into one screen" harness) draws the
    frames it needs for the sprite cache and then one final frame. What the viewer sees is that final
    frame **plus** whatever `fx_reveal` decided to hold from the frame before it - and the hold is decided
    per cell by the cut's own order, not by time.
  * So a screen that is *complete* when drawn once into a fresh `Screen` can be a **fragment** in the
    player. Batch 51 found exactly that on the opening motto: a fresh frame had
    `公诚勇毅 · 三实一新` in cells 89..107, and the replayed frame had `公诚 毅  三实一新` - `勇` still the
    previous frame's blank, the `·` still the ops box's own border, for the whole of the cut.

This is the tool that tells the two apart: one `Screen`, one `draw` + one `render_diff` per 1/24 s from
`--from` to `t`, exactly as `main()`'s loop does.

    python _dev/live_replay.py 4.30 --from 0
    python _dev/live_replay.py 190.0 --from 186 --size 197x52

It also prints, for every row that contains the motto, which cells the caption actually occupies - the
question "is this sentence on screen whole" is not answerable from a downscaled PNG.
"""
from __future__ import annotations

import argparse
import io
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

OUT = ROOT / "_dev" / "out" / "live"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("t", type=float, help="the song time to stop at")
    ap.add_argument("--from", dest="start", type=float, default=0.0, help="where the replay begins")
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--gate", action="store_true",
                    help="leave the college question *up* instead of answering it: the panel is only "
                         "drawn while nobody has answered (school_gate.window_open), so this is the "
                         "one way to render the option list - `--gate` is what preview/05 comes from")
    ap.add_argument("--text", default="\u516c\u8bda", help="report the rows holding this text")
    args = ap.parse_args()

    import tui_live as T
    import school_panels as SP

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G
    # The gate is pre-answered by default so that a render is deterministic (a seek past the question
    # assumes the same answer). `--gate` is the opposite: it leaves the state in `waiting`, which is the
    # only state the panel is drawn in - so that is how the option list itself gets rendered.
    if args.gate:
        G.reset()
    else:
        G.assume()

    cols, rows = (int(v) for v in args.size.lower().split("x"))
    eng, data = T.Engine(), T.Data()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    n = max(1, int(round((args.t - args.start) * 24)) + 1)
    for k in range(n):
        T.draw(s, data, eng, args.start + k / 24.0, True, 24.0)
        s.render_diff(sink)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = "live%08.2f" % args.t
    from tui_shot import Painter
    Painter().paint(s, out / (name + ".png"), "")
    (out / (name + ".txt")).write_text(
        "\n".join("%2d |%s|" % (y, "".join(s.buf[y][x][0] for x in range(cols))) for y in range(rows)),
        encoding="utf8")
    print(out / (name + ".png"))
    for y in range(rows):
        pat = "".join(s.buf[y][x][0] for x in range(cols))
        if args.text and args.text in pat:
            hits = [x for x in range(cols) if s.buf[y][x][0] and s.buf[y][x][0] != " "]
            print("  row %2d  ink at %s" % (y, hits[:24]))


if __name__ == "__main__":
    main()
