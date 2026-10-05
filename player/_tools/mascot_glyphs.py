"""航小天, at terminal resolution - the school variant's character.

The film draws 大肥鱼 through three routes (see `her_glyphs.py`); this is the school variant's
replacement for that whole file, and it draws 航小天 - the 2017 中国航天日 mascot, designed by
students of 西北工业大学航天学院 - for the left-hand pane.

Two things are different from `her_glyphs.py` and both matter:

  * **The source art is one drawing, not eight.** The whale came with eight expression webps; 航小天
    comes with a single illustration. Eight expressions are therefore *derived*: `face_overlay()`
    paints the eyes, brows and mouth over the original face, using the drawing's own skin tone
    sampled once from the cheek. Everything else in the figure is untouched, so every expression is
    provably the same character in the same pose.
  * **The palette is his, not hers.** The film's `blue` tint is DeepSeek brand blue and belongs to
    the whale. 航小天 wears a white 航天服 with a dark navy visor and blue-framed glasses, so the
    half-block mode tints through a ramp built from *those* colours. The `ui()` gain mechanism still
    applies - "the system colour is you, and it drains when you leave" survives the recast - but the
    mascot's own colours do not drain.

The illustration carries its own alpha (135,128 of 301,413 pixels are fully transparent - it is a
cut-out, not a rectangle), so there is nothing to key out and no flood fill here. That is worth
stating plainly because the alternative is a trap: 航小天's suit is *white*, and a "near-white
means background" rule would delete it.

`avatar_rgb()` is the one entry point the player's chat window uses: `tui_live._avatar_block`
reduces a PNG to `(top, bottom)` RGB pairs per cell, so this hands it the same shape from the
half-block portrait instead of from a file.

    from mascot_glyphs import glyph_cells, halfblock, pick_crop, fit, avatar_rgb
    cells, w, h, ox, oy = glyph_cells("normal", "upper", 60, 26)
    block, w, h = halfblock("proud", "face", 14, 7)
    blk = avatar_rgb("normal", 16, 8)
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
# the illustration lives in the *adaptation's* asset folder, not inside the player: `player/_tools/`
# -> `player/` -> `project/`, and `project/assets/`. Stated explicitly because the sibling modules in
# this folder (`her_glyphs.py` and friends) use `parents[1]` for the player root, and copying that
# here pointed at `player/assets/`, which does not exist.
SRC = ROOT.parent / "assets" / "\u822a\u5c0f\u5929.png"

# `her_glyphs.py:45-46`'s crop names, with this drawing's own boxes measured rather than copied.
#
# `face` was the one that was wrong, and the user caught it: it was `(0.20, 0.0, 0.80, 0.27)`, i.e.
# y 0..175 of a 651-tall canvas, which stops *at the eye opening* (the drawing's eyes run y 155..185)
# - so the chat avatar was the top half of a face: bangs, eyebrows, eyes, and nothing below them.
# The measurements (`_dev/measure_art.py`, and `face_region()`'s docstring for the earlier pass):
#
#   hair starts   y=2          head is widest  x 105..351, y 100..190
#   eyes          y 155..185   mouth          y ~228
#   chin narrows  y 240..244   collar arrives y ~250..256
#
# so the head is x 98..358, y 0..250 - hair to just under the chin - and it comes out 246x248,
# aspect 0.99 against the chat avatar's own 0.95. That near-square is the point: it fills the avatar
# box exactly (24x24 samples = 12 rows of 24 cells) instead of being letterboxed into it.
CROPS = {"full": None, "upper": (0.10, 0.0, 0.90, 0.47), "face": (0.212, 0.0, 0.775, 0.385),
         "bust": (0.16, 0.0, 0.84, 0.35)}
# a terminal cell is about 1:2.1, and so is a glyph cell in the film (6 x 12.65 px)
CELL_ASPECT = 2.1

EXPRESSIONS = ["normal", "happy", "serious", "confused", "worried", "proud", "shy", "flat"]

GLYPH_RAMP = " .:-=+*#%@"
RAMP_BLOCK = " \u2591\u2592\u2593\u2588"          # 5 levels, for the half-block portrait

# his own colours: white 航天服, navy visor, blue-framed glasses, warm skin, dark hair
NAVY = (18, 26, 58)
BLUE = (58, 92, 178)
SKY = (150, 190, 235)
WHITE = (238, 242, 248)
SKIN = (247, 216, 190)
BLUSH = (235, 152, 146)

# one cell of the half-block portrait is two luminance samples; the ramp runs 16 %..100 % so the
# figure does not dissolve into the background (her_glyphs.py:162 LEVEL_FLOOR)
LEVELS = len(RAMP_BLOCK)
LEVEL_FLOOR = 0.18

# background cut: near-white AND reachable from the border (see the module docstring)
BG_WHITE = 232
BG_TOL = 18


# ---------------------------------------------------------------- source

@lru_cache(None)
def raw() -> Image.Image:
    """The illustration exactly as shipped: 463x651, RGBA, its own alpha already cut."""
    return Image.open(SRC)


@lru_cache(None)
def rgba() -> Image.Image:
    """The illustration as RGBA, with four bands whatever the file happens to carry."""
    return raw().convert("RGBA")


@lru_cache(None)
def ink_box() -> tuple[int, int, int, int]:
    """The figure's bounding box inside the canvas, as (x0, y0, x1, y1) inclusive.

    Thresholded at alpha 128 rather than at "any non-zero alpha": the cut-out carries a soft edge,
    and its 1-pixel halo would push the box out to the whole canvas (measured: bbox() returns
    (0, 0, 463, 651) - the full frame - while the ink starts at y=4).
    """
    a = rgba().getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    b = a.getbbox() or (0, 0, *raw().size)
    return b[0], b[1], b[2] - 1, b[3] - 1


# ---------------------------------------------------------------- expressions

def _face_frame() -> tuple[float, float, float, float, float, float]:
    """Where the face is, as fractions of the figure's ink box: (ex0, ex1, ey, mx, my, r).

    Measured off the illustration, not guessed, and the first guess was wrong in a way worth
    recording: the obvious reading of a 463x651 cut-out is "the head is the top ~25 %, so the eyes
    are at 0.245". They are not. The ink box starts at y=1 and the drawing puts the eye line at
    y=155, i.e. 0.236 - close enough to look right - but the *figure* is a half-body crop, so the
    fractions that matter are of the whole canvas and the eyes sit at 0.24 while the mouth is at
    0.35, not 0.245 and 0.36. The earlier values painted the pupils onto the cheek and left the real
    eyes untouched; `_dev/art_probe.py` is what showed it.

    ex0/ex1 are the outer edges of the two eye patches and `r` is the radius they are drawn at;
    `r * fw` lands on ~15 px, which is the width of one of the drawing's own pupils.

    The eye line took two corrections, both caught by looking at `_dev/art_probe.py`'s frames:
    first 0.245 (pupils on the cheek), then 0.238 (pupils overlapping the bangs). The drawing's own
    pupil centres are at y=163, i.e. 0.249 of the ink box, with the eye opening running y=155..185.
    "A little higher than the pupils, because the lid is above them" is the instinct that produced
    both wrong answers; the right rule is simply to put the pupil on the pupil.
    """
    return 0.240, 0.760, 0.251, 0.500, 0.372, 0.055


@lru_cache(None)
def skin_tone() -> tuple[int, int, int]:
    """The drawing's own cheek colour: the median of an opaque patch just inside the left cheek.

    Transparent pixels are skipped rather than averaged in. At the fraction this face actually sits
    at, a plain sample of the patch lands mostly on the cut-out's empty margin and comes back pure
    white - which, painted over the eyes, would erase half the face instead of covering it.
    """
    im = rgba()
    px = im.load()
    x0, y0, x1, y1 = ink_box()
    fw, fh = x1 - x0 + 1, y1 - y0 + 1
    cx, cy = int(x0 + 0.22 * fw), int(y0 + 0.34 * fh)
    patch = [px[x, y][:3] for x in range(cx - 4, cx + 5) for y in range(cy - 4, cy + 5)
             if px[x, y][3] >= 200]
    if not patch:                                  # no opaque cheek there: give up honestly
        return (247, 216, 190)
    patch.sort(key=lambda c: c[0] + c[1] + c[2])
    return patch[len(patch) // 2]


@lru_cache(None)
def face_region() -> tuple[int, int, int, int]:
    """The drawn face as (x0, y0, x1, y1) inclusive - the patch every expression is painted into.

    Measured off the illustration (and checked by drawing the box onto the art, which is what
    `_dev/art_probe.py --boxes` is for): the skin of the face spans x 122..330, y 140..260 of a
    463x651 canvas, i.e. x 0.264..0.713 and y 0.214..0.398 of the ink box. The box is padded a
    little on all four sides and squared off by the eye line, so the fractions used to place the
    features inside it are stable.

    A colour search for warm skin tones was tried first and is not usable here: 航小天's skin, the
    suit's orange strap keepers and the flag patch are all warm, so the search returns the whole
    figure (it found (44, 3, 347, 260) - head *and* torso). The face is a fixed part of a fixed
    drawing; measuring it once and writing it down is both simpler and correct.
    """
    x0, y0, x1, y1 = ink_box()
    fw, fh = x1 - x0 + 1, y1 - y0 + 1
    return (x0 + int(0.230 * fw), y0 + int(0.196 * fh),
            x0 + int(0.760 * fw), y0 + int(0.418 * fh))


@lru_cache(None)
def face_overlay(expr: str) -> Image.Image | None:
    """The eyes, brows and mouth for `expr`, as an RGBA patch to composite at `face_region()`'s box.

    `normal` returns None: the original drawing already *is* that expression, and re-drawing it
    would only make it worse. Every other expression is painted over the region `face_region()`
    found, laid on a copy of the face itself - so the patch is the face, and the only pixels that
    can change are the face's own.

    The first two attempts at this painted a skin-coloured ellipse over a hand-kept rectangle and
    both were visibly wrong; the drawn ellipse is what a screenshot showed to be a pale disc with
    the real cheeks showing around it, and the second, larger ellipse grew upward until it ate the
    bangs and left the character with a bald patch. Copying the region instead of covering it is
    what removes the whole class of failure: there is no seam to hide because there is no cover.
    """
    if expr == "normal":
        return None
    rx0, ry0, rx1, ry1 = face_region()
    w, h = rx1 - rx0 + 1, ry1 - ry0 + 1
    if w < 8 or h < 8:
        return None
    lay = rgba().crop((rx0, ry0, rx1 + 1, ry1 + 1))
    d = ImageDraw.Draw(lay)

    def X(f: float) -> int:                        # a fraction of the face -> a pixel in the patch
        return int(round(f * (w - 1)))

    def Y(f: float) -> int:
        return int(round(f * (h - 1)))

    ink = (40, 34, 38)
    lw = max(1, int(round(h * 0.018)))
    # The eye centres and the mouth, as fractions of the face box. These come from a dark-run sweep
    # over the drawing's head (`_dev/art_probe.py --runs`, which prints the runs per row): the two
    # pupils are the dark runs at y 164..184, x 150..172 and x 233..264, and the mouth is the wide
    # dark band at y 208..220. Three earlier sets of values were taken by eye from the art and every
    # one of them put the pupils on the cheek - the glasses make the face *look* symmetric about the
    # wrong centre, and the left lens sits much further left than the eye inside it. Measuring beats
    # looking, here.
    lx, rxp = X(0.400), X(0.630)                    # screen-left pupil, then screen-right
    lye, rye = Y(0.255), Y(0.265)
    mc, my = X(0.655), Y(0.535)
    rr = w * 0.085                                  # one pupil is ~21 px, 0.085 of the box's width

    if expr == "happy":                             # the eyes are gone: two arcs curving up
        for cx in (lx, rxp):
            d.arc([cx - rr, my - h * 0.62, cx + rr, my - h * 0.32], 195, 345, fill=ink, width=lw)
        d.arc([mc - rr * 1.7, my - rr * 1.5, mc + rr * 1.7, my + rr * 1.5],
              20, 160, fill=ink, width=lw)
    elif expr == "serious":                         # pupils, with the lids cut level across them
        for cx, cy in ((lx, lye), (rxp, rye)):
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=ink)
            d.ellipse([cx - rr * 1.15, cy - rr * 1.6, cx + rr * 1.15, cy - rr * 0.30],
                      fill=skin_tone() + (255,))
            d.line([cx - rr * 1.25, cy - rr * 0.75, cx + rr * 1.25, cy - rr * 0.75], fill=ink, width=lw)
        d.line([mc - rr * 1.5, my, mc + rr * 1.5, my], fill=ink, width=lw)
    elif expr == "confused":                        # one lid half down, one all the way; a wry mouth
        for cx, cy, cut in ((lx, lye, 0.20), (rxp, rye, 0.55)):
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=ink)
            d.ellipse([cx - rr * 1.2, cy - rr * 1.6, cx + rr * 1.2, cy - rr * 1.6 + cut * rr * 2],
                      fill=skin_tone() + (255,))
        d.arc([mc - rr * 1.4, my - rr * 1.2, mc + rr * 1.4, my + rr * 1.2],
              200, 320, fill=ink, width=lw)
    elif expr == "worried":                         # both lids dropped, a small open mouth
        for cx, cy in ((lx, lye), (rxp, rye)):
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=ink)
            d.ellipse([cx - rr * 1.2, cy - rr * 1.6, cx + rr * 1.2, cy - rr * 1.6 + 0.45 * rr * 2],
                      fill=skin_tone() + (255,))
        d.ellipse([mc - rr * 0.35, my - rr * 0.45, mc + rr * 0.35, my + rr * 0.45], fill=ink)
    elif expr == "proud":                           # eyes open, and a wide grin
        for cx, cy in ((lx, lye), (rxp, rye)):
            d.ellipse([cx - rr * 0.85, cy - rr * 0.85, cx + rr * 0.85, cy + rr * 0.85], fill=ink)
        d.arc([mc - rr * 1.9, my - rr * 1.6, mc + rr * 1.9, my + rr * 1.4],
              10, 170, fill=ink, width=lw)
    elif expr == "shy":                             # eyes shut low, blush, a small smile
        for cx, cy in ((lx, lye), (rxp, rye)):
            d.arc([cx - rr, cy - rr * 0.75, cx + rr, cy + rr * 0.75], 195, 345, fill=ink, width=lw)
            bx = cx + int(rr * (1.7 if cx == lx else -1.7))
            d.ellipse([bx - rr * 0.55, cy + rr * 0.25, bx + rr * 0.55, cy + rr * 1.05], fill=BLUSH + (140,))
        d.arc([mc - rr * 1.0, my - rr * 0.9, mc + rr * 1.0, my + rr * 0.9],
              25, 155, fill=ink, width=lw)
    elif expr == "flat":                            # the deadpan: level lids, level mouth
        for cx, cy in ((lx, lye), (rxp, rye)):
            d.ellipse([cx - rr * 0.9, cy - rr * 0.9, cx + rr * 0.9, cy + rr * 0.9], fill=ink)
            d.ellipse([cx - rr * 1.15, cy - rr * 1.6, cx + rr * 1.15, cy - rr * 0.42],
                      fill=skin_tone() + (255,))
        d.line([mc - rr * 1.3, my, mc + rr * 1.3, my], fill=ink, width=lw)
    else:
        return None
    return lay, rx0, ry0


@lru_cache(None)
def sprite(expr: str) -> Image.Image:
    """The illustration with `expr`'s face. Identical to `rgba()` for `normal`."""
    base = rgba().copy()
    ov = face_overlay(expr)
    if ov is None:
        return base
    patch, px0, py0 = ov
    base.alpha_composite(patch, (px0, py0))
    return base


