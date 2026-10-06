"""Search the *decoded* dialogue and the overlay table for phrases - the sources store Chinese as \\uXXXX.

    python _dev/find_text.py 也许 三次 作风 图书馆
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import school_chat as CH        # noqa: E402
import school_fx as FX          # noqa: E402
import school_panels as SP      # noqa: E402

for needle in sys.argv[1:]:
    print(f"\n### {needle}")
    for t, lyric, lines in CH._DIALOGUE:
        for role, text in lines:
            if needle in text:
                print(f"  dialogue t={t:7.2f} [{role}] {text}")
    for s, e, fn, kw in list(FX.EVENTS) + list(FX.WINDOW_EVENTS):
        for k, v in kw.items():
            if isinstance(v, str) and needle in v:
                print(f"  fx {s:7.2f}-{e:7.2f} {fn.__name__} {k}={v!r}")
    for r in SP.shot_rows():
        if needle in r["lyric"] or any(needle in str(o) for o in r["ops"]):
            print(f"  row {r['at']:7.2f} {r['name']} lyric={r['lyric']!r} ops={r['ops']}")
