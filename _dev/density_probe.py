"""How busy each pane is, which is the one thing "构图不要显得杂乱" can be measured by.

Clutter is a judgement, but two of the things that cause it are counts:

  * **ink ratio** - what share of the cells have anything in them. Past a third, a terminal drawing stops
    reading as a drawing and starts reading as texture; the panels that do this in this film are the ones
    with a motif stacked on a drawing stacked on a terms list.
  * **band count** - how many separate horizontal runs of ink there are, and how tall the empty gaps
    between them are. A pane with six two-row bands separated by three-row gaps is a stack of things
    rather than a picture, which is what the user means by 杂乱.

It also reports how much of the pane is *text rows* (rows whose ink is mostly CJK), because the other half
of the note in the brief is that the drawings should carry the pane and the words should not.

    python _dev/density_probe.py              every scheduled pane, worst first
    python _dev/density_probe.py --size 95x33 the right column's real width at 197 columns
    python _dev/density_probe.py --top 12
"""
from __future__ import annotations

import argparse
import os
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402

# The thresholds the verdicts use. They are a starting point, not a law: the point is to have the numbers
# printed so a pane can be argued about with them rather than from memory.
#
# The first cut used "more than four bands" as the clutter test and flagged 36 of 51 panes, which is a
# useless check - a drawing with a header, a body and one machinery row is three bands before it has done
# anything. What actually reads as 杂乱 is: a pane that is mostly *words*, a pane stacked into many thin
# strips, and a pane with no structure left because the ink is everywhere.
WALL = 0.55           # ink share above which a pane has stopped being a drawing
STACKED = 7           # this many separate bands is a stack of things, not a picture
TEXTY = 0.30          # this share of inked rows being text rows is a page, not a plate
PATCHY = 9            # an empty run taller than this is a hole

# Panes whose verdict has been looked at and accepted, with the reason. A check that cannot go green is
# not a check - and one that quietly ignores its own findings is worse - so these are named, counted, and
# printed in the run rather than filtered out. `WALL` is never excused: nobody has a reason for a pane
# that is all ink.
KNOWN = {
    "pane_exec_net": "sequence diagram: one row per message is the notation",
    "pane_ai_diffusion": "the terms footer is spaced two rows apart on purpose",
    "pane_ai_cnn": "four layer strips, then the terms footer",
}

# `TEXTY` has exactly one argued exception (batch 50): the four-year timetable. The metric asks "is this
# pane a drawing or a page of words", and `pane_curriculum` **is** a page of course names - it is the one
# pane in the film whose subject is a list. The user asked for it by name twice (batch 34: "我们学院并非
# 只有我列的那些专业课", batch 50: "各年不止那几门课程，不要在对话中有相关断言"), so every row of it is a
# course title, and a timetable that passed `TEXTY` would be a timetable with the courses taken out. Its
# ink is 0.10 of its area and its rows are one band, so it is not clutter; it is a different *kind* of
# drawing from every other pane, and the exception is recorded here rather than by widening the threshold.
TEXT_OK = {
    "pane_curriculum": "the film's one timetable: the words are the drawing",
}


def _cjk(ch: str) -> bool:
    return len(ch) == 1 and unicodedata.east_asian_width(ch) in "WF"


