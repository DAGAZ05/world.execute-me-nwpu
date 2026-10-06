"""The fourteen courses, as fourteen drawings.

`02b_图像对位与可视化表达.md` §4 is the brief: bar 02:27.52-02:38.02 is the song's twelve
"Execution" hits, and the school's reading of them is *a course per hit, drawn in that course's own
graphical language*. The one rule that matters is that **no pane may be a timetable**: a screenful of
course names is the least program-like thing this player could show, while a data-flow diagram, a
three-way handshake timeline, a carry-save register trace or a burndown curve all look like what a
real machine draws.

The twelve hits are not evenly spaced (0.87 s to 1.07 s), so `school_panels.EXEC_ROWS` places each
pane on the *shot table*'s existing lyric boundaries, which are the hits themselves; a course that
would otherwise get less than 1.3 s shares its pane with the next one and the two are drawn side by
side (`_split`). Nothing here reads the lyrics: a pane is a pure function of `(t, lt, dur, u)`, so
seeking into the middle of a pane lands on the same drawing as playing into it.

Everything is drawn with `_Kit`, which owns the one framing every pane in this batch shares - a title
row, a right-aligned execution counter, and a thin progress rule - so that twelve very different
drawings still read as twelve frames of one program. That framing is the reason this file exists
rather than each pane being written freehand: the brief asks for twelve diagrams and forbids twelve
styles.
"""
from __future__ import annotations

import math
import unicodedata

# The film's own beat clock. The twelve `Execution` hits are the densest structure in the song and this
# module is what draws the sixteen drawings under them - see `_Kit._header` for why the beat is read here.
try:
    import film_panels as _FP
except Exception:                       # the module is always importable in-process; this is a guard
    _FP = None

# resolved from `school_scenes.PANE_CTX` at first use, exactly like the panes in that module
CTX: dict = {}

BG = (4, 7, 15)
DIM = (108, 122, 146)
INK = (196, 208, 228)
BLUE = (126, 152, 255)
GREEN = (120, 220, 160)
AMBER = (255, 204, 0)
RED = (255, 59, 48)
VIOLET = (186, 148, 255)
COPPER = (196, 146, 74)         # the same lit PCB trace `school_scenes` draws, for the crest watermark

BOX_H = "\u2500"
BOX_V = "\u2502"
BOX_TL, BOX_TR, BOX_BL, BOX_BR = "\u250c", "\u2510", "\u2514", "\u2518"
TEE_L, TEE_R, TEE_T, TEE_B, CROSS = "\u251c", "\u2524", "\u252c", "\u2534", "\u253c"
ARROW_R, ARROW_L, ARROW_D, ARROW_U = "\u25b6", "\u25c0", "\u25bc", "\u25b2"
DOT, BULLET = "\u00b7", "\u2022"
SHADE = " \u2591\u2592\u2593\u2588"


def _ui(level: float = 1.0):
    return CTX["ui"](level)


def _mix(c, level: float = 1.0):
    return CTX["mix"](c, level)


def resolve() -> None:
    """Pick up the player's palette and its two colour helpers."""
    g = globals()
    for name in ("BG", "INK", "BLUE", "GREEN", "AMBER", "RED", "VIOLET"):
        if name in CTX:
            g[name] = CTX[name]
    if "ui" in CTX:
        g["_ui"] = CTX["ui"]
    if "mix" in CTX:
        g["_mix"] = CTX["mix"]


def _C_BOX_H() -> str:
    """The horizontal rule, read at call time so a re-themed palette is picked up."""
    return BOX_H


def _cells(text: str) -> int:
    """How many terminal cells `text` occupies.

    Not `len(text)`. Nearly every label in these panes is Chinese, and a Chinese character is two
    cells wide while `Screen.put` advances two columns for it, so a "four character" label is eight
    cells. Measuring by character count is how a right-aligned label ends up writing three cells past
    the pane it belongs to - which is exactly the leak `_dev/pane_probe.py` caught in `c_ds_algo`.
    """
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _clip(text: str, cells: int) -> str:
    """`text` cut to at most `cells` cells, never splitting a double-width character."""
    out, n = [], 0
    for ch in text:
        cw = 2 if unicodedata.east_asian_width(ch) in "WF" else 1
        if n + cw > cells:
            break
        out.append(ch)
        n += cw
    return "".join(out)


def _pad(text: str, cells: int, right: bool = False) -> str:
    """`text` in a field `cells` cells wide - `ljust`/`rjust` for a language where 数 is two cells.

    The table in `c_ds_algo` was the visible cost of getting this wrong: `"数组".ljust(14)` pads a
    four-cell word to fourteen *characters*, which is eighteen cells, and the columns walked right.
    """
    gap = " " * max(0, cells - _cells(text))
    return gap + text if right else text + gap


class _Kit:
    """The shared frame, plus the primitives every diagram below is built from.

    A kit rather than free functions because the twelve drawings must share one look, and the look is
    small: a header, a counter, a rule, and four drawing primitives. Anything a pane needs beyond
    this it draws itself.
    """

    # the counter slot is the same width in every pane, so the numbers line up across the whole bar
    # even though the drawings behind them do not.
    W_NUM = 3

    def __init__(self, s, x0: int, y0: int, x1: int, y1: int,
                 title: str, n: int, total: int, u: float, colour=None, t: float = 0.0) -> None:
        self.s, self.x0, self.y0, self.x1, self.y1 = s, x0, y0, x1, y1
        # `u` is this pane's progress through its own slot; `t` is the song's clock. A drawing that uses
        # only `u` reveals itself and stops, which is what the user called monotone; the ones that use
        # both reveal on `u` and keep moving on `t`. Two clocks in one box, and the second one is the same
        # number in every pane, so a seek lands everywhere consistently.
        self.t = t
        self.w, self.h = x1 - x0 + 1, y1 - y0 + 1
        self.colour = colour or BLUE
        self.u = min(1.0, max(0.0, u))
        self._header(title, n, total)
        # the body rect the diagrams draw in
        self.bx0, self.by0 = x0 + 1, y0 + 2
        self.bx1, self.by1 = x1 - 1, y1 - 1
        self.bw, self.bh = max(1, self.bx1 - self.bx0 + 1), max(1, self.by1 - self.by0 + 1)

    def _header(self, title: str, n: int, total: int) -> None:
        s, x0, y0, x1 = self.s, self.x0, self.y0, self.x1
        # **The beat, on the counter that is counting it.** The sixteen course drawings do not line up
        # with the twelve `Execution` hits and cannot: sixteen does not divide into twelve plus three
        # countdown slots, so `_exec_rows` spreads them evenly and the hit times drift in and out of phase
        # with the pane boundaries. Measured (batch 38): the offsets run +0.00, -0.32, +0.43, -0.01, -0.11,
        # -0.25, -0.40, +0.35, ... - i.e. **not** the "systematically 0.8 beat late" the lyrics audit
        # reported, but a beat-against-step aliasing, worst |offset| 0.43 s. The audit's fix (shift every
        # pane 0.37 s earlier) would have broken the five that are already dead on the hit.
        #
        # What makes every hit *land* regardless of the boundary is this: the counter is the one element
        # whose meaning is "how many times has this run", so it is the one element that should answer the
        # beat. `FP.pulse` is the film's own beat detector (1 on the beat, decaying over 140 ms), and it
        # already drives the box breathing (`tui_live.beat_level`) - but that is applied to *every* box
        # uniformly, so it cannot say "this hit landed". This can, and it costs one exponent and four cells.
        p = 0.0
        if n and _FP is not None:
            try:
                p = _FP.pulse(self.t)
            except Exception:
                p = 0.0
        s.put(x0, y0, "\u258f", _mix(self.colour, 0.9 + 0.1 * p))
        s.put(x0 + 2, y0, _clip(title, max(0, self.w - 14)), _ui(0.92))
        if n:
            tag = f"EXEC {n:02d}/{total:02d}"
            s.put(x1 - len(tag) - 1, y0, tag, _mix(self.colour, 0.55 + 0.45 * p))
        rule = x0 + 1 + int((self.w - 2) * self.u)
        s.put(x0 + 1, y0 + 1, BOX_H * max(0, self.w - 2), _ui(0.20))
        s.put(x0 + 1, y0 + 1, BOX_H * max(0, rule - x0 - 1), _mix(self.colour, 0.65 + 0.35 * p))

    # ------------------------------------------------------------------ primitives

    def put(self, x: int, y: int, text: str, colour=None, level: float = 1.0) -> None:
        """Clip to the pane: every diagram below is written for a rectangle of *some* size."""
        if not (self.by0 - 1 <= y <= self.y1):
            return
        if x < self.x0 or x >= self.x1 + 1:
            return
        room = max(0, self.x1 - max(x, self.x0))
        if room <= 0:
            return
        self.s.put(max(x, self.x0), y, _clip(text, room), colour if colour is not None else _ui(0.85))

    def hline(self, x0: int, y: int, x1: int, ch: str = BOX_H, colour=None) -> None:
        if y < self.by0 or y > self.by1 or x1 < x0:
            return
        a, b = max(x0, self.bx0), min(x1, self.bx1)
        if b >= a:
            self.put(a, y, ch * (b - a + 1), colour, 1.0)

    def vline(self, x: int, y0: int, y1: int, ch: str = BOX_V, colour=None) -> None:
        if x < self.bx0 or x > self.bx1:
            return
        for y in range(max(y0, self.by0), min(y1, self.by1) + 1):
            self.put(x, y, ch, colour, 1.0)

    def frame(self, x0: int, y0: int, x1: int, y1: int, colour=None, title: str = "") -> None:
        """A box, drawn only where it fits: a pane six rows tall gets a smaller box, not a broken one."""
        x0, x1 = max(x0, self.bx0), min(x1, self.bx1)
        y0, y1 = max(y0, self.by0), min(y1, self.by1)
        if x1 - x0 < 2 or y1 - y0 < 1:
            return
        c = colour if colour is not None else _ui(0.55)
        self.put(x0, y0, BOX_TL + BOX_H * (x1 - x0 - 1) + BOX_TR, c)
        for y in range(y0 + 1, y1):
            self.put(x0, y, BOX_V, c)
            self.put(x1, y, BOX_V, c)
        self.put(x0, y1, BOX_BL + BOX_H * (x1 - x0 - 1) + BOX_BR, c)
        if title:
            self.put(x0 + 2, y0, f" {title} ", _ui(0.75), 1.0)

    def progress_cells(self, total: int, done: float) -> int:
        return int(round(total * min(1.0, max(0.0, done))))

    # ------------------------------------------------------------------ using a tall pane
    #
    # The layout gives these panes thirty-six rows under the feature bands, where they used to get
    # eleven, and a drawing that ignores the extra twenty-five rows reads as broken rather than as
    # spacious. These three helpers are what a pane uses to spend them: a section split, a caption at
    # the left margin of a section, and a right-aligned one. A pane that has something more to say uses
    # them; a pane that does not simply draws in the top third and leaves the rest quiet, which is also
    # a legitimate use of a tall pane and the reason none of this is automatic.

    def bands(self, n: int, weights=None) -> list[tuple[int, int]]:
        """Split the body into `n` stacked sections and return their `(top, bottom)` rects.

        `weights` biases the split; without it the sections are equal. The result is clipped to the
        body, so a nine-row pane gets nine rows' worth of sections and a thirty-row pane gets
        thirty - the drawing never has to know which it got.
        """
        if n < 1 or self.bh < 2:
            return []
        w = list(weights or [1] * n)
        total = sum(w) or n
        out, y = [], self.by0
        for i, k in enumerate(w):
            h = max(1, int(round(self.bh * k / total)))
            bottom = min(self.by1, y + h - 1) if i < n - 1 else self.by1
            if bottom < y:
                break
            out.append((y, bottom))
            y = bottom + 1
            if y > self.by1:
                break
        return out

    def section(self, top: int, title: str, level: float = 0.4) -> int:
        """A rule and a title at the top of a section; returns the first free row under them."""
        if top > self.by1:
            return top
        self.hline(self.bx0, top, self.bx1, _C_BOX_H(), _ui(level))
        self.put(self.bx0 + 2, top, f" {title} ", _ui(0.7))
        return min(self.by1 + 1, top + 1)

    def columns(self, n: int, weights=None, mins=None) -> list[tuple[int, int]]:
        """Split the body into `n` side-by-side columns and return their `(left, right)` rects.

        The counterpart of `bands`, and the reason the taller pane was worth having: a stack of three
        drawings in a box a hundred and thirty cells wide leaves three quarters of every row black,
        while the same three side by side fill it. The two-cell gutter between columns is left for the
        caller's divider rule, and the last column takes whatever the rounding left.

        `mins` is the user's note that "不同 panel 的宽度可以动态调整，不需要固定死": each column that
        needs at least some width to be legible says so, the minimums are handed out first, and only the
        remaining cells are shared out by `weights`. A fixed ratio broke as soon as the pane was narrower
        than the drawing needed - the table in `c_ds_algo` needs 30 cells whatever the pane is, and the
        tree gets whatever is left, which is the correct priority rather than an equal one.
        """
        if n < 1 or self.bw < 3 * n:
            return []
        w = list(weights or [1] * n)
        need = list(mins or [0] * n)
        # Refuse rather than hand back a five-cell column: a caller that said "this drawing needs thirty
        # cells" is telling the truth, and a column that cannot have them should send the pane to its
        # stacked fallback instead of printing a squeezed table nobody can read.
        if sum(need) + 2 * (n - 1) > self.bw:
            return []
        total = sum(w) or n
        avail = max(n, self.bw - 2 * (n - 1))
        usable = max(0, avail - sum(need))
        widths = [need[i] + int(round(usable * w[i] / total)) for i in range(n)]
        out, x = [], self.bx0
        for i in range(n):
            cw = max(3, widths[i])
            right = min(self.bx1, x + cw - 1) if i < n - 1 else self.bx1
            if right < x:
                break
            out.append((x, right))
            x = right + 3                                    # two cells of gutter, one of margin
            if x > self.bx1:
                break
        return out

    def sub(self, x0: int, y0: int, x1: int, y1: int) -> "_Kit":
        """A kit for a rectangle inside this one, sharing the screen, the clock and the colour.

        The same trick `_split` uses: no second `_header`, no second counter, just a clip rect that
        the drawing primitives already respect, so a helper written for a column cannot escape it.
        """
        sub = _Kit.__new__(_Kit)
        sub.s = self.s
        sub.x0, sub.y0, sub.x1, sub.y1 = x0, y0, x1, y1
        sub.w, sub.h = x1 - x0 + 1, y1 - y0 + 1
        sub.colour, sub.u, sub.t = self.colour, self.u, self.t
        sub.bx0, sub.by0, sub.bx1, sub.by1 = x0, y0, x1, y1
        sub.bw, sub.bh = max(1, x1 - x0 + 1), max(1, y1 - y0 + 1)
        return sub

    def caption(self, y: int, text: str, right: bool = False, colour=None) -> None:
        if y > self.by1:
            return
        x = self.bx1 - _cells(text) + 1 if right else self.bx0
        self.put(max(self.bx0, x), y, text, colour or _ui(0.5))

    # ------------------------------------------------------------------ easing

    @staticmethod
    def ease(v: float) -> float:
        v = min(1.0, max(0.0, v))
        return v * v * (3 - 2 * v)

    def stair(self, at: float, span: float = 0.0) -> float:
        """How far through a step that starts at `at` this pane is - the one animation clock."""
        return min(1.0, max(0.0, (self.u - at) / max(1e-6, span if span > 0 else 0.30)))


# --------------------------------------------------------------------------- the twelve drawings