# ---------------------------------------------------------------- fitting

def crop_box(crop: str) -> tuple[int, int, int, int]:
    """The crop rectangle in the sprite, before any fitting. `full` is the ink box."""
    x0, y0, x1, y1 = ink_box()
    if crop == "full":
        return x0, y0, x1 + 1, y1 + 1
    im = raw()
    w, h = im.size
    a, b, c, e = CROPS[crop]
    return int(w * a), int(h * b), int(w * c), int(h * e)


@lru_cache(None)
def crop_aspect(crop: str) -> float:
    """The crop's own width/height, measured on the ink box so the whitespace does not count."""
    x0, y0, x1, y1 = crop_box(crop)
    b = sprite("normal").getchannel("A").crop((x0, y0, x1, y1)).getbbox()
    if b is None:
        return 1.0
    return (b[2] - b[0]) / max(1.0, (b[3] - b[1]))


def pick_crop(cols: int, rows: int) -> str:
    """Which crop reads in a cols x rows pane: the one whose own shape is nearest the pane's."""
    box = cols / max(1.0, rows * CELL_ASPECT)
    return min(CROPS, key=lambda c: abs(math.log(crop_aspect(c) / box)))


def fit(cols: int, rows: int, crop: str) -> tuple[int, int]:
    """The largest cell rect inside the pane that has the crop's own aspect."""
    a = crop_aspect(crop)
    uc, ur = int(round(rows * CELL_ASPECT * a)), rows
    if uc > cols:
        uc, ur = cols, max(3, int(round(cols / (CELL_ASPECT * a))))
    return max(4, min(cols, uc)), max(3, min(rows, ur))


