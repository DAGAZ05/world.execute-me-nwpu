"""Everything that crosses the screen: the aircraft, the character art, and the AI motifs.

The panes draw *inside* the right-hand column. This module draws over the whole frame - left window,
right column, chrome and all - which is the thing that was missing: a plane can only read as flying
past if it is allowed to pass *between* the two halves of the screen, and a photograph can only land as
a hit if it is allowed to cover the chat window.

The model is one event list. Each event is `(start, end, fn, kwargs)`, `fn` draws given
`(screen, cols, rows, t, u)` where `u` is the event's own 0..1 progress, and every position inside is a
function of `u` alone - never of a frame counter or of a previous frame. That buys the two things the
skill asks for: a frame at any time is the same frame however you got there, and **several events can
be live at once**, because they are independent layers rather than a sequence.

Two kinds of event, deliberately in one place because they compete for the same screen:

  * **the aircraft** (`fly`, `sweep`), which are the school's three 三航 results and which the song
    has a rhythm for - they are placed on the chorus hits, not sprinkled.
  * **the hits** (`flash`, `glyphs`), a photograph or a piece of character art landing over the whole
    frame for a beat and going.

A sprite is loaded once, reduced to terminal cells, and cached. Nothing here re-decodes an image per
frame; the cost per frame is a splice of a few hundred cells, which is what the pane drawings already
cost.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from PIL import Image

import film_panels as FP        # the film's own beat clock, for the figure's hop (`stand`)

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
LANDMARKS = ASSETS / "\u6821\u56ed\u6807\u8bc6\u7269"          # the campus works
RESULTS = ASSETS / "\u6821\u56ed\u4e0e\u6210\u679c"              # the aircraft and the campus

# where each picture lives: a name -> (folder, filename). One table so a missing file is one lookup.
FILES = {
    "gate": (RESULTS, "\u6821\u95e8.png"),
    "library": (RESULTS, "\u56fe\u4e66\u9986.png"),
    "y20": (RESULTS, "\u8fd020.png"),
    "j20": (RESULTS, "\u6b7c20.png"),
    "z20": (RESULTS, "\u76f420.png"),
    "arj21": (RESULTS, "ARJ21.png"),
    "manta": (RESULTS, "\u9b54\u9b3c\u9c7c.png"),
    "torpedo": (RESULTS, "\u9c7c\u96f7.png"),
    "crest": (LANDMARKS, "\u6821\u5fbd.webp"),
    "sword": (LANDMARKS, "\u4e3a\u56fd\u94f8\u5251\u96d5\u5851_\u4fef\u77b0.png"),
    "dialogue": (LANDMARKS, "\u5bf9\u8bdd_\u673a\u5668\u624b\u4e0e\u4eba\u7684\u624b.png"),
    "memory": (LANDMARKS, "memory_\u5355\u5c42.jpg"),
    "hexun": (LANDMARKS, "\u4f55\u5c0a_\u7ebf\u7a3f.png"),
    "embedded": (ASSETS, "\u5d4c\u5165\u5f0f-\u8d85\u58f0\u6ce2\u7ea2\u5916\u6d4b\u8ddd.jpg"),
    # 航小天's own file: the avatar in the chat window is a *crop* of this (16x8 cells of face), and the
    # breakout at the end is the whole figure, which the film had never shown
    "mascot": (ASSETS, "\u822a\u5c0f\u5929.png"),
}
for _k, (_d, _f) in list(FILES.items()):
    # one tolerant pass: the two Chinese filenames are easy to mistype an escape for, and a missing
    # sprite is a *silent* absence at runtime (the event just draws nothing), so it is worth resolving
    # by prefix here rather than discovering it in a frame
    if not (_d / _f).exists():
        _stem = _f.split(".")[0][:2]
        for _p in _d.glob("*"):
            if _p.suffix.lower() in (".png", ".jpg", ".webp", ".jpeg", ".txt") and _p.name.startswith(_stem):
                FILES[_k] = (_d, _p.name)
                break

TITLES = {
    "gate": "\u6821\u95e8", "library": "\u56fe\u4e66\u9986",
    "y20": "\u8fd0-20", "j20": "\u6b7c-20", "z20": "\u76f4-20", "arj21": "ARJ21",
    "manta": "\u9b54\u9b3c\u9c7c", "crest": "\u897f\u5317\u5de5\u4e1a\u5927\u5b66",
    "torpedo": "\u9c7c\u96f7",
    "sword": "\u4e3a\u56fd\u94f8\u5251", "dialogue": "\u5bf9\u8bdd",
    "memory": "MEMORY", "hexun": "\u4f55\u5c0a", "embedded": "\u5d4c\u5165\u5f0f",
}

_OPEN = Image.open
CELL_ASPECT = 2.1
LEVEL_FLOOR = 0.18
SHADE = " \u2591\u2592\u2593\u2588"

# Which way each picture is *looking*, read off the files rather than assumed. Every aircraft in
# `校园与成果/` is photographed nose-left - 运-20, 歼-20, 直-20, ARJ21 and the manta all face left, and
# the torpedo faces right - so a plain left-to-right crossing flew all of them tail first. The user
# spotted it in one frame ("有的飞机方向飞反了，成了尾部在往前飞"), which is the sort of thing a
# direction table fixes once instead of at every call site.
FACES = {
    "y20": "left", "j20": "left", "z20": "left", "arj21": "left", "manta": "left",
    "torpedo": "right",
}


def _flip_for(name: str, dx: float) -> str:
    """The mirror a sprite needs so that its nose leads in direction `dx`."""
    face = FACES.get(name, "")
    if face == "left" and dx > 0:
        return "h"
    if face == "right" and dx < 0:
        return "h"
    return ""


# ---------------------------------------------------------------- the artwork, as cells

def _paper(im: Image.Image, crop: bool = True) -> Image.Image:
    """Drop the background by flooding in from the border, whatever colour the background is.

    The first version only removed *white* paper, which is what the sculpture and the vessel have. Every
    aircraft in `校园与成果/` is a photograph against **black or navy** - 运-20 on a dark blue field,
    歼-20 and 直-20 on black, the manta underwater - so for those the key removed nothing and the sprite
    was the whole rectangle: an aircraft 90 cells wide pasted a 90x14 block of character noise over the
    frame, which is what the user's frame showed as a snowstorm.

    So the background is measured rather than assumed: the mean colour of the border ring, then a flood
    from the border removing anything within `tol` of it per channel. A second pass takes the enclosed
    regions of the same colour (the dark between an aircraft's tail fins, say). The tolerance is generous
    because these photographs have a soft glow around the subject, and a key that stops at the first
    gradient change leaves a halo of bright cells in the shape of the rectangle.

    **...but a picture that came with its own cut is not keyed at all, and that is the fix for the worst
    bug this module had.** Every aircraft, the manta, the library and the gate are PNGs with a real alpha
    channel - 60 to 80 % of their pixels are transparent - so they are cut-outs, not photographs on paper.
    The border ring of a cut-out is the *transparent* pixels, whose RGB is black, so `bg` came out (3,3,5)
    and `bright` was False: the flood then removed everything within 78 of black, which is the dark manta
    body, the aircraft's dark panels, the library's shadowed glass. What survived was the pale parts of
    each subject, and *that* is why the user could not tell what the manta was ("魔鬼鱼…我没看出来") and
    why the aircraft read as smears rather than as aircraft. The alpha channel is the key; there is nothing
    to measure.

    **It runs on the already-downscaled image, and that is not an optimisation detail but the difference
    between working and not.** A 1536x1024 photograph is 1.5 million pixels and the flood visits nearly
    all of them, in Python: measured at 2-5 *seconds* for one sprite, the first time each aircraft was
    needed - which is mid-song, during playback. Keying the 90x28 cell-sized copy instead is about thirty
    thousand pixels, and the sprite looks the same because the cells are all that survive anyway. On a
    white background the old threshold visited only the border ring and cost nothing, which is why this
    hid until the key was widened to dark backgrounds.
    """
    from collections import deque
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    alpha = im.getchannel("A")
    box = alpha.getbbox()
    if alpha.getextrema()[0] < 250:               # it came with its own cut: the alpha *is* the key
        return im.crop(box) if (crop and box) else im
    ring = [(x, y) for x in range(0, w, max(1, w // 32)) for y in (0, h - 1)]
    ring += [(x, y) for y in range(0, h, max(1, h // 32)) for x in (0, w - 1)]
    n = max(1, len(ring))
    bg = tuple(sum(px[x, y][i] for x, y in ring) / n for i in range(3))
    bright = sum(bg) / 3 > 200
    tol = 46 if bright else 78

    def paper(c) -> bool:
        d = max(abs(c[i] - bg[i]) for i in range(3))
        return d <= tol

    seen = bytearray(w * h)
    q: deque = deque()
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
    # the enclosed parts of the same colour: a flood from the edge cannot reach the gap between two tail
    # fins, and that gap is background too
    if not bright:
        for y in range(h):
            for x in range(w):
                if not seen[y * w + x] and paper(px[x, y][:3]):
                    seen[y * w + x] = 1
                    px[x, y] = px[x, y][:3] + (0,)
    if not crop:
        return im
    a = im.getchannel("A").getbbox()
    return im.crop(a) if a else im


@lru_cache(None)
def sprite(name: str, cols: int, rows: int, contrast: float = 1.0, flip: str = "",
           outline: bool = False):
    """`(cells, w, h)` where a cell is `(char, level, rgb)` or None. Cached per size.

    `level` is 0..4 for the block ramp and `rgb` is the picture's own colour, so a caller can pick
    between "draw the picture" and "draw a coloured silhouette" without decoding it twice. `contrast`
    below 1 pulls the whole thing toward the middle of the ramp, which is what a *background* hit
    wants - a full-contrast photograph behind the chat window is unreadable.

    `flip` is `"v"`, `"h"` or `"vh"`. A photograph has one orientation and a crossing has a direction:
    the torpedo's nose points down-right in the file, and the transition needs it pointing *up*, so the
    image is mirrored rather than the sprite being drawn upside down by the caller. The flip is part of
    the cache key, because it is part of the sprite.

    `outline` adds a one-cell white contour around the sprite's ink - see `_outline`. It is set from
    `OUTLINED` rather than by every caller, because "which pictures get a white edge" is a property of
    the *pictures*: the aircraft and the manta are dark silhouettes against a dark frame, and the campus
    photographs are not.
    """
    spec = FILES.get(name)
    if spec is None or cols < 3 or rows < 2:
        return None
    outline = outline or name in OUTLINED
    p = spec[0] / spec[1]
    if not p.exists():
        return None
    try:
        im = _OPEN(p).convert("RGBA")
    except Exception:
        return None
    if "v" in flip:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    if "h" in flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    aspect = cols / max(1, rows * CELL_ASPECT)
    w, h = im.size
    if w / h > aspect:
        nw = max(1, int(round(h * aspect)))
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    else:
        nh = max(1, int(round(w / aspect)))
        y = int((h - nh) * 0.40)
        im = im.crop((0, y, w, y + nh))
    # **downscale first, then key.** The flood in `_paper` visits every background pixel, so on a
    # 1536x1024 photograph it costs seconds; on this cell-sized copy it costs milliseconds, and the cells
    # are all that survive the resize anyway. See the note in `_paper`.
    small = im.resize((cols, rows * 2), Image.LANCZOS)
    try:
        small = _paper(small, crop=False)
    except Exception:
        pass
    L, A, P = small.convert("L").load(), small.getchannel("A").load(), small.convert("RGB").load()
    out = []
    n_lev = len(SHADE) - 1
    for r in range(rows):
        row = []
        for c in range(cols):
            def lv(y, r=r, c=c):
                if A[c, y] <= 96:
                    return None
                v = (LEVEL_FLOOR + (1 - LEVEL_FLOOR) * L[c, y] / 255) ** (1.0 / max(0.2, contrast))
                # **ordered dithering on the ramp**, which is the one thing this project's pictures were
                # missing. A five-level ramp quantises a photograph's sky and its shadow into five flat
                # bands, and that banding is what "视觉效果还是有些单调" is looking at: the sources have
                # hundreds of greys and the picture shows five. A Bayer 4x4 threshold, at half a level,
                # turns the boundary between two levels into a checkerboard instead of a hard edge - the
                # same trick every image-to-terminal converter uses (chafa's `--dither`, libcaca before
                # it), and the reason its output reads as a photograph rather than as poster art.
                b = (BAYER4[r & 3][c & 3] + 0.5) / 16.0 - 0.5
                v = min(1.0, max(0.0, v + b * DITHER / n_lev))
                return int(round(min(1.0, v) * n_lev))
            top, bot = lv(2 * r), lv(2 * r + 1)
            if top is None and bot is None:
                row.append(None)
            else:
                k = 2 * r if top is not None else 2 * r + 1
                row.append(("\u2580" if top is not None else SHADE[1], max(top or 0, bot or 0), P[c, k]))
        out.append(tuple(row))
    if outline:
        out = _outline(out, cols, rows)
    return tuple(out), cols, rows


# The ordered-dither threshold, 4x4: the classic Bayer matrix, as the fraction of one ramp level each
# cell is nudged by before it is quantised. `DITHER` is how much of a level that nudge may be - half is
# the textbook setting, and less than that keeps the dither from reading as noise in a small pane.
BAYER4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
DITHER = 0.5


# The light every silhouette in the film is drawn against is the frame's own `(4,7,15)`, and a dark
# aircraft on it has no edge: the user's note is "各类飞机、魔鬼鱼的轮廓加上白框，这样图像清晰一些". The
# outline is one cell of white outside the sprite's own ink, with the *shape* of the neighbouring ink in
# it - `▀` when the ink is above, `▄` below, `▌`/`▐` to the sides - so what it draws is a contour rather
# than a box around the picture. It is built into the sprite (and therefore into the sprite cache) rather
# than applied per frame: a 130x41 aircraft is 5300 cells and a second pass over them every frame is
# 10 ms of a 41.7 ms budget for something that never changes.
OUTLINE_RGB = (236, 243, 255)
# **Empty, and that is the user's call.** The outline was batch 26's ("各类飞机、魔鬼鱼的轮廓加上白框，这样
# 图像清晰一些") and this batch takes it back: "我发现飞机这些加白色轮廓后不太好看，还是改回去". The
# mechanism stays because it works and is built into the sprite cache; the list is what decides who wears it,
# and nobody does. Adding a name back here is the whole change if it is ever wanted on one picture.
OUTLINED: tuple = ()


def _outline(grid, cols: int, rows: int):
    """`grid` with a one-cell white contour added around its ink. See `OUTLINE_RGB`."""
    def ink(x, y):
        if 0 <= x < cols and 0 <= y < rows:
            return grid[y][x] is not None
        return False

    out = []
    for r in range(rows):
        row = list(grid[r])
        for c in range(cols):
            if grid[r][c] is not None:
                continue
            up, dn, lf, rt = ink(c, r - 1), ink(c, r + 1), ink(c - 1, r), ink(c + 1, r)
            if not (up or dn or lf or rt):
                continue
            # the glyph follows the side the ink is on, so the white reads as the edge of the shape:
            # a half block against the ink, and a full one where the ink is on both sides of the cell
            if up and dn:
                ch = "\u2588"
            elif up:
                ch = "\u2580"
            elif dn:
                ch = "\u2584"
            elif lf:
                ch = "\u258c"
            else:
                ch = "\u2590"
            row[c] = (ch, len(SHADE) - 2, OUTLINE_RGB)
        out.append(tuple(row))
    return tuple(out)


def paste(s, cells, x0: int, y0: int, ink=None, dim: float = 1.0, box=None, flat: bool = False,
          fast: bool = False) -> None:
    """Blit a sprite's cells onto the screen at `(x0, y0)`, clipped to `box` if given.

    The clip is what lets a plane fly *off* the edge rather than being cut into a rectangle, and what
    lets a photograph be told to cover only part of the frame.

    `flat` skips the per-cell brightness ramp, for a caller whose colours are already final. It is not a
    micro-optimisation for its own sake: the basketball animation is 2800 cells and the ramp is three
    `int()` calls and a `min()` each, measured at 44 ms for that one frame against a 41.7 ms budget - the
    only frame in the film that went over it.

    `fast` writes the cells straight into the buffer instead of calling `Screen.put` per cell, and it is
    the same argument one order of magnitude up: the 运-20 low pass is 285x90 cells ("让其更大，允许超出
    屏幕"), about 10 000 of them on screen, and `put` is a method call with a `CLEAR` lookup and a pair
    repair in it - measured at **60.4 ms** for that frame, half again over budget, on the film's most
    dramatic hit. What the fast path drops is the `CLEAR` check, and dropping it is *correct* here rather
    than a shortcut: `CLEAR` protects cells that an earlier layer drew and this one is about to replace,
    and the vignette is inlined instead. Only full-frame sprites ask for it.
    """
    if not cells:
        return
    grid, w, h = cells
    bx0, by0, bx1, by1 = box or (0, 0, s.cols - 1, s.rows - 1)
    ramp_n = len(SHADE) - 1
    for r in range(h):
        y = y0 + r
        if y < by0 or y > by1:
            continue
        row = grid[r]
        if fast:
            brow, wrow, drow = s.buf[y], s.wide[y], s.dim[y]
            for c in range(w):
                x = x0 + c
                if x < bx0 or x > bx1:
                    continue
                cell = row[c]
                if cell is None:
                    continue
                ch, lv, rgb = cell
                col = ink or rgb
                k = drow[x] * dim * (0.72 + 0.42 * lv / ramp_n)
                brow[x] = (ch, (int(col[0] * k), int(col[1] * k), int(col[2] * k)), BG)
                wrow[x] = False
            continue
        for c in range(w):
            x = x0 + c
            if x < bx0 or x > bx1:
                continue
            cell = row[c]
            if cell is None:
                continue
            ch, lv, rgb = cell
            if flat:
                s.put(x, y, ch, ink or rgb)
                continue
            col = ink or rgb
            # brighter than the panes' own ramp: this layer is drawn *over* an already-finished frame,
            # so a sprite at the panels' weight reads as a dark grey smudge rather than as an aircraft.
            # The floor is 0.72 instead of 0.45 for that reason.
            s.put(x, y, ch, tuple(min(255, int(k * dim * (0.72 + 0.42 * lv / (len(SHADE) - 1))))
                                  for k in col))


def has(name: str) -> bool:
    spec = FILES.get(name)
    return bool(spec and (spec[0] / spec[1]).exists())


# ---------------------------------------------------------------- the events
#
# `t` is song time. Each entry is `(start, end, drawing, kwargs)`; `drawing` receives `(s, cols, rows,
# t, u)`. Everything inside is a function of `u`, so seeking lands on the same frame as playing.

def _undulate(cells, t: float, amp: float = 2.0, speed: float = 2.4, wavelength: float = 7.0):
    """The sprite with a travelling wave through it, for a manta ray swimming.

    Each column is shifted up or down by a sine whose amplitude is zero down the middle of the sprite and
    largest at its two edges, which is how a ray's wings actually move: the body holds its line and the
    tips flap. That the user asked for by name ("魔鬼鱼应该扰动摇摆移动") and it is also the difference
    between an animal and a decal - a photograph of a manta sliding across the frame is a sticker, and the
    same photograph rippling is a thing swimming.
    """
    grid, w, h = cells
    mid = (w - 1) / 2.0
    out = []
    for r in range(h):
        row = []
        for c in range(w):
            f = abs(c - mid) / max(1.0, mid)
            dy = int(round(math.sin(t * speed - c / wavelength * 2 * math.pi) * amp * f))
            sr = r - dy
            row.append(grid[sr][c] if 0 <= sr < h else None)
        out.append(tuple(row))
    return tuple(out), w, h


def fly(s, cols: int, rows: int, t: float, u: float, name: str, y: float, rows_n: int = 0,
        size: int = 0, body: int = 3, delay: float = 0.0, tilt: bool = False,
        caption: str = "", reverse: bool = False, dy: float = 0.0, wave: float = 0.0) -> None:
    """An aircraft crossing the frame, nose first, at the size the frame can carry.

    It enters and leaves *off* the screen, because the point of the effect is that the frame is a
    window rather than a box: at `u=0` the nose is past the right edge and at `u=1` the tail is past
    the left, so the crossing never looks like a sprite sliding inside a border.

    Four things were wrong with the first version and all four are the user's notes:

      * **the size was fixed** (52-60 cells) so the aircraft read as a smudge in a 197-cell frame; it is
        now a share of the frame unless a caller says otherwise;
      * **the direction was always left to right**, and every source photograph faces left, so all of
        them flew tail first. `FACES` + `_flip_for` mirror the sprite to match; `reverse` sends it the
        other way, and `dy` gives the crossing a vertical component so they are not all rails;
      * **`body` was doing the work of `size`** - see the note in `fly`'s history: two of the three
        aircraft came out identical because the event table passed the wrong keyword;
      * **the rows were whatever the caller said**, so a photograph whose subject fills its frame
        vertically was cropped to a letterbox. That is what the manta looked like - "魔鬼鱼…我没看出来"
        - so `rows_n = 0` now means "the rows this picture's own shape needs", and `_aspect` supplies
        them. The aircraft pass a number because for them the sky above and below is disposable.

    `wave` puts a travelling ripple through the sprite (`_undulate`) for the one thing in the set that
    swims rather than flies.
    """
    v = max(0.0, min(1.0, (u - delay) / max(1e-6, 1.0 - delay)))
    size = size or max(40, int(cols * 0.46))
    if rows_n <= 0:
        rows_n = max(6, int(round(size / (CELL_ASPECT * max(0.2, _aspect(name))))))
    rows_n = max(6, rows_n)
    body = body or max(3, rows_n // 3)
    dx = -1.0 if reverse else 1.0
    cells = sprite(name, size, rows_n, flip=_flip_for(name, dx))
    if not cells:
        return
    if wave:
        cells = _undulate(cells, t, amp=max(1.0, wave * cells[2] * 0.11))
    span = (size + cols) * v - size
    x = int(cols - size - span) if reverse else int(span)
    yy = int(rows * y + dy * (v - 0.5) * rows)
    if tilt:
        yy += int(math.sin(v * math.pi) * 4)          # a shallow climb, out and back
    grid, w, h = cells
    # thin the rows outside the fuselage, then blit: done here rather than in `paste` so the rule stays
    # with the thing it is about
    mid = h // 2
    thin = []
    for r in range(h):
        row = []
        for cell in grid[r]:
            if cell is None or abs(r - mid) <= body // 2:
                row.append(cell)
            else:
                ch, lv, rgb = cell
                row.append((ch, max(0, lv - 1), rgb))
        thin.append(tuple(row))
    paste(s, (tuple(thin), w, h), x, yy)
    trail = max(0, min(16, int(16 * (1 - abs(v - 0.5) * 2) + 5)))
    for k in range(trail):
        tx = x + w + 2 + k * 2 if reverse else x - 2 - k * 2
        if 0 <= tx < cols:
            s.put(tx, yy + mid, "\u00b7" if k % 2 else "\u2500",
                  (70 - k * 3, 170 - k * 7, 220 - k * 6))
    if caption and 0 <= x <= cols - len(caption) - 2:
        s.put(x, min(rows - 1, yy + h + 1), caption, (160, 205, 245))


def dive(s, cols: int, rows: int, t: float, u: float, name: str, x: float = 0.5,
         size: int = 0, caption: str = "", up: bool = False) -> None:
    """A vertical crossing: down the frame (or up it) instead of across it.

    A helicopter descending is the one aircraft in the set that reads better vertically than
    horizontally - its rotor disc is a horizontal line either way, and a descent is what a helicopter
    is *for* in a film about an air force. It enters above the top edge and leaves past the bottom.
    """
    size = size or max(36, int(cols * 0.34))
    rn = max(10, int(size * 0.5))
    face = "h" if x > 0.5 else ""
    cells = sprite(name, size, rn, flip=face)
    if not cells:
        return
    _, w, h = cells
    xx = int(cols * x - w / 2)
    yy = int(rows + h - (rows + 2 * h) * (1.0 - u) - h) if up else int(-h + (rows + 2 * h) * u)
    paste(s, cells, xx, yy)
    for k in range(6):                                   # a rotor wash, so it is not just a slide
        bx = xx + w // 2 + int(math.sin(t * 3 + k) * (6 + k))
        by = yy + h - 2 if not up else yy + 2
        if 0 <= bx < cols and 0 <= by < rows:
            s.put(bx, by, "\u02dc", (140, 180, 220 - k * 10))
    if caption:
        s.put(max(0, min(cols - len(caption) - 1, xx + w // 2)), rows - 1, caption,
              (160, 205, 245))


def approach(s, cols: int, rows: int, t: float, u: float, name: str, x: float = 0.5,
             y: float = 0.55, size: int = 0, caption: str = "") -> None:
    """Flying at the camera: a speck that grows until the frame is full of it.

    The one direction the set of photographs can actually support for a head-on aircraft, because it
    never has to *point* anywhere: the sprite is scaled from eight percent of the frame to seventy, and
    the eye reads the growth as approach. The user asked for exactly this ("可以由小至大向屏幕方向飞").
    """
    s0 = max(5, int(cols * 0.07))
    s1 = size or max(40, int(cols * 0.72))
    sz = int(s0 + (s1 - s0) * (u ** 1.7))
    rn = max(3, int(sz * 0.42))
    cells = sprite(name, sz, rn)
    if not cells:
        return
    _, w, h = cells
    xx = int(cols * x - w / 2 + math.sin(u * 4.0) * 3)
    yy = int(rows * y - h / 2 + math.cos(u * 3.0) * 2)
    paste(s, cells, xx, yy)
    if caption and u < 0.8:
        s.put(max(0, min(cols - len(caption) - 1, xx + w // 2)), min(rows - 1, yy + h + 1), caption,
              (160, 205, 245))


def sweep(s, cols: int, rows: int, t: float, u: float, name: str, rows_n: int = 14,
          size: int = 0, caption: str = "") -> None:
    """A diagonal crossing from the bottom right, for the second plane of a pair."""
    size = size or max(36, int(cols * 0.36))
    cells = sprite(name, size, rows_n, flip=_flip_for(name, -1.0))
    if not cells:
        return
    x = int((cols + size) * (1 - u) - size)
    y = int((rows + rows_n) * (1 - u) * 0.7 + rows * 0.05)
    paste(s, cells, x, y)
    if caption and 0 <= x <= cols - len(caption) - 2:
        s.put(x, max(0, y - 1), caption, (240, 180, 90))


def flash(s, cols: int, rows: int, t: float, u: float, name: str, cols_n: int = 0,
          rows_n: int = 0, dim: float = 1.0, caption: str = "", behind: bool = False,
          contrast: float = 0.0, zoom: float = 0.0, fill: float = 0.62, x: float = 0.5,
          y: float = 0.5) -> None:
    """A picture landing over the whole frame, growing in and fading out.

    The scale is on `u` and the fade is on `u` too, so it arrives fast, holds, and goes - a hit rather
    than a slideshow. `behind` dims it heavily, which is what a picture used as a backdrop under the
    chat window needs.

    `dim` and `contrast` exist because "behind" is not one setting. The library at the close is behind
    the last two lines of dialogue, and at the 0.42 the backdrop used to get it was invisible - the user:
    "图书馆我都没看出来" - so a caller can hold it at 0.62, and hold its contrast up, while the reading
    text is still on top.

    **The picture is fitted to the box, not cropped to it**, and that is a fix rather than a tidy-up:
    `sprite` centre-crops, which is right for a photograph in a frame and wrong for a whole picture. The
    crest is square and the default box is 62 % of the frame, so two thirds of the crest - the ring with
    the university's name on it - was being cut away, and what was left read as a striped ball. The box
    is now a bound: `_fit_box` returns the largest rect of the picture's own aspect that fits inside it.

    `zoom` is the walk-in, and it is the user's: "校门可以逐渐放大，拟态'我'走进校门的过程". With `zoom=0.2`
    the picture starts at a fifth of its final size and grows for the *whole* event instead of being
    full size in a third of a second, and the growth eases in (`u ** 1.35`) the way a gate grows when you
    walk at it: slowly from far off, fast at the end.

    `fill` is how much of the frame the picture may take, and it is allowed to be **more than one**: the
    user's "校门放大至超出屏幕" is `fill=1.45`, i.e. the gate ends up wider and taller than the terminal
    and is clipped by it, which is the difference between looking at a gate and standing in it. `x` and
    `y` are where it sits (`0.5` centred, `0.0` against the left or the header, `1.0` against the right
    or the footer) - the library needs them because "图书馆放在左下角", and a backdrop that covers the
    lyrics is not a backdrop any more.
    """
    if zoom > 0.0:
        z = zoom + (1.0 - zoom) * min(1.0, u) ** 1.35
        steps = ZOOM_STEPS
    else:
        z = min(1.0, u * 3.2)
        steps = GROW_STEPS
    # ...quantised, because `sprite` is cached per size and a grow that changes every frame decodes the
    # whole PNG every frame. Measured on the opening flash (`_dev/opening_probe.py`): 80-90 ms a frame for
    # the first second and a half of the song, which is the first thing anyone sees. Four steps is smooth
    # at 24 fps and it gives `warm` four sizes to decode before the music starts instead of twenty. A
    # walk-in needs more than four or it arrives in visible jumps: `ZOOM_STEPS` is the compromise, and
    # `warm` samples fourteen points across every event, so every size it can ask for is decoded before
    # the first note.
    z = math.ceil(z * steps) / steps
    fade = 1.0 if u < 0.72 else max(0.0, 1.0 - (u - 0.72) / 0.28)
    if fade <= 0.02:
        return
    bw = cols_n or max(20, int(cols * fill))
    bh = rows_n or max(6, int(rows * fill))
    cw, ch = _fit_box(name, bw, bh, z)
    cells = sprite(name, cw, ch, contrast=contrast or (0.75 if behind else 1.0))
    if not cells:
        return
    _, w, h = cells
    # anchored, not clamped: a picture larger than the frame has to stay *centred* on the frame rather
    # than be pushed against its left edge, or "bigger than the screen" reads as "off to one side"
    x0 = int((cols - w) * x)
    y0 = int((rows - h) * y)
    paste(s, cells, x0, y0, dim=dim * (0.42 if behind else 1.0) * fade)
    if caption:
        s.put(max(1, (cols - len(caption)) // 2), min(rows - 1, max(0, y0) + min(h, rows) + 1), caption,
              tuple(int(k * fade) for k in (255, 210, 120)))


def _fit_box(name: str, bw: int, bh: int, z: float = 1.0) -> tuple[int, int]:
    """The largest rect of `name`'s own aspect that fits `bw`x`bh`, scaled by `z`. See `flash`."""
    a = max(0.15, _aspect(name)) * CELL_ASPECT
    w = max(4, bw)
    h = max(2, int(round(w / a)))
    if h > bh:
        h = max(2, bh)
        w = max(4, int(round(h * a)))
    return max(4, int(w * z)), max(2, int(h * z))


@lru_cache(None)
def _aspect(name: str) -> float:
    """The source picture's own width/height, or 1.0 if it cannot be read.

    Needed because a sprite is requested in *cells*, and a cell is `CELL_ASPECT` times taller than it is
    wide: a caller that wants the whole picture undistorted cannot ask for a shape in the picture's own
    proportions. `stand()` asked for 0.62 of the height in width, which for a 463x651 figure is a
    twenty-seven-cell column - so `sprite` cropped the picture to the middle seventh of its width and
    the full body came out as a vertical smear of horizontal streaks.
    """
    spec = FILES.get(name)
    if spec is None:
        return 1.0
    try:
        with _OPEN(spec[0] / spec[1]) as im:
            w, h = im.size
        return w / max(1.0, float(h))
    except Exception:
        return 1.0


def stand(s, cols: int, rows: int, t: float, u: float, name: str, side: str = "right",
          size: int = 0, caption: str = "") -> None:
    """A figure standing at the edge of the frame, half out of it, **moving on the beat**.

    The chat window has always shown 航小天's *face* - a crop, at sixteen cells across, because that is
    what an avatar is. The user's note was that the full body never appears anywhere. This is that: the
    whole figure as half-block art, at the size of the frame, stepping in from an edge and standing
    there while the last lines play.

    ...and then this batch: "后面部分有航小天大图的部分，我希望航小天随音乐节奏上下跃动". So the figure
    hops: `FP.pulse` is the film's own beat detector (1 on the beat, decaying over 140 ms), and the hop is
    that pulse raised to a power - a sharp rise and a soft landing rather than a sine wave, which is what
    a body does. `breathe` stays underneath it, so the figure is alive between the beats too, and the
    landing is a small extra dip so the hop reads as weight rather than as a slide.

    `side` is which edge it is standing at; the figure is cropped by the frame rather than scaled to fit
    it, which is the whole difference between a sprite and a person standing there.
    """
    h = size or max(14, int(rows * 0.86))
    w = max(8, int(h * CELL_ASPECT * _aspect(name)))
    cells = sprite(name, w, h)
    if not cells:
        return
    _, cw, chh = cells
    breathe = int(round(math.sin(t * 1.1) * 1.2))
    rise = int((1.0 - min(1.0, u * 2.4)) * (chh * 0.5))          # steps up into place and settles
    p = FP.pulse(t)                                              # 1 on the beat, 0 between them
    hop = int(round((p ** 1.5) * max(2, chh * 0.11)))
    landing = int(round((p ** 0.5) * 1.5)) if p < 0.25 else 0     # the dip just after the beat
    x = cols - cw - 6 if side == "right" else 6
    y = rows - chh + rise // 2 + breathe - hop + landing
    paste(s, cells, x, y)
    if caption and 2 <= x <= cols - len(caption) - 3:
        s.put(x, max(0, y - 1), caption, (255, 220, 150))


def emerge(s, cols: int, rows: int, t: float, u: float, name: str, caption: str = "") -> None:
    """A picture growing out of a single point, for the frame after everything has collapsed.

    The film's `shot_collapse` (174.90-177.50) draws itself full-bleed - the picture squeezes into a line
    and then a dot - and the school variant draws no pane behind it, so for two and a half seconds the
    column is the film's own black. The user's suggestion was to bridge it: let the crest grow *from that
    dot*, so the collapse has an ending instead of a hole. `u` scales it from one cell to full size with
    a fade-in, and it is drawn over the collapsed frame rather than in a pane, because the pane is exactly
    what is not there.
    """
    grow = min(1.0, u * 1.5)
    fade = min(1.0, u * 3.0)
    # A mark, not a plate: the user's "校门、校徽的大图出现了多次，仅保留第一次" leaves this one drawing the
    # bridge out of the collapse, and at the 0.34x0.44 it used to reach it was a *third* big crest. At
    # 0.19x0.26 it grows to 37x13 cells at 197x52 - recognisably the emblem, unambiguously not a hit.
    cw = max(1, int(cols * 0.19 * grow))
    ch = max(1, int(rows * 0.26 * grow))
    cells = sprite(name, cw, ch, contrast=0.9)
    if not cells:
        return
    _, w, h = cells
    paste(s, cells, max(0, (cols - w) // 2), max(0, (rows - h) // 2 - 1), dim=fade)
    if caption and u > 0.55:
        s.put(max(1, (cols - len(caption)) // 2), min(rows - 1, (rows + h) // 2 + 1),
              caption, tuple(int(k * fade) for k in (220, 230, 255)))


def glyphs(s, cols: int, rows: int, t: float, u: float, name: str, art: str) -> None:
    """A piece of supplied character art, printed over the frame and lit line by line.

    `猫学长_字符画.txt` is *already* terminal art - eleven lines - so it is printed rather than
    characterised. The lines arrive from the top down, which is how a cat reads best: from its ears.

    何尊 used to come through here too, from `何尊_字符画.txt`. It does not any more: the user's note was
    that the vessel's character art is not good enough and that they had drawn an SVG of it to use
    instead, so it is characterised from the vector like everything else on screen (`plate` below).
    """
    lines = [ln for ln in art.splitlines() if ln.strip()]
    w = max(len(ln) for ln in lines) if lines else 0
    x = max(0, (cols - w) // 2)
    y0 = max(0, (rows - len(lines)) // 2)
    shown = int(len(lines) * min(1.0, u * 1.6))
    for i, ln in enumerate(lines[:shown]):
        s.put(x, min(rows - 1, y0 + i), ln.replace("$", " "), (150, 170, 200))


def plate(s, cols: int, rows: int, t: float, u: float, name: str, cols_n: int = 0, rows_n: int = 0,
          caption: str = "", dim: float = 1.0) -> None:
    """A campus work drawn over the whole frame as character art, lit from the top down.

    The same three routes the panes use (`school_sculpture`: half-block for a photograph, strokes for a
    line drawing, silhouette for a white solid), at frame size rather than pane size - so the vessel the
    user supplied as an SVG is on screen as the *drawing*, not as a text file somebody typed.
    """
    import school_sculpture as SC
    cw = cols_n or max(24, int(cols * 0.40))
    ch = rows_n or max(10, int(rows * 0.82))
    if name in SC.HTML_ART:
        # the supplied page, as supplied: 100x52 cells, which is the frame's own height. `field=True`
        # keeps its paper as a dim field of its own digits - the vessel out of a field of binary.
        got = SC.html_cells(name, cw, ch, field=True)
    elif name in SC.DIGITS:
        # the page's own look at frame size: the digit field, paper included (see `digit_cells`)
        got = SC.digit_cells(name, cw, ch, phase=t, field=True)
    elif name in SC.SILHOUETTE:
        got = SC.silhouette_cells(name, cw, ch)
    elif name in SC.LINE:
        got = SC.stroke_cells(name, cw, ch)
    else:
        got = None
    if got is None:
        hb = SC.halfblock(name, cw, ch)
        if hb is None:
            return
        (block, colour), cw, ch = hb
        from school_courses import SHADE
        ink = (196, 208, 228)
        shown = int(ch * min(1.0, u * 1.6))
        ox, oy = max(0, (cols - cw) // 2), max(0, (rows - ch) // 2)
        for r in range(shown):
            for c in range(cw):
                top, bot = block[r][c]
                if top is None and bot is None:
                    continue
                col = colour[r][c] or ink
                s.put(ox + c, oy + r, "\u2580" if top is not None else SHADE[1],
                      tuple(int(v * dim) for v in col))
    else:
        cells, cw, ch = got
        shown = int(ch * min(1.0, u * 1.6))
        ox, oy = max(0, (cols - cw) // 2), max(0, (rows - ch) // 2)
        for r in range(shown):
            for c in range(cw):
                cell = cells[r][c]
                if cell is None:
                    continue
                ch_, lv = cell
                s.put(ox + c, oy + r, ch_, tuple(int(v * dim * lv / 255) for v in (176, 206, 245)))
    if caption and u > 0.35:
        s.put(max(1, (cols - len(caption)) // 2), min(rows - 1, (rows + ch) // 2 + 1), caption,
              (255, 210, 120))


@lru_cache(None)
def _ink_share(name: str) -> tuple[float, float, float]:
    """How much of a sprite's own rectangle its *subject* fills: `(w, h, centre y)` as fractions.

    Every photograph in `assets/` is a cut-out with sky, paper or floor around the subject, and the
    sprite is the whole frame. "运-20 到达屏幕中间时需要占据全屏 2/3" was therefore never satisfied by
    asking for a sprite two thirds of the frame wide: the aircraft inside that sprite is about 62 % of
    its width, so the thing on screen was two fifths of the frame - measured, not guessed, which is what
    `_dev/measure_art.py` exists for. This says what the *subject* occupies, and where its middle is, so
    a caller can size and place the subject rather than the box around it.
    """
    for cols, rows in ((140, 48), (90, 30), (50, 18)):
        cells = sprite(name, cols, rows)
        if not cells:
            return (1.0, 1.0, 0.5)
        grid, w, h = cells
        xs = [x for row in grid for x, c in enumerate(row) if c is not None]
        ys = [y for y, row in enumerate(grid) for c in row if c is not None]
        if xs and ys:
            return ((max(xs) - min(xs) + 1) / float(w),
                    (max(ys) - min(ys) + 1) / float(h),
                    ((min(ys) + max(ys)) / 2.0) / float(h))
    return (1.0, 1.0, 0.5)


def lowpass(s, cols: int, rows: int, t: float, u: float, name: str, y: float = 0.42,
            peak: float = 1.45, caption: str = "", wave: float = 0.0, cover: float = 0.66) -> None:
    """A low pass: the aircraft comes over the frame, is biggest in the middle of it, and goes.

    The user asked for this one three times now - "运20需要展示掠空的冲击效果，其到达屏幕中间时需要占据全屏
    2/3", then "运20 我之前要求大图掠空，但现在依旧不够大，请让其在屏幕中间时至少覆盖2/3的全屏幕", and then
    "运20视觉冲击还是不够，让其更大，允许超出屏幕". So it is not a fraction of the frame and it is not a
    coverage either: it is **both**, and the bigger of the two wins.

      * `cover` solves the size that makes the aircraft's own ink cover that share of the frame's *area* -
        the measurement that proved the first two attempts were drawing a thin band (see `_ink_share`);
      * `peak` is now how much *wider than the frame* the sprite may be (1.45 of it, the same as the gate's
        `fill`), and the sprite is clipped by the frame on both sides - which is the whole point of a low
        pass: at the centre you are under it, not looking at a picture of it.

    At 197x52 that is 285 cells of sprite, 90 rows of it, and a hull about 49 rows tall - taller than the
    frame's mid-band and wider than the screen, on a shallow diagonal, with the frame shaking.

    It crosses on a shallow diagonal rather than a rail, and while it is over the frame the frame takes
    the hit: an expanding ring off the hull, a shock line across the whole width at its altitude, dust
    coming up off the floor, and the screen shake that `tui_live.fx_shake` asks this module for (`shock`).
    None of that is a function of anything but `u`, so a seek lands on the frame playing would.
    """
    near = math.sin(max(0.0, min(1.0, u)) * math.pi)              # 0 at the edges of the pass, 1 at the centre
    # ...and the size is quantised, for the same reason `flash`'s is: `sprite` is cached per size, so a
    # pass whose size changes every frame decodes the whole PNG every frame. Measured over 11.8-12.9 s of
    # the low pass: every frame 95-100 ms, against a 41.7 ms budget.
    frac = math.ceil((0.34 + 0.66 * near ** 0.7) * PASS_STEPS) / PASS_STEPS
    share_w, share_h, ink_cy = _ink_share(name)
    aspect = max(0.2, _aspect(name))
    # the sprite width whose *ink* covers `cover` of the frame's area - see the docstring
    want = math.sqrt(max(1e-6, cover * cols * rows * CELL_ASPECT * aspect
                         / max(0.05, share_w * share_h)))
    # ...and the frame may also simply be overflowed, which is the biggest of the two ("让其更大，允许超出屏幕")
    size = max(16, int(max(want, cols * peak) * frac))
    if wave:
        # kept for symmetry with `fly`: a boat, not a plane, if one is ever put on this path
        pass
    rn = max(6, int(round(size / (CELL_ASPECT * aspect))))
    cells = sprite(name, size, rn, flip=_flip_for(name, 1.0))
    if not cells:
        return
    _, w, h = cells
    x = int((cols + w) * u - w)
    # placed by its *ink*, not by its box: at the peak this sprite is taller than the frame, and what has
    # to be at `y` is the aircraft rather than the sky above it
    yy = (int(rows * y - h * ink_cy) + int((0.5 - u) * rows * 0.20))   # a shallow diagonal, not a rail
    paste(s, cells, x, yy, fast=True)
    cx, cy = x + w // 2, yy + h // 2
    d = abs(u - 0.5) / 0.34                                       # 0 at the centre, 1 at the edge of the hit
    if d < 1.0:
        q = 1.0 - d
        r = 4 + int(30 * d)
        # the ring off the hull: an ellipse, because a cell is CELL_ASPECT times taller than it is wide
        if 0 < r < cols:
            for a in range(40):
                ang = a / 40.0 * 2 * math.pi
                rx, ry = cx + int(r * CELL_ASPECT * math.cos(ang)), cy + int(r * math.sin(ang))
                if 0 <= rx < cols and 0 <= ry < rows:
                    s.put(rx, ry, "\u00b7" if a % 2 else "\u2500",
                          _mix((150, 205, 245), 0.45 + 0.55 * q))
        # the shock itself: the line the aircraft drags across the frame, at its own altitude
        if q > 0.25:
            for xx in range(0, cols, 2):
                s.put(xx, cy, "\u2500", _mix((120, 175, 225), 0.35 + 0.5 * q))
        if d < 0.5:                                               # dust off the floor, only near the centre
            for i in range(10):
                dx_ = cx + int((i - 5) * (cols / 14.0))
                dy_ = rows - 1 - (i * 3 % 5)
                if 0 <= dx_ < cols and 0 <= dy_ < rows:
                    s.put(dx_, dy_, "\u2591", _mix((170, 190, 215), 0.5))
    if caption and 0 <= x <= cols - len(caption) - 2:
        s.put(x, min(rows - 1, yy + h + 1), caption, (170, 215, 250))


# the windows in which this variant shakes its own frame, as (start, end, strength). `tui_live.fx_shake`
# owns the shake itself - the film's own trigger is `alert_own == "err"` or a shot in `SHAKE_SHOTS` - and
# asks for this so the variant does not need a second copy of the same pass over the buffer.
SHOCKS: list[tuple[float, float, float]] = []


def shock(t: float) -> float:
    """How hard this variant is shaking the frame at `t`, 0..1. Hardest in the middle of a window."""
    k = 0.0
    for a, b, s in SHOCKS:
        if a <= t < b and b > a:
            k = max(k, s * math.sin(math.pi * (t - a) / (b - a)))
    return k


# ---------------------------------------------------------------- 航小天 打篮球
#
# The user's `参考及想法/hangxiaotian.json`: 32 frames of 航小天 dribbling and dunking, 70x40 cells at
# 14 fps, looping ("图片里的航小天打篮球动图字符画数据"). It is not an image like everything else in this
# module - it is already character art, with a colour for each cell - so it is drawn rather than
# characterised, and it brings its own clock: the animation is a function of *song* time, so a seek lands
# on the frame playing would.
BASKET = ASSETS / "\u822a\u5c0f\u5929\u7bee\u7403.json"
BASKET_FPS = 14.0
# the picture's paper, as a terminal panel. `#e5e5e5` at 72 % with the cast `_panel` applies - see the
# note in `dunk` for why it is dimmed at all and why it is not the film's near-black either
PAPER = (229, 229, 229)
PANEL_DIM = 0.65
PANEL_TINT = (0.94, 0.98, 1.08)
# The panel is made of *glyphs*, never spaces, and this is a layering fix rather than a style: the
# film's trail writes a ghost into every cell whose character is a space (`tui_live.fx_trail`), so a
# panel made of 3000 spaces has 3000 cells that the previous frame can be drawn back into. `█` in the
# paper's own colour is the same rectangle with nothing in it for that pass to find.
PAPER_CH = "\u2588"
PAPER_COL = (139, 145, 160)               # `_panel(PAPER)`, precomputed: it is written 3000 times a frame


@lru_cache(None)
def basket_frames():
    """`[(cells, w, h)]` for the whole animation, parsed once. `[]` if the file is not there.

    Each cell is `(char, level, fg, bg)`: the character the artist put there, how much ink it carries
    (0-4, or **-1 for the paper**), and the two colours `_cells` writes, already resolved through
    `_panel`. `_dev/basket_view.py` is the tool that settled how they are resolved; the paragraphs below
    are what it found.

    What the file is, measured rather than assumed:

      * the characters carry the shade. `contentString` is 40 lines of 70, and its 45 distinct symbols
        are ordered - `&` and `8` at grey 238, `J` and `U` at 153 - so a cell with no colour of its own
        still has one, taken as the mean of that character's cells over the whole file;
      * `colors['background']` (2761 cells) is the paper `#e5e5e5` plus `#ffffff` and 436 cells of
        `#7f7f7f` shadow; `colors['foreground']` (1204) is the **drawing**: `#99CCFF` and `#333366` for
        the suit, `#663333` for the ball, `#CCCCCC` for its lit side. 1165 cells are in both, so the
        merge keeps foreground last;
      * so the picture is **dark on light**, and this is 航小天 - the file renders, as its author drew
        it, as a readable figure. The first version of this inverted it (paper dropped, figure bright on
        the film's dark ground, browns sent to the amber) and the user's report was that the animation
        had vanished: "\u822a\u5c0f\u5929\u6253\u7bee\u7403\u52a8\u56fe\u5b8c\u5168\u4e0d\u89c1\u4e86". It had not - 953 cells of a sketch
        were on screen every frame - but a figure whose paper is gone is 1200 scattered cells of letters
        on black, and nobody can read that. Inverting the luminance also threw away the figure's *light*
        half, which is a third of it.

    The frames are all 70x40 and the figure moves across the whole sheet over the 32 frames - the
    per-frame ink boxes run from (0,0,56,39) to (21,4,61,39) - so there is no margin to crop to.
    """
    import json
    if not BASKET.exists():
        return []
    try:
        data = json.loads(BASKET.read_text(encoding="utf8"))
    except Exception:
        return []
    frames = data.get("frames") or []

    def paints(fr):
        out = {}
        for key in ("background", "foreground"):
            d = fr.get("colors", {}).get(key)
            d = json.loads(d) if isinstance(d, str) else (d or {})
            for k, hexv in d.items():
                if isinstance(hexv, str) and len(hexv) == 7:
                    out[k] = hexv
        return out

    shades: dict[str, list[int]] = {}
    for fr in frames:
        lines = (fr.get("contentString") or "").splitlines()
        for key, hexv in paints(fr).items():
            x, _, ys = key.partition(",")
            try:
                xi, yi = int(x), int(ys)
            except ValueError:
                continue
            if yi < len(lines) and xi < len(lines[yi]):
                ch = lines[yi][xi]
                shades.setdefault(ch, []).append(sum(int(hexv[i:i + 2], 16) for i in (1, 3, 5)) // 3)
    mean = {k: sum(v) // len(v) for k, v in shades.items()}
    out = []
    for fr in frames:
        lines = (fr.get("contentString") or "").splitlines()
        pm = paints(fr)
        rows = []
        for y, ln in enumerate(lines):
            row = []
            for x, ch in enumerate(ln):
                hexv = pm.get(f"{x},{y}")
                if isinstance(hexv, str) and len(hexv) == 7:
                    rgb = tuple(int(hexv[i:i + 2], 16) for i in (1, 3, 5))
                else:
                    g = mean.get(ch, 90)
                    rgb = (g, g, g)
                ink = 1.0 - (rgb[0] + rgb[1] + rgb[2]) / 765.0
                if rgb[0] > 222 and rgb[1] > 222 and rgb[2] > 222:
                    # the paper: level -1, and it keeps its own colour, because the panel is drawn *lit*
                    # (`_cells`) - the paper is the panel's ground and the figure is drawn on it. Keyed on
                    # the colour rather than on a luminance threshold: the figure's own light half
                    # (`#CCCCCC`, 38 % of its cells) is only a little darker than the paper, and a
                    # threshold throws it away.
                    ground = _panel(rgb, 1.0)
                    row.append((ch, -1, _panel(rgb, 0.84), ground))
                    continue
                # `(char, level, fg, bg)`, final: the level is how much ink the cell carries, and the two
                # colours are what `_cells` writes. They are computed *here*, once per file, because the
                # alternative is 2800 of them per frame in the middle of the song.
                body = _panel(rgb, 1.0)
                row.append((ch, int(round(4 * min(1.0, ink * 1.2))),
                            tuple(int(k * 0.55) for k in body), body))
            rows.append(tuple(row))
        out.append((tuple(rows), max(len(r) for r in rows), len(rows)))
    return out


def _fit_cells(grid, w: int, h: int, bw: int, bh: int):
    """Scale a cell grid down to fit a `bw`x`bh` box, uniformly, keeping the drawing whole.

    This replaced a centre crop, and the reason is the 120-column window: the box there is 60x16, the
    art is 45x38, and the crop kept the middle sixteen rows - the torso and the arms, with the head cut
    off above and the ball below. A crop is right for a *photograph*, where the middle of the subject is
    the subject; character art is drawn to be looked at as a whole.

    Scaling down a *line* drawing by sampling a cell out of each block does not work either, and that is
    the one thing the first version of this got wrong: 526 ink cells in 2800, sampled one in six, come
    out as scattered dots - a figure of floating letters, which is worse than the crop it replaced. So a
    block contributes the **most inked** of its cells rather than its middle one. Lines stay lines, the
    ball stays a mass, and the drawing survives the reduction - the same reason a mipmap of a drawing is
    built with a maximum rather than an average.
    """
    k = max(w / max(1, bw), h / max(1, bh), 1.0)
    if k <= 1.0:
        return grid, w, h
    nw, nh = max(1, int(w / k)), max(1, int(h / k))
    rows = []
    for r in range(nh):
        y0, y1 = int(r * h / nh), max(int(r * h / nh) + 1, int((r + 1) * h / nh))
        row = []
        for c in range(nw):
            x0, x1 = int(c * w / nw), max(int(c * w / nw) + 1, int((c + 1) * w / nw))
            best = None
            for y in range(y0, min(y1, h)):
                srow = grid[y]
                for x in range(x0, min(x1, w)):
                    cell = srow[x]
                    if cell is not None and (best is None or cell[1] > best[1]):
                        best = cell
            row.append(best)
        rows.append(tuple(row))
    return tuple(rows), nw, nh


def dunk(s, cols: int, rows: int, t: float, u: float, box: tuple, caption: str = "") -> None:
    """One frame of the basketball animation, in the rect `box` - the chat window it covers.

    **It is drawn by `tui_live.draw_body`, not by `draw`**, and that is the fix for the user's second
    report about it: "我实际测了，我确定看不到打篮球面板 ... 在我这里打篮球面板似乎不在最上层". It used to be an
    ordinary event on `EVENTS`, i.e. drawn in the full-frame layer *after* `draw_body` - which put the
    window's own picture one layer above the window and left it to survive everything the film's post
    does afterwards (`fx_reveal` holds the previous frame cell by cell, `fx_trail` writes a ghost into
    every cell that is a **space**, `fx_shake` rotates rows). A panel made of spaces is a panel with
    3000 free cells in it, and any of those passes can put something back on top of it. So:

      * the box is passed in by the caller that computed it - `draw_body` - instead of being read back
        out of `tui_live.LEFT_BOX`, so the panel cannot be drawn at a stale or degenerate rect;
      * it is drawn with the window, in the window's layer, so the layering question does not arise;
      * **its cells are glyphs, never spaces** (`█` in the paper's own colour): the trail's ghost rule
        keys on `buf[y][x][0] == " "`, and a panel with no spaces in it cannot be drawn on.

    `box` is `(x0, y0, x1, y1)` inclusive; the panel fills it, so the conversation underneath is
    covered rather than read through.

    The frame index is `int(t * 14) % 32`: continuous in song time (so a seek lands where playing would)
    and exactly five loops over the eleven and a half seconds the event is given, which is 160 frames at
    14 fps.
    """
    frames = basket_frames()
    if not frames:
        return
    grid, w, h = frames[int(t * BASKET_FPS) % len(frames)]
    bx0, by0, bx1, by1 = box
    bw, bh = max(1, bx1 - bx0 + 1), max(1, by1 - by0 + 1)
    if bw < 12 or bh < 5:                     # a degenerate rect: nothing legible fits, draw nothing
        return
    # The window is *covered*, not layered over: without this the chat text behind the art reads
    # through the gaps between its cells and the two compete. The user asked for it over the
    # conversation box, so the box first becomes a panel - and the panel is the art's own paper, so
    # the drawing sits in a picture rather than on a rectangle of its own. `fill` and not a loop of
    # `put`s: the box is 3300 cells and `put` is a method call with a `CLEAR` lookup in it, which at
    # 197x52 was 12 ms of the frame - a quarter of the whole budget for a flat rectangle.
    s.fill(bx0, by0, bx1, by1, PAPER_CH, PAPER_COL, PAPER_COL)
    # Fit rather than crop: the figure is the whole sheet and it moves across it, so a shorter box
    # scales it down instead of losing the head. See `_fit_cells`.
    grid, w, h = _fit_cells(grid, w, h, bw, bh)
    ox = bx0 + max(0, (bw - w) // 2)
    oy = by0 + max(0, (bh - h) // 2)
    _cells(s, grid, w, h, ox, oy, bx0, by0, bx1, by1)
    if caption:
        # a *dark* amber, not the film's `(255,220,150)`: this caption is the one in the film that
        # sits on the picture's own paper rather than on the film's ground, and pale amber on light
        # grey is the one colour pair that cannot be read.
        s.put(max(bx0 + 1, min(bx1 - len(caption) - 1, ox + (w - len(caption)) // 2)),
              min(by1, by0 + 1), caption, (118, 72, 16))


def window_fx(s, cols: int, rows: int, t: float, box: tuple) -> int:
    """Draw whatever the score gives the chat window at `t`, into `box`. Returns how many drew.

    The window's own layer, called by `tui_live.draw_body` right after the window's contents - which is
    what makes the panel impossible to bury. `warm` plays the same table, so the file's parse cost is
    paid before the music like every other sprite's.
    """
    n = 0
    for start, end, fn, kw in WINDOW_EVENTS:
        if not (start <= t < end):
            continue
        u = (t - start) / max(1e-6, end - start)
        try:
            fn(s, cols, rows, t, u, box=box, **kw)
            n += 1
        except Exception:
            pass
    return n


# Events that belong to the *chat window* rather than to the frame. `draw_body` draws them, in the same
# layer as the window they cover - see the note in `dunk`. They are declared here, after `dunk`, because
# the table holds the function itself.
WINDOW_EVENTS: list[tuple[float, float, object, dict]] = [
    (58.65, 70.08, dunk, dict()),
]


def _panel(rgb, f: float = 1.0):
    """The art's own colour, dimmed and given the panel's slight cool cast.

    The cast is small (blue up 8 %, red down 6 %) and it is there so a light rectangle in a film of
    `(4,7,15)`, `(150,170,210)` ink and amber captions reads as *this* film's picture rather than as a
    window that lost its theme.
    """
    return tuple(max(0, min(255, int(k * f * PANEL_DIM * t))) for k, t in zip(rgb, PANEL_TINT))


def _cells(s, grid, w: int, h: int, ox: int, oy: int, bx0: int, by0: int, bx1: int, by1: int) -> None:
    """Write a basket frame's cells: the paper as a light ground, the figure as a mass on top of it.

    Two things here are not obvious and both were found by rendering the art on its own
    (`_dev/basket_view.py`):

      * a cell's **background** is what makes the figure a figure. Drawing the figure's cells as glyphs
        on the paper gives 1200 separate characters - the drawing is there and cannot be seen, because
        what the eye needs is the *mass*. So each figure cell carries its own colour as the background
        and a darkened version of it as the glyph: a solid, detailed shape instead of a scatter of
        letters.
      * the paper is kept, as the light ground, and this is the other half of it. The paper is what the
        figure is darker *than*; without it there is nothing for the eye to compare against, which is
        what "the animation is gone" was.

    `paste` cannot do either - it sets a foreground colour per cell and leaves the background alone,
    which is right for every other sprite in this module (they are keyed cut-outs with no paper). The
    colours arrive already resolved from `basket_frames`, so this writes the cell straight into the
    buffer: 2800 cells through `put` measured about 10 ms of a 41.7 ms frame (36.4 ms for this frame
    against 26.9 ms for the worst frame in the song afterwards), and there is nothing `put` does here
    that is wanted - no wide characters, no `CLEAR` span to honour, and no vignette on a picture that is
    already showing its own paper.
    """
    buf, wide = s.buf, s.wide
    for r in range(h):
        y = oy + r
        if y < by0 or y > by1:
            continue
        row, wrow = grid[r], buf[y]
        wrowf = wide[y]
        for c in range(w):
            x = ox + c
            if x < bx0 or x > bx1:
                continue
            # the two cells a wide glyph occupies are disowned at the panel's own edges: the box fill
            # covers the middle, but a CJK character straddling the border would otherwise keep half of
            # itself on screen (`Screen._unpair`)
            if x == bx0 and x > 0 and wrowf[x] and wrow[x][0] == "":
                wrow[x - 1] = (" ", wrow[x - 1][1], wrow[x - 1][2])
            if x == bx1 and x + 1 < s.cols and wrowf[x + 1] and wrow[x + 1][0] == "":
                wrow[x + 1] = (" ", wrow[x + 1][1], wrow[x + 1][2])
                wrowf[x + 1] = False
            cell = row[c]
            if cell is None:
                # the art's own transparent cells become paper too, so the panel has *no* space cells
                # anywhere in it - see `PAPER_CH`. A cell left as a space is a cell the trail may write
                # the previous frame into, and one of those lands on the figure.
                wrow[x] = (PAPER_CH, PAPER_COL, PAPER_COL)
                wrowf[x] = False
                continue
            ch, _lv, fg, bg = cell
            wrow[x] = (ch, fg, bg)
            wrowf[x] = False


def covers_band(t: float) -> bool:
    """Is a `behind` event live, i.e. has something just been painted over the reading layer?

    `tui_live.draw` asks this after the full-frame layer and re-draws the lyric band if it says yes.

    "Behind" has always meant *behind the words*: `flash(behind=True)` dims a photograph so the dialogue
    stays readable. Until the library moved to the bottom-left corner ("图书馆放在左下角") it was never
    asked to prove it - at `y=0.0` it sat above the band and never touched it. In the corner it covers
    the band's own rows, and a photograph does not dim text it has replaced.

    Measured before writing any of this: the library's four seconds (03:13.5-03:17.5) are *past the last
    lyric* - `Data.line_at` has nothing to draw from 01:00 into the tail, so the band's own rows are
    empty there and nothing is being covered today. This is therefore insurance rather than a repair,
    and it is cheap insurance: the call is a box and a caret in those frames, and it is what keeps the
    promise true the first time a `behind` event lands on a sung line.
    """
    return any(start <= t < end and kw.get("behind") for start, end, _fn, kw in EVENTS)


def particles(s, cols: int, rows: int, t: float, u: float, n: int = 90, hue=(120, 200, 255),
              rise: bool = True) -> None:
    """A sparse particle field - the AI-couplet background.

    Positions come from a hash of the particle index and of *quantised* time, so the field drifts
    without ever being random per frame: the same `t` gives the same dots.
    """
    for i in range(n):
        h1 = (i * 2654435761) & 0xFFFFFFFF
        h2 = (i * 40503) & 0xFFFFFFFF
        x = (h1 % cols)
        speed = 0.06 + (h2 % 100) / 100 * 0.22
        y = (h2 // 97 % rows) + (t * speed * rows * (-1 if rise else 1))
        y = int(y) % rows
        v = 0.25 + 0.75 * ((h1 // 31 % 100) / 100)
        k = 0.35 + 0.65 * v * (0.6 + 0.4 * math.sin(t * 2.2 + i))
        col = tuple(min(255, int(c * max(0.0, k) * (0.4 + 0.6 * u))) for c in hue)
        s.put(int(x), y, "\u00b7" if i % 3 else "\u2022", col)


def warm(cols: int = 197, rows: int = 52) -> int:
    """Draw every event once, off-screen, so each sprite is decoded at the size it is really used at.

    The sprites are cached per size, so the *first* time an aircraft flies past it is decoded - mid-song,
    in the middle of a frame. Warming them while the engine is loading moves that to where nobody is
    watching, which is what the film's own `hg2.warm_h3()` does for the mascot.

    It used to warm **every file in `FILES` at three fixed sizes**, and that was wrong twice over: it
    decoded pictures no event will ever draw (`arj21`, `embedded`, `memory`, the cat art) and it guessed
    the sizes, so an event asking for a size the guess missed still decoded inside a frame. Measured at
    197x52: 77 sprites in **2.97 s** on a cold start, almost all of it PNG decode. Playing the events
    instead warms exactly what they ask for - and it is the same list the film will draw, so it cannot
    drift out of step with `EVENTS`.

    Callers no longer have to run it before the first frame either: `tui_live.main` now calls it *before*
    the music starts (see the note there - this used to be three seconds of black screen after the first
    note). Returns how many events it managed to draw.
    """
    import tui_live as _T
    s = _T.Screen(cols, rows)
    n = 0
    # Each event is played at several points rather than only its middle, because a `flash` *grows*:
    # `grow` is quantised to `GROW_STEPS` sizes and the first of them is the one the frame after the cut
    # uses, so warming only the middle would leave the first quarter-second of every hit decoding PNGs
    # inside 41 ms frames.
    for start, end, fn, kw in EVENTS:
        # 12 points across each event plus both ends, not a handful: a `flash` grows in `GROW_STEPS` sizes
        # and a `lowpass` in `PASS_STEPS`, and which one a given frame gets depends on where in the event it
        # is. The first version sampled five points and left 95-100 ms frames inside the low pass; the
        # second sampled 16 and still missed the *smallest* size, which is the one the frame after the cut
        # uses. The repeats cost nothing (the sprite cache answers them) and the distinct sizes are few.
        for f in (0.0, 1.0) + tuple((k + 0.5) / 12.0 for k in range(12)):
            try:
                fn(s, cols, rows, start + (end - start) * f, f, **kw)
                n += 1
            except Exception:
                pass
    # ...and the basketball animation, which is 3 MB of JSON to read and 46,000 colours to sort: measured
    # at 159 ms, several frames' budget. It is drawn at its own 70x40, so there is one size and no reason
    # to put it through the event list above - but its *table* is played here, into a rect the shape of the
    # one `draw_body` publishes, so that the panel's first frame is as warm as every other sprite's.
    try:
        basket_frames()
        box = (1, 1, max(12, cols // 2), max(5, rows - 6))
        for start, end, fn, kw in WINDOW_EVENTS:
            for f in (0.0, 1.0) + tuple((k + 0.5) / 12.0 for k in range(12)):
                try:
                    fn(s, cols, rows, start + (end - start) * f, f, box=box, **kw)
                    n += 1
                except Exception:
                    pass
    except Exception:
        pass
    return n


# ---------------------------------------------------------------- the transitions
#
# Every cut in this variant is a cut, and a cut with nothing between the two shots is a hard blink. This
# section is what happens *between* them: four cheap transitions that cycle over the song's cuts, and one
# that does not cycle - the torpedo.
#
# They are post-processes on a finished frame rather than part of any drawing, which is why they live in
# this module: by the time they run, the frame is complete - panes, chrome, the lyric band, the ticker -
# and a transition is allowed to move all of it. The shatter moves the *chrome* as well, and that is the
# whole point of a screen breaking: it is not a pane that breaks, it is the frame.
#
# All of them are pure functions of `q`, the fraction of the transition that has elapsed, so a seek lands
# in the middle of a transition exactly as playing into it does.

TRANS_DUR = 0.42                  # seconds a cut transition takes; a little over half a beat at 130 BPM
SHATTER_DUR = 0.95                # the torpedo gets longer: it has to leap, hit, and break
KINDS = ("slide", "zoom", "skew", "page")
GROW_STEPS = 4                    # the steps a `flash` grows in; see the note in `flash`
ZOOM_STEPS = 12                   # ...and the steps a `zoom`-ed `flash` walks in over its whole event
PASS_STEPS = 8                    # ...and the steps a `lowpass` grows in; see the note there

# The torpedo does not cycle. It is the one transition that is *about* something - an underwater vehicle
# leaving the water and taking the screen with it - so it is spent on the cut that is structural rather
# than on a sample of them: the first "Execution", where the song stops being about a campus and starts
# being about coursework.
#
# It was spent on **two** cuts (02:27.52 and 02:42.23) and the user's note is that one is enough - the
# same complaint as the aircraft and the manta, and the right call: the second shatter was the same joke
# twice, on a cut whose own transition would have carried it.
#
# 02:05.33 was in the first draft and came out again: the sword hit (`EVENTS`, 125.50-128.20) is live over
# that cut, and a photograph of a sculpture with rays coming off it is exactly the thing a leaping torpedo
# cannot be told apart from. Both effects were fine and the frame said nothing.
SHATTER_AT = (147.52,)


def _cuts():
    """`{row start: (kind, duration)}` for every cut in the song, built once.

    The kind cycles by position in the schedule, so two consecutive cuts are never the same transition;
    that is the difference between a vocabulary and a tic. The shatter snaps to whatever cut is nearest
    its chosen line, because the effect has to land on a real cut to be a transition at all.
    """
    import school_panels as SP
    rows = SP.shot_rows()
    out = {}
    for i, row in enumerate(rows):
        at = row["at"]
        out[at] = (KINDS[i % len(KINDS)], TRANS_DUR)
    for want in SHATTER_AT:
        near = min(out, key=lambda a: abs(a - want))
        if abs(near - want) < 3.0:
            out[near] = ("shatter", SHATTER_DUR)
    return out


_CUTS = None


def transition(s, cols: int, rows: int, t: float) -> str:
    """Run the transition live at `t`, if any. Returns its name and does nothing when there is none."""
    global _CUTS
    import school_panels as SP
    row = SP.row_at(t)
    if row is None:
        return ""
    if _CUTS is None:
        _CUTS = _cuts()
    spec = _CUTS.get(row["at"])
    if spec is None:
        return ""
    kind, dur = spec
    q = (t - row["at"]) / dur
    if not (0.0 <= q < 1.0):
        return ""
    if kind == "shatter":
        _shatter(s, cols, rows, t, q)
    elif kind == "slide":
        _slide(s, cols, rows, q)
    elif kind == "zoom":
        _zoom(s, cols, rows, q)
    elif kind == "skew":
        _skew(s, cols, rows, q)
    elif kind == "page":
        _page(s, cols, rows, q)
    return kind


def _box(cols: int, rows: int) -> tuple[int, int, int, int]:
    """The right column, which is what a pane transition moves. The chrome is not a pane."""
    return int(cols * 0.46), 2, cols - 1, rows - 3


def _carry(s, dy: int, dx: int, cell, wide: bool) -> None:
    """Move one cell into `(dx, dy)`, keeping the invariant the renderer depends on.

    `Screen.put` writes a *filler* cell with an empty character after every double-width character, and
    `tui_shot`'s rasteriser skips those by testing `s.wide[y][x]`. A transition that copies the cell but
    not the flag leaves an empty character with `wide=False` in the buffer, and the next thing to read
    the frame - the PNG rasteriser, in this case - calls `east_asian_width("")` and raises. So the
    filler becomes a space, which it is: it is the blank half of a character that is not there any more.

    **And the character keeps its filler when it moves**, which the first version did not do: `_slide`,
    `_zoom`, `_skew` and `_page` run on the frame of *every* cut in this variant, and each of them moved
    a two-column character as a one-column cell - so after every cut the buffer said "wide character,
    then a space", the terminal painted the glyph across both columns, and nothing ever repainted the
    column it had taken. `_dev/ansi_probe.py` measured it: 341 of 425 frames with at least one cell where
    the terminal and the buffer disagreed. `Screen.set_cell` is the one place that knows how to write a
    cell now, so this is two lines instead of a rule every caller has to remember.
    """
    ch, fg, bg = cell
    s.set_cell(dx, dy, ch if ch else " ", fg, bg)


def _shift(s, x0: int, y0: int, x1: int, y1: int, dx: int, dy: int = 0) -> None:
    """Move the frame's own cells by `(dx, dy)`, leaving whatever they were covering behind.

    Reading from a snapshot rather than from the buffer is what makes this a move instead of a smear:
    shifting in place copies each cell over the next one and repeats the first column across the row.
    """
    src = [row[:] for row in s.buf]
    srcw = [row[:] for row in s.wide]
    for y in range(y0, y1 + 1):
        sy = y - dy
        if not (0 <= sy < s.rows):
            continue
        for x in range(x0, x1 + 1):
            sx = x - dx
            if 0 <= sx < s.cols:
                _carry(s, y, x, src[sy][sx], srcw[sy][sx])
            elif dy:
                s.set_cell(x, y, " ", s.buf[y][x][1], s.buf[y][x][2])


def _slide(s, cols: int, rows: int, q: float) -> None:
    """A parallax slide: the column arrives from the right and overshoots a little.

    The overshoot is the whole effect - a column that slides to its resting place at a constant rate
    reads as a loading animation, and one that comes in slightly too far and settles reads as motion.
    """
    x0, y0, x1, y1 = _box(cols, rows)
    v = 1.0 - (1.0 - q) ** 2
    d = int(16 * (1.0 - v) - 3 * math.sin(q * math.pi * 1.4))
    if d == 0:
        return
    _shift(s, x0, y0, x1, y1, d)
    for k in range(2, 5):                            # the trail the column left behind
        for y in range(y0, y1 + 1):
            x = x0 + k
            if x <= x1:
                ch, fg, bg = s.buf[y][x]
                s.put(x, y, ch if ch else " ", tuple(int(c * 0.35) for c in fg), bg)


def _zoom(s, cols: int, rows: int, q: float) -> None:
    """A scale: the column comes in from 1.14x and settles. Character cells cannot interpolate, so it
    samples - nearest neighbour on a grid, which at these sizes reads as a push rather than as noise."""
    x0, y0, x1, y1 = _box(cols, rows)
    sc = 1.0 + 0.14 * (1.0 - q) ** 2
    if sc <= 1.002:
        return
    src = [row[:] for row in s.buf]
    srcw = [row[:] for row in s.wide]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for y in range(y0, y1 + 1):
        sy = int(cy + (y - cy) / sc)
        if not (0 <= sy < rows):
            continue
        for x in range(x0, x1 + 1):
            sx = int(cx + (x - cx) / sc)
            if 0 <= sx < cols:
                _carry(s, y, x, src[sy][sx], srcw[sy][sx])
            else:
                s.set_cell(x, y, " ", s.buf[y][x][1], s.buf[y][x][2])


def _skew(s, cols: int, rows: int, q: float) -> None:
    """A rotation, as far as a character grid can have one: a shear, plus the leading edge lit.

    Rotating a bitmap by a few degrees inside a cell grid is not possible; shearing each row sideways
    by `k * (y - y0)` is, and the eye reads a sheared rectangle as a rotated one as long as the edge
    that is moving is drawn.
    """
    x0, y0, x1, y1 = _box(cols, rows)
    k = 0.55 * (1.0 - q) ** 2
    if k < 0.01:
        return
    src = [row[:] for row in s.buf]
    srcw = [row[:] for row in s.wide]
    for y in range(y0, y1 + 1):
        d = int(k * (y - y0)) - int(k * (y1 - y0) * 0.5)
        for x in range(x0, x1 + 1):
            sx = x - d
            if 0 <= sx < cols:
                _carry(s, y, x, src[y][sx], srcw[y][sx])
            else:
                s.set_cell(x, y, " ", s.buf[y][x][1], s.buf[y][x][2])
    for y in range(y0, y1 + 1):                      # the edge that is moving, lit
        d = int(k * (y - y0)) - int(k * (y1 - y0) * 0.5)
        s.put(min(cols - 1, max(0, x0)), y, "\u2502", (120, 180, 240))


def _page(s, cols: int, rows: int, q: float) -> None:
    """A page turn: the frame peels from the right corner back to the left.

    The peeled part is the *mirror* of what is under it, which is what a page shows while it is being
    turned, dimmed and with the fold lit. It is the one transition here that moves the chrome too,
    because a page does not start at a panel's edge.
    """
    y0, y1 = 1, rows - 2
    peel = max(1, int(cols * 0.55))
    fx = cols - 1 - int((cols - 1 + peel) * q)
    if fx < 1:
        return
    src = [row[:] for row in s.buf]
    lo = max(0, fx - peel)
    for y in range(y0, y1 + 1):
        for x in range(lo, fx):
            sx = 2 * fx - x
            if 0 <= sx < cols:
                ch, fg, bg = src[y][sx]
                s.put(x, y, ch if ch else " ", tuple(int(c * 0.42) for c in fg), bg)
        s.put(fx, y, "\u2551", (235, 240, 255))
        if fx + 1 < cols:
            s.put(fx + 1, y, "\u2502", (90, 110, 150))


# ---------------------------------------------------------------- the torpedo

def _shard_map(cols: int, rows: int, n: int = 18):
    """Voronoi shards, computed once per window size.

    A flat list of shard ids and the seed each one belongs to. Computing this per frame would be
    `cols * rows * n` distance tests - a hundred thousand operations in Python every frame - so it is
    cached and only the displacement is per frame.
    """
    seeds = []
    for i in range(n):
        # deterministic scatter: a hash rather than a random, so a frame is reproducible
        h1 = (i * 2654435761 + 12345) & 0xFFFFFFFF
        h2 = (i * 40503 + 7919) & 0xFFFFFFFF
        seeds.append((h1 % cols, h2 % rows))
    ids = []
    for y in range(rows):
        for x in range(cols):
            best, bd = 0, 1 << 30
            for j, (sx, sy) in enumerate(seeds):
                dx, dy = x - sx, (y - sy) * 2
                d = dx * dx + dy * dy
                if d < bd:
                    bd, best = d, j
            ids.append(best)
    return ids, seeds


_SHARDS: dict = {}


def _shatter(s, cols: int, rows: int, t: float, q: float) -> None:
    """The torpedo leaves the water, hits the frame, and the frame comes apart.

    Three phases on one `q`, which is why the event is longer than a cut transition: the leap has to be
    watched, the impact has to be seen, and the shards have to have time to leave. Everything is a
    function of `q`, including the crack pattern, so a seek into the middle of it shows the middle.
    """
    leap_end, hit_end = 0.42, 0.52
    ix, iy = int(cols * 0.62), int(rows * 0.44)          # where it hits
    if q < leap_end:
        # The leap: out of the bottom edge, up and over, nose first - the flipped sprite points up.
        # The rise decelerates `(1-v)**2` and the run is linear, which is a leap rather than a slide:
        # most of the travel happens early, the apex is where the impact is, and the torpedo is inside
        # the frame for the whole middle of the window instead of arriving as a sliver at the last frame.
        v = q / leap_end
        size = max(56, int(cols * 0.42))
        rn = max(14, int(size * 0.26))
        x = int(ix - size * 1.25 + size * 0.72 * v)
        y = int(iy + (rows + 4 - iy) * (1.0 - v) ** 2)
        cells = sprite("torpedo", size, rn, contrast=1.0, flip="v")
        if cells:
            paste(s, cells, x, y)
        for k in range(int(14 * (1 - v)) + 3):                # bubbles: it came out of water
            bx, by = x + 4 + k * 3, y + rn + k
            if 0 <= bx < cols and 0 <= by < rows:
                s.put(bx, by, "\u00b0" if k % 2 else "o", (90, 150, max(40, 200 - k * 8)))
        if x > 4 and 0 <= y + rn + 2 < rows:
            s.put(max(2, x), min(rows - 1, y + rn + 2), "\u9c7c\u96f7", (150, 200, 235))
    if leap_end <= q < hit_end:
        # the impact: a ring and a flash, on the frame it lands. Only *after* the leap - the first
        # version drew the ring for the whole event, so the torpedo crossed a frame that had already
        # been hit by something that had not arrived yet.
        v = (q - leap_end) / max(1e-6, hit_end - leap_end)
        r = int(2 + 16 * v)
        for k in range(0, 360, 6):
            a = math.radians(k)
            x = int(ix + r * math.cos(a))
            y = int(iy + r * math.sin(a) * 0.5)
            if 0 <= x < cols and 0 <= y < rows:
                s.put(x, y, "\u2592" if (k // 6) % 2 else "\u2593", (255, 255, 255 - r * 6))
        return
    if q < hit_end:
        return
    # the shatter
    v = (q - hit_end) / max(1e-6, 1.0 - hit_end)
    key = (cols, rows)
    if key not in _SHARDS:
        _SHARDS[key] = _shard_map(cols, rows)
    ids, seeds = _SHARDS[key]
    src = [row[:] for row in s.buf]
    srcw = [row[:] for row in s.wide]
    # Clear the whole frame *first*, then place the shards. Doing it in one pass - clear the source
    # cell as each one is moved - looks right and is wrong: a cell that has already received a shard is
    # a source cell later in the same sweep, so the sweep erases its own work and the frame ends up
    # black with cracks in it. That was the first version, and it is why the shards were missing.
    bg = (0, 0, 0)
    for y in range(rows):
        row = s.buf[y]
        for x in range(cols):
            row[x] = (" ", bg, bg)
        for x in range(cols):
            s.wide[y][x] = False
    push = 3 + 34 * (v ** 0.8)
    fade = max(0.05, 1.0 - v * 1.15)
    for y in range(rows):
        base = y * cols
        for x in range(cols):
            j = ids[base + x]
            sx, sy = seeds[j]
            dx, dy = sx - ix, (sy - iy) * 2
            d = math.hypot(dx, dy) or 1.0
            nx = int(x + dx / d * push)
            ny = int(y + dy / d * push * 0.5 + 14 * v * v)     # a little gravity on the way out
            if 0 <= nx < cols and 0 <= ny < rows:
                ch, fg, _bg = src[y][x]
                if ch in ("", " "):
                    continue
                # a shard carries its character; `set_cell` gives a wide one its placeholder back and
                # disowns whatever half was already at the landing site
                s.set_cell(nx, ny, ch, tuple(int(c * fade) for c in fg), bg)
    # the cracks: bright, jagged, radiating from the impact, and they fade with the shards
    for k in range(14):
        a = k * (2 * math.pi / 14) + 0.21
        x, y = float(ix), float(iy)
        for step in range(int(60 * min(1.0, v * 2.2))):
            x += math.cos(a) * 1.6
            y += math.sin(a) * 0.8
            jx, jy = int(x), int(y)
            if not (0 <= jx < cols and 0 <= jy < rows):
                break
            a += math.sin(step * 0.7 + k) * 0.06          # wobble, so a crack is not a spoke
            ch = "\u2502" if abs(math.sin(a)) > 0.6 else ("\u2571" if math.cos(a) * math.sin(a) > 0
                                                          else "\u2572")
            s.put(jx, jy, ch, tuple(int(c * fade) for c in (240, 248, 255)))


# ---------------------------------------------------------------- the score
#
# The event list. Times are the song's own, and the chorus hits are where the aircraft go: `If I can`
# opens the first chorus three times (00:58.65 / 01:02.41 / 01:06.17) and that triplet is the one place
# the song repeats itself closely enough to carry a repeated visual.
EVENTS: list[tuple[float, float, object, dict]] = [
    # --- P0: the gate, at the very front, as the film's own establishing shot. It **walks in**: the
    #     picture starts at a fifth of its size and grows for the whole two and a half seconds, which is
    #     the user's "校门可以逐渐放大，拟态'我'走进校门的过程" - the opening is the one place in the film
    #     where the camera can be a person. `fill=1.45` is the second half of that note, "校门放大至超出
    #     屏幕": it ends up 285x90 cells in a 197x52 frame, i.e. larger than the screen and clipped by it,
    #     which is what standing in a gateway looks like. There is only **one** gate picture in the film:
    #     the second one (01:24.70) is gone - "校门、校徽的大图出现了多次，仅保留第一次".
    (0.60, 3.30, flash, dict(name="gate", zoom=0.20, fill=1.45, caption="\u897f\u5317\u5de5\u4e1a\u5927\u5b66 \u00b7 1938")),
    # --- the crest, big, right after (its own pane is a watermark; this is the hit)
    (3.60, 5.10, flash, dict(name="crest", caption="\u516c\u8bda\u52c7\u6bc1")),
    # --- "Fill in my data parameters": 何尊, and therefore the earliest 中国. Drawn from the vector the
    # user supplied, at frame size, instead of the character art made from the scan - "何尊的字符画效果
    # 较差，我在参考及想法中准备了一张何尊svg，请使用它". The pane at 13.20 is the same drawing at pane size.
    (7.30, 9.60, plate, dict(name="he_zun", cols_n=72, rows_n=36,
                             caption="\u5b85\u5179\u4e2d\u56fd \u00b7 \u94ed\u6587\u91cc\u6700\u65e9\u7684\u4e2d\u56fd\u4e8c\u5b57")),
    # --- "Set up our new world": 运-20's one appearance, as a low pass with the shock the user asked for.
    #     "运20 我之前要求大图掠空，但现在依旧不够大，请让其在屏幕中间时至少覆盖2/3的全屏幕". The size is
    #     solved from that coverage rather than given as a share of the frame (`lowpass` has the sum), and
    #     `peak` is only a cap: at 197x52 it comes out at the full width, 63 rows of sprite and a hull
    #     34 rows tall, and the frame shakes (`SHOCKS`).
    (11.20, 13.10, lowpass, dict(name="y20", y=0.42, caption="\u8fd0-20 \u63a0\u7a7a")),
    # --- "so dizzy": 直-20, once, coming *down* the frame - the one direction a helicopter reads in, and
    #     deliberately not a horizontal crossing: the user's note was "飞机不用只是横向飞"
    (49.20, 51.00, dive, dict(name="z20", x=0.70, caption="\u76f4-20 \u4e0b\u964d")),
    # --- 魔鬼鱼, once, swimming: a diagonal crossing at its own shape's size, rippling as it goes
    (55.00, 57.40, fly, dict(name="manta", y=0.30, size=0, rows_n=0, wave=1.0, dy=0.16,
                             caption="\u9b54\u9b3c\u9c7c")),
    # --- the first chorus: 歼-20, once, on a diagonal
    (58.90, 61.10, fly, dict(name="j20", y=0.30, rows_n=13, size=0, body=4, tilt=True, dy=0.30,
                             caption="\u6b7c-20")),
    # --- 总师文化: the five firsts, on the line that claims uniqueness. **No picture.** It was the gate
    #     again (70x22, then 139x44), and the user's note is that the gate and the crest each appear once
    #     - "校门、校徽的大图出现了多次，仅保留第一次". The line is carried by the right column, which has
    #     had `pane_landmark_dialogue` on it since 84.60, and by the ops ticker ("总师摇篮 · 第一架小型
    #     无人机" is the row's own `ops`, so nothing is lost with the caption).
    # --- "Challenging your God": the sword, over everything
    (125.50, 128.20, flash, dict(name="sword", cols_n=76, rows_n=24,
                                 caption="\u4e3e\u5251\u7684\u4e0d\u662f\u795e")),
    # --- "If I can, if I can": 航小天 打篮球 is **not on this list**. It covers the chat window, so it is
    #     drawn by the layer that owns that window (`WINDOW_EVENTS`, below) - see the note in `dunk` for
    #     why that is a layering fix and not a tidy-up. The score is unchanged: 58.65 is the first line,
    #     160 frames at 14 fps is five loops to the frame, so the window is 58.65 + 160/14 = 70.08, and
    #     the dialogue inside it is trimmed rather than hidden behind the picture (see `school_lines`).
    # --- the AI couplet: a particle field over the convergence. The manta used to be here as well, which
    #     made three appearances of it; it swims once, at 55.00.
    (162.30, 169.40, particles, dict(n=70, hue=(120, 200, 255))),
    # --- P8: the hands, the biggest hit in the film, at the line about the algebra of love
    (184.40, 187.40, flash, dict(name="dialogue", cols_n=88, rows_n=26,
                                 caption="\u4e00\u4e2a\u7c7b\uff0c\u4e24\u4e2a\u89d2\u8272\uff0c\u4e00\u4e2a\u65b9\u6cd5")),
    # --- the closing: the library at night, in the **bottom-left corner** ("图书馆放在左下角"), behind the
    #     last two lines and dimmed - but at 0.62 with its contrast held up and a caption, not at the
    #     0.42 that made it invisible. `x=0.0` puts it against the left edge; `y=0.78` rather than `1.0`
    #     keeps the film's own footer and progress bar (the last four rows) out of it, which is what "the
    #     corner" means once there is a status line down there. Its rows do cover the lyric band, and that
    #     is free here: 03:13.5 is past the last lyric (see `covers_band`). It is a keyed cut-out, so the
    #     cells where the photograph has no ink stay transparent and the dialogue is only covered where
    #     the building actually is.
    (193.50, 197.50, flash, dict(name="library", fill=0.62, x=0.0, y=0.78, behind=True, dim=0.62,
                                 contrast=1.1, caption="\u56fe\u4e66\u9986 \u00b7 \u706f\u8fd8\u4eae\u7740")),
    # --- the whole body, once, on the last line of the song: he has been a face in the window for three
    #     and a half minutes and this is the only place the film shows that he has legs. He stands at the
    #     **left** edge, on the machine's side: the panels swap at 02:16.9, so by now the right column is
    #     the conversation, and the user's note is "交换位置后全身航小天应位于左侧". **No caption** either -
    #     "航小天全身图旁也不要单独加一行'航小天'" - the figure is recognisable and the window above it has
    #     his name on it already.
    (193.60, 199.00, stand, dict(name="mascot", side="left")),
    # --- the closing crest is the **pane** at 193.46 and nothing else. The flash that used to be here
    #     (199.00, 48x20) was the emblem's third big appearance, and the user's note is that there is one:
    #     "校门、校徽的大图出现了多次，仅保留第一次".
    # --- and the bridge out of the collapse: the dot the picture squeezed into is where the crest comes
    #     from (see `emerge`). 176.30 is inside `shot_collapse`, which draws full-bleed in this variant
    #     too. This one is kept - the user asked for it in batch 20 - and kept *small*, so it is a mark
    #     rather than the emblem's second plate.
    (176.30, 178.20, emerge, dict(name="crest", caption="\u516c\u8bda\u52c7\u6bc1")),
    (203.00, 206.20, flash, dict(name="sword", cols_n=80, rows_n=26,
                                 caption="\u5728\u94f8\u5251\u5417\uff1f")),
]

# The frame's own shocks: `tui_live.fx_shake` asks `shock(t)` and shakes by that much, so the variant
# does not need a second pass over the finished buffer. One entry, and it is 运-20 going over: the window
# is the middle of the low pass (11.20-13.10), where the aircraft is closest and largest.
SHOCKS.extend([
    (11.85, 12.45, 1.0),
])


@lru_cache(None)
def _art(name: str) -> str:
    """The supplied character art, read once. Empty string when the file is not there."""
    spec = FILES.get(name)
    if spec is None:
        return ""
    p = spec[0] / spec[1]
    if not p.exists() or p.suffix != ".txt":
        return ""
    try:
        return p.read_text(encoding="utf8")
    except Exception:
        return ""


def draw(s, cols: int, rows: int, t: float) -> int:
    """Draw every event live at `t`. Returns how many drew - the callers report it, nothing waits on it.

    The loop is over the whole list, which is short; an event outside its window costs a comparison. The
    events are independent, so several can be live at once and they layer in list order - that is the
    "animation can be parallel" the film was missing, and it needed no scheduler to get it.
    """
    n = 0
    for start, end, fn, kw in EVENTS:
        if not (start <= t < end):
            continue
        u = (t - start) / max(1e-6, end - start)
        try:
            fn(s, cols, rows, t, u, **kw)
            n += 1
        except Exception:
            pass
    # the character art is not on the event list: it is printed when its own pane is up
    return n


# the supplied character art, drawn over its own frame. The cat is printed as the text it is; 何尊 is
# drawn from its SVG through `plate` (it is on the event list, above) because the vessel's text art was
# the thing the user replaced with a vector drawing.
GLYPH_EVENTS: list[tuple[float, float, str, str]] = [
    (66.30, 68.20, "cat", "\u732b\u5b66\u957f_字符画.txt"),
]
FILES["cat"] = (LANDMARKS, "\u732b\u5b66\u957f_\u5b57\u7b26\u753b.txt")
FILES["hexun_art"] = (LANDMARKS, "\u4f55\u5c0a_\u5b57\u7b26\u753b.txt")


def draw_glyphs(s, cols: int, rows: int, t: float) -> None:
    """Print the supplied character art over the frame while its window is live.

    Separate from `draw` only because these read a `.txt` instead of an image and their layout is
    different (line-by-line, centred, no ramp) - they are the same kind of event.
    """
    for start, end, key, _f in GLYPH_EVENTS:
        if not (start <= t < end):
            continue
        art = _art(key)
        if art:
            glyphs(s, cols, rows, t, (t - start) / max(1e-6, end - start), key, art)
