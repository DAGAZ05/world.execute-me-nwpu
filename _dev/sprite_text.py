"""Ad-hoc: one sprite of `school_fx` as text, to see what it will look like before it is on screen.

    python _dev/sprite_text.py y20 130 41
    python _dev/sprite_text.py manta 90 0        (0 rows = the sprite's own aspect)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import school_fx as FX      # noqa: E402

name = sys.argv[1]
cols = int(sys.argv[2])
rows = int(sys.argv[3]) if len(sys.argv) > 3 else 0
if rows <= 0:
    rows = max(6, int(round(cols / (FX.CELL_ASPECT * max(0.2, FX._aspect(name))))))
cells = FX.sprite(name, cols, rows)
if not cells:
    print("no such sprite")
    raise SystemExit(1)
grid, w, h = cells
ramp = FX.SHADE
out = [f"{name}  {w}x{h}"]
for r in range(h):
    line = []
    for c in range(w):
        cell = grid[r][c]
        line.append(" " if cell is None else ramp[max(0, min(len(ramp) - 1, cell[1]))])
    out.append("".join(line))
dest = Path(__file__).resolve().parent / "out" / "sprite.txt"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text("\n".join(out) + "\n", encoding="utf8")
print(f"{w}x{h} written to {dest}")