@lru_cache(None)
def cropped(expr: str, crop: str, target_aspect: float = 0.0) -> Image.Image:
    """The crop, then centre-cropped to the cell grid's aspect so nothing is stretched."""
    x0, y0, x1, y1 = crop_box(crop)
    im = sprite(expr).crop((x0, y0, x1, y1))
    a = im.getchannel("A")
    b = a.getbbox()
    if b is not None:
        im = im.crop((b[0], b[1], b[2], b[3]))       # tighten onto the ink: the crop fractions are rough
    if target_aspect > 0:
        w, h = im.size
        if w / h > target_aspect:                    # too wide: trim the sides
            nw = max(1, int(round(h * target_aspect)))
            x = (w - nw) // 2
            im = im.crop((x, 0, x + nw, h))
        else:                                        # too tall: trim the bottom, keep the face
            nh = max(1, int(round(w / target_aspect)))
            im = im.crop((0, 0, w, nh))
    return im


# ---------------------------------------------------------------- mode "glyph"

@lru_cache(None)
def glyph_cells(expr: str, crop: str, cols: int, rows: int):
    """`(cells, w, h, ox, oy)` - one `(char, fg, bg)` per terminal cell, or None where empty.

    The same maths as `her_glyphs.glyph_lines` (Sobel -> a direction glyph on an edge, a ramp
    character in a flat region) with two changes the drawing asks for:

      * **the fg is the drawing's own colour, dimmed by the cell's luminance**, instead of a single
        tint. The whale is one flat blue and reads fine that way; 航小天 is a white suit with a navy
        visor and blue glasses, and a single tint would throw all of that away.
      * **the outline test is looser** (`> 0.9`, not `> 1.1`): a 463x651 illustration reduced to 60
        columns keeps far more edge than a 1024x1024 one, and at 1.1 the glasses and the visor split
        into ramp characters instead of drawing their own strokes.
    """
    from PIL import Image as _I
    from PIL import ImageFilter as _IF
    if cols < 4 or rows < 3:
        return (), 0, 0, 0, 0
    aspect = cols / max(1, rows * CELL_ASPECT)
    small = cropped(expr, crop, aspect).resize((cols, rows), _I.LANCZOS)
    rgb, alpha = small.convert("RGB"), small.getchannel("A")
    lum = rgb.convert("L")
    gx = lum.filter(_IF.Kernel((3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], scale=4, offset=128))
    gy = lum.filter(_IF.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=4, offset=128))
    L, A, X, Y, P = lum.load(), alpha.load(), gx.load(), gy.load(), rgb.load()
    cells = []
    for r in range(rows):
        line = []
        for c in range(cols):
            if A[c, r] < 110:
                line.append(None)
                continue
            v = L[c, r] / 255
            ex, ey = (X[c, r] - 128) / 32, (Y[c, r] - 128) / 32
            base = P[c, r]
            if math.hypot(ex, ey) > 0.9:
                ang = (math.degrees(math.atan2(ey, ex)) + 180) % 180
                ch = "|" if ang < 22.5 or ang >= 157.5 else "\\" if ang < 67.5 else "-" if ang < 112.5 else "/"
                fg = tuple(min(255, int(k * 1.15)) for k in base)
            else:
                ch = GLYPH_RAMP[min(len(GLYPH_RAMP) - 1, 1 + int(v * (len(GLYPH_RAMP) - 1)))]
                fg = tuple(int(k * (0.45 + 0.55 * v)) for k in base)
            line.append((ch, fg, None))
        cells.append(tuple(line))
    return tuple(cells), cols, rows, 0, 0


