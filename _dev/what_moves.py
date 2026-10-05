"""Ad-hoc: which cells of a pane change between two moments of its slot, and what is in them.

`clock_probe.py` answers "does this pane move at all"; this answers "*what* moves" - the difference
between a drawing whose own content is animated and one that only moves because the machinery row at
the bottom of every course pane is ticking. Run it while working on a pane, not as a check.

    python _dev/what_moves.py pane_exec_net 159.0 0.82
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402

pane = sys.argv[1]
at = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0
span = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
w, h = 113, 33

T.VAR[0] = "school"
T.SP = SP
SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))


def draw(f: float):
    s = T.Screen(w + 6, h + 4)
    SP.draw_scene_pane(pane, s, 2, 2, 2 + w - 1, 2 + h - 1, at + span * f, span * f, span, 1.0)
    return s


a, b = draw(0.15), draw(1.0)
rows = {}
for y in range(a.rows):
    for x in range(a.cols):
        ca, cb = a.buf[y][x], b.buf[y][x]
        if ca != cb:
            rows.setdefault(y, []).append((x, ca[0], cb[0]))
print(f"{pane}: {sum(len(v) for v in rows.values())} cell(s) differ in row(s) "
      f"{sorted(rows)} of 0..{a.rows - 1} (pane rows are 2..{h + 1})")
for y in sorted(rows):
    cells = rows[y]
    print(f"  row {y:3}: {len(cells):3}  " + "  ".join(f"x{x}:{ca!r}->{cb!r}" for x, ca, cb in cells[:8]))
