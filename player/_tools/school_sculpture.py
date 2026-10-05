"""The four campus landmarks, on the lines `02b_图像对位与可视化表达.md` §3 pins them to.

Unlike everything else in the school variant these are not drawn from primitives - they *are* the
reference images, characterised. `_dev/campus_probe.py` settled which route each one takes, and the
answer was not uniform:

    memory      half-block for the single-layer shot, hand-drawn block letters for the layering
                (the ghost layers smear when the photograph is characterised)
    对话         half-block, and the best of the batch: two hands that have not touched yet
    为国铸剑     half-block; the raised sword reads as a horizontal bar and the body as mass
    何尊         glyph (Sobel strokes); it is a line drawing and half-block turns it to mud
    校徽         half-block

Two things every one of these panes has to do that `mascot_glyphs` did not:

  * **the images are photographs on white paper, not cut-outs.** There is no alpha to key out, and
    "near-white means background" is the trap this project has already hit once - the sword and the
    vessel are white inside. So the white is removed by a flood fill from the *border* only, which
    cannot reach the inside of a closed outline.
  * **they must not look pasted on.** A photograph dropped into a pane reads as a photograph in a
    terminal, which breaks the one illusion this player lives on. So each one is reduced to the
    palette of the pane it sits in and given the same treatment as everything else: a title row, a
    measured caption, and its own beat of animation.
"""
from __future__ import annotations

import html
import math
import re
from collections import deque
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "\u6821\u56ed\u6807\u8bc6\u7269"

CELL_ASPECT = 2.1
# the working resolution the source is reduced to before the paper is flooded out - see `source`
WORK = 420
LEVELS = 5
LEVEL_FLOOR = 0.18
SHADE = " \u2591\u2592\u2593\u2588"

# what each landmark is called on screen, and which file it is
FILES = {
    "dialogue": "\u5bf9\u8bdd_\u673a\u5668\u624b\u4e0e\u4eba\u7684\u624b.png",
    "sword": "\u4e3a\u56fd\u94f8\u5251\u96d5\u5851_\u4fef\u77b0.png",
    # the clean line drawing the user supplied with `何尊.html` - see `DIGITS` below for why it, and not
    # the earlier scan or the vector, is what the vessel is drawn from
    "he_zun": "\u4f55\u5c0a.png",
    "crest": "\u6821\u5fbd.webp",
    "memory": "memory_\u5355\u5c42.jpg",
}
# ...and the one that was supplied as a vector drawing. It is kept because the user made it, and it is no
# longer used: `何尊.png` is the same vessel with closed, filled outlines, and the digit route needs ink
# rather than strokes. Rasterised by `school_svg.render` if anything ever asks for it again.
SVG = {
    "he_zun_svg": "\u4f55\u5c0a.svg",
}
TITLES = {
    "dialogue": "\u5bf9\u8bdd \u00b7 \u673a\u5668\u624b\u4e0e\u4eba\u7684\u624b",
    "sword": "\u4e3a\u56fd\u94f8\u5251",
    "he_zun": "\u4f55\u5c0a",
    "crest": "\u897f\u5317\u5de5\u4e1a\u5927\u5b66",
    "memory": "MEMORY",
}
# the glyph route: a line drawing, where Sobel strokes are the drawing rather than a pre-processing.
# 何尊 is one whether it arrives as a scan or as the vector, so the route does not change with the file.
GLYPH = ("he_zun",)
# ...and the ones whose picture *is* an outline, where the strokes are all there is to see. 何尊's
# vector is one. 为国铸剑 was tried here too and is *not*: its sculpture is a solid, so the outline on
# its own is a wire cage, while the shaded silhouette reads at once - what it needed was a wider tonal
# range (`_stretch`) and a bigger share of the pane, not a different route.
LINE = ("he_zun",)
# how many samples per cell `stroke_cells` looks at. Six is enough for a 4.5-unit stroke on the SVG's
# 1600-unit canvas to be two or three pixels wide at cell resolution, and cheap: a 58x31 pane is 130k
# pixels, a few milliseconds, once.
_K = 6
# a pixel is "on a stroke" when its Sobel gradient is this many grey levels from flat
_EDGE = 26
# ...and a *cell* is on a stroke when the gradients inside it point the same way at least this well
_COHERENT = 0.55