# ---------------------------------------------------------------- mode "ramp"

@lru_cache(None)
def ramp_cells(expr: str, crop: str, cols: int, rows: int, gamma: float = 0.85):
    """`(cells, w, h, ox, oy)` - the plain brightness ramp, no edge strokes.

    This is the third route, and it exists because the first two both have a failure mode on *this*
    drawing that the whale never exposed:

      * `glyph_cells` spends cells on strokes. A 463x651 illustration cut to 60 columns has edges
        everywhere - glasses, visor, seams, the peace sign - and the result reads as texture.
      * `halfblock` is honest but it is a picture, and a picture in the middle of a text pane stops
        looking like a program.

    The ramp keeps the drawing's *mass* (dark hair, dark visor, white suit) as characters and drops
    the strokes, so at chat-avatar sizes it reads as a face. `gamma` lifts the midtones: the suit is
    white and the background is nearly black, so a linear ramp spends most of its characters on
    nothing.
    """
    if cols < 4 or rows < 3:
        return (), 0, 0, 0, 0
    aspect = cols / max(1, rows * CELL_ASPECT)
    small = cropped(expr, crop, aspect).resize((cols, rows), Image.LANCZOS)
    rgb, alpha = small.convert("RGB"), small.getchannel("A")
    lum, A, P = rgb.convert("L").load(), alpha.load(), rgb.load()
    cells = []
    for r in range(rows):
        line = []
        for c in range(cols):
            if A[c, r] < 110:
                line.append(None)
                continue
            v = (lum[c, r] / 255) ** gamma
            ch = GLYPH_RAMP[min(len(GLYPH_RAMP) - 1, int(round(v * (len(GLYPH_RAMP) - 1))))]
            base = P[c, r]
            fg = tuple(min(255, int(k * (0.50 + 0.62 * v))) for k in base)
            line.append((ch, fg, None))
        cells.append(tuple(line))
    return tuple(cells), cols, rows, 0, 0


