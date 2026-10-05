"""Ad-hoc: the schedule rows in a time range, with args and lyric. Not a check.

    python _dev/rows.py 70 90
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import school_panels as SP      # noqa: E402

lo = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
hi = float(sys.argv[2]) if len(sys.argv) > 2 else 1e9
for r in SP.shot_rows():
    if lo <= r["at"] <= hi:
        print(f"{r['at']:7.2f} {r['end']:7.2f} {r['end'] - r['at']:6.2f}s  "
              f"{str(r.get('name')):24} {r.get('args') or ''}  {r.get('lyric')!r}")
