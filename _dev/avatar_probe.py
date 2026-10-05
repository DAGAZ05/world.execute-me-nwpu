"""Ad-hoc: render the chat avatar exactly as the player draws it, at every size it asks for.

    python _dev/avatar_probe.py            the sizes the header really uses, into _dev/out/avatar/
    python _dev/avatar_probe.py --expr shy just one expression

`art_probe.py` shows every crop and mode, which is how the *style* was chosen; this shows only the
one thing the player puts on screen - `mascot_glyphs.avatar_rgb`, at the cell sizes `draw_dsh` picks -
so a change to the avatar crop can be looked at the way the user sees it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
import mascot_glyphs as MG      # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "avatar"
BG = (4, 7, 15)
CELL_W, CELL_H = 10, 20
# what `draw_dsh` asks for: (cols, rows) of cells. 24x12 is the 52-row window, 10x5 a 34-row one,
# 12x6 in between - and 16x8 is the AVATAR_COLS/ROWS pair the module documents.
SIZES = [(24, 12), (16, 8), (12, 6), (10, 5), (6, 3)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--expr", default="normal")
    ap.add_argument("--cols", default="", help="only this cell size, e.g. 24x12")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    from PIL import ImageFont
    font = MG.font(CELL_H)

    sizes = SIZES
    if a.cols:
        c, _, r = a.cols.partition("x")
        sizes = [(int(c), int(r))]

    for cols, rows in sizes:
        blk = MG.avatar_rgb(a.expr, cols, rows)
        w = max(len(row) for row in blk)
        im = Image.new("RGB", (w * CELL_W + 2, rows * CELL_H + 2), (40, 40, 48))
        d = ImageDraw.Draw(im)
        for r, row in enumerate(blk):
            for c, (top, bot) in enumerate(row):
                x, y = 1 + c * CELL_W, 1 + r * CELL_H
                d.rectangle([x, y + CELL_H // 2, x + CELL_W - 1, y + CELL_H - 1], fill=tuple(bot))
                d.rectangle([x, y, x + CELL_W - 1, y + CELL_H // 2 - 1], fill=tuple(top))
        p = OUT / f"{a.expr}_{cols}x{rows}.png"
        im.save(p)
        print(f"{p}  ({w} of {cols} cells used, {len(blk)} of {rows} rows)")


if __name__ == "__main__":
    main()
