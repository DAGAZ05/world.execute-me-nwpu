"""Does the terminal end up showing what the buffer says? Decode the player's own ANSI and diff it.

    python _dev/ansi_probe.py                 the whole song at 197x52, every 0.5 s
    python _dev/ansi_probe.py --step 0.2 --size 120x34
    python _dev/ansi_probe.py --at 155.0      one frame, printed around the first mismatch

The user's report is "相当多的字符显示混乱". Every other probe in `_dev` reads `Screen.buf`, which is what
the player *intends* to draw; the terminal shows what `render_diff` writes. Those differ whenever the
two disagree about **width**: a CJK or box-drawing character is two columns wide, `put` writes a
placeholder cell after it, and `render_diff` skips placeholder cells when it writes its runs - so a cell
that loses (or keeps) its placeholder wrongly shifts every character after it on that row. That is
exactly "garbled characters", and it is invisible to a probe that reads the buffer.

The mismatch is invisible in another way too: `render_diff` only emits *changed* cells, so a wrong cell
stays wrong on the real screen for as long as nothing touches it again, while a fresh `Screen` (which is
what `school_shot` renders from) never shows it. This probe therefore keeps one terminal across the run,
decoding every frame's escape stream in order - the same thing the user's console does.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402

CSI = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")


def wide(ch: str) -> bool:
    return bool(ch) and unicodedata.east_asian_width(ch) in ("W", "F")


class Term:
    """A terminal that keeps its screen between frames: cursor moves, SGR, characters, wide chars."""

    def __init__(self, cols: int, rows: int) -> None:
        self.cols, self.rows = cols, rows
        self.fg = (200, 200, 200)
        self.bg = (0, 0, 0)
        self.x = self.y = 0
        self.clear()

    def clear(self) -> None:
        self.buf = [[(" ", (200, 200, 200), (0, 0, 0)) for _ in range(self.cols)]
                    for _ in range(self.rows)]

    def put(self, ch: str) -> None:
        if not (0 <= self.y < self.rows):
            self.x += 2 if wide(ch) else 1
            return
        if 0 <= self.x < self.cols:
            self.buf[self.y][self.x] = (ch, self.fg, self.bg)
            if wide(ch):
                # the terminal paints a wide glyph across two columns; the second one is not a cell of
                # its own, which is the placeholder the player also keeps in its buffer
                if self.x + 1 < self.cols:
                    self.buf[self.y][self.x + 1] = ("", self.fg, self.bg)
        self.x += 2 if wide(ch) else 1

    def feed(self, text: str) -> None:
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "\x1b":
                m = CSI.match(text, i)
                if not m:
                    i += 1
                    continue
                args, kind = m.group(1), m.group(2)
                if kind == "H":
                    p = args.split(";")
                    self.y = max(0, int(p[0] or 1) - 1)
                    self.x = max(0, int(p[1] or 1) - 1) if len(p) > 1 else 0
                elif kind == "J":
                    self.clear()
                elif kind == "m":
                    q = args.split(";")
                    if q[0] == "38" and len(q) >= 5:
                        self.fg = tuple(int(v) for v in q[2:5])
                    elif q[0] == "48" and len(q) >= 5:
                        self.bg = tuple(int(v) for v in q[2:5])
                i = m.end()
                continue
            if ch == "\n":
                self.y, self.x = self.y + 1, 0
            elif ch == "\r":
                self.x = 0
            else:
                self.put(ch)
            i += 1


def orphans(s: T.Screen, cols: int, rows: int, limit: int = 4) -> list[str]:
    """Placeholder cells whose character is not there: half a wide glyph, waiting to be repainted.

    These are the *buffer's* own inconsistencies - the terminal can only show what the buffer says, and
    a placeholder with no wide character to its left is a cell the renderer will skip for ever (so the
    right half of a glyph that has gone stays on screen).
    """
    out: list[str] = []
    for y in range(rows):
        row, wrow = s.buf[y], s.wide[y]
        for x in range(cols):
            if not wrow[x] or row[x][0] != "":
                continue
            left_ok = x > 0 and wide(row[x - 1][0])
            if not left_ok:
                out.append(f"y={y:2d} x={x:3d} orphan placeholder")
                if len(out) >= limit:
                    return out
    for y in range(rows):
        row, wrow = s.buf[y], s.wide[y]
        for x in range(cols):
            if not wide(row[x][0]):
                continue
            if x + 1 >= cols:
                continue                # a wide char in the last column has nowhere to put its second
                                        # half: `put` clips it, and every terminal resolves that itself
            if not wrow[x + 1] or row[x + 1][0] != "":
                nxt = row[x + 1][0]
                out.append(f"y={y:2d} x={x:3d} wide char without a placeholder "
                           f"(next={nxt!r} wide={wrow[x + 1]})")
                if len(out) >= limit:
                    return out
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--at", type=float, default=None, help="only this time, printing the differences")
    ap.add_argument("--max", type=int, default=12, help="how many example cells to print")
    ap.add_argument("--watch", default="", help="y,x - print that cell's buffer/terminal state every frame")
    ap.add_argument("--until", type=float, default=212.0, help="stop at this time (for a quick pass)")
    a = ap.parse_args()
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
    import school_fx as FX
    FX.warm(cols, rows)

    term = Term(cols, rows)
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    bad = 0
    checked = 0
    examples: list[str] = []
    t = 0.0
    frame = 0
    step = a.step
    while t <= min(212.0, a.until):
        T.draw(s, d, eng, t, True, 24.0)
        sink.seek(0)
        sink.truncate(0)
        s.render_diff(sink)
        stream = sink.getvalue()
        term.feed(stream)
        frame += 1
        if a.at is None:
            first = orphans(s, cols, rows)
            if first and not examples:
                cut = T._CUT[0]
                examples.append(f"t={t:6.2f}  orphan placeholder in the buffer: {first[0]}  "
                                f"(shot {T.SP.school_entry(t, eng.entry_at(t))['name']}, "
                                f"cut={'none' if cut is None else cut['kind']})")
        if a.watch:
            wy, wx = (int(v) for v in a.watch.split(","))
            b = s.buf[wy][wx]
            t_ = term.buf[wy][wx]
            if b != t_:
                prev = s.prev[wy][wx] if s.prev else None
                print(f"t={t:6.2f}  buffer {b!r} wide={s.wide[wy][wx]}  left={s.buf[wy][wx - 1][0]!r}  "
                      f"prev {prev!r}  terminal {t_!r}  row_written={f'[{wy + 1};' in stream}")
        if a.at is None or abs(t - a.at) < step * 0.5:
            n, ex = compare(term, s, cols, rows)
            checked += 1
            if n:
                bad += 1
                if len(examples) < a.max:
                    examples.append(f"t={t:6.2f}  {n:4d} cell(s)  {ex[0]}")
                if a.at is not None:
                    print(f"t={t:.2f}: {n} mismatching cell(s)")
                    for line in ex[: a.max]:
                        print("   ", line)
                    for line in orphans(s, cols, rows, 6):
                        print("    invariant:", line)
        t += step
    print(f"{checked} frame(s) compared at {a.size}; {bad} with at least one mismatch")
    for line in examples:
        print("  ", line)
    raise SystemExit(1 if bad else 0)


def compare(term: Term, s: T.Screen, cols: int, rows: int):
    """Cells where the terminal and the buffer disagree about the character that should be there."""
    bad: list[str] = []
    n = 0
    for y in range(rows):
        row, trow, wrow = s.buf[y], term.buf[y], s.wide[y]
        for x in range(cols):
            want_ch, want_fg, want_bg = row[x]
            got = trow[x]
            # a placeholder cell is written by the terminal as the *second column of its neighbour*, and
            # the player marks it `wide`; a placeholder the player has forgotten about is the bug
            if want_ch == "" and not wrow[x]:
                continue
            if got[0] != want_ch:
                n += 1
                if len(bad) < 6:
                    lo, hi = max(0, x - 3), min(cols, x + 3)
                    bad.append(f"y={y:2d} x={x:3d}  cols {lo}..{hi - 1}  "
                               f"buffer {classify(row, wrow, lo, hi)}  "
                               f"terminal {classify(trow, None, lo, hi)}")
    return n, bad


def classify(row, wrow, lo: int, hi: int) -> str:
    """A readable stand-in for the characters: C = a wide glyph, p = its placeholder, . = space."""
    out = []
    for i in range(lo, hi):
        ch = row[i][0]
        if ch == "":
            out.append("p" if (wrow is None or wrow[i]) else "?")
        elif not ch.strip():
            out.append(".")
        elif wide(ch):
            out.append("C")
        else:
            out.append("n")
    return "".join(out)


if __name__ == "__main__":
    main()
