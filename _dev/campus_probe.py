"""Develop the campus-identity art: which images survive characterisation, and which must be redrawn.

The rule this probe exists to settle is in `02b_图像对位与可视化表达.md` §0: a terminal has no
pictures, so every reference image takes one of three routes - half-block (a photograph or a solid),
Sobel-to-glyphs (a line drawing), or "do not use the image at all, draw the *meaning* instead". The
guess before running this was that MEMORY belongs to the third route, because its visual essence is
*one word printed twice, one solid and one ghost*, and characterising the photograph would give a
yellow smear. This prints both routes side by side so the guess can be checked rather than asserted.

    python _dev/campus_probe.py                all of them, into _dev/out/campus/
    python _dev/campus_probe.py --sheet        one contact sheet
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
sys.path.insert(0, str(ROOT / "_dev"))

import mascot_glyphs as MG          # noqa: E402
from art_probe import draw_cells, draw_halfblock, sheet   # noqa: E402

ASSETS = ROOT / "assets" / "\u6821\u56ed\u6807\u8bc6\u7269"
OUT = Path(__file__).resolve().parent / "out" / "campus"


def _load(name: str) -> Image.Image | None:
    p = ASSETS / name
    if not p.exists():
        return None
    im = Image.open(p).convert("RGBA")
    # these are photographs and screenshots: white paper, not a cut-out. Key the white out from the
    # border only, so the *inside* white (the sword, the vessel's paper) is kept - the same trap
    # `mascot_glyphs` documents, and the reason this is a flood fill and not a threshold.
    from collections import deque
    w, h = im.size
    px = im.load()
    seen = bytearray(w * h)
    q: deque = deque()

    def white(c) -> bool:
        return c[0] > 226 and c[1] > 226 and c[2] > 226

    for x in range(w):
        for y in (0, h - 1):
            if not seen[y * w + x] and white(px[x, y][:3]):
                seen[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not seen[y * w + x] and white(px[x, y][:3]):
                seen[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        px[x, y] = px[x, y][:3] + (0,)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and white(px[nx, ny][:3]):
                seen[ny * w + nx] = 1
                q.append((nx, ny))
    return im


def _grid(im: Image.Image, cols: int, rows: int, cell_w: int = 8, cell_h: int = 16):
    """Fit `im` into cols x rows and return `(block, colour)`, the shape `draw_halfblock` wants."""
    a = im.getchannel("A")
    b = a.point(lambda v: 255 if v >= 128 else 0).getbbox()
    if b:
        im = im.crop(b)
    aspect = cols / (rows * 2.0)
    w, h = im.size
    if w / h > aspect:
        nh = max(1, int(round(w / aspect)))
        y = (h - nh) // 2
        im = im.crop((0, y, w, y + nh))
    else:
        nw = max(1, int(round(h * aspect)))
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    small = im.resize((cols, rows * 2), Image.LANCZOS)
    L, A, P = small.convert("L").load(), small.getchannel("A").load(), small.convert("RGB").load()
    block, colour = [], []
    for r in range(rows):
        brow, crow = [], []
        for c in range(cols):
            def lv(y):
                if A[c, y] <= 100:
                    return None
                return int(round((MG.LEVEL_FLOOR + (1 - MG.LEVEL_FLOOR) * L[c, y] / 255) * (MG.LEVELS - 1)))
            t, bo = lv(2 * r), lv(2 * r + 1)
            brow.append((t, bo))
            crow.append(P[c, 2 * r] if t is not None else (P[c, 2 * r + 1] if bo is not None else None))
        block.append(tuple(brow))
        colour.append(tuple(crow))
    return (tuple(block), tuple(colour)), cols, rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--wide", type=int, default=118, help="columns of the right-hand pane")
    ap.add_argument("--rows", type=int, default=20, help="rows of the right-hand pane")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    shots: list[tuple[str, Image.Image]] = []

    files = [p.name for p in sorted(ASSETS.glob("*")) if p.suffix.lower() in (".jpg", ".png", ".webp")]
    for name in files:
        im = _load(name)
        if im is None:
            continue
        grid, w, h = _grid(im, a.wide, a.rows)
        shots.append((f"half  {name[:22]}  {w}x{h}", draw_halfblock(grid, w, h)))

    # and the glyph route on the one asset that is a line drawing, where Sobel strokes are the point
    for name in files:
        if "\u4f55\u5c0a" not in name and "memory" not in name:
            continue
        im = _load(name)
        if im is None:
            continue
        a_ = a.wide / (a.rows * MG.CELL_ASPECT)
        small = im.resize((a.wide, a.rows), Image.LANCZOS)
        from PIL import ImageFilter
        lum = small.convert("L")
        gx = lum.filter(ImageFilter.Kernel((3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], scale=4, offset=128))
        gy = lum.filter(ImageFilter.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=4, offset=128))
        L, A, X, Y, P = lum.load(), small.getchannel("A").load(), gx.load(), gy.load(), small.convert("RGB").load()
        import math
        cells = []
        for r in range(a.rows):
            row = []
            for c in range(a.wide):
                if A[c, r] < 110:
                    row.append(None)
                    continue
                ex, ey = (X[c, r] - 128) / 32, (Y[c, r] - 128) / 32
                if math.hypot(ex, ey) > 0.9:
                    ang = (math.degrees(math.atan2(ey, ex)) + 180) % 180
                    ch = "|" if ang < 22.5 or ang >= 157.5 else "\\" if ang < 67.5 else "-" if ang < 112.5 else "/"
                    row.append((ch, (230, 230, 230), None))
                else:
                    v = L[c, r] / 255
                    row.append((MG.GLYPH_RAMP[min(9, 1 + int(v * 9))], tuple(int(k * (0.5 + 0.6 * v)) for k in P[c, r]), None))
            cells.append(tuple(row))
        shots.append((f"glyph {name[:20]}", draw_cells(tuple(cells), a.wide, a.rows)))

    if a.sheet:
        sheet(shots, 1).save(OUT / "sheet.png")
        print(OUT / "sheet.png")
        return
    for name, im in shots:
        p = OUT / (name.replace(" ", "_").replace("/", "-") + ".png")
        im.save(p)
        print(p)


if __name__ == "__main__":
    main()
