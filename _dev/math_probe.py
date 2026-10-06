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

    # ---- 4. the labels that claim something the drawing has to contain -------------------------
    #
    # Both of these were *false for the whole life of the pane* and no probe could see it: the drawing
    # rendered perfectly, inside its rect, moving, and the words next to it described something that was
    # not there. Batch 40 found them by taking a census of the rendered glyphs rather than by looking.
    print(f"\nthe labels that promise a specific mark:")

    # `g_pareto` prints `cum 80% ──` - a legend for the cumulative curve. Censused for amber.
    s = T.Screen(w + 6, h + 4)
    CO.draw_gauge("pane_gauge_pareto", s, x0, y0, x1, y1, 0.0, 0.4, 0.44, 1.0, run=2)
    amber = [(x, y) for y in range(h + 4) for x in range(w + 6)
             if (lambda c: c[0] > 200 and c[1] > 150 and c[2] < 90)(s.buf[y][x][1])]
    rows_amber = sorted({y for _x, y in amber})
    print(f"  pane_gauge_pareto  'cum 80% ──': {len(amber)} amber cells over rows {rows_amber}")
    if len(rows_amber) < 2:
        bad.append("pane_gauge_pareto's legend promises a cumulative line and no curve is drawn "
                   "(fewer than two rows carry it)")

    # `g_fem` is captioned `mesh`; a mesh needs both directions.
    s = T.Screen(w + 6, h + 4)
    CO.draw_gauge("pane_gauge_fem", s, x0, y0, x1, y1, 0.0, 0.4, 0.44, 1.0, run=4)
    cen: dict[str, int] = {}
    for y in range(h + 4):
        for x in range(w + 6):
            ch = s.buf[y][x][0]
            if ch not in ("", " "):
                cen[ch] = cen.get(ch, 0) + 1
    vbar = cen.get("\u2502", 0)
    hbar = cen.get("\u2500", 0)
    print(f"  pane_gauge_fem     'mesh': {vbar} vertical, {hbar} horizontal")
    if vbar == 0:
        bad.append("pane_gauge_fem is captioned 'mesh' and draws no vertical edge "
                   "(rows of dashes are not a mesh)")

    # `pane_exec_ds` is captioned as a red-black tree with a search path lit. The lit path has to
    # actually arrive at the key it is searching for.
    #
    # It did not: the path was `(0, 1, 4)` - keys 10, 5, 7 - and a search for 8 in that tree walks
    # `(0, 1, 4, 10)`, i.e. 10 -> 5 -> 7 -> **8**. The drawing said "search 8" and the light stopped one
    # node short, which is the difference between a search and a walk that gave up.
    s = T.Screen(w + 6, h + 4)
    CO.draw_course("pane_exec_ds", s, x0, y0, x1, y1, 0.0, 1.0, 1.0, 1.0, run=3, total=16)
    # The tree's nodes are `marker + digit`, and every node is preceded by a marker glyph, so a node is
    # identifiable by its *left neighbour* and nothing else on the pane looks like that. (The first
    # version looked for any cell reading `8` and took the last one in scan order, which found an `8` in
    # a text row and failed a pane that was correct. A probe that cannot tell a node from a label is not
    # a probe.)
    #
    # **Lit is a colour, not a glyph.** The `◎` ring belongs to the node the roaming search light is
    # standing on, which walks the tree on the song's clock and is almost never the target; the nodes on
    # the lit path keep `●` and turn AMBER. So the test is "preceded by a marker, and amber" - the first
    # version demanded the ring and would have failed even the corrected drawing.
    MARKERS = "\u25ce\u25cf"
    found = None
    for yy in range(h + 4):
        for xx in range(1, w + 6):
            if s.buf[yy][xx][0] == "8" and s.buf[yy][xx - 1][0] in MARKERS:
                found = (xx, yy, s.buf[yy][xx - 1][0], s.buf[yy][xx][1])
    if found is None:
        print("  pane_exec_ds       'search 8': no tree node reading 8 (marker + digit) is on screen")
        bad.append("pane_exec_ds draws a search for 8 and the key 8 is not on the tree")
    else:
        xx, yy, mark, col = found
        is_lit = col[0] > 200 and 150 < col[1] < 235 and col[2] < 90
        print(f"  pane_exec_ds       'search 8': node 8 at ({xx},{yy}) marker U+{ord(mark):04X} "
              f"fg={col} lit={is_lit}")
        if not is_lit:
            bad.append("pane_exec_ds lights a search path that does not reach the key being searched "
                       "for (the search for 8 stops before 8)")

    # ---- 5. panes that contradict a number printed on the same pane ---------------------------
    #
    # Each of these was measured by rendering the pane and reading two of its own lines against each
    # other. They belong here rather than in `pane_probe` for the same reason as section 4: every one of
    # them renders perfectly.
    print(f"\nthe panes that print a number and then disagree with it:")

    # `c_os` prints `%Cpu(s): 6.2 us, 1.1 sy` and a per-process `%CPU` column. The column has to add up
    # to the summary, or the table is claiming more CPU than the machine says it is using.
    s = T.Screen(w + 6, h + 4)
    CO.draw_course("pane_exec_os", s, x0, y0, x1, y1, 0.4, 0.4, 0.8, 1.0, run=8, total=16)
    lines = _rows(s, w + 6, h + 4)
    hdr = next((r for r in lines if "%Cpu(s)" in r), "")
    m = re.search(r"([\d.]+)\s*us,\s*([\d.]+)\s*sy", hdr)
    procs = [float(g.group(1)) for r in lines
             for g in [re.match(r"\s*\d{4,5} root\s+20\s+0\s+([\d.]+)\s+0\.3", r)] if g]
    if not m:
        print("  pane_exec_os       no %Cpu(s) line found")
        bad.append("pane_exec_os prints no %Cpu(s) summary line")
    elif not procs:
        print("  pane_exec_os       no process rows found")
        bad.append("pane_exec_os prints a %Cpu(s) line and no process table")
    else:
        declared = float(m.group(1)) + float(m.group(2))
        total = sum(procs)
        print(f"  pane_exec_os       header {declared:.1f}% busy, {len(procs)} rows sum {total:.1f}%")
        if abs(total - declared) > 0.6:
            bad.append(f"pane_exec_os: the process column sums to {total:.1f}% while its own "
                       f"%Cpu(s) line claims {declared:.1f}%")

    # `_os_states` labels the transitions of the process state machine. A time slice expiring returns a
    # process to **ready**, not to blocked; I/O is what sends it to blocked.
    joined = " ".join(lines)
    if "时间片到" in joined and "就绪" not in joined:
        print("  pane_exec_os       'time slice expires' is labelled with no destination")
        bad.append("pane_exec_os labels an edge 时间片到 without saying it returns to ready")
    else:
        print("  pane_exec_os       transition labels: ok")

    # `g_burndown`'s legend names the glyphs the drawing uses - the ideal line is drawn with `·`.
    s = T.Screen(w + 6, h + 4)
    CO.draw_gauge("pane_gauge_burndown", s, x0, y0, x1, y1, 0.0, 0.4, 0.44, 1.0, run=1)
    btxt = _rows(s, w + 6, h + 4)
    legend = next((r for r in btxt if "ideal" in r), "")
    print(f"  pane_gauge_burndown legend: {legend.strip()[:46]!r}")
    if legend and "\u00b7" not in legend:
        bad.append("pane_gauge_burndown's legend does not show the glyph its ideal line is drawn with")

    # `g_assembly` - the header counts the parts and the boxes must not collide. Both were wrong: it said
    # `BOM 41 parts` while drawing six, and at 95 columns the last two boxes shared a column.
    for uu in (0.0, 1.0):
        s = T.Screen(w + 6, h + 4)
        CO.draw_gauge("pane_gauge_assembly", s, x0, y0, x1, y1, 0.0, 0.4, 0.44, uu, run=5)
        at = _rows(s, w + 6, h + 4)
        head = next((r for r in at if "BOM" in r), "")
        mm = re.search(r"BOM (\d+) parts", head)
        claimed = int(mm.group(1)) if mm else -1
        labels = sorted((int(g.group(1)), g.start()) for r in at for g in re.finditer(r"P(\d+)", r))
        print(f"  pane_gauge_assembly u={uu:.1f}: claims {claimed}, draws "
              f"{[f'P{n}@{c}' for n, c in labels]}")
        if claimed != len(labels):
            bad.append(f"pane_gauge_assembly's header claims {claimed} parts and {len(labels)} "
                       f"are drawn (u={uu})")
        for (n1, c1), (n2, c2) in zip(labels, labels[1:]):
            if c2 - c1 < 6:
                bad.append(f"pane_gauge_assembly: P{n1} and P{n2} collide at u={uu}")
                break

    print()
    if bad:
        print("FAIL:")
        for b in bad:
            print(f"  - {b}")
        raise SystemExit(1)
    print("PASS: the maths panes say true things")


if __name__ == "__main__":
    main()
