"""Smoothness has two budgets, and only one of them was ever measured.

`frame_probe` measures the first: how long Python takes to build a frame, against the 41.7 ms the film's
own 24 fps allows. The second is the terminal's: `render_diff` writes only the cells that changed, and a
photo sprite crossing the frame changes thousands of them - each one a cursor move and two 24-bit colour
escapes if its neighbours differ, which on a photograph they do. Nobody had measured that number, and on
this machine it was the bigger of the two.

Batch 59 acted on both (the numbers below are before -> after that batch):

    window        python mean            terminal mean          escapes      cells
    14.0-16.0 s   36.8 -> 31.4 ms        212 -> 171 KB          14 379 -> 9 642   7 225   (运-20 crossing)
    60.0-64.0 s   26.1 -> 22.8 ms         44 ->  35 KB           2 992 -> 2 088   3 933
    146-150 s     25.9 -> 22.4 ms         42 ->  30 KB           2 943 -> 1 828  10 455
    190-196 s     27.5 -> 23.7 ms         55 ->  43 KB           3 721 -> 2 481   6 104

What was done, in the order it paid: `_wide_char` memoised (it is called per cell and per character of
every run); the diff stops emitting a cursor move when the run starts where the cursor already is and
stops re-emitting a colour pair that is already set (`--` the escapes at the crossing); `paste(fast=True)`
folds its ramp constants; and the plate routes (`school_sculpture`'s five) blit instead of calling `put`
per cell with a colour mix per cell (`_Kit.blit`).

**A dead end, measured rather than guessed**: rounding the sprite's colours to 5-6 bits to make
neighbouring cells equal - which would merge diff runs - is worth only 8-14 % of the bytes (171 -> 158 KB
at 5 bits) while moving real colour (max 4-8/255 per channel). The sprite is *dithered*; that is what
defeats run merging, so the idea was dropped.

Measured on *playback* - consecutive 1/24 s frames, diffed against each other like the player does. (The
first version of this measured one instant over and over: `render_diff` compares with the previous frame,
so every frame after the first was empty, and the terminal budget read zero.)

Two numbers come out of it, and they answer two different questions:

  * **python** - what the loop can reach. `tui_live.main` draws as fast as it can and then sleeps to
    `--fps-cap` (60 by default since batch 59, 30 before that), so the picture's rate is
    `min(cap, 1000/ms)`.
  * **terminal** - what the console has to repaint, in bytes and escape sequences. 212 KB a frame at
    25 fps is 5 MB/s of escape stream through one pipe; a terminal that cannot keep up drops the picture
    to whatever it can paint, whatever Python's number says.

This is a **report**, not a check, and the reason is that the two budgets have different owners: 24 fps is
the film's own rate and `frame_probe` fails on it, while `--fps-cap` is a comfort setting - a window whose
mean is above the cap's own frame time simply plays below that cap.

    python _dev/paint_probe.py                  the windows above, in both currencies
    python _dev/paint_probe.py --at 15.0        one two-second window around a time
    python _dev/paint_probe.py --full           every frame of the song (a couple of minutes)
    python _dev/paint_probe.py --budget 16.7    the frame time the loop's default cap implies
"""
from __future__ import annotations

import argparse
import gc
import io
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

# (from, to) - one window per kind of frame: the aircraft, a motif, the flood, the closing
WINDOWS = [(14.0, 16.0), (60.0, 64.0), (98.0, 102.0), (146.0, 150.0), (190.0, 196.0)]


class Counting(io.StringIO):
    """A sink that measures what a terminal would receive: bytes and escape sequences."""

    def __init__(self) -> None:
        super().__init__()
        self.bytes = 0
        self.escapes = 0

    def write(self, text: str) -> int:
        self.bytes += len(text.encode("utf8"))
        self.escapes += text.count("\x1b")
        return len(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", type=float, help="one window of -1 s .. +1 s around this time")
    ap.add_argument("--full", action="store_true", help="every frame of the song")
    ap.add_argument("--budget", type=float, default=16.7,
                    help="the loop's own cap, in ms per frame (`--fps-cap` 60); reported, never failed on")
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    import tui_live as T
    import school_panels as SP
    import school_fx as FX

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    windows = ([(0.0, 212.0)] if a.full else
               [(a.at - 1.0, a.at + 1.0)] if a.at is not None else WINDOWS)
    gc.disable()
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)
    s = T.Screen(cols, rows)

    print(f"{cols}x{rows}; the loop caps at {1000 / a.budget:.1f} fps, the film's own rate is 24 fps")
    over = 0
    for lo, hi in windows:
        frames = [lo + k / 24.0 for k in range(int((hi - lo) * 24) + 1)]
        for t in frames[:-1]:                       # warm: sprites, caches, and the previous frame
            T.draw(s, data, eng, t, True, 24.0)
            s.render_diff(io.StringIO())
        sink = io.StringIO()
        ms = []
        for t in frames:                            # timing on its own, so the byte counting is not in it
            t0 = time.perf_counter()
            T.draw(s, data, eng, t, True, 24.0)
            s.render_diff(sink)
            ms.append((time.perf_counter() - t0) * 1000)
        kb, esc, cells, probe = [], [], [], Counting()
        for t in frames:                            # ...and the terminal's share, counted separately
            probe.bytes = probe.escapes = 0         # per frame, not cumulative
            T.draw(s, data, eng, t, True, 24.0)
            cells.append(s.render_diff(probe))
            kb.append(probe.bytes / 1024)
            esc.append(probe.escapes)
        mean = sum(ms) / len(ms)
        worst = max(ms)
        flag = ""
        if mean > a.budget:
            flag = f"   <-- below the loop's own cap ({1000 / mean:.0f} fps)"
            over += 1
        row = SP.row_at((lo + hi) / 2)
        print(f"{lo:6.1f}-{hi:6.1f}s  python mean {mean:5.1f} worst {worst:5.1f} ms "
              f"({1000 / mean:4.1f} fps)   terminal mean {sum(kb) / len(kb):6.1f} "
              f"worst {max(kb):6.1f} KB   escapes {sum(esc) / len(esc):6.0f} "
              f"worst {max(esc):5d}   cells {max(cells):5d}   "
              f"pane={row['name'] if row else '-'}{flag}")
    print(f"\n{over} of {len(windows)} window(s) average below the loop's cap "
          f"({a.budget:.1f} ms); nothing here fails - see the docstring for why")


if __name__ == "__main__":
    main()
