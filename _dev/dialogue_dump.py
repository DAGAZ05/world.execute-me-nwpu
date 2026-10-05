"""Ad-hoc: the left window's dialogue as a readable table, one block per lyric line.

    python _dev/dialogue_dump.py            both acts, to _dev/out/dialogue.txt
    python _dev/dialogue_dump.py --act 2
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import school_lines as L1        # noqa: E402
import school_lines_act2 as L2   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--act", type=int, default=0)
a = ap.parse_args()
rows = list(L1.ACT_ONE) + list(L2.ACT_TWO)
if a.act == 1:
    rows = list(L1.ACT_ONE)
elif a.act == 2:
    rows = list(L2.ACT_TWO)

out = []
last = None
for r in rows:
    t, lyric, role, text = r[0], r[1], r[2], r[3]
    if lyric != last:
        out.append(f"\n[{t:7.2f}] {lyric}")
        last = lyric
    out.append(f"    {role:5} | {text}")
dest = Path(__file__).resolve().parent / "out" / "dialogue.txt"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text("\n".join(out) + "\n", encoding="utf8")
print(f"{len(rows)} rows, {len([x for x in out if x.startswith(chr(10))])} lyric blocks -> {dest}")
