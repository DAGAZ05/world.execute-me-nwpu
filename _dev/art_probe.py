"""Develop the 航小天 art style: try the crops, the ramps and the palettes, and write PNGs.

    python _dev/art_probe.py            all of it, into _dev/out/
    python _dev/art_probe.py --sheet    one contact sheet instead of separate files

Nothing in here is used by the player. It exists so the art decisions are made by *looking* -
which is the only way the original film's own glyph work was settled (see her_glyphs.py's
docstring for the two wrong turns it had to look at to reject).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# `player/_tools`, not `player`: `mascot_glyphs.py` lives in `_tools` beside the other variant
# modules, and the old path meant this only ran when the cwd happened to have it on `sys.path` - which
# is how a stale set of PNGs survived a change to the avatar crop without anybody noticing.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "player" / "_tools"))
import mascot_glyphs as MG  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
CELL_W, CELL_H = 8, 16                     # one terminal cell, drawn at 8x16 px so a screenshot reads
BG = (4, 7, 15)
PAD = 8


def report_source() -> None:
    im = MG.raw()
    print(f"source: {MG.SRC.name}  PIL says format={im.format!r} mode={im.mode} size={im.size}")
    a = im.convert("RGBA").getchannel("A")
    print(f"  alpha: min={min(a.getdata())} max={max(a.getdata())}  -> "
          f"{'has transparency' if min(a.getdata()) < 250 else 'NO transparent pixels (flat background)'}")
    print(f"  ink box: {MG.ink_box()}")


def draw_cells(cells, w: int, h: int, cell_w: int = CELL_W, cell_h: int = CELL_H) -> Image.Image:
    """A grid of `(char, fg, bg)` or None into a PIL image, one glyph per cell."""
    from PIL import ImageFont
    font = MG.font(cell_h)
    im = Image.new("RGB", (w * cell_w, h * cell_h), BG)
    d = ImageDraw.Draw(im)
    for r, row in enumerate(cells):
        for c, cell in enumerate(row):
            if cell is None:
                continue
            ch, fg, bg = cell
            x, y = c * cell_w, r * cell_h
            if bg is not None:
                d.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], fill=tuple(bg))
            if ch and ch != " ":
                d.text((x, y), ch, font=font, fill=tuple(fg))
    return im


def draw_halfblock(grid, w: int, h: int, cell_w: int = CELL_W, cell_h: int = CELL_H) -> Image.Image:
    """A `(top, bottom)` level grid through the mascot ramp, as `▀` with fg=top, bg=bottom.

    The colour is the drawing's own average colour over the cell (see `mascot_glyphs.halfblock`),
    passed through `tint_color` so one HSV value drives both the glyph and the two backgrounds.
    """
    from PIL import ImageFont
    font = MG.font(cell_h)
    block, colour = grid
    im = Image.new("RGB", (w * cell_w, h * cell_h), BG)
    d = ImageDraw.Draw(im)
    for r, (brow, crow) in enumerate(zip(block, colour)):
        for c, (top, bot) in enumerate(brow):
            x, y = c * cell_w, r * cell_h
            if top is None and bot is None:
                continue
            ink = crow[c] or MG.WHITE
            fg = MG.tint_color(top, ink) if top is not None else BG
            bg = MG.tint_color(bot, ink) if bot is not None else BG
            d.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], fill=tuple(bg))
            d.text((x, y), "\u2580", font=font, fill=tuple(fg))
    return im


def label(im: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 18], fill=(0, 0, 0))
    d.text((4, 3), text, fill=(200, 214, 234))
    return im


def halfblock_image(blk) -> Image.Image:
    """`avatar_rgb`'s `(top, bottom)` RGB grid, drawn as `▀` cells - no tinting: the colours are
    already the final ones, which is the difference between this and `draw_halfblock`."""
    from PIL import ImageFont
    font = MG.font(CELL_H)
    w = max(len(row) for row in blk)
    im = Image.new("RGB", (w * CELL_W, len(blk) * CELL_H), BG)
    d = ImageDraw.Draw(im)
    for r, row in enumerate(blk):
        for c, (top, bot) in enumerate(row):
            x, y = c * CELL_W, r * CELL_H
            d.rectangle([x, y + CELL_H // 2, x + CELL_W - 1, y + CELL_H - 1], fill=tuple(bot))
            d.text((x, y + CELL_H // 2), "\u2584", font=font, fill=tuple(bot))
            d.text((x, y), "\u2580", font=font, fill=tuple(top))
    return im


def sheet(images: list[tuple[str, Image.Image]], cols: int = 3) -> Image.Image:
    cw = max(i.width for _, i in images) + PAD
    ch = max(i.height for _, i in images) + PAD + 20
    rows = (len(images) + cols - 1) // cols
    out = Image.new("RGB", (cols * cw, rows * ch), (0, 0, 0))
    for k, (name, im) in enumerate(images):
        r, c = divmod(k, cols)
        out.paste(label(im, name), (c * cw + PAD // 2, r * ch + PAD // 2))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", action="store_true", help="one contact sheet instead of separate files")
    ap.add_argument("--cols", type=int, default=60, help="terminal columns of the portrait pane")
    ap.add_argument("--rows", type=int, default=26, help="terminal rows of the portrait pane")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    report_source()

    shots: list[tuple[str, Image.Image]] = []

    # 1. every crop in every mode, so the mode is chosen by looking rather than by preference
    for crop in MG.CROPS:
        cells, cw, ch, ox, oy = MG.glyph_cells("normal", crop, a.cols, a.rows)
        shots.append((f"1 glyph {crop} {cw}x{ch}", draw_cells(cells, a.cols, a.rows)))
    for crop in MG.CROPS:
        cells, cw, ch, ox, oy = MG.ramp_cells("normal", crop, a.cols, a.rows)
        shots.append((f"2 ramp {crop} {cw}x{ch}", draw_cells(cells, a.cols, a.rows)))
    for crop in MG.CROPS:
        grid, w, h = MG.halfblock("normal", crop, a.cols, a.rows)
        shots.append((f"3 half {crop} {w}x{h}", draw_halfblock(grid, w, h)))

    # 2. the expressions in both surviving modes, on the bust crop the 60x26 pane picks
    for expr in MG.EXPRESSIONS:
        grid, w, h = MG.halfblock(expr, "bust", a.cols, a.rows // 2)
        shots.append((f"4 half {expr} bust", draw_halfblock(grid, w, h)))
    for expr in MG.EXPRESSIONS:
        cells, cw, ch, ox, oy = MG.ramp_cells(expr, "bust", a.cols, a.rows // 2)
        shots.append((f"5 ramp {expr} bust", draw_cells(cells, a.cols, a.rows // 2)))

    # 3. the panes the player really asks for: the chat avatar and the small window. The avatar goes
    #    through `avatar_rgb`, which is what `tui_live.draw_dsh` calls - showing `halfblock` here
    #    instead was how a one-row-taller block went unnoticed (see `avatar_probe.py`).
    for cols, rows in ((16, 8), (24, 12), (32, 16)):
        blk = MG.avatar_rgb("normal", cols, rows)
        shots.append((f"6 avatar {cols}x{rows} face", halfblock_image(blk)))
        grid, w, h = MG.halfblock("normal", "bust", cols, rows)
        shots.append((f"6 avatar {cols}x{rows} bust", draw_halfblock(grid, w, h)))
        cells, cw, ch, ox, oy = MG.ramp_cells("normal", "face", cols, rows)
        shots.append((f"6 avatar {cols}x{rows} ramp", draw_cells(cells, cw, ch)))

    if a.sheet:
        p = OUT / "sheet.png"
        sheet(shots, 3).save(p)
        print(f"\nwrote {p}")
        return
    for name, im in shots:
        safe = name.replace(" / ", "_").replace(" ", "_")
        im.save(OUT / f"{safe}.png")
    print(f"\nwrote {len(shots)} PNGs into {OUT}")


if __name__ == "__main__":
    main()