# ---------------------------------------------------------------- mode "half"

def tint_color(level: int, ink: tuple[int, int, int]) -> tuple[int, int, int]:
    """One luminance level of the block ramp, painted in a colour close to the drawing's own.

    The three anchors are the drawing's: navy in the shadow, the ink's own colour through the mid,
    and a cold white at the top. `ink` moves the mid anchor, so the visor stays navy while the suit
    climbs to white - which is the whole reason the ramp is not a single hue.
    """
    k = level / (LEVELS - 1)
    lo, hi = NAVY, WHITE
    mid = tuple(int(0.45 * a + 0.55 * b) for a, b in zip(ink, BLUE))
    if k <= 0.5:
        u = k * 2
        return tuple(int(a + (b - a) * u) for a, b in zip(lo, mid))
    u = (k - 0.5) * 2
    return tuple(int(a + (b - a) * u) for a, b in zip(mid, hi))


@lru_cache(None)
def halfblock(expr: str, crop: str, cols: int, rows: int, levels: int = LEVELS):
    """`(block, w, h)` where `block[r][c]` is `(top, bottom)`, each a level index or None.

    One cell is one half-block character: the top sample is the foreground and the bottom the
    background, so `▀` is a whole cell of two pixels. The colour of a cell comes from the drawing's
    own average colour over that cell, so navy stays navy.
    """
    if cols < 2 or rows < 2:
        return (), 0, 0
    a = crop_aspect(crop)
    ur = int(round(min(cols / a, rows * 2)))         # a half-block sample is ~square
    ur -= ur % 2
    uc = max(2, min(cols, int(round(ur * a))))
    small = cropped(expr, crop).resize((uc, ur), Image.LANCZOS)
    L, A, P = small.convert("L").load(), small.getchannel("A").load(), small.convert("RGB").load()

    def lv(c, r):
        if A[c, r] <= 100:
            return None
        return int(round((LEVEL_FLOOR + (1 - LEVEL_FLOOR) * L[c, r] / 255) * (levels - 1)))

    block, colour = [], []
    for r in range(ur // 2):
        row, crow = [], []
        for c in range(uc):
            t, b = lv(c, 2 * r), lv(c, 2 * r + 1)
            row.append((t, b))
            crow.append(P[c, 2 * r] if t is not None else (P[c, 2 * r + 1] if b is not None else None))
        block.append(tuple(row))
        colour.append(tuple(crow))
    return (tuple(block), tuple(colour)), uc, ur // 2


# ---------------------------------------------------------------- warm-up

def warm() -> None:
    """Read and cut everything once, during start-up rather than on the first drawn frame."""
    rgba()
    ink_box()
    for crop in CROPS:
        cropped("normal", crop, 1.0)
    for expr in EXPRESSIONS:
        sprite(expr)


# ---------------------------------------------------------------- the chat avatar

# The pane the film gives its avatar, and the reason the cap moves from 14 to 16: at 14x7 the
# half-block face still reads (it is 14x14 samples), but at 16x8 the glasses are one sample thick
# instead of a blur, and 16 is what `tui_live.AVATAR_MAX_W` becomes under the school variant.
AVATAR_COLS = 16
AVATAR_ROWS = 8

# which crop the chat avatar is: the head, from the top of the hair to the collar (`CROPS["face"]`).
# Named because it is not obvious from the call - and because the whole *point* of the avatar is that
# the face is recognisable, which it was not while this was the forehead crop.
AVATAR_CROP = "face"


@lru_cache(maxsize=128)
def avatar_rgb(expr: str, cols: int, rows: int):
    """`(top, bottom)` RGB per cell, in the shape `tui_live._avatar_block` returns for a PNG.

    The film's avatar is one PNG per frame (the face training); 航小天's is drawn from the
    illustration, so the player's avatar routine is handed the same structure from here instead of
    from a file. The colour is the drawing's own, so the half-block ramp's navy/white survives into
    the chat header at 16x8 - which is the whole reason this is a separate function rather than the
    level index that `halfblock` returns for the big pane.
    """
    # `rows`, not `rows * 2`: `halfblock` already doubles for the half-block samples, so asking it for
    # `rows * 2` cell rows let a narrow crop come back one or two rows *taller* than the header's
    # budget (measured: 13 rows for the 12 the header asks for, aspect 0.91). What the extra was meant
    # to buy - more samples per cell - is not a thing: two samples per cell is what `▀` is.
    grid, _w, _h = halfblock(expr, AVATAR_CROP, cols, rows)
    block, colour = grid
    out = []
    for r, (brow, crow) in enumerate(zip(block, colour)):
        row = []
        for c, (top, bot) in enumerate(brow):
            ink = crow[c] or WHITE
            # a transparent half shows the pane's own background, so it must not be painted at all;
            # `draw_dsh` writes `▀` with (top, bot) unconditionally, so "absent" is the pane's BG.
            t = tint_color(top, ink) if top is not None else (4, 7, 15)
            b = tint_color(bot, ink) if bot is not None else (4, 7, 15)
            row.append((t, b))
        out.append(tuple(row))
    return tuple(out)


@lru_cache(None)
def font(size: int):
    """A monospace face for the probe screenshots. The player uses its own (tui_live._pil_font)."""
    from PIL import ImageFont
    for p in ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()
