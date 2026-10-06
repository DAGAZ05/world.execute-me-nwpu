"""What is actually in the drawing column at a given time, as text.

    python _dev/column_dump.py 5.16 36.77        writes _dev/out/audit/column_<t>.txt

`school_shot` renders a PNG for looking at; this writes the buffer's own characters for *reading* - the
right column rows only, so a pane and the motif band under it can be told apart without squinting at a
1 px-per-cell image.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "audit"
OUT.mkdir(parents=True, exist_ok=True)

cols, rows = 197, 52
T.VAR[0] = "school"
import school_panels as SP      # noqa: E402

T.SP = SP
SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
import school_gate as G         # noqa: E402

G.assume()
eng, d = T.Engine(), T.Data()
T.FX.update(on=False, reveal=False, mech=False, trail=False, vig=False, shake=False)
s = T.Screen(cols, rows)
sink = io.StringIO()
for t in (float(x) for x in sys.argv[1:]):
    T.draw(s, d, eng, t, True, 24.0)
    sink.seek(0)
    sink.truncate(0)
    s.render_diff(sink)
    ent = SP.school_entry(t, eng.entry_at(t))
    g = dict(T.GEOM)
    x0, x1 = int(g.get("pane_x0") or 0), int(g.get("pane_x1") or cols - 1)
    lines = [f"t={t}  pane={ent.get('pane')!r}  pane rect=x{x0}..{x1} y{g.get('pane_y0')}.."
             f"{g.get('pane_y1')}  ops y{g.get('ops_top')}..{g.get('ops_bottom')}  "
             f"pane_h={g.get('pane_h')}", ""]
    for y in range(rows):
        row = "".join(s.buf[y][x][0] for x in range(max(0, x0), min(cols, x1 + 1))).rstrip()
        if row.strip():
            lines.append(f"{y:3d} |{row}")
    (OUT / f"column_{t:.2f}.txt").write_text("\n".join(lines) + "\n", encoding="utf8")
    print(OUT / f"column_{t:.2f}.txt")