def stats(s: T.Screen, x0: int, y0: int, x1: int, y1: int) -> dict:
    rows_ink = []
    total = 0
    for y in range(y0, y1 + 1):
        cells = [s.buf[y][x][0] for x in range(x0, x1 + 1)]
        ink = [c for c in cells if c not in ("", " ")]
        total += len(ink)
        rows_ink.append(ink)
    area = max(1, (x1 - x0 + 1) * (y1 - y0 + 1))
    occupied = [len(r) >= 3 for r in rows_ink]
    bands, run, gap, maxgap = 0, 0, 0, 0
    for occ in occupied:
        if occ:
            bands += 1 if run == 0 else 0
            run += 1
            maxgap = max(maxgap, gap)
            gap = 0
        else:
            gap += 1
            run = 0
    maxgap = max(maxgap, gap)
    text_rows = sum(1 for r in rows_ink if r and sum(1 for c in r if _cjk(c)) / len(r) > 0.5)
    return dict(ink=total / area, bands=bands, maxgap=maxgap,
                text=text_rows / max(1, len(rows_ink)), rows=sum(occupied))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default="95x33", help="the pane body, in cells")
    ap.add_argument("--top", type=int, default=14, help="how many to print")
    a = ap.parse_args()
    c, _, r = a.size.partition("x")
    w, h = int(c), int(r)

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))

    seen, out = set(), []
    for row in SP.shot_rows():
        name = row.get("name")
        key = (name, tuple(sorted((row.get("args") or {}).items())))
        if not name or key in seen:
            continue
        seen.add(key)
        s = T.Screen(w + 4, h + 4)
        try:
            SP.draw_scene_pane(name, s, 1, 1, w, h, row["at"] + 0.4, 0.3, 0.8, 0.6,
                               args=row.get("args"))
        except Exception as exc:
            print(f"{name:24} RAISED {type(exc).__name__}: {exc}")
            continue
        st = stats(s, 2, 2, w - 1, h - 2)
        flags = []
        if st["ink"] > WALL:
            flags.append("WALL")
        if st["bands"] > STACKED:
            flags.append("STACKED")
        if st["text"] > TEXTY and name not in TEXT_OK:
            flags.append("TEXTY")
        if st["maxgap"] > PATCHY:
            flags.append("PATCHY")
        out.append((st, name, flags))

    out.sort(key=lambda r: (-r[0]["ink"],))
    print(f"{'pane':26}{'ink':>7}{'bands':>7}{'gap':>6}{'text':>7}   verdict")
    for st, name, flags in out[: a.top]:
        note = ""
        if flags:
            excused = [f for f in flags if f in ("STACKED", "PATCHY")] and name in KNOWN
            note = "  (" + KNOWN[name] + ")" if excused else ""
        elif st["text"] > TEXTY and name in TEXT_OK:
            note = "  (" + TEXT_OK[name] + ")"
        print(f"{name:26}{st['ink']:7.2f}{st['bands']:7d}{st['maxgap']:6d}{st['text']:7.2f}   "
              f"{' '.join(flags)}{note}")
    hard = []
    for st, name, flags in out:
        # Only `WALL` and `TEXTY` fail the run, and `TEXTY` only where the pane is not in `TEXT_OK`: a pane
        # that is all ink is not a drawing, and a pane that is all words is not one either - unless the
        # pane's subject *is* the words, which is the timetable and nothing else. `STACKED` and `PATCHY` are
        # reported and counted but do not fail, because a sequence diagram *is* a stack of rows, a watermark
        # *is* mostly empty, and a check that cannot tell those from a mistake would either be red forever
        # or have to ignore itself. The first cut failed on all four and listed fourteen panes "to fix",
        # eleven of which were the terms footer being two rows apart.
        if "WALL" in flags or "TEXTY" in flags:
            hard.append(name)
    to_look = [name for _st, name, f in out if ("STACKED" in f or "PATCHY" in f) and name not in KNOWN]
    print(f"\n{len(out)} panes at {w}x{h}: {len(hard)} failing, {len(to_look)} worth a look, "
          f"{sum(1 for _s, n, f in out if f and n in KNOWN)} reviewed and accepted")
    print(f"  thresholds: wall>{WALL} (fails), texty>{TEXTY} (fails), "
          f"stacked>{STACKED}, patchy>{PATCHY} (reported)")
    if hard:
        print("  FAIL: " + ", ".join(hard))
    if to_look:
        print("  look: " + ", ".join(to_look))
    raise SystemExit(1 if hard else 0)


if __name__ == "__main__":
    main()