@lru_cache(None)
def source(name: str) -> Image.Image | None:
    """The image with its paper removed, cached. `None` if the file is not there.

    It is downscaled to `WORK` on the long side *before* the paper is removed, and that is a fix rather
    than a tidy-up: `_key_out_paper` floods every background pixel in Python, and these files are scans.
    何尊 alone is a couple of thousand pixels across - 1.9 seconds of flood fill, the first time the pane
    that uses it comes up, which is a visible freeze in the middle of the song. At 640 the same flood is
    a tenth of the pixels and the cells it produces are identical, because no pane ever draws one of
    these at more than about 90 cells wide (180 pixels).

    A vector source skips both steps: `school_svg.render` draws to `WORK` directly and the result has a
    transparent background already, so `_key_out_paper` finds no paper to remove and only crops to the
    ink. It is the same size and the same shape as the scan route, which is what lets the two routes
    share everything downstream. Nothing uses it now (`SVG` is empty of live names) - it is kept because
    the user drew that file and because the reader cost two hundred lines to build.
    """
    if name in SVG:
        p = ASSETS / SVG[name]
        if not p.exists():
            return None
        import school_svg
        # drawn on paper, then keyed like every other scan: the flood takes the paper that the drawing's
        # own outline does not enclose, so the vessel ends up with the same kind of alpha mask a
        # photograph of it would have - which is what lets the routes below be shared.
        return _key_out_paper(school_svg.render(p, size=WORK))
    p = ASSETS / FILES[name]
    if not p.exists():
        return None
    im = Image.open(p).convert("RGBA")
    w, h = im.size
    if max(w, h) > WORK:
        f = WORK / float(max(w, h))
        im = im.resize((max(1, int(w * f)), max(1, int(h * f))), Image.LANCZOS)
    return _stretch(_key_out_paper(im))


def _stretch(im: Image.Image) -> Image.Image:
    """Widen the picture's tonal range when it has almost none.

    为国铸剑 is a *white sculpture on white paper*. Keying the paper out leaves everything between about
    180 and 250, so a five-level ramp can only say "white" or "slightly less white": the figure had no
    form at all, and the user's note was that they could not tell what it was. The range is measured over
    the opaque pixels only (2 %..98 %, so a few specks cannot define it) and stretched to the full 0..255.

    A picture that already uses the range is returned untouched, which is every other landmark here - this
    is not a "make it prettier" pass, it is a rescue for the one asset that arrives washed out.
    """
    alpha = im.getchannel("A")
    hist = im.convert("L").histogram(mask=alpha)
    total = sum(hist)
    if not total:
        return im
    lo = hi = None
    acc = 0
    for v, n in enumerate(hist):
        acc += n
        if acc >= total * 0.02:
            lo = v
            break
    acc = 0
    for v in range(255, -1, -1):
        acc += hist[v]
        if acc >= total * 0.02:
            hi = v
            break
    if lo is None or hi is None or hi - lo >= 110:
        return im
    lut = [max(0, min(255, int((v - lo) * 255 / max(1, hi - lo)))) for v in range(256)]
    r, g, b, a = im.split()
    return Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))


