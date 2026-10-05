"""What does the terminal actually receive? Decode the player's own ANSI stream back into a grid.

    python _dev/live_screen_probe.py 197x52 63.0        (COLSxROWS, the time to dump)
    python _dev/live_screen_probe.py 120x34 62.0 --window 58.6 70.1

Every other probe in `_dev` reads `Screen.buf`, which is what the *player* believes it drew. The user
sees what `render_diff` writes, and those are not the same thing: a cell can be right in the buffer and
never reach the terminal (unchanged according to `prev`), or reach it with the wrong colour pair. The
user's report - "我确定看不到打篮球面板 ... 似乎不在最上层" - is a statement about the screen, so this
probe runs the real `main()` with the real `render_diff`, and interprets the escape stream the way a
terminal would: cursor moves, `38;2` foreground, `48;2` background, and the characters themselves.

It writes `_dev/out/live_screen.txt` (the decoded screen at the requested time, with a background map)
and prints what is in the left box: how many cells carry the panel's paper as their background, how many
still carry the film's ground, and which glyphs are on top.
"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402

CSI = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")


class Term:
    """Just enough of a terminal: absolute cursor moves, SGR colours, printable characters."""

    def __init__(self, cols: int, rows: int) -> None:
        self.cols, self.rows = cols, rows
        self.clear()
        self.x = self.y = 0

    def clear(self) -> None:
        self.buf = [[(" ", (200, 200, 200), (0, 0, 0)) for _ in range(self.cols)]
                    for _ in range(self.rows)]

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
                    parts = args.split(";")
                    self.y = max(0, int(parts[0] or 1) - 1)
                    self.x = max(0, int(parts[1] or 1) - 1) if len(parts) > 1 else 0
                elif kind == "J":
                    self.clear()
                elif kind == "m":
                    p = args.split(";")
                    if p[0] == "38" and len(p) >= 5:
                        self.fg = tuple(int(v) for v in p[2:5])
                    elif p[0] == "48" and len(p) >= 5:
                        self.bg = tuple(int(v) for v in p[2:5])
                i = m.end()
                continue
            if ch == "\n":
                self.y += 1
                self.x = 0
            elif ch == "\r":
                self.x = 0
            elif 0 <= self.y < self.rows and 0 <= self.x < self.cols:
                self.buf[self.y][self.x] = (ch, getattr(self, "fg", (200, 200, 200)),
                                            getattr(self, "bg", (0, 0, 0)))
                self.x += 1
            i += 1


def main() -> None:
    size = sys.argv[1] if len(sys.argv) > 1 else "197x52"
    want = float(sys.argv[2]) if len(sys.argv) > 2 else 63.0
    c, _, r = size.partition("x")
    cols, rows = int(c), int(r)
    T.VAR[0] = "school"
    T.term_size = lambda default=(120, 34): (cols, rows)      # type: ignore[assignment]

    term = Term(cols, rows)
    real = T.Screen.render_diff
    dumped = [False]

    def render_diff(self, out) -> int:
        n = real(self, out)
        text = out.getvalue() if isinstance(out, io.StringIO) else ""
        if text:
            term.feed(text)
            out.seek(0)
            out.truncate(0)
        if not dumped[0] and abs(self._probe_t - want) < 0.05:
            dumped[0] = True
            dump(term, cols, rows, self._probe_t)
        return n

    T.Screen.render_diff = render_diff            # type: ignore[assignment]

    real_draw = T.draw

    def draw_probe(s, d, eng, t, playing, fps, audio=None):
        s._probe_t = t
        if dumped[0] and t > want + 0.4:
            raise Stop                       # the loop holds the last frame until `q`; stop ourselves
        return real_draw(s, d, eng, t, playing, fps, audio)

    T.draw = draw_probe                           # type: ignore[assignment]

    class Stop(Exception):
        pass

    out, errf = io.StringIO(), io.StringIO()
    saved = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, errf
    sys.argv = ["tui_live.py", "--variant", "school", "--no-audio", "--start",
                str(max(0.0, want - 1.0)), "--size", size]
    try:
        T.main()
    except (SystemExit, Stop):
        pass
    except BaseException as exc:                   # noqa: BLE001
        print(f"the loop ended early: {type(exc).__name__}: {exc}", file=sys.stderr)
    finally:
        sys.stdout, sys.stderr = saved
    print(errf.getvalue().strip() or "(no stderr)")
    if not dumped[0]:
        print("the requested time was never drawn - see the log above")


def dump(term: Term, cols: int, rows: int, t: float) -> None:
    box = tuple(T.LEFT_BOX)
    paper = (172, 179, 197)                 # `_panel(PAPER)` at 197x52's PANEL_DIM... see the report
    ground = (4, 7, 15)
    lines = [f"decoded terminal screen at t={t:.2f}  {cols}x{rows}  LEFT_BOX={box}", ""]
    lines.append("      " + "".join(str(x // 10 % 10) for x in range(cols)))
    for y in range(rows):
        lines.append(f"{y:4}  " + "".join(cell[0] for cell in term.buf[y]))
    bx0, by0, bx1, by1 = box
    bgs: dict[tuple, int] = {}
    glyphs = 0
    for y in range(max(0, by0), min(rows, by1 + 1)):
        for x in range(max(0, bx0), min(cols, bx1 + 1)):
            ch, _fg, bg = term.buf[y][x]
            bgs[bg] = bgs.get(bg, 0) + 1
            if ch not in (" ", ""):
                glyphs += 1
    lines += ["", f"backgrounds inside the box ({sum(bgs.values())} cells):",
              "  " + "  ".join(f"{bg} x{n}" for bg, n in sorted(bgs.items(), key=lambda kv: -kv[1])[:6]),
              f"  glyph cells: {glyphs}",
              f"  the panel's paper would be {paper}; the film's ground is {ground}"]
    dest = Path(__file__).resolve().parent / "out" / "live_screen.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf8")
    print(f"decoded screen written to {dest}")


if __name__ == "__main__":
    main()
