"""The lyric timeline between two times - the lines the schedule rows are hung on.

    python _dev/lyrics_at.py 105 137

`_dev/rows.py` answers "what pane is up"; this answers "what is being sung", which is what a *row* has
to be anchored to. Both read the same `Data()`, so they cannot disagree about the timeline.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402

lo = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
hi = float(sys.argv[2]) if len(sys.argv) > 2 else 999.0
d = T.Data()
lines = [ln for ln in d.lines if lo <= ln["start"] <= hi]
for i, ln in enumerate(lines):
    nxt = lines[i + 1]["start"] if i + 1 < len(lines) else hi
    print(f"{ln['start']:8.2f}  {nxt - ln['start']:5.2f}s  {ln['text']}")
