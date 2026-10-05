"""Ad-hoc: the avatar before and after the crop fix, side by side, at the size the header uses.

Writes `_dev/out/avatar/before_after.png`: old crop + old double-rows call, then the fixed pair.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
import mascot_glyphs as MG      # noqa: E402

BG = (4, 7, 15)
CELL_W, CELL_H = 10, 20
COLS, ROWS = 24, 12


def render(blk) -> Image.Image:
    w = max(len(r) for r in blk)
    im = Image.new("RGB", (w * CELL_W + 2, ROWS * CELL_H + 2), (40, 40, 48))
    d = ImageDraw.Draw(im)
    for r, row in enumerate(blk):
        for c, (top, bot) in enumerate(row):
            x, y = 1 + c * CELL_W, 1 + r * CELL_H
            d.rectangle([x, y + CELL_H // 2, x + CELL_W - 1, y + CELL_H - 1], fill=tuple(bot))
            d.rectangle([x, y, x + CELL_W - 1, y + CELL_H // 2 - 1], fill=tuple(top))
    return im


def as_rgb(grid):
    """`halfblock`'s level grid -> the `avatar_rgb` RGB shape."""
    out = []
    for brow, crow in zip(*grid):
        row = []
        for c, (top, bot) in enumerate(brow):
            ink = crow[c] or MG.WHITE
            t = MG.tint_color(top, ink) if top is not None else BG
            b = MG.tint_color(bot, ink) if bot is not None else BG
            row.append((t, b))
        row_out = tuple(row)
        out.append(row_out)
    return tuple(out)


def shot(crop, rows_arg, label):
    grid, _w, _h = MG.halfblock("normal", crop, COLS, rows_arg)
    blk = as_rgb(grid)
    im = render(blk)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 16], fill=(0, 0, 0))
    d.text((4, 2), f"{label}  {len(blk)}x{len(blk[0])}", fill=(200, 214, 234))
    return im


OLD = (0.20, 0.0, 0.80, 0.27)
MG.CROPS["face"] = OLD
MG.cropped.cache_clear()
before = shot("face", ROWS * 2, "before: forehead crop, rows*2")
MG.CROPS["face"] = (0.212, 0.0, 0.775, 0.385)
MG.cropped.cache_clear()
after = shot("face", ROWS, "after: head crop, rows")

out = Image.new("RGB", (before.width + after.width + 24, before.height + 8), (0, 0, 0))
out.paste(before, (8, 4))
out.paste(after, (before.width + 16, 4))
p = ROOT / "_dev" / "out" / "avatar" / "before_after.png"
p.parent.mkdir(parents=True, exist_ok=True)
out.save(p)
print(p)