def hexagon(k: _Kit, cx: int, cy: int, r: int, colour=None, label: str = "") -> None:
    """A flat-topped hexagon of half-height `r`, so the cell is `2r+2` rows tall and `2r+2` wide.

    The user's note allows panels that are not rectangles ("圆形、正多边形、蜂巢等形状均可以"). A hexagon is
    the shape a character grid draws best, because `_`, `/` and `\\` are exactly its edges - and a
    honeycomb gives the embedded course the picture its subject has: a chip in the middle and peripherals
    around it, with visible gaps between the cells. The gaps are the point; a breadboard drawn as one
    rectangle to the edges of a 95-cell pane is a box, and a box is what makes a pane look busy.

    The first version got the geometry wrong (top edge a row too high, ring spacing two rows short) and
    the cells overlapped into a lattice of stray slashes with the labels inside each other's hexes.
    """
    col = colour if colour is not None else _ui(0.5)
    # flat-topped: a short top edge, `r` slants outward on each side to the widest row at `cy`, and the
    # mirror below. Total height 2r+1, widest width 2r+3.
    top, bot = cy - r, cy + r
    k.hline(cx - r + 1, top, cx + r - 1, "_", col)
    k.hline(cx - r + 1, bot, cx + r - 1, "_", col)
    for i in range(1, r + 1):
        off = int(round(2.0 * i / r))            # r=1 has to reach the full half-width in one step
        k.put(cx - r + 1 - off, top + i, "/", col)
        k.put(cx + r - 1 + off, top + i, "\\", col)
        k.put(cx - r + 1 - off, bot - i, "\\", col)
        k.put(cx + r - 1 + off, bot - i, "/", col)
    if label:
        k.put(cx - _cells(label) // 2 + 1, cy, label, _ui(0.82))


def c_embedded(k: _Kit, lt: float, dur: float) -> None:
    """嵌入式电子微系统: the board as a honeycomb of hex cells, with the current walking the bus.

    The reference is `assets/嵌入式-超声波红外测距.jpg`, but a photograph of a breadboard is not what this
    course teaches - the *wiring* is. The first version drew that as one rectangle labelled UNO R3 with
    four jumpers hanging off it, and in a thirty-row pane it read as a box with lines under it: the thing
    the user is asking the panes not to look like. A hexagon for the controller and six around it for the
    peripherals is the same information with the shape doing the grouping.
    """
    if k.bh < 10 or k.bw < 26:
        return
    r = 2 if k.bh >= 20 and k.bw >= 34 else 1
    step_x, step_y = 2 * r + 4, 2 * r + 2
    cx = k.bx0 + min(k.bw // 2, 2 * step_x)
    cy = (k.by0 + k.by1) // 2
    ring = (("TRIG", -1, -1), ("ECHO", 0, -1), ("LCD", 1, -1),
            ("SDA", -1, 1), ("SCL", 0, 1), ("GND", 1, 1))
    for i, (label, dx, dy) in enumerate(ring):
        on = k.u >= 0.08 + 0.11 * abs(dx + dy * 2)
        hx, hy = cx + dx * step_x, cy + dy * step_y
        if hy > k.by1 - r:
            continue
        hexagon(k, hx, hy, r, _mix(BLUE if on else DIM, 0.8 if on else 0.3), label if on else "")
        if not on:
            continue
        # the bus runs in the *gap* between the two cells - from the controller's edge to the neighbour's
        # near edge - and a pulse rides it on the song's clock. Routing it across the whole row (the first
        # version asked for the neighbour's far edge) drew a line through the neighbouring cell's interior
        # and wiped its label off the pane.
        my = (cy + hy) // 2
        if dy:
            k.vline(cx, min(cy + r + 1, my), max(cy - r - 1, my), BOX_V, _mix(BLUE, 0.3))
        if dx > 0:
            k.hline(cx + r + 1, hy, hx - r - 1, BOX_H, _mix(BLUE, 0.3))
        elif dx < 0:
            k.hline(hx + r + 1, hy, cx - r - 1, BOX_H, _mix(BLUE, 0.3))
        head = (k.t * 1.6 + i * 0.17) % 1.0
        if dx > 0:
            k.put(cx + r + 1 + int((hx - r - 1 - cx - r - 1) * head), hy, "\u25cf", _mix(GREEN, 0.9))
        elif dx < 0:
            k.put(hx + r + 1 + int((cx - r - 1 - hx - r - 1) * head), hy, "\u25cf", _mix(GREEN, 0.9))
        else:
            k.put(cx, cy + r + 1 + int((hy - r - 1 - cy - r - 1) * head), "\u25cf", _mix(GREEN, 0.9))
    hexagon(k, cx, cy, r, _mix(AMBER, 0.9), "UNO")
    if k.bw > 60:
        k.put(k.bx1 - 24, k.by0, "6 \u8def\u5916\u8bbe", _ui(0.55))
        k.put(k.bx1 - 24, k.by0 + 1, "\u4e32\u884c\u603b\u7ebf\u4e0a\u8dd1", _ui(0.45))
    k.put(k.bx0, k.by1, "\u5b9e\u9a8c\u8bfe\u5728\u5b9e\u677f\u5b50\u4e0a\uff0c\u4e0d\u5728\u5c4f\u5e55\u91cc",
          _mix(GREEN, 0.7))


def c_c(k: _Kit, lt: float, dur: float) -> None:
    """程序设计（C）: a pointer walking a stack array, and the bounds check that does not exist.

    The course's one genuinely frightening idea is that `*p++` has no idea where the array ends, so
    the drawing is a row of cells, a moving pointer, and a red cell past the end that is still legal
    to write to. The counter under it is the address, which is what makes the red cell land on a
    real number rather than being a metaphor.
    """
    n = max(4, min(14, k.bw - 6))
    x0 = k.bx0 + 2
    y = k.by0 + 1
    step = int(lt * 2.4) % (n + 3)                 # the pointer cycles, so the pane never goes static
    over = step >= n
    for i in range(n):
        xx = x0 + i * 2
        col = RED if (over and i == step) else (BLUE if i == step else DIM)
        k.put(xx, y, f"{i:2d}"[-2:], _mix(col, 0.95 if i == step else 0.55))
        k.put(xx, y + 1, BOX_TL + BOX_H + BOX_TR, _mix(col, 0.6))
        k.put(xx, y + 2, BOX_V + "\u2591" + BOX_V, _mix(col, 0.45))
        k.put(xx, y + 3, BOX_BL + BOX_H + BOX_BR, _mix(col, 0.6))
    k.put(x0 + step * 2, y + 4, ARROW_U, _mix(RED if over else BLUE, 1.0))
    k.put(k.bx0, y + 4, "p", _mix(RED if over else BLUE, 0.95))
    k.put(k.bx0, y + 6, f"*p++   {step:2d}   addr 0x{k.bx0 + step * 4:04X}", _ui(0.65))
    # and the pointer keeps walking on the song's clock after the reveal: one cell at a time, for as long
    # as the pane is up (`u` writes the trace, `k.t` walks it). The cell count is `n`, not `cols` - the
    # first version referenced a name this function does not have and the pane raised.
    walk = int(k.t * 6) % max(1, n)
    k.put(x0 + walk * 2, y + 2, "\u00bf", _mix(AMBER, 0.9))
    if over and k.bh > 9:
        k.put(k.bx0, y + 8, "warning: array subscript is above array bounds", _mix(RED, 0.9))
        k.put(k.bx0, y + 9, "  [-Warray-bounds]", _ui(0.4))


def c_software_engineering(k: _Kit, lt: float, dur: float) -> None:
    """软件工程: a complete data-flow diagram, in the notation, with every flow named.

    The user's note: "专业课涉及的一些图，比如DFD，最好有完整的图像示例，且内容能贴合歌词". The first
    version was four boxes and four unlabelled arrows placed at fixed offsets, which meant it was a
    diagram *of* a DFD rather than one - a reader could not tell which arrow carried what, and in a
    thirty-row pane it drew in the top third and stopped.

    This is the real thing, and its subject is the line it is under: the section is the twelve
    "Execution" hits, so the process being diagrammed is what happens when an assignment is executed -
    submitted, compiled, run against the tests, marked. Yourdon/DeMarco notation throughout: a square is
    an external entity, a rounded box is a process, two parallel lines with an ID are a data store, and
    every arrow carries a name, because a DFD whose flows are anonymous is a flowchart.
    """
    h = k.bh
    if h < 12:
        return
    ew = max(7, min(11, k.bw // 8))
    px = k.bx0 + ew + 6
    pw = max(14, min(24, k.bw // 4))
    sx = min(k.bx1 - 14, px + pw + 8)
    rows = max(4, min(5, h // 5))
    top = k.by0 + 1
    step = max(3, (h - 5) // rows)
    # ---- the entities, stores and processes, placed down the pane rather than across it: a pipeline is
    # read top to bottom in a terminal, and the arrows between the stages are then horizontal and named
    k.frame(k.bx0, top, k.bx0 + ew, top + 2, _mix(VIOLET, 0.75), "\u5b66\u751f")
    k.frame(k.bx0, top + 2 * step, k.bx0 + ew, top + 2 * step + 2, _mix(VIOLET, 0.75), "\u6559\u5e08")
    stages = (("1 \u63d0\u4ea4", "\u6e90\u4ee3\u7801"), ("2 \u7f16\u8bd1\u8fd0\u884c", "\u7f16\u8bd1\u65e5\u5fd7"),
              ("3 \u81ea\u52a8\u5224\u9898", "\u6d4b\u8bd5\u7528\u4f8b"), ("4 \u53cd\u9988", "\u901a\u8fc7\u7387"))
    for i, (name, flow) in enumerate(stages):
        y = top + i * step
        if y + 2 > k.by1 - 3:
            break
        on = k.u >= 0.08 + 0.20 * i
        col = _mix(BLUE if on else DIM, 0.85 if on else 0.4)
        # a process is a rounded box in this notation, so the corners are rounded, not square
        k.put(px, y, "\u256d" + BOX_H * (pw - 2) + "\u256e", col)
        k.put(px, y + 1, BOX_V + " " * (pw - 2) + BOX_V, col)
        k.put(px, y + 2, "\u2570" + BOX_H * (pw - 2) + "\u256f", col)
        k.put(px + 2, y + 1, name, _ui(0.85) if on else _ui(0.4))
        if i and on and k.bx0 + ew + 1 < px:
            k.put(px + pw // 2, y - 1, ARROW_D, col)
        if i == 0 and k.bx0 + ew + 1 < px:
            k.hline(k.bx0 + ew + 1, y + 1, px - 2, BOX_H, col)
            k.put(px - 1, y + 1, ARROW_R, col)
            k.put(k.bx0 + ew + 2, y, flow, _mix(AMBER if on else DIM, 0.8 if on else 0.35))
        # the store: two parallel lines with an ID box, which is the notation and not a box with a label.
        # Its length is its own (twenty-six cells), not "to the edge": a store that runs to the far right
        # of a hundred-and-thirty-cell pane reads as a rule with a label on it.
        if i in (0, 2) and sx + 12 <= k.bx1:
            s_end = min(k.bx1 - 1, sx + 26)
            k.hline(sx, y + 1, s_end, BOX_H, col)
            k.hline(sx, y + 2, s_end, BOX_H, col)
            k.put(sx, y + 1, f"D{i // 2 + 1}", _mix(AMBER, 0.9))
            k.put(sx + 4, y + 1, "\u63d0\u4ea4\u8bb0\u5f55" if i == 0 else "\u6d4b\u8bd5\u7528\u4f8b", _ui(0.6))
            k.hline(px + pw + 1, y + 1, sx - 2, BOX_H, col)
            k.put(sx - 1, y + 1, ARROW_R, col)
            k.put(px + pw + 2, y, "\u5199\u5165" if i == 0 else "\u8bfb\u53d6",
                  _ui(0.45) if on else _ui(0.3))
        # and the flow that leaves the stage sideways, into the entity it belongs to: the teacher is at
        # the far right of the compile row, because the compile log goes to a person
        if i == 1:
            t_end = k.bx1 - 1
            k.hline(px + pw + 1, y + 1, max(px + pw + 2, t_end - 2), BOX_H, col)
            k.put(px + pw + 2, y, flow, _mix(AMBER if on else DIM, 0.8 if on else 0.35))
            if k.bw > 70:
                k.frame(t_end - 8, y, t_end, y + 2, _mix(VIOLET, 0.75), "\u6559\u5e08")
        if i == 3 and k.bx0 + ew + 1 < px:
            k.vline(k.bx0 + ew // 2, top + 3, top + 2 * step - 1, BOX_V, _mix(VIOLET, 0.5))
            back = top + 2 * step - 1
            k.hline(k.bx0 + ew // 2, back, px + pw // 2, BOX_H, _mix(VIOLET, 0.5))
            k.put(k.bx0 + ew // 2 + 1, back, flow, _mix(AMBER, 0.8))
    k.put(k.bx0, k.by1 - 1, "\u25a1 \u5916\u90e8\u5b9e\u4f53   \u256d\u2500\u256e \u52a0\u5de5   "
                            "\u2550 D1 \u6570\u636e\u5b58\u50a8   \u2192 \u6570\u636e\u6d41", _ui(0.55))
    k.put(k.bx0, k.by1, "\u7bad\u5934\u4e0a\u90fd\u6709\u540d\u5b57\uff1a\u6ca1\u6709\u540d\u5b57\u7684"
                        "\u6d41\u5411\u56fe\u53eb\u6d41\u7a0b\u56fe", _ui(0.5))
    # ...and a packet keeps travelling the pipeline: `u` draws the diagram, `k.t` runs it
    st = int(k.t * 1.6) % max(1, len(stages))
    py2 = top + st * step
    if top <= py2 <= k.by1 - 4:
        k.put(px + pw // 2, py2 + 1, "\u25c6", _mix(GREEN, 0.95))


def _oop_chain(k: _Kit, u: float) -> None:
    """Person -> Student -> GradStudent: three levels, spread over the height the pane has.

    The first version put the base at the top and the two subclasses on the last row of a thirty-row
    box, which made the two is-a arrows thirty cells long and the diagram three classes plus a lot of
    nothing. Three levels spaced to the box keep the arrows short enough to read as arrows.
    """
    k.section(k.by0, "\u7ee7\u627f \u00b7 is-a", 0.30)
    levels = ((("Person", "- name: str"),),
              (("Student", "- sid: str"), ("Teacher", "- tno: str")),
              (("GradStudent", "- lab: str"), ("TA", "- course: str")))
    bw = max(12, min(22, k.bw // 3))
    top = k.by0 + 2
    step = max(4, (k.bh - 7) // (len(levels) - 1))
    ys = [top + i * step for i in range(len(levels))]
    for li, boxes in enumerate(levels):
        if ys[li] + 2 > k.by1 - 1:
            break
        colour = _mix(BLUE if li == 0 else GREEN, 0.8 - 0.14 * li)
        for bi, (name, member) in enumerate(boxes):
            cx = k.bx0 + int(k.bw * (2 * bi + 1) / (2 * len(boxes)))
            x0 = max(k.bx0, cx - bw // 2)
            x1 = min(k.bx1, x0 + bw)
            k.frame(x0, ys[li], x1, ys[li] + 2, colour, name)
            if u >= 0.30 + 0.20 * li:
                k.put(x0 + 2, ys[li] + 1, member[: bw - 3], _ui(0.7))
            if not li:
                continue
            pj = 0 if len(levels[li - 1]) == 1 else min(bi, len(levels[li - 1]) - 1)
            pcx = k.bx0 + int(k.bw * (2 * pj + 1) / (2 * len(levels[li - 1])))
            if u < 0.45 + 0.15 * li:
                continue
            # UML puts the hollow triangle at the *parent* end, and the line runs down from it
            k.put(pcx, ys[li - 1] + 3, "\u25b3", colour)
            for yy in range(ys[li - 1] + 4, ys[li] - 1):
                f = (yy - ys[li - 1] - 3) / max(1, ys[li] - ys[li - 1] - 3)
                k.put(int(pcx + (cx - pcx) * f), yy,
                      "\\" if cx > pcx else ("/" if cx < pcx else BOX_V), _ui(0.3))
    for j, (sym, gloss) in enumerate((("+", "\u516c\u6709"), ("-", "\u79c1\u6709"),
                                      ("#", "\u4fdd\u62a4"))):
        k.put(k.bx0 + j * 12, k.by1, f"{sym} {gloss}", _ui(0.45))


def _oop_dispatch(k: _Kit, u: float, lt: float) -> None:
    """The interface and the vtable: why one call on one variable does two different things.

    The class diagram says Student *is a* Person; this says what that buys. The interface is realized
    (UML draws it dashed, and so does this), and the call site is resolved at run time by looking the
    method up in the object's table - so the pane shows a table with the chosen row lit, and the lit
    row moves, because which one is chosen is not a property of the code.
    """
    k.section(k.by0, "\u63a5\u53e3\u4e0e\u591a\u6001", 0.30)
    y = k.by0 + 2
    bw = max(14, min(26, k.bw - 2))
    k.frame(k.bx0, y, k.bx0 + bw, y + 3, _mix(VIOLET, 0.8), "Enrollable")
    k.put(k.bx0 + 2, y + 1, "<<interface>>", _ui(0.55))
    k.put(k.bx0 + 2, y + 2, "+ enroll(): void", _ui(0.75))
    k.put(k.bx0 + bw + 1, y + 2, "\u2550\u2550\u25b7", _mix(VIOLET, 0.7))
    k.put(k.bx0 + bw + 5, y + 2, "Student \u5b9e\u73b0", _ui(0.6))
    y += 5
    k.put(k.bx0, y, "Person s = new Student();", _ui(0.75))
    k.put(k.bx0, y + 1, "s.login();", _mix(AMBER, 0.9))
    k.put(k.bx0, y + 2, "\u2193 \u8fd0\u884c\u671f\u67e5\u8868", _ui(0.5))
    y += 4
    if y + 5 > k.by1:
        return
    k.put(k.bx0, y, "vtable @0x2f40", _ui(0.5))
    rows = ("Person.login()", "Student.login()", "Teacher.login()")
    sel = int(k.t * 2.0) % len(rows)                    # the object, not the call, decides
    for i, r in enumerate(rows):
        yy = y + 1 + i
        if yy > k.by1 - 2:
            break
        hit = i == sel and u > 0.5
        k.put(k.bx0, yy, f"[{i}]", _mix(BLUE if hit else DIM, 0.8))
        k.put(k.bx0 + 5, yy, r, _mix(AMBER, 0.95) if hit else _ui(0.55))
    if y + 5 <= k.by1 - 2:
        k.put(k.bx0 + 24, y + 1 + sel, "\u2190 \u9009\u4e2d", _mix(GREEN, 0.8))
    # what an object actually is in memory: a table pointer and then its own fields. It is the other
    # half of the answer, and without it the right column ended at the table and left half a pane
    # of black under a heading that said there was more to say.
    y += 5
    if y + 4 > k.by1:
        return
    k.put(k.bx0, y, "Student s \u2192 \u5bf9\u8c61\u5185\u5b58", _ui(0.6))
    oy = y + 1
    w = max(14, min(30, k.bw - 10))
    k.frame(k.bx0 + 2, oy, k.bx0 + 2 + w, oy + 3, _mix(BLUE, 0.6))
    k.put(k.bx0 + 4, oy + 1, "vptr  \u2192 0x2f40", _mix(VIOLET, 0.85))
    k.put(k.bx0 + 4, oy + 2, "\u5b57\u6bb5  name \u00b7 sid", _ui(0.7))
    if oy + 4 <= k.by1:
        k.put(k.bx0 + 2, oy + 4, "new \u5728\u5806\u4e0a\uff0c\u5f15\u7528\u5728\u6808\u4e0a", _ui(0.5))
    k.put(k.bx0, k.by1, "\u540c\u4e00\u53e5\u8c03\u7528\uff0c\u4e0d\u540c\u5bf9\u8c61\u4e0d\u540c\u884c\u4e3a", _ui(0.5))


def c_oop(k: _Kit, lt: float, dur: float) -> None:
    """面向对象: a UML class diagram, built top-down, because that is how inheritance is read.

    Wide and tall, the pane is two columns: the inheritance chain on the left, and on the right the
    interface and the dispatch table that explain what the chain is for. Narrow, it is the original
    three-box diagram, which is what fits.
    """
    if k.bw >= 64 and k.bh >= 18:
        cols = k.columns(2, [5, 4], mins=[40, 34])
        if len(cols) == 2:
            _oop_chain(k.sub(cols[0][0], k.by0, cols[0][1], k.by1), k.u)
            k.vline(cols[1][0] - 2, k.by0, k.by1, BOX_V, _ui(0.18))
            _oop_dispatch(k.sub(cols[1][0], k.by0, cols[1][1], k.by1), k.u, lt)
            return
    w = k.bw
    bw = max(12, min(20, w // 3))
    base_x = k.bx0 + max(0, (w - bw) // 2)
    y0 = k.by0
    shown = int(0.5 + k.u * 3)                     # 0,1,2,3 members revealed
    k.frame(base_x, y0, base_x + bw, y0 + min(4, k.bh - 1), _mix(BLUE, 0.75), "Person")
    rows = ["- name: str", "- id: int", "+ login(): bool"]
    for i, r in enumerate(rows[:max(0, shown)]):
        k.put(base_x + 2, y0 + 1 + i, r[: bw - 3], _ui(0.75))
    if k.bh < 7:
        return
    sub_y = k.by1 - 2
    for j, (name, at) in enumerate((("Student", 0.45), ("Teacher", 0.70))):
        if k.u < at:
            continue
        sx = k.bx0 + j * (bw + 4)
        if sx + bw > k.bx1:
            sx = k.bx1 - bw
        k.frame(sx, sub_y, sx + bw, sub_y + 2, _mix(GREEN, 0.7), name)
        k.put(sx + 2, sub_y + 1, "+ borrow()" if j == 0 else "+ grade()", _ui(0.7))
        # the is-a arrow: up from the subclass to the base, hollow triangle at the base end
        ax = sx + bw // 2
        k.vline(ax, y0 + min(4, k.bh - 1) + 1, sub_y - 1, BOX_V, _mix(GREEN, 0.6))
        k.put(ax, sub_y - 1, "\u25b3", _mix(GREEN, 0.95))


def c_network(k: _Kit, lt: float, dur: float) -> None:
    """计算机网络: the three-way handshake and the four-way close, as a sequence diagram.

    Two lifelines and the messages between them. This is the one drawing in the set where the
    *timing* is the content, so it is the one pane whose animation is a clock rather than a reveal:
    the messages arrive at their real relative positions in the shot, and the close at the end is the
    reason this pane is placed where it is.
    """
    ax, bx = k.bx0 + 12, k.bx1 - 4
    if bx - ax < 8:
        return
    # the two ends are hexagons, not words - the primitive the embedded board uses - and they get their own
    # head rows, so the messages start below them. Drawn at the message rows themselves (the first version)
    # the hexes and the SYN arrow overwrote each other and the labels came out "CL─ACK" and "▶ER".
    head = 3
    hexagon(k, ax, k.by0 + 1, 1, _mix(BLUE, 0.85), "C")
    hexagon(k, bx, k.by0 + 1, 1, _mix(GREEN, 0.85), "S")
    # `CLIENT` goes to the *left* of its cell: written three cells in - beside the hexagon - the word ran
    # over the cell's own slants and over the letter inside it
    k.put(ax - 8, k.by0 + 1, "CLIENT", _mix(BLUE, 0.6))
    # ...and the other end *has* a name: this was an empty string, so the server lifeline was unlabelled
    # (there is no room to its right, so the label goes under its hexagon, on the row the messages do not
    # reach until `by0 + head + 1`)
    k.put(max(k.bx0, bx - 6), k.by0 + 2, "SERVER", _mix(GREEN, 0.6))
    msgs = [("SYN  seq=x", 0.04, ">", "\u4e09\u6b21\u63e1\u624b"),
            ("SYN+ACK  ack=x+1", 0.12, "<", "\u4e09\u6b21\u63e1\u624b"),
            ("ACK  ack=y+1", 0.20, ">", "\u4e09\u6b21\u63e1\u624b"),
            ("GET /student?id=41827", 0.30, ">", "HTTP"),
            ("200 OK  application/json", 0.40, "<", "HTTP"),
            ("GET /static/app.js", 0.50, ">", "HTTP"),
            ("200 OK  1.2 KB  keep-alive", 0.60, "<", "HTTP"),
            ("FIN  seq=u", 0.72, ">", "\u56db\u6b21\u6325\u624b"),
            ("ACK  ack=u+1", 0.80, "<", "\u56db\u6b21\u6325\u624b"),
            ("FIN+ACK  seq=w", 0.88, "<", "\u56db\u6b21\u6325\u624b"),
            ("ACK  ack=w+1", 0.96, ">", "\u56db\u6b21\u6325\u624b")]
    # The messages are spread down the whole pane. Packing eleven of them into the top six rows and
    # then drawing two lifelines to the floor is what the first version did, and it looked like a
    # sequence diagram with nothing in it - the box is thirty rows tall and the timing *is* the
    # content here, so the timing gets the rows.
    bottom = k.by1 - (2 if k.bh >= 12 else 0)
    space = max(1, bottom - (k.by0 + head) - 1)
    step = max(1, space // max(1, len(msgs)))
    spill = max(0, space - step * (len(msgs) - 1))          # the remainder, spread over the messages
    k.vline(ax, k.by0 + head, bottom, BOX_V, _ui(0.30))
    k.vline(bx, k.by0 + head, bottom, BOX_V, _ui(0.30))
    seen = {}
    for i, (label, at, d, phase) in enumerate(msgs):
        y = k.by0 + head + 1 + i * step + (i * spill) // max(1, len(msgs) - 1)
        if y > bottom:
            break
        # every wire is on screen from the first frame; `at` only decides how bright the message on
        # it is. There used to be a `break` here and it is why the pane measured 6% ink at frame one.
        seen.setdefault(phase, y)
        fwd = d == ">"
        x_from, x_to = (ax, bx) if fwd else (bx, ax)
        # `x_to - x_from` is negative when the message travels right to left, and `label[:span - 3]`
        # then cuts the label to nothing: five of the eleven messages (SYN+ACK, both 200 OK, ACK ack=u+1,
        # FIN+ACK) had no text on screen at all while the pane's title said "三次握手" (batch 31's audit).
        span = abs(x_to - x_from)
        col = _mix(BLUE if fwd else GREEN, 0.75)
        f = k.stair(at, 0.10)
        # `tip`, not `head`: the arrow's x position was called `head` here, and `head` is the *row* the
        # two hexagons sit on. Nothing below the loop used the row until the packet did, and then the
        # packet was drawn at `by0 + head` with `head` a hundred-odd columns wide - off the pane, where
        # `Screen.put` drops it without a word and the animation simply does not happen.
        tip = x_from + int(span * f)
        # the wire is drawn for its whole length from the first frame, faint, and the message is the
        # bright part that has arrived. Otherwise a sequence diagram in a 0.82 s slot is an empty box
        # for half its life: `_dev/span_probe.py` measured 6% of the finished ink on frame one.
        k.hline(min(x_from, x_to), y, max(x_from, x_to) - 1, BOX_H, _ui(0.14))
        k.hline(min(x_from, tip), y, max(x_from, tip) - 1, BOX_H, col)
        k.put(tip, y, ARROW_R if fwd else ARROW_L, col)
        lab = label[: max(0, span - 3)]
        k.put(x_from + 1 if fwd else max(x_from - _cells(lab) - 1, k.bx0), y, lab,
              _ui(0.35 + 0.27 * f))
    # ...and the connection itself is alive: one packet runs down the client's lifeline and back up
    # the server's, which is "time passing on an open socket" drawn rather than written. On the reveal
    # it crossed the diagram once, in the last frame of the slot, and the drawing - a sequence diagram,
    # the one drawing in the set whose subject *is* timing - was a still picture for the rest of it:
    # `_dev/what_moves.py` showed all six of this pane's moving cells in the machinery row at the
    # bottom, i.e. none of them in the drawing. It runs on the lifelines rather than along the wires
    # because a wire row carries a message label, and a bright dot inside the text reads as a typo.
    top, bot = k.by0 + head, bottom
    lap = (k.t * 0.55) % 2.0
    if lap < 1.0:
        k.put(ax, top + int((bot - top) * lap), "\u25cf", _mix(AMBER, 0.95))
    else:
        k.put(bx, bot - int((bot - top) * (lap - 1.0)), "\u25cf", _mix(AMBER, 0.95))
    # the three phases named once each, in the margin the lifelines were moved right to leave
    for phase, y in seen.items():
        k.put(k.bx0, y, phase, _mix(AMBER if phase == "HTTP" else VIOLET, 0.7))
    if k.bh >= 12 and k.u > 0.5:
        k.put(k.bx0, k.by1, "\u63e1\u624b \u2192 \u4f20\u6570\u636e \u2192 \u6325\u624b\uff1a"
                            "\u4e00\u6761\u8fde\u63a5\u7684\u4e00\u751f", _ui(0.55))


def c_os(k: _Kit, lt: float, dur: float) -> None:
    """计算机操作系统: a live scheduler on OpenEuler - `top`, the run queue, and the context switches.

    The lab runs on OpenEuler, so the drawing is that machine's own output rather than a diagram: a
    scrolling process table with PIDs and states, a run queue that reorders, and a switch counter.
    Numbers move; nothing is asserted. It is the most literal reading of "Execution" in the set.
    """
    k.put(k.bx0, k.by0, "top - 03:11:24 up 41 days,  3:07,  1 user", _ui(0.65))
    k.put(k.bx0, k.by0 + 1, "Tasks: 214 total,   1 running, 213 sleeping", _ui(0.65))
    k.put(k.bx0, k.by0 + 2, "%Cpu(s):  6.2 us,  1.1 sy, 92.7 id", _mix(GREEN, 0.8))
    hdr_y = k.by0 + 4
    k.put(k.bx0, hdr_y, "  PID USER      PR  NI  %CPU  %MEM  STAT  COMMAND", _ui(0.6))
    names = ["systemd", "kworker/0:1", "sshd", "postgres", "python3", "bash", "gcc", "opencode"]
    rows = max(1, min(len(names), k.by1 - hdr_y - 1))
    # **The table and the summary have to agree, and they did not.** The header prints
    # `%Cpu(s): 6.2 us, 1.1 sy, 92.7 id`, i.e. **7.3 % busy**; each row was
    # `cpu = 0.4 + 4.0 * abs(sin(...))`, so eight rows summed to 21.4-25.5 % (measured, batch 42) -
    # the process table claimed three times the CPU the line above it reported. On a pane whose whole
    # point is "this is the machine's own output, numbers move, nothing is asserted", a table that
    # contradicts its own header is asserting something false.
    #
    # The busy share is now divided among the rows, and the **jitter conserves it**: the first version
    # scaled each row by `0.82 + 0.18 * |sin|`, which shrank every row at once and made the column sum to
    # 6.7 % under a header claiming 7.3 % (measured by the batch-42 probe). A table that contradicts its
    # own summary by *rounding down a little* is the same defect as one that contradicts it by 3x - just
    # harder to notice. Now the two busy rows split the reported `us + sy` in a breathing ratio whose two
    # halves always add to one, so the sum is the summary by construction.
    user_pct, sys_pct = 6.2, 1.1
    busy = user_pct + sys_pct
    ratio = 0.85 + 0.05 * math.sin(lt * 1.1)               # how the busy time splits user/system
    share = [busy * ratio, busy * (1.0 - ratio)] + [0.0] * max(0, rows - 2)
    for i in range(rows):
        y = hdr_y + 1 + i
        tick = (int(lt * 1.6) + i) % len(names)
        nm = names[tick]
        cpu = share[i] if i < len(share) else 0.0
        k.put(k.bx0, y, f"{4100 + i * 137:5d} root      20   0 {cpu:5.1f}  0.3",
              _mix(BLUE if i == 0 else INK, 0.75))
        k.put(k.bx0 + 38, y, nm, _mix(AMBER, 0.8) if i == 0 else _ui(0.6))
    # the row 	op is reading right now, walking the table on the song's clock
    if rows:
        ry = hdr_y + 1 + int(k.t * 2.5) % rows
        k.put(k.bx1 - 2, ry, "\u25c0", _mix(AMBER, 0.8))
    if k.by1 - 2 > hdr_y + rows:
        y = min(hdr_y + rows + 1, k.by1 - 1)
        k.put(k.bx0, y, "run queue", _ui(0.5))
        q = ["R:python3", "S:sshd", "S:postgres", "S:gcc"]
        for i, qq in enumerate(q):
            k.put(k.bx0 + 11 + i * 11, y, qq, _mix(BLUE if i == 0 else DIM, 0.8))
    # ---- and under the table, the three things the course is actually about. `top` is what the lab
    # machine prints; these are what the exam asks, and the pane is tall enough for both.
    top = hdr_y + rows + 3
    cols = k.columns(3, [5, 6, 5], mins=[24, 30, 24]) if k.by1 - top >= 7 else []
    if len(cols) == 3:
        _os_states(k.sub(cols[0][0], top, cols[0][1], k.by1), lt)
        _os_pages(k.sub(cols[1][0], top, cols[1][1], k.by1), lt)
        _os_sched(k.sub(cols[2][0], top, cols[2][1], k.by1), lt)


def _os_states(d: _Kit, lt: float) -> None:
    """The process state machine: five states and the transitions between them."""
    d.section(d.by0, "\u8fdb\u7a0b\u72b6\u6001", 0.25)
    states = (("new", "\u65b0\u5efa"), ("ready", "\u5c31\u7eea"), ("running", "\u8fd0\u884c"),
              ("blocked", "\u963b\u585e"), ("exit", "\u7ec8\u6b62"))
    # **The four forward edges, labelled with what actually causes them.** The list used to be
    # `("fork", "调度", "时间片到", "I/O 请求")` drawn under states 0..3, i.e. it named the edge
    # running->blocked "时间片到" and the edge blocked->exit "I/O 请求". Both are wrong and both are the
    # exam's first question: a time slice expiring sends `running` back to **ready**, and an I/O request
    # sends `running` to `blocked` - not out of the process. (`exit` is reached by 终止/退出, not by I/O.)
    # Measured against the sequence the pane draws (batch 42).
    trans = ("fork", "\u8c03\u5ea6", "I/O \u8bf7\u6c42", "\u7ec8\u6b62")
    here = (0, 1, 2, 3, 1)[int(lt * 2.0) % 5]              # the state the pane is standing on
    step = max(2, (d.bh - 2) // len(states))
    for i, (en, zh) in enumerate(states):
        y = d.by0 + 1 + i * step
        if y > d.by1 - 1:
            break
        d.put(d.bx0, y, "\u25cf", _mix(AMBER if i == here else BLUE, 0.85))
        d.put(d.bx0 + 2, y, f"{zh} {en}", _ui(0.8) if i == here else _ui(0.6))
        if i < len(trans) and y + 1 <= d.by1 - 1:
            d.put(d.bx0 + 1, y + 1, BOX_V, _ui(0.3))
            d.put(d.bx0 + 3, y + 1, trans[i], _ui(0.42))
    d.put(d.bx0, d.by1, "\u963b\u585e\u4e0d\u5360 CPU\uff1b\u65f6\u95f4\u7247\u5230\u2192\u5c31\u7eea\uff0c"
                        "I/O \u5b8c\u6210\u2192\u5c31\u7eea", _mix(GREEN, 0.75))


def _os_pages(d: _Kit, lt: float) -> None:
    """Address translation: the virtual address, the tables it walks, and the frame it lands in."""
    d.section(d.by0, "\u5730\u5740\u7ffb\u8bd1", 0.25)
    hit = int(lt * 1.3) % 4 != 3                          # a TLB miss every fourth step
    stages = (("0x7ffd_1a3c", "\u865a\u62df\u5730\u5740", BLUE),
              ("PGD  \u2192 0x2f", "\u9875\u76ee\u5f55", VIOLET),
              ("PTE  \u2192 0x8c", "\u9875\u8868\u9879", VIOLET),
              ("0x1a3_a3c", "\u7269\u7406\u5730\u5740", GREEN))
    step = max(2, (d.bh - 4) // len(stages))
    for i, (val, name, col) in enumerate(stages):
        y = d.by0 + 1 + i * step
        if y > d.by1 - 2:
            break
        d.put(d.bx0, y, val, _mix(col, 0.9))
        d.put(d.bx0 + 14, y, name, _ui(0.45))
        for yy in range(y + 1, min(y + step, d.by1 - 1)):
            d.put(d.bx0 + 4, yy, ARROW_D if yy == y + 1 else BOX_V, _ui(0.35))
    d.put(d.bx0, d.by1 - 1, "TLB " + ("\u547d\u4e2d" if hit else "\u672a\u547d\u4e2d"),
          _mix(GREEN if hit else RED, 0.85))
    d.put(d.bx0 + 12, d.by1 - 1, "1 \u4e2a\u5468\u671f" if hit else "miss \u2192 \u67e5\u8868", _ui(0.5))
    d.put(d.bx0, d.by1, "\u7f13\u5b58\u547d\u4e2d\u7387\u51b3\u5b9a\u5b9e\u9645\u901f\u5ea6", _ui(0.5))


def _os_sched(d: _Kit, lt: float) -> None:
    """The scheduler: three runnable processes sharing one CPU in time slices."""
    d.section(d.by0, "\u8c03\u5ea6", 0.25)
    procs = ("P1", "P2", "P3")
    span = max(6, d.bw - 5)
    slices = 10
    now = int(lt * 3) % slices
    step = max(2, (d.bh - 5) // len(procs))
    for i, nm in enumerate(procs):
        y = d.by0 + 1 + i * step
        if y > d.by1 - 3:
            break
        d.put(d.bx0, y, nm, _mix(BLUE, 0.8))
        for s in range(slices):
            xx = d.bx0 + 4 + int(span * s / slices)
            w = max(1, span // slices - 1)
            owns = (s + i) % len(procs) == 0
            d.put(xx, y, ("\u2588" if owns else "\u2591") * w,
                  _mix(AMBER, 0.9) if (owns and s == now) else (_mix(GREEN, 0.7) if owns else _ui(0.2)))
    d.put(d.bx0, d.by1 - 1, "\u65f6\u95f4\u7247 4 ms\uff0c\u5c31\u7eea\u961f\u5217\u91cd\u6392", _ui(0.5))
    d.put(d.bx0, d.by1, "R:python3 \u5728\u8dd1", _mix(GREEN, 0.75))


def c_co(k: _Kit, lt: float, dur: float) -> None:
    """计算机组成原理: two's-complement multiplication, one shift-add step at a time.

    This is the course's classic pencil-and-paper算法 done in registers, and the drawing is literally
    the register trace: A, Q and M in binary, the shifted carry, and a counter. The step index is a
    function of `lt`, so the multiplication walks rather than blinks - the point is the *sequence*.
    """
    # **Four** steps, not eight: this is a four-bit multiply (A and Q are four bits each), and its own
    # label says 13 x 11 = 143 - which four steps produce and eight do not (they give 171). The rate is
    # set so the whole sequence happens inside the pane's own slot: at 2.2 steps/s an 0.83 s slot only
    # ever reached step 2, so the drawing never showed the answer it claimed.
    steps = 4
    step = min(steps, 1 + int(lt * 6.0))
    a = 0
    carry = 0
    q = 0b1101                                   # 13 * 11, the textbook example
    m = 0b1011
    # **`range(step)`, not `range(step - 1)`.** The one-iteration-short loop was why the register trace
    # printed 111 on the line whose own text says `13 × 11 = 143`: four iterations give 143 and three give
    # 111 (verified by replaying the shift-add by hand - 3 iters -> A=6, Q=15 -> 111; 4 -> A=8, Q=15 ->
    # 143). The comment below already said "four steps", so the intent was right and the loop disagreed
    # with it. Found by batch 37's maths audit.
    for i in range(step):
        if q & 1:
            t_ = a + m
            carry = (t_ >> 8) & 1                # the carry is real now; `(a + m) > 255` was never true
            a = t_ & 0xFF
        else:
            carry = 0
        q = ((q >> 1) | ((a & 1) << 3)) & 0xFF
        a >>= 1
    # the clock keeps ticking after the reveal: the window slides and the bit leaving it is lit
    shift = int(k.t * 4) % 8
    def bits(v, n=8):
        return "".join("1" if v & (1 << (n - 1 - i)) else "0" for i in range(n))
    y = k.by0
    k.put(k.bx0, y, f"M    {bits(m)}   = {m:3d}", _mix(AMBER, 0.85))
    k.put(k.bx0, y + 2, f"A    {bits(a)}", _mix(BLUE, 0.9))
    k.put(k.bx0, y + 3, f"Q    {bits(q)}", _mix(GREEN, 0.9))
    # the bit about to leave the window, on the song's clock: the register trace keeps ticking after the
    # reveal has finished, which is the difference between a snapshot and a machine
    k.put(k.bx0 + 5 + (7 - shift), y + 3, "\u25b2", _mix(RED, 0.9))
    k.put(k.bx0, y + 4, f"C    {carry}   step {step}/{steps}", _ui(0.6))
    if k.bh > 7:
        k.put(k.bx0, y + 6, "\u25b8 若 Q0=1：A \u2190 A+M；否则跳过", _ui(0.65))
        k.put(k.bx0, y + 7, "\u25b8 算术右移 (C,A,Q) 一位", _ui(0.65))
    if k.bh > 9:
        k.put(k.bx0, y + 9, f"product  {(a << 4) | q:3d}   (13 \u00d7 11 = 143)",
              _mix(GREEN, 0.9) if step >= steps else _ui(0.4))


def c_db(k: _Kit, lt: float, dur: float) -> None:
    """数据库: PostgreSQL's `EXPLAIN` plan tree with a B+ tree underneath it.

    A plan tree is what a database *decides*, and a B+ tree is what it walks; the course teaches
    both, so the pane shows both at once. The plan reveals top-down because a plan is read
    top-down, and the leaf level of the index fills as the scan descends into it.
    """
    y = k.by0
    plan = [("Limit  (cost=0.29..8.31 rows=1 width=36)", 0.0, 0),
            ("  \u2514\u2500 Index Scan using student_pkey on student", 0.16, 1),
            ("       Index Cond: (id = 41827)", 0.34, 2),
            ("       Filter: (college = 'software')", 0.52, 2)]
    # a plan prints in order, so the reveal order *is* the row order - the indent carries the depth
    for i, (label, at, depth) in enumerate(plan):
        if k.u < at:
            continue
        k.put(k.bx0 + depth * 2, y + i, label[: max(0, k.bw - depth * 2)], _ui(0.78))
    if k.bh < 8:
        return
    # The B+ tree the scan is walking: root, an internal level, and the leaf level the plan's
    # `Index Cond` lands in. It used to be one strip of leaf keys pinned to the last row, which left
    # twenty rows of nothing between the plan and the index the plan was talking about.
    ly = k.by1 - (2 if k.bh >= 12 else 0)
    leaves = max(4, min(12, (k.bw - 2) // 5))
    hot = int(k.t * 3) % max(1, leaves)          # the scan keeps running on the song clock
    root_y = k.by0 + 4
    mid_y = (root_y + ly) // 2 if k.bh >= 12 else root_y + 2
    k.put(k.bx0, root_y, "B+ root", _ui(0.5))
    k.put(k.bx0 + 9, root_y, "\u250c" + BOX_H * 3 + "\u252c" + BOX_H * 3 + "\u2510", _ui(0.45))
    k.put(k.bx0, mid_y, "internal", _ui(0.5))
    for i in range(4):
        ix = k.bx0 + 9 + i * 15
        if ix + 3 > k.bx1:
            break
        k.put(ix, mid_y, f"{i * 137:>3}", _mix(BLUE if i == hot // 3 else DIM, 0.7))
        # the root fans out to the internal level, and the internal level fans out to the leaves:
        # a B+ tree drawn as three named strips with nothing between them is three strips
        for yy in range(root_y + 1, mid_y):
            k.put(ix + 1, yy, BOX_V, _ui(0.2))
        for j in range(3):
            cx = k.bx0 + 9 + (i * 3 + j) * 5
            if cx + 4 > k.bx1:
                break
            # the fan only in the last few rows: spread over fourteen rows an interpolated diagonal
            # is a dotted vertical line, and a B+ tree drawn with dotted vertical lines is a comb
            fan = max(1, min(6, ly - mid_y - 2))
            for yy in range(mid_y + 1, ly - 1 - fan):
                k.put(ix + 1, yy, BOX_V, _ui(0.2))
            for yy in range(ly - 1 - fan, ly - 1):
                f = (yy - (ly - 1 - fan)) / max(1, fan)
                k.put(int(ix + (cx - ix) * f), yy,
                      "\\" if cx > ix else ("/" if cx < ix else BOX_V), _ui(0.22))
    k.put(k.bx0, ly - 1, "B+ leaf", _ui(0.45))
    for i in range(leaves):
        xx = k.bx0 + 9 + i * 5
        if xx + 4 > k.bx1:
            break
        k.put(xx, ly - 1, f"{i * 137:5d}"[:5], _mix(BLUE if i == hot else DIM, 0.9 if i == hot else 0.5))
    if k.bh >= 12:
        k.put(k.bx0, ly + 1, "\u4e09\u5c42\u6811\uff0c\u4e00\u6b21\u67e5\u8be2\u4e09\u6b21 I/O", _mix(GREEN, 0.75))


def c_pm(k: _Kit, lt: float, dur: float) -> None:
    """软件项目管理: a WBS with a Gantt chart, and the critical path lighting up.

    Four tasks, their bars, and the dependencies between them. The critical path is the one thing in
    this course that is drawn rather than tabulated, and it is drawn last, in red, because that is the
    order the method works in.
    """
    tasks = [("需求", 0.02, 3, 0), ("设计", 0.14, 2, 3), ("编码", 0.28, 4, 5), ("测试", 0.44, 3, 9)]
    x0 = k.bx0 + 8
    span = max(6, k.bx1 - x0 - 2)
    total = 12
    for i, (name, at, length, start) in enumerate(tasks):
        y = k.by0 + 1 + i
        if y > k.by1:
            break
        k.put(k.bx0, y, name, _ui(0.8))
        if k.u < at:
            continue
        bx = x0 + int(span * start / total)
        bw = max(1, int(span * length / total))
        critical = i in (2, 3)
        col = RED if critical else BLUE
        k.put(bx, y, "\u2588" * bw, _mix(col, 0.85))
        k.put(bx + bw, y, f" {length}d", _ui(0.5))
    # the sprint's today line, moving on the song's clock: the bars are a reveal, this is a clock
    tx = x0 + int(span * ((k.t * 0.22) % 1.0))
    for yy2 in range(k.by0 + 1, min(k.by1, k.by0 + 1 + len(tasks))):
        k.put(tx, yy2, "\u2502", _mix(RED, 0.45))
    if k.bh > 6:
        yy = k.by0 + 1 + len(tasks)
        if yy <= k.by1:
            k.hline(x0, yy, k.bx1 - 1, BOX_H, _ui(0.30))
            for i, w in enumerate(("W1", "W2", "W3", "W4")):
                k.put(x0 + int(span * (i * 3 + 1.5) / total), yy, w, _ui(0.45))
        if k.u > 0.7 and yy + 1 <= k.by1:
            k.put(k.bx0, yy + 1, "critical path", _mix(RED, 0.9))
            k.put(k.bx0 + 14, yy + 1, "\u2588" * 12, _mix(RED, 0.6))


def c_test(k: _Kit, lt: float, dur: float) -> None:
    """软件测试: the coverage matrix, filling green, with the failures staying red.

    A grid of test cases by code paths. The cells turn green as the run proceeds and the ones that
    fail never do - the distribution of red cells *is* the bug report, which is why the histogram
    underneath is drawn from the same grid rather than being a separate statistic.
    """
    rows = max(3, min(6, k.bh - 4))
    cols = max(4, min(16, (k.bw - 6) // 2))
    # The axis labels get their own row and the bars start past the longest of them. They used to be
    # written at `bx0` on the rows the matrix and the histogram occupied: the row numbers overwrote
    # "cases" into "c 4es" and the first bar overwrote "defects" into "defec▓s", which a frame dump shows
    # at once and nothing else does - the pane probe is happy, because all of it is inside the pane.
    k.put(k.bx0, k.by0, "cases", _ui(0.5))
    k.put(k.bx0 + 7, k.by0, "\u2192 paths", _ui(0.35))
    x0, y0 = k.bx0 + 5, k.by0 + 1
    done = k.progress_cells(rows * cols, k.u * 1.15)
    fail = set()
    for i in range(rows * cols):
        if i % 11 == 3 or i % 17 == 5:
            fail.add(i)
    for r in range(rows):
        if y0 + r > k.by1:
            break
        k.put(k.bx0 + 1, y0 + r, f"{r + 1:2d}", _ui(0.45))
        for c in range(cols):
            xx = x0 + c * 2
            if xx > k.bx1:
                break
            i = r * cols + c
            if i >= done:
                ch, col = "\u00b7", DIM
            elif i in fail:
                ch, col = "\u00d7", RED
            else:
                ch, col = "\u2713", GREEN
            k.put(xx, y0 + r, ch, _mix(col, 0.9 if i < done else 0.3))
    # the runner is still on a cell: the matrix fills on u, the cursor walks it on k.t
    if done < rows * cols:
        ci = int(k.t * 30) % (rows * cols)
        k.put(x0 + (ci % cols) * 2, y0 + ci // cols, "\u25cb", _mix(AMBER, 0.95))
    # the failure histogram, drawn from the same set of red cells
    hy = min(k.by1, y0 + rows + 1)
    if hy <= k.by1:
        k.put(k.bx0, hy, "defects", _ui(0.5))
        # the bars are the *actual* failures, binned by column: `(nfail * (b+2) // (b+3)) % 4` was a
        # sawtooth off one total, so every bar was a function of `nfail` alone (batch 31's audit)
        nfail = len([i for i in fail if i < done])
        nb = min(12, cols)
        per = [0] * nb
        for i in sorted(fail):
            if i < done and nb:
                per[min(nb - 1, (i % cols) * nb // max(1, cols))] += 1
        top = max(per) or 1
        for b, cnt in enumerate(per):
            h = int(round(4 * cnt / top))
            k.put(k.bx0 + 9 + b * 2, hy, SHADE[min(4, h + 1)] if cnt else "\u00b7",
                  _mix(RED, 0.8) if cnt else _ui(0.25))
        # ...and the coverage the matrix above really shows, on the row under it.
        #
        # **The denominator is the whole matrix, not `done`.** `(done - nfail) * 100 // done` was the
        # share of the *executed* cases that passed, which is a pass rate wearing the word "cov": it read
        # 85 % at u=0.5 when the matrix had only 57 % of its cells executed, and it *fell* as the run
        # progressed to 84 % at u=1.0 - i.e. the more of the suite had run, the smaller the number the
        # suite reported, which is the one thing a coverage figure cannot do. Coverage is executed over
        # total; the failures are a separate fact and now get their own parenthesis. (Batch 37's maths
        # audit; the matrix itself was already drawing the truth.)
        if hy + 1 <= k.by1:
            total = max(1, rows * cols)
            k.put(k.bx0, hy + 1, f"cov {done * 100 // total:3d} %  "
                                 f"({done}/{total} executed, {nfail} failed)",
                  _mix(GREEN, 0.85))


def c_dl(k: _Kit, lt: float, dur: float) -> None:
    """深度学习: the loss curve over a backward pass drawn on top of it.

    The curve is the training run; the red edges are the gradient flowing back through the same graph
    the blue edges carried activations forward. Drawing them on one graph is the course's central
    idea and it is also the reason this pane can animate: forward and backward are two directions.
    """
    w, h = k.bw, k.bh
    if h < 4 or w < 12:
        return
    # the loss curve: descending, with the noise a real run has
    pts = []
    for c in range(w):
        v = 0.92 * math.exp(-3.1 * (c / max(1, w - 1))) + 0.06
        v += 0.03 * math.sin(c * 0.7 + lt * 1.4) * (1 - c / max(1, w - 1))
        pts.append(v)
    shown = int(w * min(1.0, k.u * 1.5))
    for c in range(1, shown):
        y_prev = k.by1 - 1 - int(pts[c - 1] * (h - 2))
        y_now = k.by1 - 1 - int(pts[c] * (h - 2))
        k.put(k.bx0 + c, y_now, "\u00b7" if abs(y_now - y_prev) < 2 else "\u2571", _mix(BLUE, 0.85))
    k.put(k.bx0, k.by0, f"loss {pts[max(0, shown - 1)]:.3f}", _mix(BLUE, 0.9))
    # the curve's leading point, still descending, on the song's clock: a loss curve that stops moving is
    # a plot, and the whole point of a training run is that it is still going
    lx = k.bx0 + 2 + int((k.t * 7) % max(1, k.bw - 6))
    ly = k.by0 + 2 + int(max(1, k.bh - 6) * (0.5 + 0.5 * math.sin(k.t * 1.9)))
    k.put(lx, min(k.by1 - 2, ly), "\u25cf", _mix(GREEN, 0.85))
    # the backward pass: the same edges, in red, walking right to left
    if k.u > 0.55:
        back = int(w * min(1.0, (k.u - 0.55) / 0.40))
        for c in range(max(1, w - back), w):
            y = k.by1 - 1 - int(pts[c] * (h - 2))
            k.put(k.bx0 + c, y + (1 if c % 3 else -1), "\\" if c % 2 else "/", _mix(RED, 0.9))
        k.put(max(k.bx0, k.bx1 - 12), k.by0, "\u2207loss", _mix(RED, 0.95))


def _ind_tree(k: _Kit, u: float) -> None:
    """The feature tree: a part, its features and their sketches, revealed in build order."""
    k.frame(k.bx0, k.by0, k.bx1, k.by1, _ui(0.40), "feature tree")
    # \u62c9\u4f38 = 拉伸, not \u62c9\u4f28: the escape was one digit off from the first version and the feature
    # tree said "\u62c9\u4f28" in every frame since, which is a character nobody would type on purpose and
    # `pane_probe` has no opinion about
    items = [("\u25be Part1", 0.04, 0), ("  \u25be \u62c9\u4f381", 0.16, 1),
             ("    \u8349\u56fe1", 0.26, 2), ("  \u25be \u62c9\u4f382", 0.38, 1),
             ("    \u8349\u56fe2", 0.48, 2), ("  \u25be \u5706\u89d21", 0.60, 1),
             ("  \u25be \u9635\u52171", 0.72, 1)]
    step = max(1, min(2, (k.bh - 2) // len(items)))
    for i, (label, at, d) in enumerate(items):
        if u < at:
            break
        y = k.by0 + 1 + i * step
        if y > k.by1 - 1:
            break
        k.put(k.bx0 + 1 + d, y, label[: max(0, k.bw - 2 - d)], _ui(0.8))


def _ind_model(k: _Kit, lt: float) -> None:
    """The viewport: the part as a wireframe that turns, because that is what the software shows."""
    k.frame(k.bx0, k.by0, k.bx1, k.by1, _ui(0.40), "")
    cx, cy = (k.bx0 + k.bx1) // 2, (k.by0 + k.by1) // 2
    rw, rh = max(4, (k.bx1 - k.bx0) // 3), max(2, k.bh // 3)
    ph = lt * 0.7
    for kk in range(4):
        th = ph + kk * math.pi / 2
        k.put(int(cx + rw * math.cos(th)), int(cy + rh * math.sin(th) * 0.5),
              "\u00b7", _mix(BLUE, 0.75))
    for kk in range(4):
        th0, th1 = ph + kk * math.pi / 2, ph + (kk + 1) * math.pi / 2
        x0 = int(cx + rw * math.cos(th0))
        y0 = int(cy + rh * math.sin(th0) * 0.5)
        x1 = int(cx + rw * math.cos(th1))
        y1 = int(cy + rh * math.sin(th1) * 0.5)
        k.put(min(x0, x1), min(y0, y1), "\u2571" if (x1 - x0) * (y1 - y0) > 0 else "\u2572",
              _mix(BLUE, 0.6))
    k.put(k.bx0 + 2, max(k.by0 + 1, k.by1 - 1), "isometric  \u00b1X \u00b1Y \u00b1Z", _ui(0.45))


def _ind_bom(k: _Kit, u: float) -> None:
    """The parts list: 件号 / 名称 / 材料 / 数量, which is the other half of what such software is."""
    k.section(k.by0, "BOM \u96f6\u4ef6\u8868", 0.28)
    rows = (("01", "\u7aef\u76d6", "45 \u94a2", "1"),
            ("02", "\u6df1\u6c9f\u7403\u8f74\u627f", "GCr15", "2"),
            ("03", "\u4e3b\u4f53", "ZL104", "1"),
            ("04", "\u87ba\u6813 M8", "Q235", "6"),
            ("05", "\u5bc6\u5c01\u5708", "\u4e01\u8148", "2"))
    c1, c2, c3 = 4, 11, 8
    # the guard is against the *column*, not against the pane: at the old 34 cells the left column of
    # a 111-cell pane is 30 wide and the whole parts list silently vanished, leaving a heading and
    # nothing under it - which is exactly what `pane_probe` cannot see and only a dump can.
    if k.bw < c1 + c2 + c3 + 2:
        return
    k.put(k.bx0, k.by0 + 1, _pad("\u4ef6\u53f7", c1) + _pad("\u540d\u79f0", c2)
          + _pad("\u6750\u6599", c3) + "\u6570\u91cf", _ui(0.5))
    k.hline(k.bx0, k.by0 + 2, k.bx1, BOX_H, _ui(0.22))
    show = min(len(rows), 1 + int(u * 6))
    for i, (no, name, mat, qty) in enumerate(rows[:show]):
        y = k.by0 + 3 + i
        if y > k.by1:
            break
        k.put(k.bx0, y, _pad(no, c1) + _pad(name, c2) + _pad(mat, c3) + qty,
              _ui(0.78) if i % 2 == 0 else _ui(0.6))


def _ind_explode(k: _Kit, u: float) -> None:
    """The exploded view: the same parts pulled apart along the assembly axis.

    Drawn as the parts flying out from a centre line, which is what the button in that software does
    and why anyone presses it: to see how the thing goes together without taking it apart.
    """
    k.section(k.by0, "\u7206\u70b8\u89c6\u56fe", 0.28)
    parts = (("\u7aef\u76d6", 10), ("\u8f74\u627f", 14), ("\u4e3b\u4f53", 18),
             ("\u87ba\u6813", 6), ("\u5bc6\u5c01\u5708", 8))
    # three rows per part - top edge, body, bottom edge - so a two-row gap draws part three's bottom
    # through part four's top, which is what the first version did
    room = max(0, (k.bh - 2) // 3)
    parts = parts[: max(1, room)]
    n = len(parts)
    gap = 3 if n < 2 else max(3, (k.bh - 2) // n)
    mid = k.bx0 + k.bw // 2
    out = int(3 * min(1.0, u * 1.4))                   # the parts fly out as the pane plays
    k.vline(mid, k.by0 + 1, k.by1, "\u254c", _ui(0.22))
    for i, (name, w) in enumerate(parts):
        y = k.by0 + 1 + i * gap
        if y + 2 > k.by1:
            break
        w = max(4, min(w, k.bw // 2 - 4))
        x0 = max(k.bx0, mid - w // 2 - i * out)
        x1 = min(k.bx1, x0 + w)
        shade = _mix(BLUE, max(0.35, 0.7 - 0.07 * i))
        k.put(x0, y, "\u250c" + BOX_H * max(0, x1 - x0 - 1) + "\u2510", shade)
        k.put(x0, y + 1, BOX_V + " " * max(0, x1 - x0 - 1) + BOX_V, _mix(BLUE, 0.45))
        k.put(x0, y + 2, "\u2514" + BOX_H * max(0, x1 - x0 - 1) + "\u2518", shade)
        k.put(min(x1 + 2, k.bx1 - 8), y + 1, "\u2460\u2461\u2462\u2463\u2464"[i] + " " + name, _ui(0.6))


def c_industrial(k: _Kit, lt: float, dur: float) -> None:
    """大型工业软件: the four panes the software itself has - tree, model, parts list, exploded view.

    Tall, it is all four: the tree and the parts list on the left, the viewport and the exploded view
    on the right. The first version drew only the tree and the wireframe into a thirty-row box, which
    left the middle of both columns empty and made an application window look like a screenshot with
    the content missing.
    """
    tree_w = max(14, min(30, k.bw // 3))
    left = k.sub(k.bx0, k.by0, k.bx0 + tree_w, k.by1)
    right = k.sub(k.bx0 + tree_w + 2, k.by0, k.bx1, k.by1)
    if right.bx1 - right.bx0 < 8:
        return
    if k.bh >= 20:
        lb = left.bands(2, [3, 2])
        rb = right.bands(2, [1, 1])
        if len(lb) == 2 and len(rb) == 2:
            _ind_tree(left.sub(left.bx0, lb[0][0], left.bx1, lb[0][1]), k.u)
            _ind_bom(left.sub(left.bx0, lb[1][0], left.bx1, lb[1][1]), k.u)
            _ind_model(right.sub(right.bx0, rb[0][0], right.bx1, rb[0][1]), lt)
            _ind_explode(right.sub(right.bx0, rb[1][0], right.bx1, rb[1][1]), k.u)
            return
    _ind_tree(left, k.u)
    _ind_model(right, lt)


def _ds_tree(k: _Kit, u: float) -> None:
    """The red-black tree, with a search path lit and the invariants written under it.

    Fifteen keys drawn as a complete tree of depth three, which is the shape a reader recognises and
    the shape that makes the height bound obvious. The colouring is by depth - even rows black, odd
    rows red - and is not arbitrary: it is the one colouring of *this* shape that satisfies all three
    invariants at once, which is the point of drawing them rather than writing them down.

    The node's depth is `(i + 1).bit_length() - 1`, not `i.bit_length() - 1`. The second form is the
    depth of the *one-indexed* node, and on the root it yields -1: the label came out eighty cells to
    the right of the column and the edges were interpolated from there, which is what a pane with a
    long stray diagonal in it looks like.
    """
    k.section(k.by0, "\u7ea2\u9ed1\u6811 \u00b7 \u63d2\u5165", 0.30)
    keys = [10, 5, 15, 3, 7, 12, 18, 1, 4, 6, 8, 11, 13, 17, 20]
    top = k.by0 + 2
    step = max(3, min(7, int(k.bh * 0.62 / 3)))
    tail = 5 if k.bh >= 18 else 1
    depth = 3 if k.bw >= 34 else 2
    while depth > 0 and top + depth * step > k.by1 - tail:
        depth -= 1
    n_nodes = 2 ** (depth + 1) - 1
    # the path a search for 8 takes, replayed on a short loop: one animation, on its own clock.
    #
    # **The path has four nodes, not three, and the last one is the point of it.** It used to be
    # `(0, 1, 4)` - keys 10, 5, 7 - which stops one step short of the key it is searching for: the whole
    # drawing is captioned "搜索 8" and the light never arrives at 8. Measured by replaying the search
    # over the array (batch 40): a lookup of 8 walks indices `[0, 1, 4, 10]`, i.e. keys 10 -> 5 -> 7 -> 8.
    # The reveal is divided over the four steps so the arrival is the last thing that happens.
    path = (0, 1, 4, 10)
    lit = set(path[: 1 + int(u * 3.99)])
    xs, ys = {}, {}
    for i in range(n_nodes):
        d = (i + 1).bit_length() - 1
        off = i - (2 ** d - 1)
        xs[i] = k.bx0 + 1 + int((k.bw - 4) * (2 * off + 1) / (2 ** (d + 1)))
        ys[i] = top + d * step
    # A ring of light walks the nodes for as long as the pane is up: `u` fills the tree in, the song's
    # clock searches it. The node it is on is green as well as ringed, because the ring alone is one
    # cell on a digit and `_dev/what_moves.py` counted the whole drawing as two moving cells.
    walk = int((k.t * 3.2) % max(1, n_nodes))
    for i in range(n_nodes):
        on = i == walk
        col = GREEN if on else (AMBER if i in lit else (RED if (i + 1).bit_length() % 2 == 0 else INK))
        k.put(xs[i], ys[i], str(keys[i]), _mix(col, 0.95))
        k.put(xs[i] - 1, ys[i], "\u25ce" if on else "\u25cf", _mix(col, 0.7))
    for i in range(1, n_nodes):
        p = (i - 1) // 2
        for y in range(ys[p] + 1, ys[i]):
            f = (y - ys[p]) / max(1, ys[i] - ys[p])
            k.put(int(xs[p] + (xs[i] - xs[p]) * f), y, "\\" if xs[i] > xs[p] else "/", _ui(0.3))
    if tail < 5:
        k.put(k.bx0, k.by1, f"\u63d2\u5165 {15 * u:4.0f}/15  \u00b7  \u9ed1\u9ad8\u76f8\u7b49", _ui(0.7))
        return
    # the counter and the invariants, in the space the leaves left behind
    done = int(round(15 * min(1.0, 0.45 + 0.55 * u)))
    k.put(k.bx0, k.by1 - 4, f"\u63d2\u5165 {done:2d}/15", _ui(0.7))
    bar = max(4, k.bw - 14)
    fill = int(bar * done / 15)
    k.put(k.bx0 + 10, k.by1 - 4, "\u2588" * fill, _mix(GREEN, 0.8))
    k.put(k.bx0 + 10 + fill, k.by1 - 4, "\u2591" * (bar - fill), _ui(0.3))
    for j, lab in enumerate(("\u2460 \u6839\u4e0e\u53f6\u4e3a\u9ed1",
                             "\u2461 \u7ea2\u7ed3\u70b9\u4e4b\u5b50\u5fc5\u9ed1",
                             "\u2462 \u5404\u8def\u5f84\u9ed1\u9ad8\u76f8\u7b49")):
        k.put(k.bx0, k.by1 - 2 + j, lab, _ui(0.78 if j == 0 else 0.62))


def _ds_curves(k: _Kit, u: float) -> None:
    """Three growth curves on one log-scaled axis, so that all three are curves.

    The first version plotted operations on a linear axis against the n-squared maximum, which is
    honest and useless: log n and n log n both lie flat on the x-axis and the pane becomes one red
    curve leaving the top of the box. Taking the logarithm of the operation count is what a textbook
    does with these three, and it is what makes the *ordering* - always log n below n log n below n
    squared, at every n, not just at the end - the thing the eye reads.
    """
    k.section(k.by0, "\u590d\u6742\u5ea6", 0.30)
    x0, x1 = k.bx0 + 2, k.bx1
    y0, y1 = k.by0 + 3, k.by1 - 4
    if x1 - x0 < 5 or y1 - y0 < 4:
        return
    k.vline(x0 - 1, y0, y1, BOX_V, _ui(0.35))
    k.hline(x0 - 1, y1, x1, BOX_H, _ui(0.35))
    n = x1 - x0 + 1
    grown = max(2, int(n * min(1.0, 0.20 + 0.80 * u)))
    span = y1 - y0
    denom = math.log2(1.0 + float((n + 1) ** 2))
    for f, col, lab in (
            (lambda x: math.log2(1 + x), GREEN, "log n"),
            (lambda x: (1 + x) * math.log2(1 + x), AMBER, "n log n"),
            (lambda x: float((1 + x) ** 2), RED, "n\u00b2")):
        last = y1
        for c in range(grown):
            y = y1 - int(span * math.log2(1.0 + f(c + 1)) / denom)
            y = max(y0, min(y1, y))
            k.put(x0 + c, y, "\u00b7", _mix(col, 0.9))
            last = y
        k.put(min(x0 + grown + 1, k.bx1 - _cells(lab)), max(y0, last - 1), lab, _mix(col, 0.95))
    k.put(k.bx0, k.by1 - 2, "\u6a2a\u8f74 = \u5143\u7d20\u4e2a\u6570 n", _ui(0.5))
    k.put(k.bx0, k.by1 - 1, "\u7eb5\u8f74 = \u64cd\u4f5c\u6b21\u6570\uff08\u53d6\u5bf9\u6570\uff09", _ui(0.5))


def _ds_shapes(k: _Kit, top: int, u: float) -> None:
    """The same six keys in the two shapes the note under the table is about.

    A chain and a balanced tree, drawn next to each other, because "二叉搜索树最坏退化成链" is a
    sentence and a chain beside a bushy tree is the reason the sentence is worth remembering.
    """
    if k.by1 - top < 13 or k.bw < 30:
        return
    k.section(top, "\u540c\u4e00\u7ec4\u952e\uff0c\u4e24\u79cd\u5f62\u72b6", 0.30)
    y = top + 2
    # 1, 2, 3, 4, 5, 6 inserted in order: a binary search tree with nothing to balance it is a list
    for i in range(6):
        k.put(k.bx0 + 1 + i * 2, y + i, "\u25cf", _mix(RED, 0.85))
        if i < 5:
            k.put(k.bx0 + 2 + i * 2, y + i + 1, "\\", _ui(0.35))
    k.put(k.bx0 + 1, y + 7, "\u987a\u5e8f\u63d2\u5165 \u2192 \u94fe", _mix(RED, 0.85))
    k.put(k.bx0 + 1, y + 8, "\u9ad8 6", _mix(RED, 0.9))
    # the same six keys in a shape a rebalancing insertion would have built instead
    bx = k.bx0 + 20
    xs = ((3, 0), (1, 2), (5, 2), (0, 4), (2, 4), (4, 4), (6, 4))
    step = max(1, min(3, (k.bw - 21) // 6))
    for i in range(1, 7):
        x0p, y0p = xs[(i - 1) // 2]
        x1p, y1p = xs[i]
        for yy in range(y + y0p + 1, y + y1p):
            f = (yy - y - y0p) / max(1, y1p - y0p)
            k.put(int(bx + (x0p + (x1p - x0p) * f) * step), yy,
                  "\\" if x1p > x0p else "/", _ui(0.3))
    for dx, dy in xs:
        k.put(bx + dx * step, y + dy, "\u25cf", _mix(GREEN, 0.85))
    k.put(bx, y + 7, "\u91cd\u5e73\u8861 \u2192 \u9ad8 3", _mix(GREEN, 0.85))


def _ds_table(k: _Kit, u: float) -> None:
    """The revision table: what goes on the back of a hand before the exam."""
    k.section(k.by0, "\u5bf9\u7167", 0.30)
    rows = (("\u6570\u7ec4", "O(1)", "O(1)"),
            ("\u94fe\u8868", "O(n)", "O(n)"),
            ("\u4e8c\u53c9\u641c\u7d22\u6811", "O(log n)", "O(n)"),
            ("\u7ea2\u9ed1\u6811", "O(log n)", "O(log n)"),
            ("\u54c8\u5e0c\u8868", "O(1)", "O(n)"),
            ("\u5806", "O(1) \u6700\u5c0f", "O(1) \u6700\u5c0f"))
    c1, c2 = 12, 9
    if k.bw < c1 + 2 * c2:
        return
    y = k.by0 + 2
    k.put(k.bx0, y, _pad("\u7ed3\u6784", c1) + _pad("\u5e73\u5747", c2, True)
          + _pad("\u6700\u574f", c2, True), _ui(0.55))
    k.hline(k.bx0, y + 1, k.bx1, BOX_H, _ui(0.25))
    show = min(len(rows), 1 + int(u * 8))
    end = y + 1
    for i, (a, b, c) in enumerate(rows):
        if i >= show:
            break
        yy = y + 2 + i * 2
        if yy > k.by1 - 6:
            break
        end = yy
        k.put(k.bx0, yy, _pad(a, c1) + _pad(b, c2, True) + _pad(c, c2, True),
              _mix(AMBER, 0.95) if a == "\u7ea2\u9ed1\u6811" else _ui(0.82 if i % 2 == 0 else 0.62))
        if i < len(rows) - 1:
            k.hline(k.bx0, yy + 1, k.bx1, "\u00b7", _ui(0.18))
    _ds_shapes(k, end + 2, u)
    k.put(k.bx0, k.by1 - 3, "\u4e8c\u53c9\u641c\u7d22\u6811\u6700\u574f\u9000\u5316\u6210\u94fe\u3002", _ui(0.55))
    k.put(k.bx0, k.by1 - 2, "\u7ea2\u9ed1\u6811\u628a\u6700\u574f\u4e5f\u505a\u5230 O(log n)\uff0c", _mix(GREEN, 0.8))
    k.put(k.bx0, k.by1 - 1, "\u8fd9\u5c31\u662f\u5b83\u503c\u5f97\u5b58\u7684\u539f\u56e0\u3002", _mix(GREEN, 0.8))


def _algo_recurse(k: _Kit, u: float) -> None:
    """Divide and conquer: the recursion tree of a merge sort, splitting down and merging up."""
    k.section(k.by0, "\u5206\u6cbb \u00b7 \u5f52\u5e76\u6392\u5e8f", 0.30)
    top = k.by0 + 2
    depth = 3 if k.bh >= 16 else 2
    step = max(2, min(5, (k.bh - 6) // max(1, depth)))
    w = k.bw - 2
    for d in range(depth + 1):
        n = 2 ** d
        y = top + d * step
        if y > k.by1 - 3:
            break
        if d >= 1 and u < 0.15 * d:
            break
        for i in range(n):
            x = k.bx0 + 1 + int(w * (2 * i + 1) / (2 * n))
            # the level being split right now, on the song's clock: the tree is built by `u` and worked on
            # by `k.t`, so the pane has a recursion *running* in it rather than a finished diagram
            live = int(k.t * 3) % max(1, depth + 1)
            k.put(x, y, "\u25aa",
                  _mix(AMBER if d == live else BLUE, 0.95 if d == live else 0.85 - 0.1 * d))
            if d:
                px = k.bx0 + 1 + int(w * (2 * (i // 2) + 1) / (2 ** d))
                for yy in range(y - step + 1, y):
                    f = (yy - (y - step)) / max(1, step)
                    k.put(int(px + (x - px) * f), yy,
                          "\\" if x > px else ("/" if x < px else BOX_V), _ui(0.22))
    if u > 0.5:
        y = min(k.by1, top + depth * step + 1)
        k.put(k.bx0, y, "\u5206\u5230\u53ea\u5269\u4e00\u4e2a\uff0c\u518d\u5408\u5e76\u4e0a\u53bb",
              _mix(GREEN, 0.8))
        k.put(k.bx0, min(k.by1, y + 1), "T(n) = 2T(n/2) + O(n) = O(n log n)", _ui(0.6))


def _algo_dp(k: _Kit, u: float) -> None:
    """Dynamic programming: a real LCS table, filling, with the recurrence printed under it.

    The table is computed rather than decorated - nine by nine is sixty-four additions - because a
    decorative table full of plausible-looking numbers next to the word "LCS" is the kind of drawing
    that teaches nothing and, the first time someone checks it, is wrong. It also gives the reveal
    something true to be a reveal *of*: row by row, the way the recurrence fills it.
    """
    k.section(k.by0, "\u52a8\u6001\u89c4\u5212 \u00b7 LCS", 0.30)
    n = min(8, max(4, (k.bw - 8) // 4), max(2, (k.bh - 6)))
    if n < 3:
        return
    A, B = "NWPUSOFT", "NWUNWPU!"
    a, b = A[:n], B[:n]
    dp = [[0] * (n + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i - 1][j], dp[i][j - 1])
    k.put(k.bx0 + 4, k.by0 + 2, " ".join(b), _ui(0.55))
    for j, ch in enumerate(a):
        k.put(k.bx0 + 1, k.by0 + 3 + j, ch, _ui(0.55))
    filled = int((n + 1) * (n + 1) * min(1.0, u * 1.25))
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if (i - 1) * (n + 1) + j >= filled:
                continue
            match = a[i - 1] == b[j - 1]
            k.put(k.bx0 + 4 + j * 2, k.by0 + 3 + i, f"{dp[i][j]}",
                  _mix(AMBER, 0.95) if match else _ui(0.55))
    # the two halves of the recurrence, one after the other. The first version put the `if/else` on the
    # *colour* argument by accident, so half the time the pane passed a string where an RGB tuple goes
    # and `render` raised - `pane_probe` caught it at u=0.85, where the else branch is the live one.
    line = ("a[i]==b[j]: dp[i][j] = dp[i-1][j-1] + 1" if u < 0.5
            else "\u5426\u5219 = max(dp[i-1][j], dp[i][j-1])")
    # both captions sit under the *table*, not on the pane's last row: a caption pinned to `by1` makes
    # `_last_ink` answer "the last row", and the terms footer then never has a band to go in
    ly = min(k.by1 - 1, k.by0 + 4 + n)
    k.put(k.bx0, ly, line, _mix(GREEN, 0.8) if u < 0.5 else _ui(0.6))
    k.put(k.bx0, min(k.by1, ly + 1), "\u628a\u91cd\u7b97\u7684\u90e8\u5206\u5b58\u8d77\u6765\uff0c"
                                     "\u5c31\u662f\u52a8\u6001\u89c4\u5212\u7684\u5168\u90e8", _ui(0.5))


def _algo_greedy(k: _Kit, u: float) -> None:
    """Greedy: intervals sorted by end time, and the ones a greedy choice keeps.

    **The selection is computed now, and it used to be a hard-coded guess that was wrong twice over.**
    The rows were `(i * 7) % 20` and the picks were `[0, 2, 5, 7]`, which meant:

      * the rows were **not sorted by end time** - the ends ran 4, 12, 20, 5, 13, 21, 6, 14 - while the
        caption under them says `按结束时间排序`, and sorting by end time is the *entire* first step of
        this algorithm. A reader checking the drawing against the label found them disagreeing;
      * worse, the chosen set **overlapped itself**: C was [14, 20] and F was [15, 21], and an interval
        scheduler that returns two overlapping intervals is not a scheduler.

    Both were measured by replaying the code's own arithmetic (batch 40). The intervals are now sorted by
    end time and the picks come out of the real greedy rule - take the earliest-finishing interval, then
    the next one that starts after it ends - so the picture, the caption and the algorithm agree.
    """
    k.section(k.by0, "\u8d2a\u5fc3 \u00b7 \u533a\u95f4\u8c03\u5ea6", 0.30)
    rows = max(3, min(8, k.bh - 5))
    span = max(6, k.bw - 14)
    # 1. the intervals, **sorted by end time** (the algorithm's own first step, now actually done)
    ivs = sorted(((2, 6), (0, 4), (7, 12), (1, 5), (9, 14), (8, 13), (15, 21), (14, 20)),
                 key=lambda z: (z[1], z[0]))
    # 2. the greedy sweep: keep an interval if it starts after the last one kept has ended
    picks, last = set(), -1
    for idx, (st, en) in enumerate(ivs):
        if st >= last:
            picks.add(idx)
            last = en
    for i in range(rows):
        y = k.by0 + 2 + i
        if y > k.by1 - 2 or i >= len(ivs):
            break
        st, en = ivs[i]
        x0 = k.bx0 + 6 + int(span * st / 24)
        x1 = k.bx0 + 6 + int(span * min(24, en) / 24)
        keep = i in picks and u > 0.4
        k.put(k.bx0, y, f"{chr(65 + i)}", _ui(0.6))
        k.put(x0, y, "\u2591" * max(1, x1 - x0), _mix(GREEN, 0.85) if keep else _ui(0.25))
        if keep:
            k.put(x1 + 1, y, "\u2190 \u9009", _mix(GREEN, 0.8))
    k.put(k.bx0, min(k.by1, k.by0 + 3 + min(rows, len(ivs))),
          f"\u6309\u7ed3\u675f\u65f6\u95f4\u6392\u5e8f\uff0c\u80fd\u63a5\u4e0a\u5c31\u63a5\uff1a"
          f"\u9009\u51fa {len(picks)} \u4e2a\uff0c\u4e24\u4e24\u4e0d\u91cd\u53e0",
          _ui(0.5))


def c_algo(k: _Kit, lt: float, dur: float) -> None:
    """算法设计: three paradigms side by side, each on its own clock.

    The course used to share `pane_exec_ds` with 数据结构, which meant it never had a drawing of its own -
    the tree and the complexity curves are *data structures*, and the second half of the course (分治、
    动态规划、贪心) had no picture in the film at all. Three columns: the recursion tree splitting and
    merging, a DP table filling, and a greedy scan that keeps some intervals and drops the rest.
    """
    if k.bw >= 64 and k.bh >= 18:
        cols = k.columns(3, [1, 1, 1], mins=[26, 30, 22])
        if len(cols) == 3:
            for i, fn in enumerate((_algo_recurse, _algo_dp, _algo_greedy)):
                cx0, cx1 = cols[i]
                if i:
                    k.vline(cx0 - 2, k.by0, k.by1, BOX_V, _ui(0.18))
                fn(k.sub(cx0, k.by0, cx1, k.by1), k.u)
            return
    _algo_recurse(k, k.u)


def c_ds_algo(k: _Kit, lt: float, dur: float) -> None:
    """数据结构 + 算法设计, in one pane.

    These two share a pane because they share a picture: a red-black tree whose heights are the
    *proof* that the algorithm is O(log n), the curves that show what the proof buys, and the table
    that says what it costs against the structures that do not give it.

    The pane is wide and it is now tall, so the three drawings are **columns**, not a stack. Stacked,
    each one is thirty cells of content in a hundred and thirty cell row and the pane reads as three
    quarters empty; side by side the same three fill it. The columns also run on three different
    clocks - the tree walks a search path, the curves grow with n, the table fills a row at a time -
    which is what stops a full-width pane from being one slow reveal.
    """
    w, h = k.bw, k.bh
    if h < 5:
        return
    if w >= 64 and h >= 18:
        # **The minimums have to fit the pane the film actually has.** They were `[40, 26, 30]`, and
        # `columns` needs `sum(need) + 2 * (n - 1)` = 100 columns before it will lay out three of them -
        # while this pane's body is **95** at 197x52. So the three-column branch *never ran*: every frame
        # of this pane in the whole film fell through to the stacked fallback below, which is the layout
        # the docstring argues against, and the tree got eleven rows instead of twenty-eight. Dumped by
        # batch 40 (`_dev/_b40_dump_ds.py`): the tree was one full-width band at y04-y14 and the two
        # other drawings sat under it with six empty rows between.
        #
        # The minimums are what each drawing needs to be *legible*, not what it would like: the tree's
        # width is the widest leaf row, and the two smaller ones fit narrower than they asked. At 95 the
        # three now fit with room to spare, and at narrower sizes the fallback still catches it.
        #
        # **Each minimum is a number the drawing checks for itself.** `_ds_table` returns immediately
        # when it has fewer than `12 + 2 * 9 = 30` columns, so a 26 here did not give the table a narrow
        # column - it gave it *no column at all*, and the third of the pane came out empty. The first
        # version of this fix had exactly that bug and the frame dump caught it; the minimums below are
        # read off the guards inside the three drawings rather than guessed.
        cols = k.columns(3, [10, 7, 9], mins=[34, 22, 30])
        if len(cols) == 3:
            for i, fn in enumerate((_ds_tree, _ds_curves, _ds_table)):
                cx0, cx1 = cols[i]
                if i:
                    k.vline(cx0 - 2, k.by0, k.by1, BOX_V, _ui(0.18))
                fn(k.sub(cx0, k.by0, cx1, k.by1), k.u)
            return
    # Narrow or short: the same content stacked, which is the honest way to lose width.
    bands = k.bands(3, [5, 3, 3]) if h >= 24 else (k.bands(2, [2, 1]) if h >= 13 else k.bands(1))
    if not bands:
        return
    _ds_tree(k.sub(k.bx0, bands[0][0], k.bx1, bands[0][1]), k.u)
    if len(bands) >= 2:
        _ds_curves(k.sub(k.bx0, bands[1][0], k.bx1, bands[1][1]), k.u)
    if len(bands) >= 3:
        _ds_table(k.sub(k.bx0, bands[2][0], k.bx1, bands[2][1]), k.u)


# --------------------------------------------------------------------------- the six instruments

def g_burndown(k: _Kit, lt: float, dur: float) -> None:
    """软件项目管理: a Sprint burndown that is not going to make it.

    The ideal line is straight and grey; the actual line is drawn from real-looking daily numbers and
    is above it, and it stays above it. That is the whole reason to draw a burndown instead of saying
    "the sprint is behind": the gap is visible.
    """
    w, h = k.bw, k.bh
    days = 10
    for d in range(days + 1):
        x = k.bx0 + 2 + int((w - 6) * d / days)
        k.put(x, k.by1 - 1, "\u252c", _ui(0.3))
    ideal = [(0, 100), (10, 0)]
    for d in range(days + 1):
        x = k.bx0 + 2 + int((w - 6) * d / days)
        y = k.by1 - 2 - int((h - 3) * (1 - d / days))
        k.put(x, y, "\u00b7", _ui(0.35))
    actual = [100, 96, 88, 85, 74, 70, 66, 61, 58, 52, 50]
    shown = 1 + int(k.u * days)
    for d in range(shown):
        x = k.bx0 + 2 + int((w - 6) * d / days)
        y = k.by1 - 2 - int((h - 3) * actual[d] / 100.0)
        k.put(x, y, "\u25cf", _mix(AMBER, 0.95))
        if d:
            xp = k.bx0 + 2 + int((w - 6) * (d - 1) / days)
            yp = k.by1 - 2 - int((h - 3) * actual[d - 1] / 100.0)
            k.put(min(x, xp) + 1, min(y, yp) + 1, "\u2571" if y < yp else "\u2572", _mix(AMBER, 0.7))
    k.put(k.bx0, k.by0, "\u5728\u8dd1\u4e0d\u5b8c\u7684 Sprint", _ui(0.8))
    # the legend names the glyphs the drawing actually uses: the ideal line is `·` (drawn above), not
    # `─`. A legend that shows a solid rule for a dotted line is the smallest possible lie, and this pane
    # got it wrong for its whole life. (Batch 42, by reading the two lines together.)
    k.put(k.bx1 - 16, k.by0, "ideal \u00b7  actual \u25cf", _ui(0.45))


def g_pareto(k: _Kit, lt: float, dur: float) -> None:
    """软件测试: a defect Pareto chart with its cumulative line.

    Bars descending, cumulative percentage rising, and the 80 % rule marked. A toolbar of defects
    drawn this way says which few things are worth fixing, which is the only decision this course
    makes.
    """
    w, h = k.bw, k.bh
    bars = [42, 27, 15, 9, 5, 2]
    labels = ["\u7a7a\u6307\u9488", "\u8d8a\u754c", "\u7ade\u6001", "\u5185\u5b58", "\u7cbe\u5ea6", "\u5176\u4ed6"]
    n = len(bars)
    bw = max(3, min(9, (w - 4) // n - 1))
    base = k.by1 - 1
    # This instrument gets 0.44 s - the shortest slot in the song - so the bars grow fast and start
    # visible: the first version skipped any bar whose reveal had not begun, and at the frame the pane
    # appeared the whole chart was one axis label and twelve lit cells (`_dev/span_probe.py`).
    for i, v in enumerate(bars):
        x = k.bx0 + 2 + i * (bw + 1)
        if x + bw > k.bx1:
            break
        hgt = max(1, int((h - 4) * v / 45.0))
        grown = max(1, int(hgt * min(1.0, k.u * 3.2 - i * 0.18)))
        for yy in range(hgt):
            if yy >= grown:
                k.put(x, base - 1 - yy, "\u2591" * bw, _ui(0.16))
                continue
            k.put(x, base - 1 - yy, "\u2588" * bw, _mix(BLUE, 0.55 + 0.02 * yy))
        k.put(x, base, labels[i][:bw], _ui(0.5))
    # **The cumulative curve the legend has claimed all along.** The corner has read `cum 80% ──` - with
    # a line glyph in it - since the pane was written, and a census of the rendered frame found **zero
    # amber cells**: the one thing that makes a Pareto chart a Pareto chart was missing, and the label
    # was pointing at nothing. The `──` was a legend for a curve that was never drawn.
    #
    # The numbers were always here: 42, 27, 15, 9, 5, 2 sums to 100, so the running total is
    # 42 / 69 / 84 / 93 / 98 / 100 % and it crosses 80 % **on the third bar** - which is the reading the
    # instrument exists to give ("these three defect classes are four fifths of everything"). Drawn over
    # the bars, amber, one dot per bar and a dotted run between them, revealing with `u` like the bars.
    run, pts = 0, []
    for i, v in enumerate(bars):
        x = k.bx0 + 2 + i * (bw + 1) + bw // 2
        if x > k.bx1:
            break
        run += v
        pts.append((x, base - 1 - int((h - 4) * min(1.0, run / 100.0))))
    shown = max(1, int(len(pts) * min(1.0, k.u * 1.3)))
    for i in range(shown):
        x, y = pts[i]
        if i:
            xp, yp = pts[i - 1]
            for xx in range(xp, x + 1):
                t = (xx - xp) / max(1, x - xp)
                k.put(xx, int(round(yp + (y - yp) * t)), "\u00b7", _mix(AMBER, 0.8))
        k.put(x, y, "\u25cf", _mix(AMBER, 0.95))
    k.put(k.bx0, k.by0, "defect pareto", _ui(0.8))
    k.put(k.bx1 - 14, k.by0, "cum 80% \u2500\u2500", _mix(AMBER, 0.9) if k.u > 0.75 else _ui(0.3))


def g_attention(k: _Kit, lt: float, dur: float) -> None:
    """深度学习: an attention heat map, with the diagonal lighting up.

    A grid of query-by-key weights where the softmax concentrates on the diagonal as the head trains;
    the bright band is the model learning to look at the token itself. It is drawn as a heat map
    because that is how the paper draws it, and because intensity across a grid is the one thing a
    terminal does well.
    """
    w, h = k.bw, k.bh
    n = max(6, min(18, min(w - 8, (h - 3) * 2)))
    x0, y0 = k.bx0 + 5, k.by0 + 1
    # **A real softmax.** The old line was `focus = min(0.92, k.u * 1.1)` - the pane's own *progress* -
    # printed as `softmax focus {focus:.2f}`, and the cell values were the literals 3/2/1/0 chosen by
    # `abs(c-r)`. So the number on screen was styled as a softmax report and was in fact a progress bar,
    # and the heat map never contained a probability. Now the scores are real (a training run that
    # sharpens the diagonal as it goes), the softmax is the real normalisation `exp(s)/Σexp(s)` per row,
    # and what is printed is the **diagonal's own weight** - the quantity the sentence claims and the
    # thing attention does. Batch 37's maths audit flagged the label; the arithmetic is this batch's.
    sharp = 0.7 + 4.3 * min(1.0, k.u * 1.15)          # how peaked the head's scores are, training
    head = hash((int(lt * 0.5), 3)) % 3               # which head this frame is showing: a slow rotation
    diag_w = 0.0
    for r in range(n):
        y = y0 + r // 2
        if y > k.by1:
            break
        if r % 2 == 0:
            k.put(k.bx0 + 1, y, f"{r:2d}", _ui(0.4))
        # the row's scores: this head attends to itself and to a neighbour that drifts
        scores = []
        for c in range(n):
            jitter = ((hash((r, c, head, int(lt * 0.35))) % 100) - 50) / 500.0
            s = sharp * (1.0 if c == r else 0.0) + (0.55 if abs(c - r) == 1 else 0.0) + jitter
            scores.append(s)
        mx = max(scores)
        ex = [math.exp(s - mx) for s in scores]
        z = sum(ex) or 1.0
        p = [e / z for e in ex]
        diag_w = max(diag_w, p[r] if r < len(p) else 0.0)
        for c in range(n):
            if x0 + c > k.bx1:
                break
            prob = p[c]
            # the shade *is* the probability: 0.05 of the row's mass is one dot, the diagonal is solid
            if prob >= 0.55:
                v = 3
            elif prob >= 0.25:
                v = 2
            elif prob >= 0.10:
                v = 1
            else:
                v = 0
            k.put(x0 + c, y, SHADE[v],
                  _mix(AMBER if c == r else BLUE, 0.3 + 0.7 * min(1.0, prob * 2.2)))
    k.put(k.bx0, k.by0, f"attention  head {head + 1}", _ui(0.8))
    # ...on `by1 - 1`, not `by1`: the shared gauge cursor (`_gauge_live`) draws its rule and its moving
    # triangle across the whole of the bottom row, so the readout printed there was erased every frame.
    # The batch-37 probe caught it - the line was in the code and never on the screen.
    k.put(k.bx0, max(k.by0, k.by1 - 1), f"softmax  \u03a3e^s \u2192 diag {diag_w:.2f}  n={n}", _ui(0.55))


def g_fem(k: _Kit, lt: float, dur: float) -> None:
    """工业模型: a finite-element mesh over the *part*, refined where the stress is.

    A structured grid with a denser patch, and the stress field as shading. The refinement is the
    content: an FEM model is a decision about where to spend elements.

    The grid is clipped to the shape of the part - an aerofoil section, which is the thing this school
    actually meshes - and that clip is what the panel was missing. Drawn edge to edge it covered 87 % of
    the pane in `-` and `+`, which is not a mesh, it is a wall of ink: the user's note about 杂乱 is
    exactly this. Outside the part there is nothing, which is also what the software shows.
    """
    w, h = k.bw, k.bh
    if h < 4:
        return
    k.put(k.bx0, k.by0, "mesh  4820 nodes  9,318 elements", _ui(0.75))
    y0 = k.by0 + 1
    rows = max(1, h - 3)
    denom = float(max(1, rows - 1))
    # **Alternating edge rows: horizontal edges on one row, vertical edges on the next.** The caption
    # says `mesh` and the census said otherwise - a rendered frame had **1052 horizontal rules and
    # zero** `│` - so what the panel drew was a stack of dashes inside an aerofoil outline: the part's
    # silhouette was right and the *mesh* was missing, which is the one thing this instrument is about.
    # (Batch 40, by glyph census: `U+2500 x1052, U+2502 x0`.)
    #
    # A structured mesh in a cell grid is a lattice of crossings, and a crossing needs both directions.
    # Drawing every row as `┼ ─ ─ ┼ ─ ─ ┼` gives horizontals but no verticals, because the rows are
    # adjacent and a `│` would have to live *between* two rows that already have ink. Alternating solves
    # it at no cost in ink: node rows carry `┼` at the nodes and `─` between them, and the rows between
    # carry `│` at the nodes only - which, next to the `┼` above and below, reads as a continuous
    # vertical edge through the crossing. Same cell count as before, and now it is a mesh.
    for r in range(rows):
        y = y0 + r
        if y > k.by1:
            break
        # the section: thick at the leading edge, tapering aft, with a camber line
        f = r / denom
        thick = 0.30 * (1.0 - f) ** 0.6 + 0.06
        camber = 0.18 * f * f
        mid = 0.45 + camber
        lo, hi = mid - thick, mid + thick
        dense = 3 <= r <= 5
        edge_row = bool(r % 2)                       # vertical-edge row: nodes only
        step = 3 if dense else 7
        for c in range(w - 2):
            fc = c / float(max(1, w - 3))
            if not (lo <= fc <= hi):
                continue
            node = c % step == 0
            if edge_row and not node:
                continue                             # the cell between two vertical edges stays empty
            inside = abs(fc - mid) < thick * 0.35
            if edge_row:
                ch = "\u2502"
            else:
                ch = "\u253c" if node else "\u2500"
            k.put(k.bx0 + 1 + c, y, ch,
                  _mix(RED if (dense and inside) else (BLUE if dense else DIM),
                       0.7 if dense else 0.35))
    if k.u > 0.5:
        k.put(k.bx0 + 6, y0 + 4, "\u25b2 \u5e94\u529b\u96c6\u4e2d", _mix(RED, 0.9))
    k.put(k.bx0, k.by1, "\u7f51\u683c\u53ea\u5728\u96f6\u4ef6\u4e0a\uff0c"
                        "\u96f6\u4ef6\u5916\u9762\u4ec0\u4e48\u90fd\u6ca1\u6709", _ui(0.5))


def g_assembly(k: _Kit, lt: float, dur: float) -> None:
    """大型工业软件: an exploded assembly view.

    Parts separated along an axis with leader lines back to where they belong. The separation is
    animated because an exploded view is a *motion* - it exists to show the order things go together.
    """
    w, h = k.bw, k.bh
    if h < 4:
        return
    # **The boxes no longer collide, and the header counts what is drawn.** Two separate contradictions
    # were measured here (batch 42):
    #
    #   * the header said `BOM 41 parts` while the loop drew at most six, so the number was a claim about
    #     a bill of materials that the picture did not support - and anyone counting the boxes found a
    #     different film from the one the caption describes. The count now comes from the loop;
    #   * at `w = 95` the last two boxes overlapped: `cx = min(cx + sep, k.bx1 - 6)` clamps *every* box
    #     past the right edge onto the same column, so P5 sat at 83..89 and P6 at 89..95 and they shared
    #     column 89. An exploded view whose parts are inside each other is not exploded. The step is now
    #     solved from the width so the boxes fit, and the separation is capped at what is left over.
    n = max(3, min(8, (w - 4) // 8))
    # the room each box may travel in, before it would touch the next one: six cells of box plus a gap
    step = max(0.0, (w - 8) / max(1, n))
    sep = int(k.u * min(w // 4, max(0, step - 7)))
    k.put(k.bx0, k.by0, f"assembly  BOM {n} parts", _ui(0.75))
    for i in range(n):
        # the home position, spread across the width so nothing is clamped on top of anything else
        home = k.bx0 + 3 + int(step * i)
        cx = min(home + sep, k.bx1 - 6)
        if cx <= k.bx0 + 1:
            continue
        yy = k.by0 + 2 + (i % 2)
        k.frame(cx, yy, cx + 6, min(yy + 2, k.by1), _mix(BLUE, 0.6))
        k.put(cx + 2, yy + 1, f"P{i + 1}", _ui(0.7))
        k.put(cx + 3, min(yy + 3, k.by1), BOX_V, _ui(0.3))
    if k.u > 0.4:
        k.put(k.bx0, k.by1, "explode  \u2190\u2500\u2500\u2500\u2500\u2500\u2500\u2192", _ui(0.5))


def g_final(k: _Kit, lt: float, dur: float) -> None:
    """毕业设计: a Gantt chart with exactly one bar on it.

    The joke is the drawing: every other pane in this bar is dense, and this one is a single line
    called 毕设 running off the end of the chart. It is the last number in the countdown, so it is
    also the honest one.
    """
    w = k.bw
    k.put(k.bx0, k.by0, "Gantt  \u6bd5\u4e1a\u8bbe\u8ba1", _ui(0.8))
    x0 = k.bx0 + 8
    span = max(6, k.bx1 - x0 - 2)
    months = max(4, min(12, span // 5))
    for m in range(months + 1):
        x = x0 + int(span * m / months)
        k.put(x, k.by0 + 2, "\u252c", _ui(0.3))
    if k.bh > 4:
        y = k.by0 + 4
        k.put(k.bx0, y, "\u6bd5\u8bbe", _mix(AMBER, 0.9))
        # the track is drawn from the first frame and the bar fills along it: in a 0.53 s slot a bar
        # that only exists once `u` has moved is a pane that shows an axis and nothing else
        k.put(x0, y, BOX_H * span, _ui(0.16))
        grow = max(1, int(span * min(1.0, k.u * 1.2)))
        k.put(x0, y, "\u2588" * grow, _mix(AMBER, 0.85))
        k.put(min(x0 + grow + 1, k.bx1 - 4), y, "???", _mix(RED, 0.9) if k.u > 0.8 else _ui(0.3))
    if k.bh > 6:
        k.put(k.bx0, k.by1, "\u5b83\u6ca1\u6709\u7ec8\u70b9", _ui(0.55))


GAUGES = {
    "g_burndown": g_burndown,
    "g_pareto": g_pareto,
    "g_attention": g_attention,
    "g_fem": g_fem,
    "g_assembly": g_assembly,
    "g_final": g_final,
}


def _split(k: _Kit, parts) -> None:
    """Draw `parts` side by side in one pane, each in its own half.

    Used where two courses share a "Execution" hit because the hit is too short to carry one drawing
    on its own (`school_panels.EXEC_ROWS`). Splitting is done here rather than in the table so the
    durations stay the table's business and the layout stays the drawing's.
    """
    n = len(parts)
    if n == 1:
        parts[0](k)
        return
    total = k.bx1 - k.bx0 + 1
    for i, fn in enumerate(parts):
        sub_x0 = k.bx0 + (total * i) // n
        sub_x1 = k.bx0 + (total * (i + 1)) // n - 2
        if sub_x1 - sub_x0 < 8:
            continue
        if i and sub_x0 - 1 >= k.bx0:
            k.vline(sub_x0 - 1, k.by0, k.by1, BOX_V, _ui(0.22))
        fn(k.sub(sub_x0, k.by0, sub_x1, k.by1))


# --------------------------------------------------------------------------- the dispatch

# The pane name is the key, and it is the *only* place a course's name is written: `school_panels`
# builds its schedule from these keys and reads the titles back out, so the two files cannot drift.
# A `pane_gauge_` key is one of the six instruments of the countdown; everything else is a course.
def c_compiler(k: _Kit, lt: float, dur: float) -> None:
    """编译原理: the pipeline from characters to a program, with a parse tree on it.

    The course the curriculum names that no pane drew - the user asked me to check the drawings once the
    curriculum changed, and this was the gap. 词法 → 语法 → 语义 →
    中间代码 → 目标代码 across the box, the expression the front end
    is chewing under them, and a cursor that walks the five stages on the song clock.
    """
    w = k.bw
    if w < 24 or k.bh < 5:
        return
    stages = ["词法", "语法", "语义", "中间代码", "目标代码"]
    bw = max(6, (w - 2 * (len(stages) - 1)) // len(stages))
    step = bw + 2
    live = int(k.t * 1.4) % len(stages)
    for i, name in enumerate(stages):
        bx = k.bx0 + i * step
        if bx + bw - 1 > k.bx1:
            break
        k.frame(bx, k.by0, bx + bw - 1, k.by0 + 2, _mix(BLUE, 0.9 if i == live else 0.45), name)
        if i < len(stages) - 1 and bx + bw <= k.bx1:
            k.put(bx + bw, k.by0 + 1, "→", _mix(AMBER, 0.9 if i == live else 0.35))
    k.put(k.bx0, k.by0 + 4, "a = b + c * d", _ui(0.85))
    if k.bh >= 9:
        cx, cy = k.bx0 + 8, k.by0 + 6
        nodes = [("=", cx + 8, cy), ("a", cx + 2, cy + 2), ("+", cx + 8, cy + 2),
                 ("b", cx + 5, cy + 4), ("*", cx + 11, cy + 4),
                 ("c", cx + 9, cy + 6), ("d", cx + 13, cy + 6)]
        edges = ((8, 0, 2, 2), (8, 0, 8, 2), (8, 2, 5, 4), (8, 2, 11, 4), (11, 4, 9, 6), (11, 4, 13, 6))
        for ex0, ey0, ex1, ey1 in edges:
            y = cy + (ey0 + ey1) // 2
            if y <= k.by1 - 1:
                k.put(cx + ex0, y, "╲" if ex1 >= ex0 else "╱", _ui(0.3))
        for ch_, x_, y_ in nodes:
            if y_ <= k.by1 - 1:
                k.put(x_, y_, ch_, _mix(GREEN, 0.9))
    if k.bh >= 6:
        k.put(k.bx0, k.by1, "词法到目标代码：一个程序"
                            "是怎么被读进去的", _ui(0.5))


COURSES: dict[str, tuple[str, object, tuple | None]] = {
    "pane_exec_embedded": ("\u5d4c\u5165\u5f0f\u7535\u5b50\u5fae\u7cfb\u7edf", c_embedded, None),
    "pane_exec_c": ("\u7a0b\u5e8f\u8bbe\u8ba1\uff08C\uff09", c_c, None),
    "pane_exec_ds": ("\u6570\u636e\u7ed3\u6784 \u00b7 \u7ea2\u9ed1\u6811", c_ds_algo, None),
    "pane_exec_algo": ("\u7b97\u6cd5\u8bbe\u8ba1 \u00b7 \u5206\u6cbb/\u52a8\u89c4/\u8d2a\u5fc3", c_algo, None),
    "pane_exec_se": ("\u8f6f\u4ef6\u5de5\u7a0b \u00b7 \u6570\u636e\u6d41\u56fe", c_software_engineering, None),
    "pane_exec_oop": ("\u9762\u5411\u5bf9\u8c61 \u00b7 UML", c_oop, None),
    "pane_exec_net": ("\u8ba1\u7b97\u673a\u7f51\u7edc \u00b7 \u4e09\u6b21\u63e1\u624b", c_network, None),
    "pane_exec_os": ("\u8ba1\u7b97\u673a\u64cd\u4f5c\u7cfb\u7edf \u00b7 OpenEuler", c_os, None),
    "pane_exec_co": ("\u8ba1\u7b97\u673a\u7ec4\u6210\u539f\u7406 \u00b7 \u8865\u7801\u4e58\u6cd5", c_co, None),
    "pane_exec_compiler": ("\u7f16\u8bd1\u539f\u7406 \u00b7 \u4e94\u6b65\u7ba1\u9053", c_compiler, None),
    "pane_exec_db": ("\u6570\u636e\u5e93 \u00b7 EXPLAIN \u4e0e B+ \u6811", c_db, None),
    "pane_exec_pm": ("\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406 \u00b7 WBS/Gantt", c_pm, None),
    "pane_exec_test": ("\u8f6f\u4ef6\u6d4b\u8bd5 \u00b7 \u8986\u76d6\u7387", c_test, None),
    "pane_exec_dl": ("\u6df1\u5ea6\u5b66\u4e60 \u00b7 \u53cd\u5411\u4f20\u64ad", c_dl, None),
    "pane_exec_industrial": ("\u5927\u578b\u5de5\u4e1a\u8f6f\u4ef6", c_industrial, None),
    # the six instruments of the countdown, and the one course that shares the FEM drawing with them
    "pane_gauge_fem": ("\u5de5\u4e1a\u6a21\u578b \u00b7 FEM", g_fem, None),
    "pane_gauge_burndown": ("\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406 \u00b7 \u71c3\u5c3d\u56fe", g_burndown, None),
    "pane_gauge_pareto": ("\u8f6f\u4ef6\u6d4b\u8bd5 \u00b7 \u7f3a\u9677\u5e15\u7d2f\u6258", g_pareto, None),
    "pane_gauge_attention": ("\u6df1\u5ea6\u5b66\u4e60 \u00b7 \u6ce8\u610f\u529b", g_attention, None),
    "pane_gauge_assembly": ("\u5927\u578b\u5de5\u4e1a\u8f6f\u4ef6 \u00b7 \u88c5\u914d\u4f53", g_assembly, None),
    "pane_gauge_final": ("\u6bd5\u4e1a\u8bbe\u8ba1 \u00b7 \u7518\u7279\u56fe", g_final, None),
}

# the six instruments, in the order the countdown's three numbers carry them (two per number)
GAUGE_PANES = ["pane_gauge_burndown", "pane_gauge_pareto", "pane_gauge_attention",
               "pane_gauge_fem", "pane_gauge_assembly", "pane_gauge_final"]

# name -> (title, drawing fn). Read out of COURSES, so a course title is written down exactly once.
# The countdown's own six words, one per instrument, in `GAUGE_PANES` order.
#
# **They were a dead parameter and never once reached the screen.** `draw_gauge` has taken `lang` and
# `digit` since it was written and prints them at `k.bx1 - 10` - and the only call site
# (`school_panels.draw_scene_pane`) never passed either, so the six words the song actually counts
# (`Ein, dos / Trios, ne / Fem, liu` - German, Spanish, Greek, Chinese, Swedish, Chinese) were designed,
# wired, and invisible. Keyed by pane name and read here rather than passed in, so there is no second
# copy of the mapping and no call site that can forget it. (Batch 37's maths audit.)
GAUGE_WORDS: dict[str, tuple[str, str]] = {
    "pane_gauge_burndown": ("ein", "\u5fb7"),      # 软件项目管理
    "pane_gauge_pareto": ("dos", "\u897f"),        # 软件测试
    "pane_gauge_attention": ("trios", "\u5e0c"),   # 深度学习
    "pane_gauge_fem": ("ne", "\u4e2d"),            # 工业模型
    "pane_gauge_assembly": ("fem", "\u745e"),      # 大型工业软件
    "pane_gauge_final": ("liu", "\u4e2d"),         # 毕业设计
}

GAUGES: dict[str, tuple[str, object]] = {n: (COURSES[n][0], COURSES[n][1]) for n in GAUGE_PANES}

# The vocabulary each course actually asks for, drawn under its diagram when the pane is tall enough
# to have rows left over (`draw_course`). This is the part of the pane that is *text*, and it is
# deliberately the part that is text: a diagram can show a red-black tree, but the word the exam, the
# manual and the error message all use is "red-black tree", and the two belong on the same screen.
# Only the courses get one. The six instruments of the countdown live for three tenths of a second.
DETAIL: dict[str, tuple[tuple[str, str], ...]] = {
    "pane_exec_compiler": (
        ("lexer", "\u8bcd\u6cd5\uff1a\u5b57\u7b26\u6d41 \u2192 token"),
        ("parser", "\u8bed\u6cd5\uff1atoken \u2192 \u8bed\u6cd5\u6811"),
        ("IR", "\u4e2d\u95f4\u4ee3\u7801\uff1a\u4e09\u5730\u5740\u7801"),
        ("opt", "\u4f18\u5316\uff1a\u5e38\u91cf\u6298\u53e0\u3001\u516c\u5171\u5b50\u8868\u8fbe\u5f0f"),
    ),

    "pane_exec_embedded": (
        ("MCU / SoC", "微控制器与片上系统"),
        ("register", "寄存器：外设的编程接口"),
        ("GPIO", "通用输入输出，第一颗 LED"),
        ("interrupt / ISR", "中断与中断服务程序"),
        ("timer / PWM", "定时器与脉宽调制"),
        ("UART · I2C · SPI", "三种片上总线，三种距离"),
        ("ADC", "模拟量变成数字量"),
        ("RTOS", "实时操作系统：任务与优先级"),
        ("HC-SR04", "超声波测距，就是上面那只"),
    ),
    "pane_exec_c": (
        ("pointer", "指针：地址就是值"),
        ("malloc / free", "堆内存，谁申请谁释放"),
        ("struct", "结构体：相关数据放一起"),
        ("buffer overflow", "越界写，第一个安全漏洞"),
        ("segfault", "段错误：在错误的地方读写"),
        ("GDB", "断点、单步、看调用栈"),
        ("compile / link", "编译与链接，符号与头文件"),
        ("Makefile", "构建规则，不是脚本"),
        ("valgrind", "内存泄漏检查器"),
    ),
    "pane_exec_ds": (
        ("red-black tree", "红黑树：近似平衡的搜索树"),
        ("rotation", "旋转：不改中序的局部改写"),
        ("amortized", "摊还：把偶发代价摊平"),
        ("hash", "哈希：用空间换常数"),
        ("big-O", "上界，不是运行时间"),
        ("BST invariant", "左小右大：所有操作的前提"),
        ("heap", "堆：只保证父子有序"),
        ("union-find", "并查集：路径压缩"),
        ("STL", "标准模板库：别人写好的容器"),
    ),
    "pane_exec_algo": (
        ("divide and conquer", "分治：切开、解决、合并"),
        ("recurrence", "递推式：T(n) = 2T(n/2) + O(n)"),
        ("master theorem", "主定理：不展开就能读出复杂度"),
        ("memoization", "记忆化：算过就不再算"),
        ("dynamic programming", "动态规划：状态、转移、边界"),
        ("greedy", "贪心：每步选当前最好，不回头"),
        ("exchange argument", "交换论证：贪心为何对"),
        ("NP-hard", "没有已知多项式解法"),
        ("loop invariant", "循环不变式：证明算法对的方式"),
    ),
    "pane_exec_se": (
        ("requirement", "需求：一句可验证的话"),
        ("DFD / ERD", "数据流图与实体关系图"),
        ("use case", "用例：谁对系统做什么"),
        ("SRS", "软件需求规格说明书"),
        ("coupling / cohesion", "低耦合，高内聚"),
        ("UML", "统一建模语言：图的语法"),
        ("waterfall / agile", "瀑布与敏捷，顺序与迭代"),
        ("version control", "版本控制：git 是记录不是备份"),
        ("CI / CD", "持续集成与持续交付"),
    ),
    "pane_exec_oop": (
        ("class / object", "类与对象：模板与实例"),
        ("encapsulation", "封装：只暴露接口"),
        ("inheritance", "继承：复用，也制造耦合"),
        ("polymorphism", "多态：同一消息，不同响应"),
        ("interface", "接口：一份契约"),
        ("design pattern", "设计模式：别人踩过的坑"),
        ("refactor", "重构：外面不变，里面变好"),
        ("Java", "面向对象的工业语言"),
        ("JVM", "虚拟机：一次编写，到处运行"),
    ),
    "pane_exec_net": (
        ("TCP handshake", "SYN · SYN-ACK · ACK"),
        ("reliability", "可靠：确认、重传、排序"),
        ("congestion window", "拥塞窗口：慢启动与退避"),
        ("DNS", "把域名换成地址"),
        ("HTTP / HTTPS", "请求应答，加上 TLS"),
        ("socket", "套接字：网络的编程接口"),
        ("subnet / NAT", "子网划分与地址转换"),
        ("MQTT", "工业现场的轻量协议"),
        ("OSI 七层", "分层：每层只跟对面那层说话"),
    ),
    "pane_exec_os": (
        ("process / thread", "进程与线程：资源与执行"),
        ("scheduler", "调度器：下一个谁上 CPU"),
        ("page / TLB", "分页与地址翻译缓存"),
        ("system call", "系统调用：用户态进内核态"),
        ("deadlock", "死锁：四个必要条件"),
        ("semaphore", "信号量：同步与互斥"),
        ("filesystem / inode", "文件系统与索引节点"),
        ("shell", "命令行：程序的组合方式"),
        ("openEuler", "开放欧拉：国产服务器系统"),
    ),
    "pane_exec_co": (
        ("ALU", "算术逻辑单元"),
        ("two's complement", "补码：减法就是加法"),
        ("pipeline", "流水线：吞吐与冒险"),
        ("cache", "命中率决定平均访存时间"),
        ("ISA", "指令集：硬件与软件的契约"),
        ("Booth", "布斯算法：带符号乘法"),
        ("bus / DMA", "总线与直接内存访问"),
        ("microprogram", "微程序：控制器的一种实现"),
        ("Verilog", "硬件描述语言"),
    ),
    "pane_exec_db": (
        ("primary key", "主键：唯一且非空"),
        ("index / B+ tree", "索引：用树换查询速度"),
        ("EXPLAIN", "看执行计划，别靠猜"),
        ("ACID", "原子、一致、隔离、持久"),
        ("normal form", "范式：拆表消除冗余"),
        ("join", "连接：关系库的看家本领"),
        ("transaction log", "日志：先写日志再改数据"),
        ("PostgreSQL", "开源关系库，实践中在用"),
        ("SQL 注入", "把输入当代码的下场"),
    ),
    "pane_exec_pm": (
        ("WBS", "工作分解：把大活切小"),
        ("critical path", "关键路径：拖它就拖全项目"),
        ("burndown", "燃尽图：剩余工作量"),
        ("risk register", "风险登记册"),
        ("Gantt", "甘特图：时间与依赖"),
        ("milestone", "里程碑：可交付的检查点"),
        ("stakeholder", "干系人：会被影响到的人"),
        ("scope creep", "范围蔓延：需求慢慢长大"),
        ("retrospective", "复盘：这一轮学到了什么"),
    ),
    "pane_exec_test": (
        ("black box", "黑盒：只看输入输出"),
        ("statement coverage", "语句覆盖"),
        ("branch coverage", "分支覆盖，比语句严"),
        ("regression", "回归：改一处别弄坏十处"),
        ("fuzzing", "模糊测试：让机器找边界"),
        ("unit test", "单元测试：最小的可测单位"),
        ("boundary value", "边界值最容易出 bug"),
        ("pytest", "写测试比写文档有用"),
        ("CI", "每次提交都跑一遍"),
    ),
    "pane_exec_dl": (
        ("tensor", "张量：多维数组"),
        ("forward / backward", "前向算损失，反向求梯度"),
        ("chain rule", "链式法则：反向传播的全部"),
        ("learning rate", "步长：大了发散，小了不走"),
        ("loss", "损失：把对错变成一个数"),
        ("epoch / batch", "轮次与批大小"),
        ("overfitting", "过拟合：背答案不是学会"),
        ("attention", "注意力：让模型自己选看哪里"),
        ("PyTorch", "框架，不是魔法"),
    ),
    "pane_exec_industrial": (
        ("CAD / CAE / CAM", "设计、仿真、制造"),
        ("mesh", "网格：把连续体切成有限块"),
        ("solver", "求解器：一次解上百万个方程"),
        ("digital twin", "数字孪生：先算后造"),
        ("PLM", "产品全生命周期管理"),
        ("tolerance", "公差：工业里的误差预算"),
        ("OpenFOAM", "开源流体仿真"),
        ("Abaqus", "商用有限元，航空常用"),
        ("MBSE", "基于模型的系统工程"),
    ),
}


# The one course pane that carries a motif from `想法.md` instead of its terms: `pane_exec_os` is where
# the fork bomb belongs - 处决 is the section, and 4096 processes is the drawing - and the pane already
# fills every row it is given, so the band has to be reserved rather than found.
MOTIF = {"pane_exec_os": "fork_bomb",
         # the pixel sort was under 为国铸剑 until the user said the sculpture could not be read at the
         # size two motif bands left it. It belongs here anyway: sorting a row by brightness is what the
         # data-structures pane is about, and a plate of bars is not a photograph to be recognised.
         "pane_exec_ds": "pixelsort"}


def _activity(k: _Kit, t: float, seed: int) -> None:
    """One row of machinery that runs on the *song's* clock, under every course drawing.

    The user's point 2 was that the animations are monotone rather than parallel, and for the fifteen
    course panes the honest state of it is this: each drawing reveals itself on `u`, its own progress
    through its slot, and nothing in it moves for any other reason. A drawing that reveals on one clock
    and *runs* on another is two clocks in one box, which is what the motif panes already do - this is the
    same idea for the panes that have no motif.

    It is deliberately the same strip in every course pane (a carrier, a moving head, a cycle counter)
    because it is the pane's own "the machine is executing" indicator, not a drawing: the differences
    between the courses belong to the drawings above it. The *course-specific* second clock, for the
    courses the user named, is `_live`.

    Narrow panes keep a short strip rather than nothing: at 34 cells the first version returned early and
    those panes silently had one clock again, which is the kind of difference the eye reads as a bug.
    """
    y = k.by1
    if k.bw < 10:
        return
    counter = 6 if k.bw >= 30 else 0
    n = max(4, k.bw - 4 - counter)
    head = int((t * 3.0 + seed * 0.37) % n)
    k.put(k.bx0, y, "\u25b8", _mix(BLUE, 0.7))
    for i in range(n):
        on = i == head
        lag = (head - i) % n
        k.put(k.bx0 + 2 + i, y, "\u25cf" if on else "\u2500",
              _mix(AMBER, 0.95) if on else _ui(max(0.12, 0.42 - lag * 0.02)))
    if counter:
        k.put(k.bx1 - counter + 1, y, f"{int(t * 2.0 + seed) % 100:3d}", _mix(GREEN, 0.7))


# ---------------------------------------------------------------- the second clock, per course
#
# The user's named courses each get their own animated element, on the song's clock and in their own
# subject's language - the strip above says "a machine is executing", and these say *what* the course is
# executing. One mechanism and fifteen specs rather than fifteen hand-written animations: a kind, a row,
# a label, and (for the kinds that need one) a period. Every one of them is a pure function of `t`, so a
# seek lands on the same frame.
#
#   pulse    a dot travelling a track, wrapping - current, packets, a clock
#   count    a number that will not sit still - a rate, a register, a percentage
#   sweep    a bar filling and restarting - a progress, a load, a sweep
#   blink    a status light with a pattern - a heartbeat, a lock, an error
#   cursor   a caret walking a line of text - a compile, a query, a log
LIVE: dict[str, tuple] = {
    "pane_exec_embedded": ("pulse", "5V \u603b\u7ebf", 2.6),
    "pane_exec_c": ("count", "addr", 0),
    "pane_exec_ds": ("cursor", "search 8", 0),
    "pane_exec_algo": ("sweep", "T(n)", 3.0),
    "pane_exec_se": ("pulse", "data", 3.4),
    "pane_exec_oop": ("cursor", "dispatch", 0),
    "pane_exec_net": ("pulse", "seq", 1.8),
    "pane_exec_os": ("count", "%CPU", 0),
    "pane_exec_co": ("count", "A/Q", 0),
    "pane_exec_db": ("cursor", "scan", 0),
    "pane_exec_pm": ("sweep", "sprint 3", 4.2),
    "pane_exec_test": ("count", "cov %", 0),
    "pane_exec_dl": ("sweep", "loss", 2.2),
    "pane_exec_industrial": ("blink", "solver", 1.1),
    "pane_gauge_fem": ("blink", "mesh", 0.7),
}


def _live(k: _Kit, t: float, spec: tuple) -> None:
    """Draw one course's own live element, on the single row the pane reserved for it.

    The row is reserved rather than chosen (see `draw_course`): the first version put these inside the
    drawing at `by0 + row` and drew them straight over the course's own labels - "cases" came out
    "c 4es" and "defects" "defec▓s", which a frame dump shows immediately and nothing else does.
    """
    kind, label, period = spec
    y = k.by0
    if k.bw < 14:
        return
    k.put(k.bx0, y, label[:12], _ui(0.5))
    x0 = k.bx0 + min(14, max(10, k.bw // 6))
    w = max(8, k.bx1 - x0 - 1)
    if kind == "pulse":
        head = int((t / max(0.2, period)) * w) % w
        for i in range(w):
            k.put(x0 + i, y, "\u2500", _ui(0.18))
        k.put(x0 + head, y, "\u25cf", _mix(AMBER, 0.95))
        for b in range(1, 3):                       # the wake behind it
            k.put(x0 + (head - b) % w, y, "\u00b7", _mix(AMBER, 0.4 / b))
    elif kind == "count":
        v = abs(math.sin(t * 1.3)) * 99
        k.put(x0, y, f"{v:5.1f}", _mix(GREEN, 0.9))
        bars = int(v / 100 * (w - 8))
        k.put(x0 + 7, y, "\u2588" * max(0, bars), _mix(GREEN, 0.55))
        k.put(x0 + 7 + max(0, bars), y, "\u2591" * max(0, w - 8 - bars), _ui(0.2))
    elif kind == "sweep":
        f = (t % max(0.4, period)) / max(0.4, period)
        done = int(w * f)
        k.put(x0, y, "\u2588" * done, _mix(BLUE, 0.8))
        k.put(x0 + done, y, "\u2591" * (w - done), _ui(0.2))
    elif kind == "blink":
        ph = (t % max(0.2, period)) / max(0.2, period)
        on = ph < 0.5
        k.put(x0, y, "\u25cf" if on else "\u25cb", _mix(GREEN if on else RED, 0.9))
        for i in range(1, w):
            k.put(x0 + i, y, "\u00b7" if (i + int(t * 4)) % 4 else "\u2500", _ui(0.16))
    elif kind == "cursor":
        msg = "0123456789abcdef"
        c = int(t * 7) % min(len(msg), w)
        k.put(x0, y, msg[:w], _mix(AMBER, 0.65))
        k.put(x0 + c, y, "\u2588", _mix(INK, 0.95))


def draw_course(name: str, s, x0: int, y0: int, x1: int, y1: int,
                t: float, lt: float, dur: float, u: float, run: int = 0,
                total: int = 12) -> bool:
    """Draw one course pane. False if `name` is not a course.

    The pane the layout hands over is thirty-odd rows tall and these diagrams were drawn for eleven.
    Reserving a fixed slice at the bottom for the terms does not fix that: the diagram is small, so
    the black band simply moves up and sits between the diagram and the terms. Instead the drawing is
    given the whole box, and the terms are then placed in *whatever the drawing did not use* - found
    by looking at the buffer rather than by being told - and spaced out to the bottom. A pane whose
    drawing fills the box gets no terms, which is the correct outcome and needs no special case.
    """
    spec = COURSES.get(name)
    if spec is None:
        return False
    title, fn, pair = spec
    motif = MOTIF.get(name)
    # The drawing gets a box shorter than the pane and one machinery row takes what it gave up. There used
    # to be two - a generic strip *and* the course's own live element - and that is exactly the kind of
    # stacking the user's note ("构图不要显得杂乱") is about: two rows of machinery under one drawing, saying
    # the same thing twice. Now a named course gets its own element and the rest get the strip.
    has_live = name in LIVE
    foot = 1
    draw_y1 = y1 - foot - 1
    k = _Kit(s, x0, y0, x1, draw_y1, title, run, total, u, t=t)
    if pair:
        _split(k, list(pair))
    else:
        fn(k, lt, dur)
    # the second clock, on the row the drawing gave up: the drawing reveals on `u`, this runs on the song
    row = y1 - 1
    if has_live:
        _live(k.sub(k.bx0, row, k.bx1, row), t, LIVE[name])
    else:
        _activity(k.sub(k.bx0, row, k.bx1, row), t, run)
    detail = DETAIL.get(name, ())
    if detail:
        used = _last_ink(s, k.bx0, k.bx1, k.by0, k.by1)
        if used is not None and k.by1 - used >= 6:
            _terms(k, x0, used + 2, x1, y1 - 2, detail)
    return True


def _last_ink(s, bx0: int, bx1: int, by0: int, by1: int):
    """The lowest row in the body that has anything on it, or None if the body is empty.

    The pane asks the screen what the drawing did instead of the drawing declaring a height it does
    not know: the same diagram draws three rows tall in a five-row box and twenty in a forty-row one,
    and only the buffer knows which happened this frame.
    """
    for y in range(by1, by0 - 1, -1):
        row = s.buf[y]
        for x in range(bx0, bx1 + 1):
            if row[x][0] not in ("", " "):
                return y
    return None


def _terms(k: _Kit, x0: int, y0: int, x1: int, y1: int, rows) -> None:
    """The course's working vocabulary, in the rows the drawing did not need.

    English on the left of each cell because that is the word in the textbook, the manual and the
    error message; the Chinese is the gloss, not the other way round. The rows are spaced to the
    bottom of the pane rather than packed at the top, so a term list that would have ended half way
    down ends at the edge instead, and the pane has no band of black in it.
    """
    dk = k.sub(x0 + 1, y0, x1 - 1, y1 - 1)
    dk.section(dk.by0, "术语 · TERMS", 0.25)
    cols = 2 if dk.bw >= 80 else 1
    cw = dk.bw // cols
    lines = (len(rows) + cols - 1) // cols
    room = max(1, dk.bh - 1)
    step = max(1, min(4, room // max(1, lines)))
    for i, (term, gloss) in enumerate(rows):
        r, c = divmod(i, cols)
        y = dk.by0 + 1 + r * step
        if y > dk.by1:
            break
        dk.put(dk.bx0 + c * cw, y, _pad(term, 22), _mix(BLUE, 0.85))
        dk.put(dk.bx0 + c * cw + 22, y, _clip(gloss, cw - 24), _ui(0.6))


def draw_gauge(name: str, s, x0: int, y0: int, x1: int, y1: int,
               t: float, lt: float, dur: float, u: float, run: int = 0,
               lang: str = "", digit: str = "") -> bool:
    """Draw one of the six senior-year instruments, with the countdown's own language and digit."""
    spec = GAUGES.get(name)
    if spec is None:
        return False
    title, fn = spec
    digit, lang = GAUGE_WORDS.get(name, ("", ""))
    # **The countdown word rides in the title line**, which is the one row no instrument writes to. The
    # first attempt drew it at `bx1 - 10` on `by0` - and `by0` is exactly where three of the six
    # instruments put their own legend (`ideal · actual ·`, `defect pareto ... cum 80%`), so it was
    # overwritten as soon as the drawing ran. Measured by the batch-37 probe: two of the six words were
    # still missing after the "fix" that was supposed to add them.
    head = f"{title}  {digit} {lang}".strip() if digit else title
    k = _Kit(s, x0, y0, x1, y1, head, run, 3, u)
    fn(k, lt, dur)
    _gauge_live(k, t, run)
    return True


def _gauge_live(k: _Kit, t: float, run: int) -> None:
    """A sampling cursor under every instrument, on the song's clock.

    The six gauges are the countdown's own drawings and each one already moves on `lt` - a burndown that
    burns, a Pareto that grows, a plate that vibrates. What they did not have is anything that keeps
    moving *after* the reveal, and the user's note about parallel animation applies to them too. One
    cursor and one counter, drawn here rather than six times, because an instrument reading out is the
    same gesture whichever instrument it is.
    """
    y = k.by1
    if k.bw < 22 or y <= k.by0:
        return
    span = k.bw - 12
    x = k.bx0 + 6 + int((t * 0.55 + run * 0.17) % 1.0 * span)
    k.put(k.bx0 + 4, y, "\u2570", _ui(0.3))
    k.hline(k.bx0 + 5, y, k.bx0 + 5 + span, "\u2500", _ui(0.18))
    k.put(x, y, "\u25b2", _mix(AMBER, 0.95))
    k.put(k.bx0, y, f"{(int(t * 8) + run) % 1000:03d}", _mix(GREEN, 0.6))


# --------------------------------------------------------------------------- the four AI motifs
#
# The user's point 4 named four things the film was missing from the model half of its subject:
# attention, reinforcement learning, diffusion and a convolutional net. Two of them were already here in
# small print (`pane_exec_dl` draws the backward pass, `pane_gauge_attention` is a heat map in the
# countdown) and the other three were not drawn at all, so this is one pane each - full size, in the
# closing act, where the song stops talking about lectures and starts talking about what a model does.
#
# They are not `COURSES`: the twelve "Execution" hits are allocated and the `EXEC n/14` counter counts
# them. These hang on their own rows in `school_panels.LANDMARK_ROWS`, which is why they are looked up
# through `AI` rather than through `COURSES`.

def _kernel_grid(k: _Kit, x0: int, y0: int, size: int, cell: int, prog: float, target) -> int:
    """A convolutional kernel sliding over an input image, with its output filling in behind it.

    `target(x, y)` is the image, as a predicate - a letter, a cross, whatever the pane is convolving.
    `prog` is how far across the image the kernel has got, as a fraction of the whole sweep.
    Returns the first free row under the two grids.
    """
    steps = max(1, (size - 2) * (size - 2))
    pos = int(steps * min(1.0, prog * 1.15))
    kx, ky = pos % max(1, size - 2), pos // max(1, size - 2)
    for y in range(size):
        for x in range(size):
            k.put(x0 + x * cell, y0 + y, "\u2588" * cell if target(x, y) else "\u2591" * cell,
                  _mix(BLUE, 0.85) if target(x, y) else _ui(0.22))
    # the kernel window, drawn as a box over the image
    wx, wy = x0 + kx * cell, y0 + ky
    k.put(wx, wy, "\u250c" + BOX_H * (cell * 2 + 1) + "\u2510", _mix(AMBER, 0.95))
    k.put(wx, wy + 3, "\u2514" + BOX_H * (cell * 2 + 1) + "\u2518", _mix(AMBER, 0.95))
    for r in (1, 2):
        k.put(wx, wy + r, BOX_V, _mix(AMBER, 0.95))
        k.put(wx + cell * 2 + 2, wy + r, BOX_V, _mix(AMBER, 0.95))
    # and the feature map it produces. It is a real convolution - the sum of the kernel window over the
    # image, shaded by that sum - rather than "visited / not visited": the first version drew a solid
    # rectangle, which is what a convolution layer looks like if you do not do the convolution.
    fx = x0 + size * cell + 4
    ks = 3
    for oy in range(size - ks + 1):
        for ox in range(size - ks + 1):
            done = (oy * (size - ks + 1) + ox) < pos
            hot = (ox, oy) == (kx, ky)
            val = sum(1 for dy in range(ks) for dx in range(ks) if target(ox + dx, oy + dy))
            lv = val / (ks * ks)
            ch = "\u2588" if lv > 0.55 else ("\u2593" if lv > 0.25 else "\u2591")
            k.put(fx + ox * 2, y0 + oy, ch * 2,
                  _mix(AMBER, 0.95) if hot else (_mix(GREEN, 0.35 + 0.5 * lv) if done else _ui(0.2)))
    return y0 + size + 2


def ai_cnn(k: _Kit, lt: float, dur: float) -> None:
    """卷积网络: one kernel over one letter, and then the layers that stop looking like letters."""
    k.section(k.by0, "\u5377\u79ef \u00b7 \u7279\u5f81\u56fe", 0.30)
    size, cell = 9, 2

    def target(x, y):
        """A capital N, and nothing else: two verticals and the diagonal between them."""
        if not (0 <= x < size and 0 <= y < size):
            return False
        return x in (1, 7) or abs((x - 1) - (y - 0) * 6 / 8) < 0.7
    # The kernel keeps sweeping for as long as the pane is up, on the pane's own clock rather than on
    # the reveal: `u` gets it across the image exactly once, in the last frame of the slot, which is a
    # picture of a convolution rather than one being run - and after the reveal the pane was a still
    # image (`_dev/clock_probe.py`). The feature map fills in behind it and is wiped at the start of
    # each sweep, which is the honest picture of what a sliding window does.
    y1 = _kernel_grid(k, k.bx0, k.by0 + 2, size, cell, (lt * 0.45) % 1.0, target)
    k.put(k.bx0, k.by0 + 2 + size + 1, "\u8f93\u5165 9\u00d79", _ui(0.5))
    k.put(k.bx0 + size * cell + 4, k.by0 + 2 + size + 1, "\u7279\u5f81\u56fe 7\u00d77", _ui(0.5))
    if k.by1 - y1 < 5:
        return
    # The stack: four layers, each drawn smaller, because that is the whole claim of the architecture.
    # A strip four rows tall rather than four nine-row grids - the first version pitched them at fifteen
    # cells with eighteen-cell grids and the four layers printed on top of each other.
    names = ("\u8fb9\u7f18", "\u7eb9\u7406", "\u90e8\u4ef6", "\u7269\u4f53")
    for i, w in enumerate((9, 7, 5, 3)):
        x0 = k.bx0 + i * 22
        if x0 + w * 2 + 1 > k.bx1:
            break
        k.put(x0, y1, f"L{i + 1} \u00b7 {names[i]}", _ui(0.7))
        for yy in range(min(3, max(0, k.by1 - y1 - 2))):
            for xx in range(w):
                k.put(x0 + xx * 2, y1 + 1 + yy,
                      "\u2593\u2593" if (xx + yy + i) % 3 else "\u2591\u2591",
                      _mix(BLUE, 0.35 + 0.12 * i))
        if i < 3:
            k.put(x0 + w * 2 + 3, y1 + 1, "\u2192", _ui(0.4))
    # anchored to the drawing, not to the pane: a caption on the last row of the pane is a caption
    # that stops the vocabulary footer from ever being placed
    k.put(k.bx0, min(k.by1, y1 + 4),
          "\u5377\u79ef\u6838\u5728\u6ed1\uff0c\u6ed1\u5230\u54ea\u91cc\u5c31\u5728\u54ea\u91cc\u5199\u4e00\u4e2a\u6570",
          _ui(0.55))


def ai_attention(k: _Kit, lt: float, dur: float) -> None:
    """注意力: QK^T, the softmax over it, and the one row that is being asked."""
    k.section(k.by0, "\u6ce8\u610f\u529b \u00b7 QK\u1d40 \u2192 softmax", 0.30)
    # one character per token, four cells apart. The first version used the words themselves
    # ("\u897f\u5de5\u5927", "\u8f6f\u4ef6") on the same pitch and the row of seven labels printed as one
    # smeared line - a CJK token is two cells per character and the pitch was two.
    toks = ("\u897f", "\u5de5", "\u5927", "\u8f6f", "\u4ef6", "\u5b66", "\u9662")
    n = len(toks)
    cx, cy = k.bx0 + 3, k.by0 + 3
    k.put(k.bx0, k.by0 + 1, "\u53e5\u5b50\uff1a\u897f\u5de5\u5927\u8f6f\u4ef6\u5b66\u9662 \u00b7 "
                            "\u6bcf\u4e2a\u5b57\u662f\u4e00\u4e2a token", _ui(0.5))
    for j, tkn in enumerate(toks):
        k.put(cx + j * 4, cy - 1, tkn, _ui(0.55))
        k.put(cx - 3, cy + j, tkn, _ui(0.55))
    q = int(lt * 1.1) % n                       # the query row being asked, on its own clock
    for r in range(n):
        for c in range(n):
            w = math.exp(-abs(r - c) * 0.7) + 0.08 * math.exp(-abs(r - c - 3) * 0.5)
            lv = min(1.0, w)
            ch = "\u2588" if lv > 0.6 else ("\u2593" if lv > 0.3 else "\u2591")
            k.put(cx + c * 4, cy + r, (ch * 2) + "  ",
                  _mix(AMBER if r == q else BLUE, 0.9 if r == q else float(0.20 + 0.55 * lv)))
    y = cy + n + 1
    k.put(k.bx0, y, f"\u7b2c {q + 1} \u884c\uff1a\u201c{toks[q]}\u201d\u5728\u770b\u8c01", _mix(AMBER, 0.9))
    if k.by1 - y >= 3:
        bar = max(8, k.bw - 22)
        weights = [math.exp(-abs(q - c) * 0.7) + 0.08 * math.exp(-abs(q - c - 3) * 0.5)
                   for c in range(n)]
        tot = sum(weights)
        run = 0
        for c, w in enumerate(weights):
            # scaled to the bar, not to 1.6 bars: the first version multiplied by 1.6 "to make it
            # visible" and the weight row came out as one solid rule with no weights in it
            n_cells = int(bar * w / tot)
            k.put(k.bx0 + run, y + 1, "\u2588" * max(0, n_cells),
                  _mix(GREEN, 0.85) if c == q else _mix(BLUE, 0.6))
            run += n_cells
        k.put(k.bx0, y + 2, "\u6bcf\u884c\u52a0\u8d77\u6765\u7b49\u4e8e 1\uff1a\u5206\u914d\u6ce8\u610f\u529b"
                            "\uff0c\u4e0d\u662f\u5e73\u5747\u5206\u914d", _ui(0.55))
    k.put(k.bx0, min(k.by1, y + 3), "\u6ce8\u610f\u529b\u5c31\u662f\u4e00\u4e2a\u6743\u91cd\u77e9\u9635\uff0c"
                                    "\u8f6f\u5316\u4e86\u7684\u67e5\u627e\u8868", _ui(0.5))


def ai_rl(k: _Kit, lt: float, dur: float) -> None:
    """强化学习: the loop, the group of rollouts, and the reward curve those rollouts move.

    Three panels because the idea has three parts and the pane has room for all three: *what* is being
    updated (the loop), *how* it is scored (a group of samples against their own mean), and *whether it
    worked* (the curve). The curve is the part the user asked for by name, and it is the part that makes
    the point - a policy update is only interesting if the line goes up afterwards.
    """
    k.section(k.by0, "\u5f3a\u5316\u5b66\u4e60 \u00b7 \u7b56\u7565\u66f4\u65b0", 0.30)
    # --- the loop
    loop = ("\u73af\u5883 state", "\u7b56\u7565 \u03c0", "\u52a8\u4f5c a", "\u5956\u52b1 r")
    step = int(lt * 1.6) % len(loop)
    for i, lab in enumerate(loop):
        yy = k.by0 + 2 + i
        if yy > k.by1 - 4:
            break
        k.put(k.bx0 + 2, yy, "\u25cf", _mix(AMBER if i == step else BLUE, 0.9))
        k.put(k.bx0 + 4, yy, lab, _ui(0.8) if i == step else _ui(0.6))
        if i < len(loop) - 1:
            k.put(k.bx0 + 2, yy + 1, BOX_V, _ui(0.3))
    # --- the group of rollouts: same question, different answers, scored against their own mean
    gx = k.bx0 + 18
    if gx + 20 > k.bx1:
        return
    k.put(gx, k.by0 + 2, "\u540c\u4e00\u4e2a\u95ee\u9898\uff0c\u91c7\u6837 G \u6b21", _ui(0.55))
    rewards = (0.90, 0.40, 0.75, 0.20)
    mean = sum(rewards) / len(rewards)
    for i, r in enumerate(rewards):
        yy = k.by0 + 3 + i
        if yy > k.by1 - 6:
            break
        bar = max(2, int((k.bx1 - gx - 26) * r))
        k.put(gx, yy, "\u2588" * bar, _mix(GREEN if r > mean else RED, 0.8))
        k.put(gx + bar + 1, yy, f"r={r:.2f}", _ui(0.6))
        k.put(gx + bar + 8, yy, f"A={r - mean:+.2f}", _mix(GREEN if r > mean else RED, 0.85))
    ky = k.by0 + 3 + len(rewards)
    k.put(gx, ky, f"\u57fa\u51c6 = \u7ec4\u5185\u5e73\u5747 {mean:.2f}\uff0c\u6bd4\u5b83\u597d\u7684\u52a0\u6743"
                  f"\u3001\u6bd4\u5b83\u5dee\u7684\u538b\u4f4e", _ui(0.6))
    # --- the reward curve: 40 updates, rising, with the policy step marked
    cy0, cy1 = ky + 2, k.by1 - 2
    if cy1 - cy0 < 3:
        return
    w = max(10, k.bw - 14)
    k.put(k.bx0, cy0 - 1, "\u5956\u52b1\u66f2\u7ebf\uff08\u6bcf\u6b21\u7b56\u7565\u66f4\u65b0\u4e4b\u540e\uff09",
          _ui(0.6))
    k.vline(k.bx0 + 10, cy0, cy1, BOX_V, _ui(0.3))
    k.hline(k.bx0 + 10, cy1, k.bx0 + 10 + w, BOX_H, _ui(0.3))
    n = 40
    shown = max(2, int(n * min(1.0, k.u * 1.15)))
    prev = None
    for i in range(shown):
        f = i / (n - 1)
        # a rising mean with the noise of a real run, and one dip where the step size was too large
        base = 0.18 + 0.72 * (1 - math.exp(-2.6 * f))
        wob = 0.075 * math.sin(i * 1.9) + 0.045 * math.sin(i * 0.7 + 1.2)
        if 0.42 < f < 0.52:
            base -= 0.16
        v = max(0.02, min(1.0, base + wob))
        x = k.bx0 + 11 + int(w * f)
        y = cy1 - 1 - int((cy1 - cy0 - 1) * v)
        if prev:
            for xx in range(prev[0] + 1, x):
                yy = int(prev[1] + (y - prev[1]) * (xx - prev[0]) / max(1, x - prev[0]))
                k.put(xx, yy, "\u00b7", _mix(BLUE, 0.75))
        k.put(x, y, "\u00b7", _mix(BLUE, 0.95))
        prev = (x, y)
    if k.u > 0.55:
        dx = k.bx0 + 11 + int(w * 0.47)
        k.vline(dx, cy0, cy1, "\u254c", _mix(RED, 0.5))
        k.put(dx + 1, cy0, "\u6b65\u957f\u592a\u5927", _mix(RED, 0.8))
    k.put(k.bx0, min(k.by1, cy1 + 1), "\u66f2\u7ebf\u4e0a\u5347\u624d\u8bf4\u660e\u66f4\u65b0\u6709\u6548\uff0c"
                                      "\u4e0d\u662f\u635f\u5931\u4e0b\u964d", _ui(0.55))


def ai_diffusion(k: _Kit, lt: float, dur: float) -> None:
    """扩散: the same picture at four noise levels, and a marker for the step being taken.

    The four panels are a fixed illustration - t=3 noisiest on the left, t=0 clean on the right - and the
    animation is the marker walking along them, with the noise itself moving under it: the noise cells
    step through three shades on the pane's clock while the heart stays solid, which is the whole claim
    of the drawing (the signal holds, the noise does not). The first version animated the *resolution* of
    the panels, and because it resolved the wrong end first the strip read right-to-left: the clean panel
    was the noisy one and pure noise was drawn as the finished picture.
    """
    k.section(k.by0, "\u6269\u6563 \u00b7 \u9010\u6b65\u53bb\u566a", 0.30)
    # Three panels, not four: four noise grids side by side filled 44 % of the pane and split it into
    # eight bands, which the density probe flags as STACKED - and a noise field is the one drawing where
    # one cell of extra width makes the whole panel shout. Three panels at t=2, t=1, t=0 say the same
    # thing with a third less ink.
    panels = 3
    size = max(7, min(11, k.bh - 14))
    cell = 2
    pw = size * cell + 6
    if k.bx0 + pw * panels > k.bx1 + 6:
        panels = max(2, (k.bx1 - k.bx0) // pw)
    now = int(lt * 1.2) % panels                            # which step is being taken
    for pi in range(panels):
        x0 = k.bx0 + pi * pw
        nl = (panels - 1 - pi) / max(1, panels - 1)        # 1.0 = pure noise, 0.0 = the picture
        k.put(x0, k.by0 + 2, f"t={panels - 1 - pi}", _mix(AMBER, 0.9) if pi == now else _ui(0.5))
        if pi == now:
            k.put(x0 + 8, k.by0 + 2, "\u25c0 \u73b0\u5728", _mix(AMBER, 0.85))
        for y in range(size):
            for x in range(size):
                # the target: a heart, because the line this pane is under is about one. `uy` is
                # negated because the grid's y grows downward and the implicit heart's cusp is at +y,
                # so without it the heart is drawn upside down (it was, in the first version).
                ux = (x - (size - 1) / 2) / max(1.0, size / 2)
                uy = -(y - (size - 1) / 2) / max(1.0, size / 2)
                inside = (ux * ux + uy * uy - 1) ** 3 - ux * ux * uy * uy * uy <= 0
                h = ((x * 2654435761 + y * 40503) >> 8) % 100
                if nl <= 0.001 or h > nl * 92:
                    # the clean panel is the *heart*, not a rectangle of background with a heart in it:
                    # drawing every outside cell as `░` inked the whole pane, which the density probe
                    # flagged as 44 % ink and STACKED, and made the quietest panel the loudest thing on
                    # screen. Nothing outside the shape, in either state.
                    if not inside:
                        continue
                    ch, col = "\u2588", _mix(RED, 0.85)
                elif h % 3 == 0:
                    continue                       # the noise is a field, not a fill
                else:
                    ch = "\u2593\u2592\u2591"[(h + int(lt * 4.0)) % 3]
                    col = _mix(RED if inside else DIM, 0.30 + 0.30 * (h % 3) / 2)
                k.put(x0 + x * cell, k.by0 + 3 + y, ch * cell, col)
        if pi < panels - 1:
            k.put(x0 + size * cell + 2, k.by0 + 3 + size // 2, "\u2190", _ui(0.4))
    y = k.by0 + 3 + size + 1
    k.put(k.bx0, min(k.by1, y), "\u6bcf\u4e00\u6b65\u90fd\u662f\u201c\u9884\u6d4b\u566a\u58f0\uff0c"
                                "\u7136\u540e\u628a\u5b83\u51cf\u6389\u201d", _ui(0.55))
    k.put(k.bx0, min(k.by1, y + 1), "\u4ece\u7eaf\u566a\u58f0\u5230\u4e00\u4e2a\u5f62\u72b6\uff1a"
                                    "\u6700\u540e\u4e00\u6b65\u624d\u770b\u5f97\u51fa\u662f\u4ec0\u4e48", _ui(0.5))


AI = {
    "pane_ai_cnn": ("\u5377\u79ef\u795e\u7ecf\u7f51\u7edc \u00b7 \u7279\u5f81\u56fe", ai_cnn),
    "pane_ai_attention": ("\u6ce8\u610f\u529b \u00b7 \u6743\u91cd\u77e9\u9635", ai_attention),
    "pane_ai_rl": ("\u5f3a\u5316\u5b66\u4e60 \u00b7 \u5956\u52b1", ai_rl),
    "pane_ai_diffusion": ("\u6269\u6563\u6a21\u578b \u00b7 \u53bb\u566a", ai_diffusion),
}

# the same footer the courses get, and for the same reason: these four drawings are two thirds of a
# tall pane and the last third was black until they had one
DETAIL.update({
    "pane_ai_cnn": (
        ("kernel / filter", "\u5377\u79ef\u6838\uff1a\u4e00\u4e2a\u5c0f\u77e9\u9635"),
        ("stride", "\u6b65\u957f\uff1a\u6ed1\u51e0\u683c"),
        ("padding", "\u8fb9\u8fb9\u8865\u96f6\uff0c\u4e0d\u8ba9\u8fb9\u7f18\u88ab\u9057\u5fd8"),
        ("feature map", "\u7279\u5f81\u56fe\uff1a\u5377\u79ef\u7684\u8f93\u51fa"),
        ("pooling", "\u6c60\u5316\uff1a\u53d6\u6700\u5927\uff0c\u53d8\u5c0f\u4e0d\u53d8\u5f62"),
        ("ReLU", "\u8d1f\u6570\u5f52\u96f6\uff0c\u975e\u7ebf\u6027\u5728\u8fd9\u91cc"),
        ("receptive field", "\u611f\u53d7\u91ce\uff1a\u8d8a\u6df1\u770b\u5f97\u8d8a\u5bbd"),
        ("batch / channel", "\u6279\u6b21\u4e0e\u901a\u9053"),
        ("backbone", "\u9aa8\u5e72\u7f51\u7edc\uff1a\u7279\u5f81\u63d0\u53d6\u90e8\u5206"),
    ),
    "pane_ai_attention": (
        ("query / key / value", "Q\u3001K\u3001V\uff1a\u95ee\u3001\u88ab\u6bd4\u3001\u5185\u5bb9"),
        ("dot product", "\u70b9\u79ef\uff1a\u76f8\u4f3c\u5ea6"),
        ("softmax", "\u628a\u5206\u6570\u53d8\u6210\u6743\u91cd\uff0c\u548c\u4e3a 1"),
        ("temperature", "\u6e29\u5ea6\uff1a\u8c03\u6743\u91cd\u7684\u9510\u5ea6"),
        ("multi-head", "\u591a\u5934\uff1a\u51e0\u79cd\u5173\u7cfb\u540c\u65f6\u770b"),
        ("causal mask", "\u4e0d\u8ba9\u770b\u5230\u672a\u6765"),
        ("context length", "\u4e0a\u4e0b\u6587\u957f\u5ea6\uff1a\u80fd\u8bb0\u591a\u4e45"),
        ("self-attention", "\u81ea\u6ce8\u610f\u529b\uff1aQ\u3001K\u3001V \u540c\u6e90"),
        ("flash attention", "\u5206\u5757\u8ba1\u7b97\uff0c\u7701\u663e\u5b58"),
    ),
    "pane_ai_rl": (
        ("policy \u03c0", "\u7b56\u7565\uff1a\u770b\u5230\u72b6\u6001\u9009\u52a8\u4f5c"),
        ("rollout", "\u91c7\u6837\uff1a\u8ba9\u5b83\u81ea\u5df1\u8dd1\u51e0\u904d"),
        ("reward", "\u5956\u52b1\uff1a\u597d\u4e0d\u597d\u7684\u552f\u4e00\u4fe1\u53f7"),
        ("advantage", "\u4f18\u52bf\uff1a\u6bd4\u5e73\u5747\u597d\u591a\u5c11"),
        ("baseline", "\u57fa\u51c6\uff1a\u7ec4\u5185\u5e73\u5747\uff0c\u964d\u65b9\u5dee"),
        ("exploration", "\u63a2\u7d22\uff1a\u4e0d\u8bd5\u5c31\u4e0d\u77e5\u9053"),
        ("value function", "\u4ef7\u503c\u51fd\u6570\uff1a\u9884\u4f30\u80fd\u62ff\u591a\u5c11"),
        ("GRPO", "\u7ec4\u76f8\u5bf9\u7b56\u7565\u4f18\u5316\uff1a\u4e0d\u8981 critic"),
        ("PPO", "\u88c1\u526a\u66f4\u65b0\uff0c\u522b\u4e00\u6b65\u8de8\u592a\u5927"),
    ),
    "pane_ai_diffusion": (
        ("forward process", "\u52a0\u566a\uff1a\u4e00\u6b65\u4e00\u6b65\u6d82\u9ed1"),
        ("reverse process", "\u53bb\u566a\uff1a\u4e00\u6b65\u4e00\u6b65\u64e6\u51c0"),
        ("timestep t", "\u6b65\u6570\uff1a\u5468\u671f\u91cc\u7684\u4f4d\u7f6e"),
        ("noise schedule", "\u566a\u58f0\u8868\uff1a\u6bcf\u6b65\u52a0\u591a\u5c11"),
        ("U-Net", "\u9884\u6d4b\u566a\u58f0\u7684\u7f51\u7edc"),
        ("latent space", "\u6f5c\u7a7a\u95f4\uff1a\u5728\u538b\u7f29\u540e\u7684\u56fe\u4e0a\u505a"),
        ("classifier-free", "\u65e0\u5206\u7c7b\u5668\u5f15\u5bfc"),
        ("sampler", "\u91c7\u6837\u5668\uff1aDDIM\u3001Euler\u2026"),
        ("CFG scale", "\u63d0\u793a\u8bcd\u5f3a\u5ea6\uff1a\u542c\u8bdd\u5230\u4ec0\u4e48\u7a0b\u5ea6"),
    ),
})


def draw_ai(name: str, s, x0: int, y0: int, x1: int, y1: int,
            t: float, lt: float, dur: float, u: float, run: int = 1) -> bool:
    """Draw one of the four AI panes. False if `name` is not one of them."""
    spec = AI.get(name)
    if spec is None:
        return False
    title, fn = spec
    k = _Kit(s, x0, y0, x1, y1, title, run, len(AI), u)
    fn(k, lt, dur)
    # the vocabulary goes in whatever the drawing left, found by looking at the buffer rather than by
    # the drawing declaring a height - the same rule as `draw_course`, and the same reason
    detail = DETAIL.get(name, ())
    if detail:
        used = _last_ink(s, k.bx0, k.bx1, k.by0, k.by1)
        if used is not None and k.by1 - used >= 6:
            _terms(k, x0, used + 2, x1, y1, detail)
    return True
