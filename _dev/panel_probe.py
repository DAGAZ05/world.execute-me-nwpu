"""Walk the basketball window frame by frame and say whether the panel reached the buffer.

    python _dev/panel_probe.py [58.65 70.08] [--size 197x52] [--step 0.25]

`_dev/dunk_live_probe.py` answers "did `dunk` run"; this answers "is the panel in the finished frame",
which is a different question and the one the user's report is about ("我确定看不到打篮球面板 ... 似乎不在
最上层"). For every sampled time it draws the real frame the player would draw and counts, inside
`tui_live.LEFT_BOX`:

  * `paper` - cells whose background is the panel's paper: the panel is on screen;
  * `ground` - cells still painted with the film's own `(4, 7, 15)`: something painted over it;
  * `spaces` - cells whose character is a space: the trail, the reveal and every other pass in the player
    treat those as free cells, so a panel full of them is a panel that can be drawn on;
  * `chat` - whether the chat window was drawn at all this frame (`WINDOW[0]`), and the shot's name.

A frame with paper 0 is a frame where the animation is invisible. The probe exits non-zero if any frame
inside the window is like that, so it can be wired into `check.cmd`.
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("window", nargs="*", type=float, default=[58.65, 70.08])
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--step", type=float, default=0.25)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    t0, t1 = (a.window + [58.65, 70.08])[:2]
    c, _, r = a.size.partition("x")
    cols, rows = int(c), int(r)

    T.VAR[0] = "school"
    import school_panels as SP
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G
    G.assume()
    eng = T.Engine()
    d = T.Data()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)

    s, sink = T.Screen(cols, rows), io.StringIO()
    # one continuous run, the way the player does it: the trail, the reveal and the ghost all depend on
    # the previous frame, so warming up separately per sample would measure a different program
    bad, n = 0, 0
    t = t0 - 1.5
    rows_out = []
    while t <= t1 + 0.05:
        T.draw(s, d, eng, max(0.0, t), True, 24.0)
        s.render_diff(sink)
        if t >= t0:
            bx0, by0, bx1, by1 = T.LEFT_BOX
            paper = ground = spaces = 0
            for y in range(max(0, by0), min(rows, by1 + 1)):
                for x in range(max(0, bx0), min(cols, bx1 + 1)):
                    ch, _fg, bg = s.buf[y][x]
                    if bg == (0, 0, 0) or bg == (4, 7, 15):
                        ground += 1
                    elif abs(bg[0] - 139) < 12 and abs(bg[1] - 145) < 12:
                        paper += 1
                    if ch in (" ", ""):
                        spaces += 1
            ent = SP.school_entry(t, eng.entry_at(t))
            n += 1
            if paper < 200:
                bad += 1
            if not a.quiet:
                rows_out.append(f"t={t:7.2f}  box={T.LEFT_BOX}  paper={paper:5d} ground={ground:5d} "
                                f"spaces={spaces:5d}  win={T.WINDOW[0]:<6} {ent['name'] if ent else '-'}")
        t += a.step
    if not a.quiet:
        print("\n".join(rows_out))
    print(f"{n} frame(s) sampled in {t0:.2f}-{t1:.2f} at {a.size}; "
          f"{bad} with the panel missing (paper < 200 cells)")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
