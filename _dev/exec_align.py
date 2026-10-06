"""Batch 38: measure the alignment between the Execution hits and the course panes.

The lyrics audit claims the twelve course drawings appear "0.37 s / 0.8 beat late" against the
`Execution` hits, and that fixing it is the base of the whole densest section. Before touching
`_exec_rows` (whose docstring argues at length for spreading the panes evenly), measure the actual
offsets: for every course row, the nearest hit and the signed distance.

    python _dev/_b38_exec.py
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import film_panels as FP          # noqa: E402
import tui_live as T              # noqa: E402
import school_panels as SP        # noqa: E402

# the hits, straight out of the song's own lyric file
lrc = (ROOT / "player" / "input" / "lyrics.lrc").read_text(encoding="utf-8-sig")
hits = []
for ln in lrc.splitlines():
    m = re.match(r"^\[(\d+):(\d+(?:\.\d+)?)\](.*)$", ln)
    if m and m.group(3).strip() == "Execution":
        hits.append(int(m.group(1)) * 60 + float(m.group(2)))
print("Execution hits in the lrc:")
print("  " + ", ".join(f"{h:.2f}" for h in hits))
print(f"  {len(hits)} of them; beat length {FP.BEAT:.4f}s")

rows = [r for r in SP.shot_rows() if r.get("name")]
course = [r for r in rows if str(r["name"]).startswith("pane_exec_")
          or r["name"] == "pane_motif_powerdown"]
course.sort(key=lambda r: r["at"])
print(f"\n{len(course)} course rows (EXEC_PANES is {len(SP.EXEC_PANES)} long):")
print(f"{'at':>8} {'span':>6}  {'nearest hit':>11} {'offset':>8} {'beats':>7}  pane")
worst = 0.0
for r in course:
    at = r["at"]
    near = min(hits, key=lambda h: abs(h - at))
    off = at - near
    worst = max(worst, abs(off))
    print(f"{at:8.2f} {r['end'] - at:6.2f}  {near:11.2f} {off:+8.2f} {off / FP.BEAT:+7.2f}  {r['name']}")
print(f"\nworst |offset| = {worst:.2f}s = {worst / FP.BEAT:.2f} beats")

print("\nhow the hits themselves are spaced (should be the song's own 2-beat grid):")
gaps = [b - a for a, b in zip(hits, hits[1:])]
print("  " + ", ".join(f"{g:.2f}" for g in gaps))
print(f"  mean {sum(gaps) / len(gaps):.3f}s = {sum(gaps) / len(gaps) / FP.BEAT:.3f} beats")

print("\nEXEC_AT (the schedule's own record of the hit times):")
print("  " + ", ".join(f"{h:.2f}" for h in SP.EXEC_AT))
print("  == the lrc hits?", [round(h, 2) for h in SP.EXEC_AT] == [round(h, 2) for h in hits
                                                                  if h < 200])
