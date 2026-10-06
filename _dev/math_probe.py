"""Do the maths panes say true things about themselves?

Three claims, each of which was false at some point in this project's life, and each of which a smoke
test cannot see because the pane renders perfectly while saying something untrue:

1. **The six instruments print the countdown's own words.** `draw_gauge` took `lang`/`digit` from the day
   it was written and printed them at `bx1 - 10`; the only call site never passed either, so
   `Ein, dos / Trios, ne / Fem, liu` - six words the song actually sings, in six languages - were
   designed, wired, and never once on screen. Then the first fix drew them on `by0`, which is where three
   of the six instruments put their own legend, and two of the six were still invisible.
2. **`g_attention`'s softmax figure is a softmax.** It used to print `focus = min(0.92, u * 1.1)` - the
   pane's own *progress* - under the word "softmax", while the heat map was four hard-coded shadings.
3. **`pane_converge` really reduces seven diagrams into one class.** It used to move seven full-size
   rectangles to the middle, drop them all with a `break`, and then draw the class in the same place -
   so there was no frame in which a source and the target coexisted. The first attempt at a fix still had
   none (labels left at 0.45, class arrived at 0.72).

Run: `python _dev/math_probe.py`. Exit 1 if any claim fails.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T                     # noqa: E402
import school_courses as CO              # noqa: E402
import school_panels as SP               # noqa: E402
import school_scenes as SC               # noqa: E402

W, H = 95, 30


def _rows(s, cols, rows):
    out = []
    for y in range(rows):
        row = "".join(s.buf[y][x][0] if s.buf[y][x][0] else " " for x in range(cols))
        if row.strip():
            out.append(row)
    return out


def _text(s, cols, rows):
    return "\n".join(_rows(s, cols, rows))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default=f"{W}x{H}", help="the pane, in cells (default 95x30)")
    a = ap.parse_args()
    c, _, r = a.size.partition("x")
    w, h = int(c), int(r)

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))

    x0, y0, x1, y1 = 2, 2, 2 + w - 1, 2 + h - 1
    bad: list[str] = []

    # ---- 1. the six countdown words ------------------------------------------------------------
    print(f"the six instruments, at {w}x{h}:")
    for i, (_at, _end, lyric) in enumerate(SP.GAUGE_SLOTS):
        for side in (0, 1):
            j = i * 2 + side
            pane = CO.GAUGE_PANES[j]
            word, _lang = CO.GAUGE_WORDS[pane]
            s = T.Screen(w + 6, h + 4)
            CO.draw_gauge(pane, s, x0, y0, x1, y1, 0.0, 0.3, 0.4, 1.0, run=j + 1)
            on = word in _text(s, w + 6, h + 4)
            print(f"  {'OK ' if on else 'NO '} {pane:26s} {word:6s} ({lyric})")
            if not on:
                bad.append(f"{pane} does not print its countdown word {word!r}")

    # ---- 2. the softmax ------------------------------------------------------------------------
    print(f"\nthe attention instrument's softmax figure:")
    diag = []
    for u in (0.05, 0.5, 1.0):
        s = T.Screen(w + 6, h + 4)
        CO.draw_gauge("pane_gauge_attention", s, x0, y0, x1, y1, 0.0, 0.2, 0.4, u, run=3)
        txt = _text(s, w + 6, h + 4)
        m = re.search(r"diag\s+([0-9.]+)", txt)
        if not m:
            bad.append(f"pane_gauge_attention prints no softmax figure at u={u}")
            print(f"  NO  u={u:.2f}  no figure")
            continue
        v = float(m.group(1))
        diag.append(v)
        print(f"  OK  u={u:.2f}  diagonal weight {v:.2f}")
    if len(diag) == 3:
        if not (0.0 < diag[0] <= 1.0 and 0.0 < diag[-1] <= 1.0):
            bad.append(f"the softmax diagonal weight is not a probability: {diag}")
        if not diag[-1] > diag[0]:
            bad.append(f"the diagonal does not sharpen as the head trains: {diag}")

    # ---- 3. the reduction ----------------------------------------------------------------------
    print(f"\nall the execution -> only execution, at {w}x{h}:")
    both = 0
    for k in range(41):
        u = 0.55 + 0.45 * k / 40.0
        s = T.Screen(w + 6, h + 4)
        SC.pane_converge(s, x0, y0, x1, y1, 1.0, u, 1.0, u)
        txt = _text(s, w + 6, h + 4)
        if "class" in txt and any(t in txt for t in ("DFD", "ER", "\u9700\u6c42")):
            both += 1
    print(f"  frames with a source diagram and the class both on screen: {both}")
    if both == 0:
        bad.append("pane_converge has no frame in which a source and the class coexist "
                   "(that is a fade-out plus a fade-in, not a reduction)")

    print()
    if bad:
        print("FAIL:")
        for b in bad:
            print(f"  - {b}")
        raise SystemExit(1)
    print("PASS: the maths panes say true things")


if __name__ == "__main__":
    main()
