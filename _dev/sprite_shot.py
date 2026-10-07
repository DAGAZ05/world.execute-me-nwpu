"""Batch 54 scratch: draw one sprite alone, the way `fly` draws it, and save it as a PNG (temp).

The question is "is the manta's picture clean" - and that is a question about *cells*, not about the
frame it lands in. This puts the sprite on an empty screen with the same `paste` options the event uses
(`lift`/`span`/`ambient`) and writes it out, so the shape and any speckle around it can be looked at.
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")
sys.stdout.reconfigure(encoding="utf8", errors="replace")

import tui_live as T
import school_fx as FX

name = sys.argv[1] if len(sys.argv) > 1 else "manta"
cols, rows = 100, 40
flip = sys.argv[2] if len(sys.argv) > 2 else ""
amb = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0

s = T.Screen(cols, rows + 2)
cells = FX.sprite(name, cols - 8, rows, flip=flip, contrast=1.0)
if cells is None:
    raise SystemExit("no sprite")
_, w, h = cells
FX.paste(s, cells, 4, 1, lift=FX.AIRCRAFT_LIFT, span=FX.AIRCRAFT_SPAN, ambient=amb)
out = ROOT / "_dev" / "out" / f"sprite_{name}{'_' + flip if flip else ''}_{amb}.png"
from tui_shot import Painter     # noqa: E402
Painter().paint(s, out, "")
print(out, f"{w}x{h} cells")