def _key_out_paper(im: Image.Image) -> Image.Image:
    """Make the paper transparent by flooding in from the border.

    A threshold would delete the inside of the sword blade and the inside of the vessel, both of
    which are white and both of which are the subject. A flood fill from the edge stops at the
    drawing's own outline, so only the paper that is *connected to the outside* goes.
    """
    w, h = im.size
    px = im.load()
    seen = bytearray(w * h)
    q: deque = deque()

    def paper(c) -> bool:
        return c[0] > 224 and c[1] > 224 and c[2] > 224

    for x in range(w):
        for y in (0, h - 1):
            if not seen[y * w + x] and paper(px[x, y][:3]):
                seen[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not seen[y * w + x] and paper(px[x, y][:3]):
                seen[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        px[x, y] = px[x, y][:3] + (0,)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and paper(px[nx, ny][:3]):
                seen[ny * w + nx] = 1
                q.append((nx, ny))
    a = im.getchannel("A").getbbox()
    return im.crop(a) if a else im


def _fit(im: Image.Image, cols: int, rows: int) -> Image.Image:
    """Centre-crop to the cell grid's aspect, then resample. Never stretched."""
    aspect = cols / max(1, rows * CELL_ASPECT)
    w, h = im.size
    if w / h > aspect:
        nw = max(1, int(round(h * aspect)))
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    else:
        nh = max(1, int(round(w / aspect)))
        y = int((h - nh) * 0.42)               # biased up: these are figures and vessels, not landscapes
        im = im.crop((0, y, w, y + nh))
    return im.resize((cols, rows * 2), Image.LANCZOS)


@lru_cache(None)
def halfblock(name: str, cols: int, rows: int):
    """`((block, colour), w, h)` for `draw` - the same shape `school_courses` works in."""
    im = source(name)
    if im is None or cols < 3 or rows < 2:
        return None
    small = _fit(im, cols, rows)
    L, A, P = small.convert("L").load(), small.getchannel("A").load(), small.convert("RGB").load()

    def lv(c, y):
        if A[c, y] <= 96:
            return None
        return int(round((LEVEL_FLOOR + (1 - LEVEL_FLOOR) * L[c, y] / 255) * (LEVELS - 1)))

    block, colour = [], []
    for r in range(rows):
        brow, crow = [], []
        for c in range(cols):
            t, b = lv(c, 2 * r), lv(c, 2 * r + 1)
            brow.append((t, b))
            crow.append(P[c, 2 * r] if t is not None else (P[c, 2 * r + 1] if b is not None else None))
        block.append(tuple(brow))
        colour.append(tuple(crow))
    return (tuple(block), tuple(colour)), cols, rows


@lru_cache(None)
def glyph_cells(name: str, cols: int, rows: int):
    """`(cells, w, h)` for a line drawing: Sobel strokes, as `artist_glyphs` does for 航小天."""
    import math
    im = source(name)
    if im is None or cols < 4 or rows < 3:
        return None
    small = _fit(im, cols, rows * 2).resize((cols, rows), Image.LANCZOS)
    lum = small.convert("L")
    gx = lum.filter(ImageFilter.Kernel((3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], scale=4, offset=128))
    gy = lum.filter(ImageFilter.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=4, offset=128))
    L, A, X, Y = lum.load(), small.getchannel("A").load(), gx.load(), gy.load()
    ramp = " .:-=+*#%@"
    cells = []
    for r in range(rows):
        row = []
        for c in range(cols):
            if A[c, r] < 110:
                row.append(None)
                continue
            ex, ey = (X[c, r] - 128) / 32, (Y[c, r] - 128) / 32
            if math.hypot(ex, ey) > 0.9:
                ang = (math.degrees(math.atan2(ey, ex)) + 180) % 180
                ch = "|" if ang < 22.5 or ang >= 157.5 else "\\" if ang < 67.5 else "-" if ang < 112.5 else "/"
                lv = 255
            else:
                v = L[c, r] / 255
                ch, lv = ramp[min(9, 1 + int(v * 9))], int(255 * (0.4 + 0.6 * v))
            row.append((ch, lv))
        cells.append(tuple(row))
    return tuple(cells), cols, rows


def has(name: str) -> bool:
    return source(name) is not None


# ---------------------------------------------------------------- a solid shape

# The third route, and the one 为国铸剑 ends up on. The sculpture is a white figure on white paper: its
# contour is a soft grey edge (too faint to trace) and its shading is a 70-level band (too narrow to
# ramp), so both of the other routes give a mass with no form in it. What the picture *does* have is a
# silhouette - a figure with a sword held over its head - and a silhouette is what a monument is
# recognised by from the ground. So: one character wherever the picture is opaque, with the sculpture's
# own luminance as the tone, and nothing anywhere else.
SILHOUETTE = ("sword",)


@lru_cache(None)
def silhouette_cells(name: str, cols: int, rows: int):
    """`(cells, w, h)` with one glyph per opaque cell and the picture's tone behind it."""
    im = source(name)
    if im is None or cols < 3 or rows < 2:
        return None
    small = _fit(im, cols, rows * 2)
    L, A = small.convert("L").load(), small.getchannel("A").load()
    cells = []
    for r in range(rows):
        row = []
        for c in range(cols):
            ys = [y for y in (2 * r, 2 * r + 1) if A[c, y] > 96]
            if not ys:
                row.append(None)
                continue
            tone = sum(L[c, y] for y in ys) / len(ys)
            # 0.45..1.0 of the pane's ink: the shape has to be *solid*, and its tone only says which
            # parts of the stone catch the light - a fuller range here just re-draws the striations
            row.append(("\u2588", int(115 + 140 * tone / 255.0)))
        cells.append(tuple(row))
    return tuple(cells), cols, rows


# ---------------------------------------------------------------- a drawing of lines

# the four glyphs a stroke can be, given in *cell* space: a cell is `CELL_ASPECT` times taller than it
# is wide, so the diagonal glyphs are much steeper in the picture than the 45 degrees their name
# suggests. `_stroke` compares directions in cell space for that reason.
_GLYPHS = (("-", (1.0, 0.0)), ("|", (0.0, 1.0)), ("/", (1.0, -1.0)), ("\\", (1.0, 1.0)))


# The fourth route: the picture as *binary digits*, one `0` or `1` per cell.
#
# `参考及想法/何尊.html` is the vessel drawn exactly that way - every cell a `0` or a `1`, in a grey taken
# from how much ink is in it - and the user's note was "何尊的演出效果还是不太好，试一试参考及想法中的
# 何尊.html". It is a better fit than any of the three routes above: this film is a terminal, so the
# picture is made of the machine's own two characters, and the vessel arrives as a *field* rather than as
# a wire. 何尊_线稿.png (the scan) and 何尊.svg (the vector) are both superseded by it; `何尊.png` - the
# clean line drawing the page itself was made from - is the source.
DIGITS = ("he_zun",)


# The fourth route, and the one 何尊 uses: the picture as *the page the user drew it as*.
#
# `参考及想法/何尊.html` is the vessel as a `<pre>` of coloured `<b>` cells - one binary digit per cell, its
# grey taken from the ink in that cell - and it is 100 cells wide by **52 lines tall**, which is this
# player's frame height to the line. That is not a coincidence: it was made as a picture for a terminal.
# The user's note was "何尊的演出效果还是不太好，试一试参考及想法中的 何尊.html", so the art is used as
# supplied, parsed at load, and simply scaled when a caller wants a different size.
#
# The two routes it replaces are both still here - `digit_cells` derives the same look from `何尊.png` at
# any size, and `stroke_cells` traces the outline - but the page is what was asked for, and at frame size
# it needs no scaling at all.
HTML_ART = {"he_zun": "\u4f55\u5c0a_\u5b57\u7b26\u753b.html"}
_HTML_CELL = re.compile(r'<b style="color:(#[0-9A-Fa-f]{6})">(.*?)</b>', re.S)


@lru_cache(None)
def html_art(name: str):
    """The page as `[[(digit, grey)]]`, one entry per character. Cached; 154 KB of markup, parsed once."""
    p = ASSETS / HTML_ART[name]
    if not p.exists():
        return None
    rows = []
    for line in p.read_text(encoding="utf8").splitlines():
        line = line.strip()
        if not line or line.startswith("<pre"):
            continue
        row = []
        for col, chunk in _HTML_CELL.findall(line):
            grey = int(col[1:3], 16) + int(col[3:5], 16) + int(col[5:7], 16)
            grey //= 3
            for ch in html.unescape(chunk):
                row.append((ch, grey))
        if row:
            rows.append(row)
    return rows or None


@lru_cache(None)
def html_cells(name: str, cols: int, rows: int, field: bool = False):
    """`(cells, w, h)`: the page's own cells, nearest-sampled into a `cols` x `rows` box.

    Two changes to the page, both measured:

      * **the vessel is drawn solid**, one `█` per cell, not as its `0`/`1`. The page's digits are its
        medium and they do not survive the trip: a browser rasterises them as dense blobs, this draws them
        as strokes, so a digit covers about a seventh of its cell and the *colour* - which is what carries
        the picture, the paper at #D2 and the vessel at #40 - lands in a seventh of the area. Measured by
        looking: the digit version is a wall with a ghost in it at every size tried (64x31, 95x30,
        100x48), and the same grid drawn solid is unmistakably a 尊 - mouth, flanges, taotie, base.
      * **the paper is a dim field of the page's digits** (`field=True`), which is where the page's own
        medium belongs: the vessel out of a field of binary rather than a picture pasted on black. It is
        off for a pane, where a wall of digits would bury the column, and on for the full-frame hit.

    The brightness is the page's own grey, inverted - the page's dark cells are this film's ink - so the
    vessel keeps the tonality the page gave it.
    """
    art = html_art(name)
    if art is None or cols < 4 or rows < 3:
        return None
    sh, sw = len(art), max(len(r) for r in art)
    cells = []
    for r in range(rows):
        y = min(sh - 1, r * sh // max(1, rows))
        row = []
        for c in range(cols):
            x = min(sw - 1, c * sw // max(1, cols))
            src = art[y][x] if x < len(art[y]) else None
            if src is None:
                row.append(None)
                continue
            ink = 1.0 - src[1] / 255.0
            if ink >= 0.30:
                row.append(("\u2588", int(70 + 185 * min(1.0, ink))))
            elif field:
                row.append((src[0], 58))
            else:
                row.append(None)
        cells.append(tuple(row))
    return tuple(cells), cols, rows


@lru_cache(None)
def digit_cells(name: str, cols: int, rows: int, phase: float = 0.0, field: bool = False):
    """`(cells, w, h)`: one binary digit per cell, its brightness from that cell's ink.

    `phase` flips a scattered tenth of the digits, for the pane's own clock: a still field of digits is a
    photograph of data, and one that settles is data being read.

    `field` draws the *paper* as well, very dim, and that is the page's own look: `何尊.html` is a full
    field of digits - light ones for the paper, dark ones for the vessel - so the vessel reads as a shape
    in a texture rather than as free-floating marks. It is off for the pane, where a wall of digits would
    bury everything else in the column, and on for the full-frame hit, where the field *is* the effect.
    """
    im = source(name)
    if im is None or cols < 4 or rows < 3:
        return None
    from PIL import ImageFilter
    # At pane size the drawing's strokes are thinner than a cell, so the mask is widened by a couple of
    # pixels to keep the lines joined; at full-frame size the samples are already dense enough (the page
    # itself is 100 cells wide) and dilating only closes the gaps between the ornament's lines, which
    # flattens the vessel into a block: measured, 22 % of the plate inked with none and 54 % with a
    # 3-pixel one at 64x31.
    cell_px = max(1.0, im.width / float(cols))
    k = 1 if cell_px >= 5.0 else 3
    alpha = im.getchannel("A")
    if k > 1:
        alpha = alpha.filter(ImageFilter.MaxFilter(k))
    lum = im.convert("L")
    small_a = _fit(alpha, cols, rows * 2).load()
    small_l = _fit(lum, cols, rows * 2).load()
    tick = int(phase * 3.0)
    # a soft presence threshold: the resample spreads a hairline over two samples, so `>96` (the mask
    # test the other routes use) drops most of the drawing at pane size
    floor = 40 if k > 1 else 96
    cells = []
    for r in range(rows):
        row = []
        for c in range(cols):
            # ink, not darkness: the cut-outs have a transparent ground whose RGB is black, so "1 - L"
            # alone would make the background the inkiest thing in the picture. Both the scan and the
            # flat-paper version give the same answer through this.
            ink = 0.0
            on = False
            for y in (2 * r, 2 * r + 1):
                if small_a[c, y] > floor:
                    on = True
                    ink = max(ink, 1.0 - small_l[c, y] / 255.0)
            h = (c * 7 + r * 13 + c * r * 3) & 0xFFFF
            digit = "1" if h % 5 < 2 else "0"
            if not on:
                if not field:
                    row.append(None)
                    continue
                if h % 4:                       # a sparse paper: every cell would be a wall of digits
                    row.append(None)
                    continue
                row.append((digit, 26))
                continue
            if h % 11 == 0 and (h // 11 + tick) % 3 == 0:
                digit = "1" if digit == "0" else "0"          # the scattered cells that settle
            row.append((digit, int(105 + 150 * min(1.0, ink * 1.6))))
        cells.append(tuple(row))
    return tuple(cells), cols, rows


# ...and the supplied lettering, which is what the `为国铸剑` pane draws now.
#
# The user's note: "微缩的为国铸剑雕塑效果还是不太好，用NWPU字符画代替". They are right, and the reason is
# measurable: at pane size the sculpture is twenty rows of white stone on white paper, and a reader gets
# nothing from it. The lettering is the school's own name, it is a logo rather than a photograph, and it
# carries at any size. The supplied art is used as the *stencil* - the letterforms are the user's - and
# the cells are filled solid, because the art's own `| / \ _` strokes at double size read as a fence.
BANNER = {"NWPU": "NWPU_\u5b57\u7b26\u753b.txt"}
BANNER_FOR = {"sword": "NWPU"}


@lru_cache(None)
def banner_cells(name: str, cols: int, rows: int):
    """`(cells, w, h)` for the supplied ASCII lettering, scaled up to fill the box."""
    p = ASSETS / BANNER[name]
    if not p.exists():
        return None
    lines = [ln.rstrip() for ln in p.read_text(encoding="utf8").splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    if not lines:
        return None
    w = max(len(ln) for ln in lines)
    h = len(lines)
    scale = max(1, min(max(1, cols) // w, max(1, rows - 1) // h))
    cw, ch = w * scale, h * scale
    ox, oy = (cols - cw) // 2, (rows - ch) // 2
    cells = [[None] * cols for _ in range(rows)]
    for r in range(h):
        for c in range(len(lines[r])):
            if lines[r][c] == " ":
                continue
            for dy in range(scale):
                for dx in range(scale):
                    y, x = oy + r * scale + dy, ox + c * scale + dx
                    if 0 <= y < rows and 0 <= x < cols:
                        cells[y][x] = ("\u2588", 235)
    return tuple(tuple(r) for r in cells), cols, rows


@lru_cache(None)
def stroke_cells(name: str, cols: int, rows: int):
    """`(cells, w, h)` for a drawing whose subject is its *outline*: one glyph per cell that a stroke
    passes through, and nothing anywhere else.

    The existing `glyph_cells` cannot do this, and the reason is worth writing down because it is the
    whole of why 何尊 looked like a smudge. It resizes the picture to the cell grid (`cols` x `rows`
    pixels) and *then* looks for edges, so at 58x31 cells a 4.5-unit stroke on the SVG's 1600-unit
    canvas is a third of a pixel wide: it averages into the background, the Sobel sees a gentle grey
    gradient instead of an edge, and what survives is the ramp fallback - a scattering of `·` and `-`
    that is not the vessel. It works for 航小天 because that is a *filled* illustration, where the
    shape survives the downscale.

    So this measures the picture at `_K` samples per cell, and reports each cell as the direction of the
    stroke through it. The angle is converted to cell space before it is named, because `/` in a
    terminal is not 45 degrees: it is one cell across and one cell down, which is `CELL_ASPECT` times
    steeper than the picture's own diagonal.

    **The gradient it follows is the alpha channel's, not the luminance's**, and that is the whole trick.
    Two earlier versions used luminance and both failed, in opposite directions:

      * on a transparent ground (23-on-0) almost nothing passed the threshold - forty marks, the version
        the user was reacting to when they said the character art of the vessel was not good enough;
      * on paper (23-on-255) *everything* passed: 58 % of the plate, at every threshold from 26 to 120,
        because a dark line's two sides have opposite gradients that cancel when they are summed, so the
        direction per cell became noise. This drawing has ornament smaller than a cell, so a threshold
        cannot separate "a line runs through here" from "there is detail here" either.

    The alpha has neither problem: the key leaves one solid silhouette, so its boundary is a single
    clean edge with a one-sided gradient - the vessel's outline, its flanges, its mouth and its base, in
    the right directions. What is deliberately given up is the taotie *inside* the silhouette: at 6
    samples per cell it is smaller than the characters that would have to carry it, and drawing it is
    what produced the mush. A recognisable vessel beats a faithful texture.
    """
    im = source(name)
    if im is None or cols < 4 or rows < 3:
        return None
    import math
    from PIL import ImageFilter
    # the crop `_fit` would take, but at `_K` times the resolution
    aspect = cols / max(1.0, rows * CELL_ASPECT)
    w, h = im.size
    if w / h > aspect:
        nw = max(1, int(round(h * aspect)))
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    else:
        nh = max(1, int(round(w / aspect)))
        y = int((h - nh) * 0.42)
        im = im.crop((0, y, w, y + nh))
    big = im.resize((cols * _K, rows * 2 * _K), Image.LANCZOS)
    # the mask, not the picture: see the docstring - the silhouette's boundary is unambiguous where a
    # line's two sides are not
    lum = big.getchannel("A")
    gx = lum.filter(ImageFilter.Kernel((3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], scale=4, offset=128))
    gy = lum.filter(ImageFilter.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=4, offset=128))
    A, X, Y = big.getchannel("A").load(), gx.load(), gy.load()
    cells = []
    for r in range(rows):
        row = []
        for c in range(cols):
            sx = sy = 0.0
            total = 0.0
            n = 0
            for yy in range(2 * _K):
                for xx in range(_K):
                    px_, py_ = c * _K + xx, r * 2 * _K + yy
                    if A[px_, py_] < 110:
                        continue
                    ex, ey = X[px_, py_] - 128, Y[px_, py_] - 128
                    mag = math.hypot(ex, ey)
                    if mag < _EDGE:
                        continue
                    sx += ex
                    sy += ey
                    total += mag
                    n += 1
            if n < 2 or total <= 0.0:
                row.append(None)
                continue
            # the gradient is across the outline, so it runs along the perpendicular
            dxx, dyy = -sy, sx / CELL_ASPECT
            norm = math.hypot(dxx, dyy) or 1.0
            dxx, dyy = dxx / norm, dyy / norm
            best = max(_GLYPHS, key=lambda g: g[1][0] * dxx + g[1][1] * dyy)
            row.append((best[0], min(255, 150 + int(8 * n))))
        cells.append(tuple(row))
    return tuple(cells), cols, rows
