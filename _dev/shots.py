"""Ad-hoc: the film's own shot table with lyrics, in a time range. Not a check.

    python _dev/shots.py 28 42
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T      # noqa: E402

lo = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
hi = float(sys.argv[2]) if len(sys.argv) > 2 else 1e9
eng = T.Engine()
for e in eng.table:
    if lo <= e["start"] <= hi:
        print(f"{e['start']:7.2f} {e['end']:7.2f} {e['end'] - e['start']:6.2f}s  "
              f"{e['name']:22} {str(e.get('lyric'))!r}")
